import sys
import re

def preprocess_sbnfc(src):
    """
    Preprocess .sbnfc C-like source code into normalized statements for SBNF compilation.
    - Strips #include directives
    - Strips main() function wrappers (int main() { ... })
    - Normalizes printf(...) calls:
        printf("%d\n", val); -> print val;
        printf("%d ", val);  -> printn val;
        printf("\n");        -> println;
        printf(" ");         -> printsp;
    - Normalizes sprintf(buf, "%d", val); -> sprintf buf val;
    """
    lines = src.split("\n")
    out = []

    for line in lines:
        sline = line.strip()
        # 1. Strip #include
        if sline.startswith("#include"):
            continue

        # 2. Strip main function declaration / outer braces
        if re.match(r'^int\s+main\s*\([^)]*\)\s*\{?', sline):
            continue
        if sline == '}' and len(out) > 0 and not out[-1].endswith('}'):
            # If line is just closing brace of main
            continue

        # 3. Normalize printf calls
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

        # 4. Normalize sprintf calls
        m = re.match(r'^sprintf\s*\(\s*([a-zA-Z_]\w*)\s*,\s*"%d"\s*,\s*(.*?)\s*\)\s*;', sline)
        if m:
            out.append(f"sprintf {m.group(1)} {m.group(2)};")
            continue

        out.append(line)

    return "\n".join(out)

def main():
    if len(sys.argv) < 3:
        print("Usage: python -m engine.c_prep <input.sbnfc> <output.c>")
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
