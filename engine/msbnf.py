import sys
import re
import ast

BUILTIN_ALIASES = {
    "$NO_MUL": r"/(?:[^*/(]+|\((?:[^()]+|\((?:[^()]+|\([^()]*\))*\))*\))+/",
    "$NO_ADD": r"/(?:[^+(\-]+|\((?:[^()]+|\((?:[^()]+|\([^()]*\))*\))*\))+/",
    "$NO_COMP": r"/(?:[^<]+|\((?:[^()]+|\((?:[^()]+|\([^()]*\))*\))*\))+/",
    "$PAREN":  r"/(?:[^()]+|\((?:[^()]+|\((?:[^()]+|\([^()]*\))*\))*\))*/",
    "$VAR":    r"/[a-zA-Z_@0-9]+/",
    "$NUM":    r"/[0-9]+/",
}

def compile_msbnf(text):
    """Compile Meta-SBNF (.msbnf) text into standard SBNF (.sbnf) text."""
    # 1. Parse and extract custom aliases ($MY_ALIAS = ...)
    text, custom_aliases = extract_custom_aliases(text)

    aliases = dict(BUILTIN_ALIASES)
    aliases.update(custom_aliases)

    # 2. Expand %for loops
    text = expand_for_loops(text)

    # 3. Expand pattern aliases ($NO_MUL:label -> regex:label)
    text = expand_aliases(text, aliases)

    # 4. Desugar sequential let statements in action expressions
    text = desugar_let_actions(text)

    return text.strip() + "\n"

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
    """
    Expand %for loop blocks with balanced brace matching.
    Syntax:
    %for val, shift in [("4","2"), ("8","3")] {
        | $NO_MUL:l "*" "{val}" => RULE("Expr", l) + "\nshl eax, {shift}"
    }
    """
    pos = 0
    out = []
    while pos < len(text):
        m = re.search(r'%for\s+([a-zA-Z_0-9,\s]+)\s+in\s+\[(.*?)\]\s*\{', text[pos:])
        if not m:
            out.append(text[pos:])
            break

        out.append(text[pos:pos+m.start()])
        vars_str = m.group(1)
        items_str = m.group(2)
        var_names = [v.strip() for v in vars_str.split(",") if v.strip()]

        try:
            items = ast.literal_eval("[" + items_str + "]")
        except Exception as e:
            raise ValueError(f"Failed to parse %for loop items: {items_str} - {e}")

        # Find matching closing brace }
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
                item = (item,)

            sub_body = body
            for var_name, var_val in zip(var_names, item):
                val_str = str(var_val)
                # Replace {var_name} placeholders
                sub_body = sub_body.replace("{" + var_name + "}", val_str)

            expanded_lines.append(sub_body)

        out.append("\n".join(expanded_lines))

    return "".join(out)

def expand_aliases(text, aliases):
    """Replace $ALIAS with its mapped regex/terminal pattern, keeping labels attached."""
    sorted_keys = sorted(aliases.keys(), key=len, reverse=True)

    for key in sorted_keys:
        val = aliases[key]
        pattern = re.compile(re.escape(key) + r'(:[a-zA-Z_]\w*)?')
        def replacer(m):
            lbl = m.group(1) if m.group(1) else ""
            return val + lbl
        text = pattern.sub(replacer, text)

    return text

def desugar_let_actions(text):
    """Desugar sequential `let x = val;` statements inside actions into LET(x, val, body)."""
    lines = text.split("\n")
    out_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if "=>" in line:
            parts = line.split("=>", 1)
            pat_part = parts[0]
            act_part = parts[1].strip()

            action_block = [act_part]
            j = i + 1
            while j < len(lines):
                sline = lines[j].strip()
                if not sline or sline.startswith("//"):
                    j += 1
                    continue
                if sline.startswith("|") or "::=" in sline:
                    break
                action_block.append(sline)
                j += 1

            full_act = " ".join(action_block).strip()
            if full_act.startswith("let "):
                desugared = transform_let_block(full_act)
                out_lines.append(pat_part + "=> " + desugared)
                i = j
                continue
            else:
                out_lines.append(line)
                i += 1
        else:
            out_lines.append(line)
            i += 1

    return "\n".join(out_lines)

def transform_let_block(text):
    """Transform sequential `let name = expr; ... body` into nested `LET(name, expr, body)`."""
    statements = []
    cur = text
    while cur.startswith("let "):
        m = re.match(r'^let\s+([a-zA-Z_]\w*)\s*=\s*(.*?);\s*(.*)', cur, re.DOTALL)
        if not m:
            break
        var_name = m.group(1)
        var_val = m.group(2).strip()
        cur = m.group(3).strip()
        statements.append((var_name, var_val))

    body = cur
    result = body
    for var_name, var_val in reversed(statements):
        result = f'LET({var_name}, {var_val}, {result})'
    return result

def main():
    if len(sys.argv) < 3:
        print("Usage: python -m engine.msbnf <input.msbnf> <output.sbnf>")
        sys.exit(1)

    inp_path = sys.argv[1]
    out_path = sys.argv[2]

    with open(inp_path, "r", encoding="utf-8") as f:
        src = f.read()

    compiled = compile_msbnf(src)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(compiled)

    print(f"Successfully compiled {inp_path} -> {out_path}")

if __name__ == "__main__":
    main()
