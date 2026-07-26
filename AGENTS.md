# BNFLang — SBNF compiler pipeline

## Pipeline
```
.c  →  c-to-asm.sbnf  →  .s  →  asm-to-bin.sbnf  →  .bin
```

## Engine (5 primitives)
All in `engine/`. CLI: `python -m engine examples/c-to-asm.sbnf examples/counter.c examples/counter.s`

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
- `engine/matcher.py` — PEG matcher + action evaluator (117 lines)
- `engine/__main__.py` — CLI entry point
- `examples/c-to-asm.sbnf` — C-like → x86-64 assembly (macOS)
- `examples/asm-to-bin.sbnf` — assembly → flat binary (partial)
- `examples/counter.c` — test program
- `Makefile` — build and test targets

## Testing
- `make test` / `make test-full` — full pipeline test (counter + scope)
- `make test-c-to-asm` — verify assembly patterns
- `make test-counter` — run counter, verify `0\n1\n2\n3\n4\n`
- `make test-scope` — run scope, verify `10\n0\n1\n2\n`
- `make all` — build all programs (counter, scope)
- `make asm` — just generate `.s` files
- `make clean` — remove build artifacts
- Always use `gtimeout` when running binaries: `gtimeout 2 ./counter`
- Install coreutils for `gtimeout`: `brew install coreutils`
- Assembly target: x86-64 macOS. Use `clang -arch x86_64` to assemble.
- Full manual test: `make clean && make test`

## Git workflow
- Commit after every unit of work (feature, fix, refactor, doc update).
- Before committing: `git status`, `git diff`, `git log --oneline -5`.
- Stage only intended files. Write concise commit messages matching repo style.
- Before any commit, ensure git identity is set: `git config user.name "Chris Dennett" && git config user.email "dessimat0r@gmail.com"`.
- Run `make test` before pushing to verify nothing is broken.

## Verified test outputs
```
counter: 0\n1\n2\n3\n4\n   — loops 0..4 with while (i < n)
scope:   10\n0\n1\n2\n      — block-scoped variable + outer while loop
```

## Conventions
- `.sbnf` files contain the grammar; `.c` files are test inputs
- Target assembly syntax: GAS `.intel_syntax noprefix` with `.data`/`.text` sections
- Variable names annotated with `@N` during declaration processing (e.g., `i@8`)
- Arithmetic helpers (`Inc`, `Dec`, `Add`) defined as grammar rules using decimal reversal + carry
- `Add` uses repeated Inc/Dec (O(b)). Fine for small `b` (always 4 in this codebase). For general use, replace with column addition (digit-by-digit with carry table).
