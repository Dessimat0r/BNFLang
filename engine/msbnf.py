import sys
import re
import ast

BUILTIN_ALIASES = {
    "$NO_MUL":  r"/(?:\((?:[^()]+|\((?:[^()]+|\([^()]*\))*\))*\)|[^*/%()])+/",
    "$NO_ADD":  r"/(?:\((?:[^()]+|\((?:[^()]+|\([^()]*\))*\))*\)|[^+(\-&|^~<>()])+/",
    "$NO_COMP": r"/(?:\((?:[^()]+|\((?:[^()]+|\([^()]*\))*\))*\)|[^<>=!()])+/",
    "$PAREN":   r"/(?:[^()]+|\((?:[^()]+|\((?:[^()]+|\([^()]*\))*\))*\))*/",
    "$VAR_OFF": r'/[^@]+/:name "@" /[0-9]+/:off',
    "$VAR":     r"/[a-zA-Z_@0-9]+/",
    "$NUM":     r"/[0-9]+/",
}

def compile_msbnf(text):
    """Compile Meta-SBNF (.msbnf) text into standard SBNF (.sbnf) text."""
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
                continue
        out_lines.append(line)

    return "\n".join(out_lines)

def desugar_newline_concat(text):
    """Replace `\\+` with `+ "\\n" +` in action expressions."""
    return re.sub(r'\\\+', r'+ "\\n" +', text)

def extract_custom_aliases(text):
    custom = {}
    out_lines = []
    for line in text.split("\n"):
        m = re.match(r'^\$([a-zA-Z_]\w*)\s*=\s*(.+)$', line.strip())
        if m:
            alias_name = "$" + m.group(1)
            alias_val = m.group(2).strip()
            custom[alias_name] = alias_val
        else:
            out_lines.append(line)
    return "\n".join(out_lines), custom

def expand_for_loops(text):
    """Expand %for loop blocks with balanced brace matching."""
    pos = 0
    out = []
    while pos < len(text):
        m = re.search(r'%for\s+([a-zA-Z_0-9,\s]+)\s+in\s+([^{\n]+)\s*\{', text[pos:])
        if not m:
            out.append(text[pos:])
            break

        out.append(text[pos:pos+m.start()])
        vars_str = m.group(1)
        expr_str = m.group(2).strip()
        var_names = [v.strip() for v in vars_str.split(",") if v.strip()]

        try:
            items = list(eval(expr_str, {"range": range, "list": list, "tuple": tuple}))
        except Exception as e:
            raise ValueError(f"Failed to parse %for loop expression: {expr_str} - {e}")

        start_body = pos + m.end()
        depth = 1
        i = start_body
        while i < len(text) and depth > 0:
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    break
            i += 1

        body = text[start_body:i].rstrip()
        pos = i + 1

        expanded_lines = []
        for item in items:
            if not isinstance(item, (tuple, list)):
                item = [item]
            if len(item) != len(var_names):
                raise ValueError(f"For loop variable count mismatch: expected {len(var_names)} vars, got {len(item)} in item {item}")

            item_body = body
            scope = dict(zip(var_names, item))

            # Replace {expression} in body
            def replacer(match):
                expr = match.group(1).strip()
                try:
                    return str(eval(expr, {}, scope))
                except Exception:
                    return str(scope.get(expr, match.group(0)))

            item_body = re.sub(r'\{([^}]+)\}', replacer, item_body)
            expanded_lines.append(item_body)

        out.append("\n".join(expanded_lines))

    return "".join(out)

def expand_aliases(text, aliases):
    """Expand pattern aliases in rules (e.g. $NO_MUL:label -> regex:label)."""
    for name, pattern in sorted(aliases.items(), key=lambda x: -len(x[0])):
        text = text.replace(name, pattern)
    return text

def desugar_let_actions(text):
    """Desugar sequential `let x = e; body` inside action expressions."""
    lines = text.split("\n")
    out_lines = []

    for line in lines:
        if "=>" in line and "let " in line:
            m = re.search(r'(=>\s*)(.+)$', line)
            if m:
                prefix = line[:m.start()]
                arrow = m.group(1)
                action_str = m.group(2).strip()

                desugared = parse_and_desugar_lets(action_str)
                out_lines.append(prefix + arrow + desugared)
                continue

        out_lines.append(line)

    return "\n".join(out_lines)

def parse_and_desugar_lets(action_str):
    """
    Transform:
    let val_asm = RULE("Expr", val); let buf_off = RULE("OffOf", buf + "\x00" + val); body...
    into nested LET calls:
    LET(val_asm, RULE("Expr", val), LET(buf_off, RULE("OffOf", buf + "\x00" + val), body...))
    """
    lets = []
    rem = action_str

    while True:
        m = re.match(r'^\s*let\s+([a-zA-Z_]\w*)\s*=\s*([^;]+?)\s*;\s*', rem)
        if not m:
            break
        var_name = m.group(1)
        expr_val = m.group(2)
        lets.append((var_name, expr_val))
        rem = rem[m.end():]

    if not lets:
        return action_str

    body = rem.strip()
    result = body

    for var_name, expr_val in reversed(lets):
        result = f'LET({var_name}, {expr_val}, {result})'

    return result

def main():
    if len(sys.argv) < 3:
        print("Usage: python -m engine.msbnf <input.msbnf> <output.sbnf>")
        sys.exit(1)

    inp_path = sys.argv[1]
    out_path = sys.argv[2]

    with open(inp_path, "r", encoding="utf-8") as f:
        text = f.read()

    compiled = compile_msbnf(text)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(compiled)

    print(f"Successfully compiled {inp_path} -> {out_path}")

if __name__ == "__main__":
    main()
