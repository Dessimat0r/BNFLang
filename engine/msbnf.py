import sys
import re
import ast

BUILTIN_ALIASES = {
    "$DECL_HDR": r'/[0-9]+/:n "\x00" /[^\x00]*/:i "\x00" /(?:long\s+long|char|short|int|long|void)\s*/',
    "$NO_MUL":  r"/(?:\([^)]*\)|[^*\/%;\x00])+/",
    "$NO_ADD":  r"/(?:\([^)]*\)|[^+\-;\x00])+/",
    "$NO_COMP": r"/(?:\([^)]*\)|[^<>=!;\x00])+/",
    "$PAREN":   r"/[^)]*/",
    "$VAR_OFF": r'/[^@]+/:name "@" /[0-9]+/:off',
    "$VAR":     r"/[a-zA-Z_@0-9]+/",
    "$NUM":     r"/[0-9]+/",
}

import os

def expand_includes(text, base_dir="."):
    """Expand %include "filename.msbnf" directives inline."""
    lines = text.split("\n")
    out_lines = []
    for line in lines:
        m = re.match(r'^\s*%include\s+["\']([^"\']+)["\']\s*$', line.strip())
        if m:
            inc_path = os.path.join(base_dir, m.group(1))
            if os.path.exists(inc_path):
                with open(inc_path, "r", encoding="utf-8") as f:
                    inc_text = f.read()
                inc_text = expand_includes(inc_text, os.path.dirname(inc_path))
                out_lines.append(inc_text)
            else:
                raise FileNotFoundError(f"Include file not found: {inc_path}")
        else:
            out_lines.append(line)
    return "\n".join(out_lines)

def compile_msbnf(text, base_dir="."):
    """Compile Meta-SBNF (.msbnf) text into standard SBNF (.sbnf) text."""
    # 0. Expand %include directives
    text = expand_includes(text, base_dir)

    # 1. Parse and extract custom aliases ($MY_ALIAS = ...)
    text, custom_aliases = extract_custom_aliases(text)

    aliases = dict(BUILTIN_ALIASES)
    aliases.update(custom_aliases)

    # 2. Expand %for loops
    text = expand_for_loops(text)

    # 3. Desugar DECL(v, n, i, c, code) helpers
    text = desugar_decl_helpers(text)

    # 4. Desugar sequential let statements in action expressions (MUST run before \\+)
    text = desugar_let_actions(text)

    # 5. Desugar \+ (newline-concat operator)
    text = desugar_newline_concat(text)

    # 6. Expand pattern aliases ($NO_MUL:label -> regex:label)
    text = expand_aliases(text, aliases)

    return text.strip() + "\n"

def desugar_decl_helpers(text):
    """
    Desugar DECL(v, n, i, c, code) into standard declaration state-threading calls.
    DECL(v, n, i, c, code) =>
    LET(new_n, n + "8", LET(anno, v + "@" + n, LET(new_i, i + code, RULE("Decls", new_n + "\x00" + new_i + "\x00" + REPLACE(v, anno, c)))))
    """
    lines = text.split("\n")
    out_lines = []
    for line in lines:
        if "DECL(" in line:
            m = re.search(r'DECL\s*\(\s*([a-zA-Z_]\w*)\s*,\s*([a-zA-Z_]\w*)\s*,\s*([a-zA-Z_]\w*)\s*,\s*([a-zA-Z_]\w*)\s*,\s*(.*)\)\s*$', line)
            if m:
                v, n, i, c, code = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
                prefix = line[:m.start()]
                expanded = (
                    f'LET(new_n, {n} + "8", '
                    f'LET(anno, {v} + "@" + {n}, '
                    f'LET(new_i, {i} + {code}, '
                    f'RULE("Decls", new_n + "\\x00" + new_i + "\\x00" + REPLACE({v}, anno, {c})))))'
                )
                out_lines.append(prefix + expanded)
            else:
                out_lines.append(line)
        else:
            out_lines.append(line)
    return "\n".join(out_lines)

def desugar_let_actions(text):
    """
    Desugar sequential 'let var = val;' inside Meta-SBNF action blocks:
    => let a = expr1; let b = expr2; action_expr
    becomes:
    => LET(a, expr1, LET(b, expr2, action_expr))
    """
    lines = text.split("\n")
    out_lines = []

    for line in lines:
        if "=>" not in line:
            out_lines.append(line)
            continue

        arrow_pos = line.find("=>")
        prefix = line[:arrow_pos + 2]
        action = line[arrow_pos + 2:].strip()

        # Find all 'let var = val;' clauses in action
        let_pattern = re.compile(r'\blet\s+([a-zA-Z_]\w*)\s*=\s*(.+?);')
        matches = list(let_pattern.finditer(action))

        if not matches:
            out_lines.append(line)
            continue

        # Extract bindings in order
        bindings = []
        last_end = 0
        for m in matches:
            var_name = m.group(1)
            var_val = m.group(2).strip()
            bindings.append((var_name, var_val))
            last_end = m.end()

        final_expr = action[last_end:].strip()

        # Build nested LET calls from inside out
        res_expr = final_expr
        for var_name, var_val in reversed(bindings):
            res_expr = f"LET({var_name}, {var_val}, {res_expr})"

        out_lines.append(f"{prefix} {res_expr}")

    return "\n".join(out_lines)

def extract_custom_aliases(text):
    """Extract top-level $NAME = pattern definitions."""
    aliases = {}
    lines = text.split("\n")
    clean_lines = []
    for line in lines:
        m = re.match(r'^\$(\w+)\s*=\s*(.+)$', line.strip())
        if m:
            aliases[f"${m.group(1)}"] = m.group(2)
        else:
            clean_lines.append(line)
    return "\n".join(clean_lines), aliases

def expand_for_loops(text):
    """
    Expand %for loop blocks:
    %for var, val in [(v1, w1), (v2, w2)] { ... }
    %for var in range(...) { ... }
    """
    lines = text.split("\n")
    out_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r'^\s*%for\s+([a-zA-Z0-9_,\s]+)\s+in\s+(\[.*?\]|range\(.*?\))\s*\{', line.strip())
        if m:
            var_names = [v.strip() for v in m.group(1).split(",") if v.strip()]
            items_str = m.group(2)
            try:
                if items_str.startswith("range("):
                    items = list(eval(items_str))
                else:
                    items = ast.literal_eval(items_str)
            except Exception as e:
                raise ValueError(f"Failed to parse %for items on line {i+1}: {items_str}") from e

            # Collect body until matching '}'
            body_lines = []
            i += 1
            depth = 1
            while i < len(lines) and depth > 0:
                sline = lines[i].strip()
                if sline == '}':
                    depth -= 1
                    if depth == 0:
                        break
                elif sline.endswith('{') and not sline.startswith('//'):
                    depth += 1
                body_lines.append(lines[i])
                i += 1

            body_template = "\n".join(body_lines)

            # Expand template for each item
            expanded_blocks = []
            for item in items:
                block = body_template
                if len(var_names) == 1:
                    scope = {var_names[0]: item}
                else:
                    scope = dict(zip(var_names, item))

                def eval_expr(match):
                    expr_str = match.group(1)
                    try:
                        return str(eval(expr_str, scope))
                    except Exception:
                        return match.group(0)

                block = re.sub(r'\{([^{}]+)\}', eval_expr, block)
                expanded_blocks.append(block)

            out_lines.append("\n".join(expanded_blocks))
            i += 1
        else:
            out_lines.append(line)
            i += 1

    return "\n".join(out_lines)

def desugar_newline_concat(text):
    """Desugar \\+ into + "\\n" + """
    lines = text.split("\n")
    out_lines = []
    for line in lines:
        if "\\+" in line:
            # Replace \+ with + "\\n" +
            line = line.replace("\\+", '+ "\\n" +')
        out_lines.append(line)
    return "\n".join(out_lines)

def expand_aliases(text, aliases):
    """Replace $ALIAS:label or $ALIAS with their regex/pattern definitions."""
    sorted_aliases = sorted(aliases.keys(), key=len, reverse=True)

    for alias in sorted_aliases:
        replacement = aliases[alias]
        pattern_with_label = re.compile(re.escape(alias) + r':([a-zA-Z_]\w*)')
        text = pattern_with_label.sub(lambda m: f"{replacement}:{m.group(1)}", text)

        pattern_standalone = re.compile(re.escape(alias) + r'\b')
        text = pattern_standalone.sub(lambda m: replacement, text)

    return text

def main():
    if len(sys.argv) < 3:
        print("Usage: python -m engine.msbnf <input.msbnf> <output.sbnf>")
        sys.exit(1)

    inp_path = sys.argv[1]
    out_path = sys.argv[2]

    with open(inp_path, "r", encoding="utf-8") as f:
        msbnf_src = f.read()

    base_dir = os.path.dirname(os.path.abspath(inp_path))
    sbnf_compiled = compile_msbnf(msbnf_src, base_dir)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(sbnf_compiled)

    print(f"Successfully compiled {inp_path} -> {out_path}")

if __name__ == "__main__":
    main()
