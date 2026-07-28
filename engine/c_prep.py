import sys
import os
import re

INCLUDE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "include")

tmp_counter = 0

def get_tmp_var(expr, raw_lines):
    global tmp_counter
    expr = expr.strip()
    if re.match(r'^[a-zA-Z_]\w*$', expr):
        return expr
    tmp_counter += 1
    tname = f"_tmp{tmp_counter}"
    raw_lines.append(f"int {tname} = {expr};")
    return tname

def preprocess_sbnfc(src, processed_includes=None, typedefs=None, struct_defs=None, struct_vars=None):
    """
    Preprocess C source code into normalized statements for SBNF compilation.
    - Resolves #include <header.h> from include/ directory
    - Resolves typedef statements
    - Desugars struct declarations and member access (s.field -> s_field)
    - Desugars buffer/array declarations (char buf[64] -> 64-byte stack allocation)
    - Normalizes multi-argument printf(...) and sprintf(...)
    """
    if processed_includes is None:
        processed_includes = set()
    if typedefs is None:
        typedefs = {}
    if struct_defs is None:
        struct_defs = {}
    if struct_vars is None:
        struct_vars = {}

    lines = src.split("\n")
    raw_lines = []
    has_main = 'main' in src
    in_main = False
    brace_depth = 0
    current_struct = None

    for line in lines:
        sline = line.strip()
        if not sline:
            continue

        # 1. Handle #include <file.h> or "file.h"
        inc_m = re.match(r'^#include\s+[<"]([^>"]+)[>"]', sline)
        if inc_m:
            header_name = inc_m.group(1)
            if header_name not in processed_includes:
                processed_includes.add(header_name)
                header_path = os.path.join(INCLUDE_DIR, header_name)
                if os.path.exists(header_path):
                    with open(header_path, "r", encoding="utf-8") as f:
                        header_src = f.read()
                    header_out = preprocess_sbnfc(header_src, processed_includes, typedefs, struct_defs, struct_vars)
                    if header_out:
                        raw_lines.extend([l for l in header_out.split("\n") if l.strip()])
            continue

        # Strip preprocessor guards / directives
        if sline.startswith("#"):
            continue

        # 2. Handle typedef
        td_m = re.match(r'^typedef\s+(.+?)\s+([a-zA-Z_]\w*)\s*;', sline)
        if td_m:
            base_type = td_m.group(1).strip()
            alias = td_m.group(2).strip()
            typedefs[alias] = base_type
            continue

        # Apply typedef replacements
        for alias, base in typedefs.items():
            sline = re.sub(rf'\b{alias}\b', base, sline)

        # Desugar buffer / array declarations: char buf[64]; -> allocate 64 bytes via dummy vars
        arr_m = re.match(r'^(?:char|int|short|long|int\d+_t)\s+([a-zA-Z_]\w*)\[\d+\]\s*;', sline)
        if arr_m:
            arr_var = arr_m.group(1)
            for k in range(7):
                raw_lines.append(f"int {arr_var}_pad{k} = 0;")
            raw_lines.append(f"int {arr_var} = 0;")
            continue

        # 3. Handle struct definitions: struct Point { int x; int y; };
        st_def_m = re.match(r'^struct\s+([a-zA-Z_]\w*)\s*\{', sline)
        if st_def_m:
            current_struct = st_def_m.group(1)
            struct_defs[current_struct] = []
            continue

        if current_struct:
            if sline.startswith("};") or sline == "}":
                current_struct = None
                continue
            mem_m = re.match(r'^(?:[a-zA-Z_]\w*)\s+\*?\s*([a-zA-Z_]\w*)\s*;', sline)
            if mem_m:
                struct_defs[current_struct].append(mem_m.group(1))
                continue

        # Skip function prototypes (e.g. int printf(...);)
        if re.match(r'^(?:int|void|char|long|short)\s+[a-zA-Z_]\w*\s*\([^)]*\)\s*;', sline):
            continue

        # 4. Handle return statements in main
        if sline.startswith("return"):
            continue

        # 5. Handle main function declaration / outer braces if main() exists
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
                brace_depth += sline.count('{') - sline.count('}')

        # 6. Desugar struct instance declaration: struct Point p;
        st_inst_m = re.match(r'^struct\s+([a-zA-Z_]\w*)\s+([a-zA-Z_]\w*)\s*;', sline)
        if st_inst_m:
            st_type = st_inst_m.group(1)
            var_name = st_inst_m.group(2)
            struct_vars[var_name] = st_type
            if st_type in struct_defs:
                for mem in struct_defs[st_type]:
                    raw_lines.append(f"int {var_name}_{mem} = 0;")
            continue

        # 7. Desugar struct member access (var.member -> var_member)
        for var_name, st_type in struct_vars.items():
            if st_type in struct_defs:
                for mem in struct_defs[st_type]:
                    sline = re.sub(rf'\b{var_name}\.{mem}\b', f"{var_name}_{mem}", sline)

        # 8. Normalize multi-argument printf calls:
        m3 = re.match(r'^printf\s*\(\s*"[^"]*%d[^"]*%d[^"]*%d[^"]*"\s*,\s*(.*?)\s*,\s*(.*?)\s*,\s*(.*?)\s*\)\s*;', sline)
        if m3:
            v1 = get_tmp_var(m3.group(1), raw_lines)
            v2 = get_tmp_var(m3.group(2), raw_lines)
            v3 = get_tmp_var(m3.group(3), raw_lines)
            raw_lines.append(f"print3 {v1} {v2} {v3};")
            continue

        m2 = re.match(r'^printf\s*\(\s*"[^"]*%d[^"]*%d[^"]*"\s*,\s*(.*?)\s*,\s*(.*?)\s*\)\s*;', sline)
        if m2:
            v1 = get_tmp_var(m2.group(1), raw_lines)
            v2 = get_tmp_var(m2.group(2), raw_lines)
            raw_lines.append(f"print2 {v1} {v2};")
            continue

        m = re.match(r'^printf\s*\(\s*"%d\\n"\s*,\s*(.*?)\s*\)\s*;', sline)
        if m:
            raw_lines.append(f"print {m.group(1)};")
            continue

        m = re.match(r'^printf\s*\(\s*"%d "\s*,\s*(.*?)\s*\)\s*;', sline)
        if m:
            raw_lines.append(f"printn {m.group(1)};")
            continue

        m = re.match(r'^printf\s*\(\s*"\\n"\s*\)\s*;', sline)
        if m:
            raw_lines.append("println;")
            continue

        m = re.match(r'^printf\s*\(\s*"\s+"\s*\)\s*;', sline)
        if m:
            raw_lines.append("printsp;")
            continue

        m = re.match(r'^printf\s*\(\s*"%d"\s*,\s*(.*?)\s*\)\s*;', sline)
        if m:
            raw_lines.append(f"printn {m.group(1)};")
            continue

        # 9. Normalize multi-argument sprintf calls:
        sm3 = re.match(r'^sprintf\s*\(\s*([a-zA-Z_]\w*)\s*,\s*"[^"]*"\s*,\s*(.*?)\s*,\s*(.*?)\s*,\s*(.*?)\s*\)\s*;', sline)
        if sm3:
            buf = sm3.group(1)
            v1 = get_tmp_var(sm3.group(2), raw_lines)
            v2 = get_tmp_var(sm3.group(3), raw_lines)
            v3 = get_tmp_var(sm3.group(4), raw_lines)
            raw_lines.append(f"sprintf3 {buf} {v1} {v2} {v3};")
            continue

        sm2 = re.match(r'^sprintf\s*\(\s*([a-zA-Z_]\w*)\s*,\s*"[^"]*"\s*,\s*(.*?)\s*,\s*(.*?)\s*\)\s*;', sline)
        if sm2:
            buf = sm2.group(1)
            v1 = get_tmp_var(sm2.group(2), raw_lines)
            v2 = get_tmp_var(sm2.group(3), raw_lines)
            raw_lines.append(f"sprintf2 {buf} {v1} {v2};")
            continue

        m = re.match(r'^sprintf\s*\(\s*([a-zA-Z_]\w*)\s*,\s*"%d"\s*,\s*(.*?)\s*\)\s*;', sline)
        if m:
            raw_lines.append(f"sprintf {m.group(1)} {m.group(2)};")
            continue

        raw_lines.append(sline)

    # Separate declarations vs statements to hoist all decls to top
    decls = []
    stmts = []

    type_pattern = re.compile(r'^(?:long\s+long|char|short|int|long|void)\s+\*?\s*[a-zA-Z_]\w*')

    for l in raw_lines:
        if type_pattern.match(l.strip()):
            decl_m = re.match(r'^((?:long\s+long|char|short|int|long|void)\s+\*?\s*[a-zA-Z_]\w*)\s*=\s*(.+);$', l.strip())
            if decl_m:
                var_decl = decl_m.group(1)
                expr_val = decl_m.group(2)
                if re.match(r'^\d+$', expr_val) or expr_val.startswith('&'):
                    decls.append(l)
                else:
                    var_name = var_decl.split()[-1].lstrip('*')
                    decls.append(f"{var_decl} = 0;")
                    stmts.append(f"{var_name} = {expr_val};")
            else:
                decls.append(l)
        else:
            stmts.append(l)

    return "\n".join(decls + stmts)

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
