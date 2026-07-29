# BNFLang — 2-Stage Micro-IR Compiler Pipeline

## Pipeline
```
.c  →  c-to-ir.sbnf  →  .ir  ──┬──>  ir-to-x86.sbnf    →  x86-64 .s    →  clang  →  bin
                               └──>  ir-to-arm64.sbnf  →  ARM64 .s     →  clang  →  bin
```

## Engine (5 primitives)
All in `engine/`. CLI: `python -m engine examples/c-to-ir.sbnf examples/counter.c /tmp/counter.ir`

| Primitive | Role |
|-----------|------|
| PEG | pattern matching (incl. NEWLINE type for `"\n"`) |
| `+` | string concat / number addition |
| `LET` | binding |
| `RULE` | invoke grammar rule on computed text |
| `REPLACE` | word-boundary find-and-replace (`\b` anchored) |

No GET/SET/IF/JOIN in engine — all handled by grammar rules in `.sbnf`.

## Grammar syntax
- Rules: `name ::= pattern => action | pattern => action`
- Patterns: `"text"`, `/regex/`, `Rule`, `Rule:label`, `pat*`, `pat+`, `pat?`, `(pat)`, `&pat`, `!pat`
- Actions: `+`, `LET`, `RULE`, `REPLACE`, labels, string/number literals, `@def` macros
- `@def NAME(args):\n    body` — compile-time macro expansion
- `"\n"` becomes NEWLINE pattern (bypasses `_ws` whitespace skipping)
- `\xNN` escape sequences supported in strings and terminals
- `\x00` is used as field separator in threaded state

## State threading (no GET/SET)
Variable offsets and label counters are embedded in the text itself and threaded through recursive `RULE` calls. Format: `"nxt\x00inits\x00code"` where `\x00` separates fields. `REPLACE` annotates variable names with `name@offset` to avoid name-lookup.

## Project structure
- `engine/grammar.py` — grammar parser (.sbnf → rule structures)
- `engine/matcher.py` — PEG matcher + action evaluator
- `engine/msbnf.py` — Meta-SBNF macro expander
- `engine/c_prep.py` — C preprocessor & desugarer
- `examples/c-to-ir.msbnf` — C-like → Micro-IR compiler grammar
- `examples/ir-to-x86.msbnf` — Micro-IR → x86-64 assembly generator
- `examples/ir-to-arm64.msbnf` — Micro-IR → ARM64 assembly generator
- `Makefile` — build and test targets

## Testing
- `make test` — run all 26 test programs (x86-64 & ARM64) + stack tests
- `make clean` — remove build artifacts
- Always use `gtimeout` when running binaries: `gtimeout 2 ./counter`
- Target architectures: x86-64 macOS (`clang -arch x86_64`) and ARM64 Apple Silicon (`clang -arch arm64`).
- Full manual test: `make clean && make test`

## Git workflow
- Commit after every unit of work (feature, fix, refactor, doc update).
- Before committing: `git status`, `git diff`, `git log --oneline -5`.
- Stage only intended files. Write concise commit messages matching repo style.
- Before any commit, ensure git identity is set: `git config user.name "Chris Dennett" && git config user.email "dessimat0r@gmail.com"`.
- Write comprehensive tests covering the change before committing.
- Run `make test` before pushing to verify nothing is broken.

## Verified test outputs
```
counter: 0\n1\n2\n3\n4\n   — loops 0..4 with while (i < n)
scope:   10\n0\n1\n2\n      — block-scoped variable + outer while loop
pascal:  formatted triangle    — nested loops, *, /, (, ) operators
pointer: 5\n4\n3\n           — & and * operators, pointer write through
dptr:    5\n42\n             — double pointers **pp, deref chain through pp→p→n
```

## Conventions
- `.sbnf` / `.msbnf` files contain the grammar; `.c` files are test inputs
- Target assembly syntax: GAS `.intel_syntax noprefix` for x86-64, Apple Silicon GAS for ARM64
- Variable names annotated with `@N` during declaration processing (e.g., `i@8`)
