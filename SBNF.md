# SBNF — Stateful BNF

## Concept

SBNF is a notation for writing text transformers. A grammar is a set of rewrite rules. Each rule matches a pattern in the input and produces output text. State is threaded through the text itself — there is no mutable memory store.

Apply one grammar after another to drive a file through successive transformations:

```
counter.c
    ↓  c-to-asm.sbnf    (C → x86-64 assembly)
counter.s
    ↓  asm-to-bin.sbnf  (assembly → binary, WIP)
counter.bin
```

Every stage of the compiler pipeline is just a grammar.

## Engine primitives

The engine provides exactly 5 operations. Everything else is defined in `.sbnf` files:

| Primitive | Role |
|-----------|------|
| **PEG** | pattern matching (terminals, regex, rules, groups, repetition, lookahead) |
| **`+`** | string concatenation / decimal number addition |
| **`LET`** | local binding |
| **`RULE`** | invoke a grammar rule on computed text |
| **`REPLACE`** | whole-word find-and-replace (`\b`-anchored) |

## Rule syntax

```
rulename ::= pattern => action
           | pattern => action
```

Alternatives are tried in order. The first match wins.

## Pattern syntax

| Syntax | Meaning |
|--------|---------|
| `"text"` | Match literal text |
| `"\n"` | Match newline (NEWLINE type, bypasses whitespace skipping) |
| `/regex/` | Match a regex |
| `Rule` | Invoke rule |
| `Rule:label` | Invoke rule, bind result to `label` |
| `pattern*` | Zero or more (produces list) |
| `pattern+` | One or more (produces list) |
| `pattern?` | Optional |
| `(pattern)` | Grouping |
| `&pattern` | Positive lookahead |
| `!pattern` | Negative lookahead |

Captured values are accessible by label in the action expression.

## Actions

Actions are expressions evaluated when a pattern matches:

- `+` — concatenation of two values (converts both to string)
- `LET(name, val, body)` — bind `val` to `name`, evaluate `body`
- `RULE(name, arg1, ...)` — invoke grammar rule with arguments joined by `\x1f`
- `REPLACE(target, replacement, text)` — replace whole words in text
- String/number literals, label references, list literals

## @def macros

```
@def NAME(args):
    body
```

Compile-time macro expansion. `NAME(...)` in any action is replaced with `body`, with parameter names substituted. Macros are processed before the grammar is parsed.

## State threading

There is no mutable state dict. Instead, state is encoded as text fields separated by `\x00` (null byte, which cannot appear in normal text):

```
"4\x00mov eax, 5\n...\x00while (i@8 < n@4) { ... }"
  ↑        ↑                        ↑
  next     accumulated init code    remaining code
```

Each rule that modifies state receives the current state string, extracts fields by pattern matching, produces output with the updated state embedded, and passes it to the next recursive `RULE` call.

Variable offsets are tracked by annotating names with `@N` (e.g., `i@8`). The `REPLACE` primitive substitutes variable names during declaration processing, avoiding name-lookup at code-generation time.

## Escape sequences

Strings and terminals support `\n`, `\t`, `\r`, `\"`, `\\`, and `\xNN` hex escapes.

## Arithmetic

Decimal arithmetic is implemented as grammar rules using reversal and carry propagation:
- `Inc(n)` — add 1 by reversing, incrementing the LSB, handling carries, reversing back
- `Dec(n)` — subtract 1 similarly
- `Add(a, b)` — repeated Inc/Dec

All defined in `.sbnf` files using only PEG, `+`, `LET`, `RULE`.

## Testing

```
make test       # full pipeline test
make test-c-to-asm  # verify assembly output
make test-run   # compile and run, check output
```

See `Makefile` for all targets.
