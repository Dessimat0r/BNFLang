import sys
import os
import re

INCLUDE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "include")

tmp_counter = 0
aptr_cnt = 0

def get_tmp_var(expr, raw_lines):
    global tmp_counter
    expr = expr.strip()
    if re.match(r'^[a-zA-Z_]\w*$', expr):
        return expr
    tmp_counter += 1
    tname = f"_tmp{tmp_counter}"
    raw_lines.append(f"int {tname} = {expr};")
    return tname

def desugar_high_level_control_flow(src):
    """
    Desugar C control flow constructs, array subscripting, and operator syntaxes:
    - Array Subscripting: arr[i] -> int *_aptrN = &arr + (i) * 8; *_aptrN
    - Compound assignment: x += y; -> x = x + (y);
    - Inc/dec: x++; -> x = x + 1;
    - Ternary: [int] x = cond ? e1 : e2; -> if-else assignment
    - for (init; cond; incr) { body } -> init; while (cond) { body incr; }
    - else if (cond) -> else { if (cond) ... } }
    - switch (expr) { case V1: s1; break; ... default: s3; } -> if-else chain
    - do { body } while (cond); -> do_while (cond) { body }
    """
    global aptr_cnt
    type_decl_pattern = re.compile(r'^(?:int|char|short|long|void)\s+[a-zA-Z_]\w*\[\d+\]\s*;')
    lines = src.split('\n')
    out_lines = []
    for line in lines:
        sline = line.strip()
        if type_decl_pattern.match(sline):
            out_lines.append(line)
        else:
            matches = list(re.finditer(r'\b([a-zA-Z_]\w*)\s*\[\s*([^\[\]]+)\s*\]', sline))
            if not matches:
                out_lines.append(line)
                continue
            
            newline = sline
            for m in reversed(matches):
                arr_var = m.group(1)
                idx_expr = m.group(2).strip()
                aptr_cnt += 1
                aptr_name = f"_aptr{aptr_cnt}"
                out_lines.append(f"int *{aptr_name} = &{arr_var} + ({idx_expr}) * 8;")
                newline = newline[:m.start()] + f"*{aptr_name}" + newline[m.end():]
            out_lines.append(newline)
    src = '\n'.join(out_lines)

    # 1. Desugar Ternary Operator: [type] target = cond ? e1 : e2;
    pos = 0
    while True:
        m = re.search(r'((?:(?:int|char|short|long)\s+)?([a-zA-Z_]\w*))\s*=\s*([^;?]+)\?\s*([^;:]+):\s*([^;]+);', src[pos:])
        if not m:
            break
        start_idx = pos + m.start()
        end_idx = pos + m.end()
        full_lhs = m.group(1).strip()
        target = m.group(2).strip()
        cond = m.group(3).strip()
        e1 = m.group(4).strip()
        e2 = m.group(5).strip()

        is_decl = full_lhs != target
        decl_line = f"{full_lhs} = 0;\n" if is_decl else ""
        replacement = f"\n{decl_line}if ({cond}) {{\n{target} = {e1};\n}} else {{\n{target} = {e2};\n}}\n"
        src = src[:start_idx] + replacement + src[end_idx:]
        pos = start_idx + len(replacement)

    # 2. Desugar for loops: for (init; cond; incr) { ... }
    pos = 0
    while True:
        m = re.search(r'\bfor\s*\(\s*([^;]*);\s*([^;]*);\s*([^)]*)\)\s*\{', src[pos:])
        if not m:
            break
        start_idx = pos + m.start()
        open_brace = pos + m.end() - 1
        depth = 1
        i = open_brace + 1
        while i < len(src) and depth > 0:
            if src[i] == '{':
                depth += 1
            elif src[i] == '}':
                depth -= 1
            i += 1
        body = src[open_brace+1:i-1].strip()
        init = m.group(1).strip()
        cond = m.group(2).strip()
        incr = m.group(3).strip()

        incr = re.sub(r'([a-zA-Z_]\w*)\s*\+\+', r'\1 = \1 + 1', incr)
        incr = re.sub(r'\+\+\s*([a-zA-Z_]\w*)', r'\1 = \1 + 1', incr)
        incr = re.sub(r'([a-zA-Z_]\w*)\s*--', r'\1 = \1 - 1', incr)
        incr = re.sub(r'--\s*([a-zA-Z_]\w*)', r'\1 = \1 - 1', incr)

        if init and not init.endswith(';'):
            init += ';'
        if incr and not incr.endswith(';'):
            incr += ';'
        replacement = f"\n{init}\nwhile ({cond}) {{\n{body}\n{incr}\n}}\n"
        src = src[:start_idx] + replacement + src[i:]
        pos = start_idx + len(replacement)

    # 3. Desugar do { body } while (cond);
    pos = 0
    while True:
        m = re.search(r'\bdo\s*\{', src[pos:])
        if not m:
            break
        start_idx = pos + m.start()
        open_brace = pos + m.end() - 1
        depth = 1
        i = open_brace + 1
        while i < len(src) and depth > 0:
            if src[i] == '{':
                depth += 1
            elif src[i] == '}':
                depth -= 1
            i += 1
        body = src[open_brace+1:i-1].strip()
        wm = re.match(r'^\s*while\s*\(\s*([^)]+)\s*\)\s*;', src[i:])
        if wm:
            cond = wm.group(1).strip()
            end_idx = i + wm.end()
            replacement = f"\ndo_while ({cond}) {{\n{body}\n}}\n"
            src = src[:start_idx] + replacement + src[end_idx:]
            pos = start_idx + len(replacement)
        else:
            pos = i

    # 4. Desugar else if chains
    pos = 0
    while True:
        m = re.search(r'\bif\s*\(\s*([^)]+)\s*\)\s*\{', src[pos:])
        if not m:
            break
        start_idx = pos + m.start()
        open_brace = pos + m.end() - 1
        depth = 1
        i = open_brace + 1
        while i < len(src) and depth > 0:
            if src[i] == '{':
                depth += 1
            elif src[i] == '}':
                depth -= 1
            i += 1
        
        rem = src[i:]
        elseif_m = re.match(r'^\s*else\s+if\s*\(\s*([^)]+)\s*\)\s*\{', rem)
        if elseif_m:
            cur = i
            else_count = 0
            while cur < len(src):
                m_else = re.match(r'^\s*else\s+if\s*\(\s*([^)]+)\s*\)\s*\{', src[cur:])
                if m_else:
                    else_count += 1
                    ob = cur + m_else.end() - 1
                    d = 1
                    j = ob + 1
                    while j < len(src) and d > 0:
                        if src[j] == '{': d += 1
                        elif src[j] == '}': d -= 1
                        j += 1
                    cur = j
                    continue
                m_final_else = re.match(r'^\s*else\s*\{', src[cur:])
                if m_final_else:
                    ob = cur + m_final_else.end() - 1
                    d = 1
                    j = ob + 1
                    while j < len(src) and d > 0:
                        if src[j] == '{': d += 1
                        elif src[j] == '}': d -= 1
                        j += 1
                    cur = j
                    break
                break
            
            chain_str = src[i:cur]
            chain_trans = re.sub(r'\belse\s+if\s*\(', r'else {\nif (', chain_str) + ("\n}" * else_count)
            src = src[:i] + chain_trans + src[cur:]
            pos = i + len(chain_trans)
        else:
            pos = i

    # 5. Desugar switch (expr) { case V1: s1; break; case V2: s2; break; default: s3; }
    pos = 0
    while True:
        m = re.search(r'\bswitch\s*\(\s*([^)]+)\s*\)\s*\{', src[pos:])
        if not m:
            break
        start_idx = pos + m.start()
        open_brace = pos + m.end() - 1
        depth = 1
        i = open_brace + 1
        while i < len(src) and depth > 0:
            if src[i] == '{':
                depth += 1
            elif src[i] == '}':
                depth -= 1
            i += 1
        sw_expr = m.group(1).strip()
        sw_body = src[open_brace+1:i-1]

        case_blocks = re.findall(r'case\s+([^:]+):\s*(.*?)(?=case\s+|default\s*:|$)', sw_body, re.DOTALL)
        def_block = re.search(r'default\s*:\s*(.*)$', sw_body, re.DOTALL)

        global tmp_counter
        tmp_counter += 1
        sw_var = f"_sw{tmp_counter}"

        if_chain = [f"int {sw_var} = {sw_expr};"]
        first = True
        else_count = 0
        for cval, cstmts in case_blocks:
            cval = cval.strip()
            cstmts = cstmts.replace("break;", "").strip()
            if first:
                if_chain.append(f"if ({sw_var} == {cval}) {{\n{cstmts}\n}}")
                first = False
            else:
                if_chain.append(f"else {{\nif ({sw_var} == {cval}) {{\n{cstmts}\n}}")
                else_count += 1
        if def_block:
            def_stmts = def_block.group(1).replace("break;", "").strip()
            if_chain.append(f"else {{\n{def_stmts}\n}}")
            else_count += 1

        if else_count > 0:
            if_chain.append("}" * (else_count - 1 if def_block else else_count))

        replacement = "\n" + "\n".join(if_chain) + "\n"
        src = src[:start_idx] + replacement + src[i:]
        pos = start_idx + len(replacement)

    # 6. Desugar Compound Assignments (+=, -=, *=, /=, %=)
    src = re.sub(r'([a-zA-Z_]\w*)\s*\+=\s*([^;]+);', r'\1 = \1 + (\2);', src)
    src = re.sub(r'([a-zA-Z_]\w*)\s*-=\s*([^;]+);', r'\1 = \1 - (\2);', src)
    src = re.sub(r'([a-zA-Z_]\w*)\s*\*=\s*([^;]+);', r'\1 = \1 * (\2);', src)
    src = re.sub(r'([a-zA-Z_]\w*)\s*/=\s*([^;]+);', r'\1 = \1 / (\2);', src)
    src = re.sub(r'([a-zA-Z_]\w*)\s*%=\s*([^;]+);', r'\1 = \1 % (\2);', src)

    # 7. Desugar Increment / Decrement (x++; ++x; x--; --x;)
    src = re.sub(r'([a-zA-Z_]\w*)\s*\+\+;', r'\1 = \1 + 1;', src)
    src = re.sub(r'\+\+\s*([a-zA-Z_]\w*);', r'\1 = \1 + 1;', src)
    src = re.sub(r'([a-zA-Z_]\w*)\s*--;', r'\1 = \1 - 1;', src)
    src = re.sub(r'--\s*([a-zA-Z_]\w*);', r'\1 = \1 - 1;', src)

    # 8. Desugar Logical Operators (&&, ||, !)
    src = src.replace("&&", "*")
    src = src.replace("||", "+")
    src = re.sub(r'(?<![a-zA-Z0-9_!=])!\s*\(([^)]+)\)', r'((\1) == 0)', src)

    return src

def desugar_function_calls(src, known_funcs):
    """
    Desugar user function calls into normalized call primitives (call0, call1, call2, call3).
    Extracts nested function calls to temporary variables for clean stack frame preservation.
    """
    if not known_funcs:
        return src

    func_pattern = rf'\b({"|".join(known_funcs)})\s*\(([^()]*)\)'

    lines = src.split("\n")
    out_lines = []
    global tmp_counter

    for line in lines:
        sline = line.strip()
        if not sline or sline.startswith("#") or sline.startswith("//"):
            out_lines.append(line)
            continue

        # Check if line contains user function call
        matches = list(re.finditer(func_pattern, sline))
        if not matches:
            out_lines.append(line)
            continue

        # Helper to format args and hoist complex expressions
        def process_args(args_str):
            global tmp_counter
            raw_args = [a.strip() for a in args_str.split(',') if a.strip()]
            clean_args = []
            for a in raw_args:
                if re.match(r'^[a-zA-Z_]\w*$|^[0-9]+$', a):
                    clean_args.append(a)
                else:
                    tmp_counter += 1
                    tvar = f"_arg{tmp_counter}"
                    out_lines.append(f"int {tvar} = {a};")
                    clean_args.append(tvar)
            return len(clean_args), " ".join(clean_args)

        # If it's a standalone assignment: [type] var = fname(args);
        m_assign = re.match(r'^(?:(?:int|char|short|long|void)\s+\*?\s*)?([a-zA-Z_]\w*)\s*=\s*([a-zA-Z_]\w*)\s*\(([^()]*)\)\s*;$', sline)
        if m_assign and m_assign.group(2) in known_funcs:
            var_lhs = line[:line.find('=')].strip()
            fname = m_assign.group(2)
            nargs, args_formatted = process_args(m_assign.group(3).strip())
            if nargs == 0:
                out_lines.append(f"{var_lhs} = call0 {fname};")
            else:
                out_lines.append(f"{var_lhs} = call{nargs} {fname} {args_formatted};")
            continue

        # If it's a standalone call statement: fname(args);
        m_stmt = re.match(r'^([a-zA-Z_]\w*)\s*\(([^()]*)\)\s*;$', sline)
        if m_stmt and m_stmt.group(1) in known_funcs:
            fname = m_stmt.group(1)
            nargs, args_formatted = process_args(m_stmt.group(2).strip())
            if nargs == 0:
                out_lines.append(f"call0 {fname};")
            else:
                out_lines.append(f"call{nargs} {fname} {args_formatted};")
            continue

        # Otherwise: nested function calls inside expressions
        # Extract each call to a temporary variable before the line
        newline_expr = sline
        for m in reversed(matches):
            fname = m.group(1)
            nargs, args_formatted = process_args(m.group(2).strip())

            tmp_counter += 1
            tmp_var = f"_fn{tmp_counter}"

            if nargs == 0:
                out_lines.append(f"int {tmp_var} = call0 {fname};")
            else:
                out_lines.append(f"int {tmp_var} = call{nargs} {fname} {args_formatted};")

            newline_expr = newline_expr[:m.start()] + tmp_var + newline_expr[m.end():]

        out_lines.append(newline_expr)

    return "\n".join(out_lines)

def preprocess_sbnfc(src, processed_includes=None, typedefs=None, struct_defs=None, struct_vars=None):
    """
    Preprocess C source code into normalized statements for SBNF compilation.
    Supports user function definitions, recursive functions, ABI register calling conventions,
    global variables, and static local variables.
    """
    is_root = (processed_includes is None)
    if processed_includes is None:
        processed_includes = set()
    if typedefs is None:
        typedefs = {}
    if struct_defs is None:
        struct_defs = {}
    if struct_vars is None:
        struct_vars = {}

    clean_src = desugar_high_level_control_flow(src)

    # Extract global variables outside function bodies (root level only)
    global_vars = {}
    global_decls_sbnf = []

    if is_root:
        g_decl_pattern = re.compile(r'^(?:int|char|short|long|void)\s+([a-zA-Z_]\w*)\s*(?:=\s*(.+?))?\s*;$', re.MULTILINE)
        
        func_spans = []
        pos = 0
        while True:
            m = re.search(r'\b(int|void|char|long|short)\s+([a-zA-Z_]\w*)\s*\(([^)]*)\)\s*\{', clean_src[pos:])
            if not m:
                break
            start_brace = pos + m.end() - 1
            depth = 1
            i = start_brace + 1
            while i < len(clean_src) and depth > 0:
                if clean_src[i] == '{': depth += 1
                elif clean_src[i] == '}': depth -= 1
                i += 1
            func_spans.append((pos + m.start(), i))
            pos = i

        for m in g_decl_pattern.finditer(clean_src):
            m_start = m.start()
            if not any(fstart <= m_start < fend for fstart, fend in func_spans):
                gname = m.group(1)
                gval = m.group(2).strip() if m.group(2) else "0"
                global_vars[gname] = gval
                global_decls_sbnf.append(f"GLOBAL G_{gname} {gval}")

    # Extract all top-level user function definitions
    user_funcs = []
    pos = 0
    while True:
        m = re.search(r'\b(int|void|char|long|short)\s+([a-zA-Z_]\w*)\s*\(([^)]*)\)\s*\{', clean_src[pos:])
        if not m:
            break
        ret_type = m.group(1)
        fname = m.group(2)
        params_raw = m.group(3).strip()
        start_brace = pos + m.end() - 1
        depth = 1
        i = start_brace + 1
        while i < len(clean_src) and depth > 0:
            if clean_src[i] == '{': depth += 1
            elif clean_src[i] == '}': depth -= 1
            i += 1
        body = clean_src[start_brace+1:i-1]

        # Extract static local variables inside this function
        static_m = re.findall(r'\bstatic\s+(?:int|char|short|long|void)\s+([a-zA-Z_]\w*)\s*(?:=\s*(.+?))?\s*;', body)
        for sname, sval in static_m:
            sval = sval.strip() if sval else "0"
            mangled_gname = f"static_{fname}_{sname}"
            global_decls_sbnf.append(f"GLOBAL G_{mangled_gname} {sval}")
            body = re.sub(rf'\bstatic\s+(?:int|char|short|long|void)\s+{sname}\s*(?:=\s*.+?)?\s*;', '', body)
            body = re.sub(rf'(?<!G_)\b{sname}\b', f"G_{mangled_gname}", body)

        # Replace global variable references in body with G_ prefix
        for gname in global_vars:
            if not gname.startswith("static_"):
                body = re.sub(rf'(?<!G_)\b{gname}\b', f"G_{gname}", body)

        user_funcs.append((ret_type, fname, params_raw, body))
        pos = i

    known_func_names = [f[1] for f in user_funcs if f[1] != 'main']

    # If user functions are defined, preprocess each function body
    if len(user_funcs) > 1 or (len(user_funcs) == 1 and user_funcs[0][1] != 'main'):
        compiled_blocks = list(global_decls_sbnf)
        for ret_type, fname, params_raw, body in user_funcs:
            body_desugared = desugar_function_calls(body, known_func_names)

            params = [p.strip() for p in params_raw.split(',') if p.strip()]
            param_decls = []
            param_binds = []
            for idx, p in enumerate(params):
                p_parts = p.split()
                p_name = p_parts[-1].lstrip('*')
                p_type = p_parts[0] if len(p_parts) > 1 else "int"
                param_decls.append(f"{p_type} {p_name} = 0;")
                param_binds.append(f"{p_name} = _param{idx + 1};")

            prep_body = preprocess_sbnfc(body_desugared, processed_includes, typedefs, struct_defs, struct_vars)
            
            if fname == 'main':
                compiled_blocks.append(prep_body)
            else:
                body_lines = [l for l in prep_body.split('\n') if l.strip()]
                type_pattern = re.compile(r'^(?:long\s+long|char|short|int|long|void)\s+\*?\s*[a-zA-Z_]\w*')
                body_decls = [l for l in body_lines if type_pattern.match(l.strip())]
                body_stmts = [l for l in body_lines if not type_pattern.match(l.strip())]

                all_decls = param_decls + body_decls
                all_stmts = param_binds + body_stmts

                compiled_blocks.append(f"FUNC _{fname}\n" + "\n".join(all_decls + all_stmts))

        return "\x00".join(compiled_blocks)

    # Standard single function / main compilation path
    lines = clean_src.split("\n")
    raw_lines = []
    has_main = 'main' in clean_src
    in_main = False
    brace_depth = 0
    current_struct = None

    for line in lines:
        sline = line.strip()
        if not sline:
            continue

        # Handle #include <file.h> or "file.h"
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

        if sline.startswith("#"):
            continue

        # Handle typedef
        td_m = re.match(r'^typedef\s+(.+?)\s+([a-zA-Z_]\w*)\s*;', sline)
        if td_m:
            base_type = td_m.group(1).strip()
            alias = td_m.group(2).strip()
            typedefs[alias] = base_type
            continue

        for alias, base in typedefs.items():
            sline = re.sub(rf'\b{alias}\b', base, sline)

        # Desugar buffer declarations
        arr_m = re.match(r'^(char|int|short|long|int\d+_t)\s+([a-zA-Z_]\w*)\[(\d+)\]\s*;', sline)
        if arr_m:
            elem_type = arr_m.group(1)
            arr_var = arr_m.group(2)
            arr_size = int(arr_m.group(3))
            num_slots = (arr_size + 7) // 8 if elem_type == 'char' else arr_size
            for k in range(num_slots):
                raw_lines.append(f"int {arr_var}_pad{k} = 0;")
            raw_lines.append(f"int {arr_var} = 0;")
            continue

        # Handle struct definitions
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

        if re.match(r'^(?:int|void|char|long|short)\s+[a-zA-Z_]\w*\s*\([^)]*\)\s*;', sline):
            continue

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

        st_inst_m = re.match(r'^struct\s+([a-zA-Z_]\w*)\s+([a-zA-Z_]\w*)\s*;', sline)
        if st_inst_m:
            st_type = st_inst_m.group(1)
            var_name = st_inst_m.group(2)
            struct_vars[var_name] = st_type
            if st_type in struct_defs:
                for mem in struct_defs[st_type]:
                    raw_lines.append(f"int {var_name}_{mem} = 0;")
            continue

        for var_name, st_type in struct_vars.items():
            if st_type in struct_defs:
                for mem in struct_defs[st_type]:
                    sline = re.sub(rf'\b{var_name}\.{mem}\b', f"{var_name}_{mem}", sline)

        # Normalize printf calls into CALL printf, fmt, args...
        m_pf = re.match(r'^printf\s*\(\s*"([^"]*)"\s*(?:,\s*(.*))?\)\s*;', sline)
        if m_pf:
            fmt = m_pf.group(1)
            args_str = m_pf.group(2) or ""
            fmt_lbl = "fmt"
            if fmt == "%d\\n":
                fmt_lbl = "fmt"
            elif fmt == "%d ":
                fmt_lbl = "fmtn"
            elif fmt == "\\n":
                fmt_lbl = "fmt_nl"
            elif fmt == " ":
                fmt_lbl = "fmt_sp"
            elif "%d %d %d\\n" in fmt:
                fmt_lbl = "fmt_3d"
            elif "%d %d\\n" in fmt:
                fmt_lbl = "fmt_2d"

            if args_str:
                args = [get_tmp_var(a.strip(), raw_lines) for a in args_str.split(",") if a.strip()]
                raw_lines.append(f"CALL printf {fmt_lbl} " + " ".join(args) + ";")
            else:
                raw_lines.append(f"CALL printf {fmt_lbl};")
            continue

        # Normalize sprintf calls into CALL sprintf, buf, fmt, args...
        m_spf = re.match(r'^sprintf\s*\(\s*([a-zA-Z_]\w*)\s*,\s*"([^"]*)"\s*(?:,\s*(.*))?\)\s*;', sline)
        if m_spf:
            buf = m_spf.group(1)
            fmt = m_spf.group(2)
            args_str = m_spf.group(3) or ""
            fmt_lbl = "fmt"
            if "%d %d %d" in fmt:
                fmt_lbl = "fmt_3d"
            elif "%d %d" in fmt:
                fmt_lbl = "fmt_2d"

            if args_str:
                args = [get_tmp_var(a.strip(), raw_lines) for a in args_str.split(",") if a.strip()]
                raw_lines.append(f"CALL sprintf {buf} {fmt_lbl} " + " ".join(args) + ";")
            else:
                raw_lines.append(f"CALL sprintf {buf} {fmt_lbl};")
            continue

        # Normalize legacy print statements
        m_p3 = re.match(r'^print3\s+(.*?)\s+(.*?)\s+(.*?)\s*;', sline)
        if m_p3:
            raw_lines.append(f"CALL printf fmt_3d {m_p3.group(1)} {m_p3.group(2)} {m_p3.group(3)};")
            continue
        m_p2 = re.match(r'^print2\s+(.*?)\s+(.*?)\s*;', sline)
        if m_p2:
            raw_lines.append(f"CALL printf fmt_2d {m_p2.group(1)} {m_p2.group(2)};")
            continue
        m_pr = re.match(r'^print\s+(.*?)\s*;', sline)
        if m_pr:
            raw_lines.append(f"CALL printf fmt {m_pr.group(1)};")
            continue
        m_prn = re.match(r'^printn\s+(.*?)\s*;', sline)
        if m_prn:
            raw_lines.append(f"CALL printf fmtn {m_prn.group(1)};")
            continue
        if sline == "println;":
            raw_lines.append("CALL printf fmt_nl;")
            continue
        if sline == "printsp;":
            raw_lines.append("CALL printf fmt_sp;")
            continue

        # Normalize legacy sprintf statements
        m_sp3 = re.match(r'^sprintf3\s+([a-zA-Z_]\w*)\s+(.*?)\s+(.*?)\s+(.*?)\s*;', sline)
        if m_sp3:
            raw_lines.append(f"CALL sprintf {m_sp3.group(1)} fmt_3d {m_sp3.group(2)} {m_sp3.group(3)} {m_sp3.group(4)};")
            continue
        m_sp2 = re.match(r'^sprintf2\s+([a-zA-Z_]\w*)\s+(.*?)\s+(.*?)\s*;', sline)
        if m_sp2:
            raw_lines.append(f"CALL sprintf {m_sp2.group(1)} fmt_2d {m_sp2.group(2)} {m_sp2.group(3)};")
            continue
        m_sp1 = re.match(r'^sprintf\s+([a-zA-Z_]\w*)\s+(.*?)\s*;', sline)
        if m_sp1:
            raw_lines.append(f"CALL sprintf {m_sp1.group(1)} fmt {m_sp1.group(2)};")
            continue

        # Normalize legacy call0..3 statements
        m_c3 = re.match(r'^(?:(.*?)\s*=\s*)?call3\s+([a-zA-Z_]\w*)\s+(.*?)\s+(.*?)\s+(.*?)\s*;', sline)
        if m_c3:
            dest, func, a1, a2, a3 = m_c3.group(1), m_c3.group(2), m_c3.group(3), m_c3.group(4), m_c3.group(5)
            if dest:
                raw_lines.append(f"{dest.strip()} = CALL {func} {a1} {a2} {a3};")
            else:
                raw_lines.append(f"CALL {func} {a1} {a2} {a3};")
            continue
        m_c2 = re.match(r'^(?:(.*?)\s*=\s*)?call2\s+([a-zA-Z_]\w*)\s+(.*?)\s+(.*?)\s*;', sline)
        if m_c2:
            dest, func, a1, a2 = m_c2.group(1), m_c2.group(2), m_c2.group(3), m_c2.group(4)
            if dest:
                raw_lines.append(f"{dest.strip()} = CALL {func} {a1} {a2};")
            else:
                raw_lines.append(f"CALL {func} {a1} {a2};")
            continue
        m_c1 = re.match(r'^(?:(.*?)\s*=\s*)?call1\s+([a-zA-Z_]\w*)\s+(.*?)\s*;', sline)
        if m_c1:
            dest, func, a1 = m_c1.group(1), m_c1.group(2), m_c1.group(3)
            if dest:
                raw_lines.append(f"{dest.strip()} = CALL {func} {a1};")
            else:
                raw_lines.append(f"CALL {func} {a1};")
            continue
        m_c0 = re.match(r'^(?:(.*?)\s*=\s*)?call0\s+([a-zA-Z_]\w*)\s*;', sline)
        if m_c0:
            dest, func = m_c0.group(1), m_c0.group(2)
            if dest:
                raw_lines.append(f"{dest.strip()} = CALL {func};")
            else:
                raw_lines.append(f"CALL {func};")
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
                expr_val = decl_m.group(2).strip()
                if (re.match(r'^\d+$', expr_val) or (expr_val.startswith('&') and ' ' not in expr_val and '+' not in expr_val)):
                    decls.append(l)
                else:
                    var_name = var_decl.split()[-1].lstrip('*')
                    decls.append(f"{var_decl} = 0;")
                    stmts.append(f"{var_name} = {expr_val};")
            else:
                decls.append(l)
        else:
            stmts.append(l)

    res = "\n".join(decls + stmts)
    if is_root and global_decls_sbnf:
        res = "\x00".join(global_decls_sbnf) + "\x00" + res
    return res

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
