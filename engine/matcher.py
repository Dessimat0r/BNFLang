import re
from .grammar import Pattern

CATCHALL_RE = re.compile(r'^\[\\s\\S\][*+]$')

def _is_catchall(alt):
    return bool(len(alt.patterns) == 1 and alt.patterns and CATCHALL_RE.match(alt.patterns[0].data))

def match_grammar(grammar, text, state=None):
    if state is None: state = {}
    state['_g'] = grammar
    r, p = _rule(grammar, grammar.start, text, 0, state, {})
    if p is None or p > len(text):
        raise SyntaxError("Parse failed")
    return r

OPT_RULES = {'Expr', 'Compare', 'AddExpr', 'MulExpr', 'Primary', 'Ceil16'}

def _rule(g, name, text, pos, state, scope):
    rule = g.rules.get(name)
    if not rule: raise KeyError(f"Unknown rule: {name}")
    saved = dict(state)
    if name in OPT_RULES:
        best_r, best_p, best_cost, best_state = None, None, None, None
        fallback_r, fallback_p, fallback_state = None, None, None
        for alt in rule.alts:
            state.clear(); state.update(saved)
            ns = dict(scope)
            r, p = _alt(g, alt, text, pos, state, ns)
            if p is not None and r is not None:
                if _is_catchall(alt):
                    fallback_r, fallback_p, fallback_state = r, p, dict(state)
                else:
                    cost = len(str(r))
                    if best_r is None or p > best_p or (p == best_p and cost < best_cost):
                        best_r, best_p, best_cost, best_state = r, p, cost, dict(state)
        if best_r is not None:
            state.clear(); state.update(best_state)
            return best_r, best_p
        if fallback_r is not None:
            state.clear(); state.update(fallback_state)
            return fallback_r, fallback_p
        state.clear(); state.update(saved)
        return None, None
    for alt in rule.alts:
        ns = dict(scope)
        r, p = _alt(g, alt, text, pos, state, ns)
        if p is not None: return r, p
        state.clear(); state.update(saved)
    return None, None

def _alt(g, alt, text, pos, state, scope):
    return _seq(g, alt.patterns, text, pos, state, scope, alt.action)

def _seq(g, pats, text, pos, state, scope, action=None):
    vals, res = {}, []
    for p in pats:
        r, pos = _pat(g, p, text, pos, state, scope)
        if pos is None: return None, None
        res.append(r)
        if p.label: vals[p.label] = r
    scope.update(vals)
    return (eval_node(action, scope, state) if action else (res[-1] if res else None)), pos

def _pat(g, pat, text, pos, state, scope):
    t = pat.type
    if t == Pattern.TERMINAL:
        pos = _ws(text, pos)
        if text[pos:pos+len(pat.data)] == pat.data:
            return pat.data, pos+len(pat.data)
        return None, None
    if t == Pattern.NEWLINE:
        if pos < len(text) and text[pos] == '\n':
            return '\n', pos+1
        return None, None
    if t == Pattern.REGEX:
        pos = _ws(text, pos)
        m = re.match(pat.data, text[pos:])
        if m: return m.group(0), pos+m.end()
        return None, None
    if t == Pattern.RULE: return _rule(g, pat.data, text, pos, state, scope)
    if t == Pattern.GROUP: return _seq(g, pat.data, text, pos, state, scope, None)
    if t == Pattern.REPEAT:
        inner, mn = pat.data; res = []
        while True:
            sv, sc = dict(state), dict(scope)
            r, np = _pat(g, inner, text, pos, state, scope)
            if np is not None and np > pos:
                res.append(r); pos = np
            else:
                state.clear(); state.update(sv)
                scope.clear(); scope.update(sc); break
        return (res, pos) if len(res) >= mn else (None, None)
    if t == Pattern.OPTIONAL:
        inner = pat.data; sv, sc = dict(state), dict(scope)
        r, np = _pat(g, inner, text, pos, state, scope)
        if np is not None and np > pos: return r, np
        state.clear(); state.update(sv); scope.clear(); scope.update(sc)
        return None, pos
    if t == Pattern.LOOKAHEAD:
        pf, inner = pat.data
        r, np = _pat(g, inner, text, pos, state, scope)
        return (r is not None) if pf else (r is None), pos
    return None, None

def _ws(text, pos):
    while pos < len(text):
        c = text[pos]
        if c in ' \t\r\n': pos += 1
        elif c == '/' and pos+1 < len(text) and text[pos+1] == '/':
            e = text.find('\n', pos); pos = e+1 if e != -1 else len(text)
        else: break
    return pos

def eval_node(node, scope, state):
    if node is None: return None
    t = node['type']
    if t == 'str':   return node['value']
    if t == 'num':   return node['value']
    if t == 'label': return scope.get(node['name'])
    if t == 'list':  return [eval_node(x, scope, state) for x in node['items']]
    if t == 'plus':
        l = str(eval_node(node['left'], scope, state))
        r = str(eval_node(node['right'], scope, state))
        if l.isdigit() and r.isdigit(): return str(int(l) + int(r))
        return l + r
    if t == 'let':
        v = eval_node(node['val'], scope, state)
        ns = dict(scope); ns[node['name']] = v
        return eval_node(node['body'], ns, state)
    if t == 'call':
        fn = node['func']; args = [eval_node(a, scope, state) for a in node['args']]
        if fn == 'REPLACE':
            target = str(args[0])
            repl = str(args[1])
            text = str(args[2])
            cache = state.setdefault('_re_cache', {})
            if target not in cache:
                cache[target] = re.compile(r'\b' + re.escape(target) + r'\b')
            return cache[target].sub(repl, text)
        if fn == 'RULE': return call_rule(args, state)
        if fn == 'MATCH_BRACE':
            text = str(args[0]) if args else ''
            pos = int(str(args[1])) if len(args) > 1 else 0
            depth = 0
            i = pos
            while i < len(text):
                if text[i] == '{':
                    depth += 1
                elif text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        return str(i)
                i += 1
            return str(len(text))
        if fn in (state.get('_g') or {}).rules:
            return call_rule([fn] + args, state)
        raise KeyError(f"Unknown: {fn}")
    return None

def call_rule(args, state):
    if not args: return None
    g = state.get('_g')
    if not g: return None
    name = str(args[0])
    if not g.rules.get(name): return None
    inp = '\x1f'.join(str(a) for a in args[1:])
    ns = dict(state); ns['_g'] = g
    r, _ = _rule(g, name, inp, 0, ns, {})
    return str(r) if r is not None else None
