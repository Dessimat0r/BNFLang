import sys
import re

def preprocess_sbnfc(src):
    """
    Preprocess .c source code into normalized statements for SBNF compilation.
    - Strips #include directives
    - Strips main() function wrappers (int main() { ... return 0; })
    - Normalizes printf(...) calls:
        printf("%d\n", val); -> print val;
        printf("%d ", val);  -> printn val;
        printf("\n");        -> println;
        printf(" ");         -> printsp;
    - Normalizes sprintf(buf, "%d", val); -> sprintf buf val;
    """
    has_main = 'main' in src
    lines = src.split("\n")
    out = []
    in_main = False
    brace_depth = 0

    for line in lines:
        sline = line.strip()
        # 1. Strip #include
        if sline.startswith("#include"):
            continue

        # 2. Strip return statements in main
        if sline.startswith("return"):
            continue

        # 3. Strip main function declaration / outer braces if main() exists
        if has_main:
            if re.match(r'^int\s+main\s*\([^)]*\)\s*\{?', sline):
                in_main = True
                brace_depth += sline.count('{') - sline.count('}')
                continue
            if in_main:
                if sline == '}' and brace_depth == 1:
                    brace_depth = 0
                    in_main = False
                    continue
                # Update brace depth for inner blocks
                brace_depth += sline.count('{') - sline.count('}')

        # 4. Normalize printf calls
        m = re.match(r'^printf\s*\(\s*"%d\\n"\s*,\s*(.*?)\s*\)\s*;', sline)
        if m:
            out.append(f"print {m.group(1)};")
            continue

        m = re.match(r'^printf\s*\(\s*"%d "\s*,\s*(.*?)\s*\)\s*;', sline)
        if m:
            out.append(f"printn {m.group(1)};")
            continue

        m = re.match(r'^printf\s*\(\s*"\\n"\s*\)\s*;', sline)
        if m:
            out.append("println;")
            continue

        m = re.match(r'^printf\s*\(\s*" "\s*\)\s*;', sline)
        if m:
            out.append("printsp;")
            continue

        m = re.match(r'^printf\s*\(\s*"%d"\s*,\s*(.*?)\s*\)\s*;', sline)
        if m:
            out.append(f"printn {m.group(1)};")
            continue

        # 5. Normalize sprintf calls
        m = re.match(r'^sprintf\s*\(\s*([a-zA-Z_]\w*)\s*,\s*"%d"\s*,\s*(.*?)\s*\)\s*;', sline)
        if m:
            out.append(f"sprintf {m.group(1)} {m.group(2)};")
            continue

        out.append(line)

    return "\n".join(out)

def main():
    if len(sys.argv) < 3:
        print("Usage: python -m engine.c_prep <input.c> <output.c>")
        sys.exit(1)

    inp_path = sys.argv[1]
    out_path = sys.argv[2]

    with open(inp_path, "r", encoding="utf-8") as f:
        src = f.read()

    preprocessed = preprocess_sbnfc(src)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(preprocessed)

    print(f"Successfully preprocessed {inp_path} -> {out_path}")

if __name__ == "__main__":
    main()
