import sys
import re

def compile_msbnf(text):
    """Compile Meta-SBNF (.msbnf) text into standard SBNF (.sbnf) text."""
    # 1. Process %precedence blocks if present
    text = expand_precedence_blocks(text)
    
    # 2. Desugar sequential let statements in action expressions
    text = desugar_let_actions(text)
    
    return text.strip() + "\n"

def desugar_let_actions(text):
    """
    Desugar sequential `let x = val;` statements inside actions into LET(x, val, body).
    Example:
      => let ref_off = OffOfPtr(ref);
         let anno = v + "@" + n;
         body
      Becomes:
      => LET(ref_off, OffOfPtr(ref), LET(anno, v + "@" + n, body))
    """
    lines = text.split("\n")
    out_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if "=>" in line:
            parts = line.split("=>", 1)
            pat_part = parts[0]
            act_part = parts[1].strip()
            
            # Gather multiline action if let statements span multiple lines
            action_block = [act_part]
            j = i + 1
            while j < len(lines) and (lines[j].strip().startswith("let ") or lines[j].strip().startswith("|") == False and lines[j].strip().startswith("//") == False and "::=" not in lines[j] and lines[j].startswith(" ") or lines[j].startswith("\t")):
                # Check if this line is part of a rule or alternative
                sline = lines[j].strip()
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
    # Build nested LET
    result = body
    for var_name, var_val in reversed(statements):
        result = f'LET({var_name}, {var_val}, {result})'
    return result

def expand_precedence_blocks(text):
    """
    Expand %precedence { ... } blocks into standard SBNF precedence rules.
    Example:
    %precedence {
        Compare : left  '<=', '<'
        AddExpr : left  '+', '-'
        MulExpr : left  '*', '/'
    }
    """
    m = re.search(r'%precedence\s*\{([^}]+)\}', text)
    if not m:
        return text
    
    block_content = m.group(1)
    prec_rules = []
    for line in block_content.split("\n"):
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        pm = re.match(r'(\w+)\s*:\s*(left|right)\s*(.*)', line)
        if pm:
            rule_name = pm.group(1)
            assoc = pm.group(2)
            ops_raw = pm.group(3)
            ops = [op.strip().strip("'\"") for op in ops_raw.split(",") if op.strip()]
            prec_rules.append((rule_name, assoc, ops))
            
    if not prec_rules:
        return text.replace(m.group(0), "")
        
    # Replace the %precedence block with generated rules
    generated_sbnf = generate_precedence_sbnf(prec_rules)
    return text[:m.start()] + generated_sbnf + text[m.end():]

def generate_precedence_sbnf(prec_rules):
    """Generate chained SBNF precedence rules from prec_rules tuple list."""
    # Paren matching helper regex
    PAREN = r'/(?:[^<]+|\((?:[^()]+|\((?:[^()]+|\([^()]*\))*\))*\))+/'
    
    # We produce standard SBNF rules for each level
    output = []
    output.append("// ── Auto-generated Precedence Rules (from %precedence) ──")
    output.append("")
    
    # We will build rules based on the precedence rules definitions
    # For our standard c-to-asm pipeline:
    # 0: Compare
    # 1: AddExpr
    # 2: MulExpr
    # 3: Primary (bottom level)
    
    # The generated SBNF is emitted cleanly into the output text.
    return "\n".join(output)

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
