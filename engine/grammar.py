import re

class Pattern:
    TERMINAL, REGEX, RULE, GROUP, REPEAT, OPTIONAL, LOOKAHEAD, NEWLINE = range(8)
    __slots__ = ('type', 'data', 'label')
    def __init__(self, type, data=None, label=None):
        self.type = type; self.data = data; self.label = label

class Alternative:
    __slots__ = ('patterns', 'action')
    def __init__(self, patterns, action):
        self.patterns = patterns; self.action = action

class Rule:
    __slots__ = ('name', 'alts')
    def __init__(self, name, alts):
        self.name = name; self.alts = alts

class Grammar:
    def __init__(self, rules, macros=None):
        self.rules = {r.name: r for r in rules}
        self.start = rules[0].name if rules else None
        self.macros = macros or {}
    @classmethod
    def parse(cls, text):
        text, macros = extract_macros(strip_comments(text))
        rules = []
        for block in split_rule_blocks(text):
            r = parse_rule_block(block, macros)
            if r: rules.append(r)
        return cls(rules, macros)

RE_MACRO = re.compile(r'@def\s+(\w+)\s*\(([^)]*)\)\s*:\s*\n((?:(?!\n\s*\n|\n(?:@def|\w)).*\n)*)', re.MULTILINE)

def extract_macros(text):
    macros = {}
    def replacer(m):
        name = m.group(1)
        args = [a.strip() for a in m.group(2).split(',') if a.strip()]
        body = m.group(3).strip()
        macros[name] = (args, body)
        return ''
    cleaned = RE_MACRO.sub(replacer, text)
    return cleaned, macros

def expand_call(text, macros):
    for name, (args, body) in macros.items():
        result = []
        i = 0
        while i < len(text):
            m = re.match(r'\b' + name + r'\s*\(', text[i:])
            if m:
                start = i + m.end()
                depth, j = 0, 0
                while j < len(text) - start:
                    if text[start + j] == '(':
                        depth += 1
                    elif text[start + j] == ')':
                        depth -= 1
                        if depth < 0:
                            break
                    j += 1
                inner = text[start:start + j]
                arg_vals = split_macro_args(inner)
                replacement = body
                for a, v in zip(args, arg_vals):
                    replacement = re.sub(r'\b' + a + r'\b', v.strip(), replacement)
                result.append(replacement)
                i = start + j + 1
            else:
                result.append(text[i])
                i += 1
        text = ''.join(result)
    return text

def split_macro_args(text):
    args, cur, depth = [], [], 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch in '([': depth += 1; cur.append(ch)
        elif ch in ')': depth -= 1; cur.append(ch)
        elif ch == ',' and depth == 0:
            args.append(''.join(cur).strip()); cur = []
        else: cur.append(ch)
        i += 1
    if cur: args.append(''.join(cur).strip())
    return args

def strip_comments(text):
    out, i = [], 0
    while i < len(text):
        if text[i:i+2] == '//':
            e = text.find('\n', i)
            i = e+1 if e != -1 else len(text)
        else:
            out.append(text[i]); i += 1
    return ''.join(out)

def split_rule_blocks(text):
    blocks, cur = [], []
    for line in text.split('\n'):
        s = line.strip()
        if '::=' in s and not s.startswith('|'):
            if cur: blocks.append('\n'.join(cur))
            cur = [s]
        elif not s:
            if cur: cur.append('')
        else:
            cur.append(s)
    if cur: blocks.append('\n'.join(cur))
    return blocks

def parse_rule_block(text, macros=None):
    m = re.match(r'(\w+)\s*::=', text)
    if not m: return None
    name = m.group(1)
    rest = text[m.end():].strip()
    alts = []
    for alt_text in split_alternatives(rest):
        alt_text = alt_text.strip()
        if not alt_text: continue
        parts = alt_text.split('=>', 1)
        pat_text = parts[0].strip()
        act_text = parts[1].strip() if len(parts) > 1 else None
        if act_text and macros:
            act_text = expand_call(act_text, macros)
        patterns = parse_pattern_seq(pat_text)
        action = parse_action(act_text) if act_text else None
        alts.append(Alternative(patterns, action))
    return Rule(name, alts) if alts else None

def _unescape(raw):
    out = []
    i = 0
    while i < len(raw):
        if raw[i] == '\\' and i + 1 < len(raw):
            n = raw[i+1]
            if n == 'n': out.append('\n'); i += 2; continue
            if n == 't': out.append('\t'); i += 2; continue
            if n == 'r': out.append('\r'); i += 2; continue
            if n == '\\': out.append('\\'); i += 2; continue
            if n == '"': out.append('"'); i += 2; continue
            if n == 'x' and i + 3 < len(raw):
                try:
                    out.append(chr(int(raw[i+2:i+4], 16)))
                    i += 4; continue
                except: pass
            out.append(raw[i]); i += 1
        else:
            out.append(raw[i]); i += 1
    return ''.join(out)

def split_alternatives(text):
    parts, cur, depth, instr = [], [], 0, False
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '"' and (i == 0 or text[i-1] != '\\'):
            instr = not instr; cur.append(ch)
        elif ch == '/' and not instr:
            cur.append(ch); i += 1
            while i < len(text) and text[i] != '/':
                cur.append(text[i]); i += 1
            if i < len(text): cur.append('/')
        elif not instr:
            if ch == '(':
                depth += 1; cur.append(ch)
            elif ch == ')':
                depth -= 1; cur.append(ch)
            elif ch == '|' and depth == 0:
                parts.append(''.join(cur).strip()); cur = []
                i += 1; continue
            else:
                cur.append(ch)
        else:
            cur.append(ch)
        i += 1
    if cur: parts.append(''.join(cur).strip())
    return parts

# ── Pattern parsing ─────────────────────────────────────────────────────────

RE_TERM = re.compile(r'^"((?:[^"\\]|\\.)*)"')
RE_REGX = re.compile(r'^/((?:[^/\\]|\\.)*)/')
RE_ID   = re.compile(r'^([a-zA-Z_]\w*)')

def read_label(text, i):
    if i < len(text) and text[i] == ':':
        j = i + 1
        while j < len(text) and text[j] not in ' \t\r\n)': j += 1
        return text[i+1:j], j
    return None, i

def parse_pattern_seq(text):
    pats, i = [], 0
    while i < len(text):
        ch = text[i]
        if ch in ' \t\r\n': i += 1; continue
        if ch == '"':
            m = RE_TERM.match(text[i:])
            if m:
                raw = m.group(1)
                val = _unescape(raw)
                ptype = Pattern.NEWLINE if val == '\n' else Pattern.TERMINAL
                pat = Pattern(ptype, val)
                i += m.end()
                lab, i = read_label(text, i)
                pat.label = lab
                pats.append(pat)
                continue
        if ch == '/':
            m = RE_REGX.match(text[i:])
            if m:
                pat = Pattern(Pattern.REGEX, m.group(1))
                i += m.end()
                lab, i = read_label(text, i)
                pat.label = lab
                pats.append(pat)
                continue
        if ch == '(':
            d, j = 1, i+1
            while j < len(text) and d:
                if text[j]=='(': d+=1
                elif text[j]==')': d-=1
                j+=1
            pat = Pattern(Pattern.GROUP, parse_pattern_seq(text[i+1:j-1]))
            i = j
            lab, i = read_label(text, i)
            pat.label = lab
            pats.append(pat)
            continue
        if ch in '!&':
            start = i; i += 1
            while i < len(text) and text[i] in ' \t': i += 1
            inner = parse_one_pattern(text[i:])
            if inner:
                pats.append(Pattern(Pattern.LOOKAHEAD, (ch=='&', inner)))
                continue
        m = RE_ID.match(text[i:])
        if m:
            name = m.group(1); i += m.end()
            rep = None
            if i < len(text) and text[i] == '*': rep='*'; i+=1
            elif i < len(text) and text[i] == '+': rep='+'; i+=1
            elif i < len(text) and text[i] == '?': rep='?'; i+=1
            label, i = read_label(text, i)
            inner = Pattern(Pattern.RULE, name)
            if rep == '*': pat = Pattern(Pattern.REPEAT, (inner, 0), label)
            elif rep == '+': pat = Pattern(Pattern.REPEAT, (inner, 1), label)
            elif rep == '?': pat = Pattern(Pattern.OPTIONAL, inner, label)
            else: pat = Pattern(Pattern.RULE, name, label)
            pats.append(pat); continue
        i += 1
    return pats

def parse_one_pattern(text):
    text = text.lstrip()
    if not text: return None
    if text[0]=='"':
        m=RE_TERM.match(text); return Pattern(Pattern.TERMINAL,m.group(1)) if m else None
    if text[0]=='/':
        m=RE_REGX.match(text); return Pattern(Pattern.REGEX,m.group(1)) if m else None
    m=RE_ID.match(text)
    return Pattern(Pattern.RULE,m.group(1)) if m else None

# ── Action parsing ──────────────────────────────────────────────────────────

def parse_action(text):
    text = text.strip()
    if not text: return None
    m = re.match(r'LET\s*\(', text)
    if m: return parse_let(text[m.end()-1:])
    m = re.match(r'IF\s*\(', text)
    if m: return parse_if(text[m.end()-1:])
    return parse_expr(text)

def parse_let(text):
    assert text[0] == '('
    parts = split_args(text)
    if len(parts) < 3: return None
    name = parts[0].strip().strip('"')
    val = parse_expr(parts[1])
    body = parse_expr(' , '.join(parts[2:]))  # rejoin rest
    return {'type': 'let', 'name': name, 'val': val, 'body': body}

def parse_if(text):
    assert text[0] == '('
    parts = split_args(text)
    if len(parts) < 3: return None
    cond = parse_expr(parts[0])
    then = parse_expr(parts[1])
    else_ = parse_expr(parts[2]) if len(parts) > 2 else None
    return {'type': 'if', 'cond': cond, 'then': then, 'else': else_}

def split_args(text):
    args, cur, depth, instr = [], [], 0, False
    first = True
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '"' and (i == 0 or text[i-1] != '\\'):
            instr = not instr; cur.append(ch)
        elif ch == '/' and not instr:
            cur.append(ch); i += 1
            while i < len(text) and text[i] != '/': cur.append(text[i]); i += 1
            if i < len(text): cur.append('/')
        elif not instr:
            if ch == '(':
                depth += 1
                if first: first = False
                else: cur.append(ch)
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    args.append(''.join(cur).strip())
                    return args
                cur.append(ch)
            elif ch == ',' and depth == 1:
                args.append(''.join(cur).strip()); cur = []
            else: cur.append(ch)
        else: cur.append(ch)
        i += 1
    if cur: args.append(''.join(cur).strip())
    return args

def parse_expr(text):
    text = text.strip()
    if not text: return None
    depth, instr = 0, False

    ops = {'+': 'plus', '-': 'minus', '*': 'mul', '/': 'div'}
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '"' and (i == 0 or text[i-1] != '\\'):
            instr = not instr; i += 1; continue
        if ch == '/' and not instr:
            i += 1
            while i < len(text) and text[i] != '/': i += 1
            i += 1; continue
        if not instr:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            elif ch in ops and depth == 0:
                left = text[:i].strip()
                right = text[i+1:].strip()
                return {'type': ops[ch],
                        'left': parse_expr(left),
                        'right': parse_expr(right)}
        i += 1
    # No + → LET, IF, function call, literal, or label
    m = re.match(r'LET\s*\(', text)
    if m: return parse_let(text[m.end()-1:])
    m = re.match(r'IF\s*\(', text)
    if m: return parse_if(text[m.end()-1:])
    m = re.match(r'(\w+)\s*\((.*)\)\s*$', text, re.DOTALL)
    if m:
        func = m.group(1)
        args_text = m.group(2).strip()
        args = parse_args(args_text)
        return {'type': 'call', 'func': func, 'args': args}
    if text.startswith('"') and text.endswith('"'):
        return {'type': 'str', 'value': _unescape(text[1:-1])}
    if text.isdigit() or (text.startswith('-') and text[1:].isdigit()):
        return {'type': 'num', 'value': int(text)}
    if text.startswith('[') and text.endswith(']'):
        inner = text[1:-1].strip()
        items = []
        if inner:
            for part in split_list_items(inner):
                items.append(parse_expr(part.strip()))
        return {'type': 'list', 'items': items}
    if re.match(r'^[a-zA-Z_]\w*$', text):
        return {'type': 'label', 'name': text}
    return {'type': 'str', 'value': text}

def split_list_items(text):
    items, cur, depth, instr = [], [], 0, False
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '"' and (i == 0 or text[i-1] != '\\'):
            instr = not instr; cur.append(ch)
        elif not instr:
            if ch in '([': depth += 1; cur.append(ch)
            elif ch in ')': depth -= 1; cur.append(ch)
            elif ch == ',' and depth == 0:
                items.append(''.join(cur).strip()); cur = []
            else: cur.append(ch)
        else: cur.append(ch)
        i += 1
    if cur: items.append(''.join(cur).strip())
    return items

def parse_args(text):
    args, cur, depth, instr = [], [], 0, False
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '"' and (i == 0 or text[i-1] != '\\'):
            instr = not instr; cur.append(ch)
        elif not instr:
            if ch in '([':
                depth += 1; cur.append(ch)
            elif ch in ')':
                depth -= 1; cur.append(ch)
            elif ch == ',' and depth == 0:
                args.append(''.join(cur).strip()); cur = []
            else: cur.append(ch)
        else: cur.append(ch)
        i += 1
    if cur:
        a = ''.join(cur).strip()
        if a: args.append(a)
    return [parse_expr(a) for a in args]
