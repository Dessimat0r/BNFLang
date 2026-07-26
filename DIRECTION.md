# Direction

A compiler is a sequence of text transformations:

```
counter.c
    ↓  apply c-to-asm.sbnf
counter.s
    ↓  apply asm-to-bin.sbnf
counter
```

This project expresses every stage as a **Stateful BNF grammar** — rewrite rules that transform input text into output text (or binary). Applying one grammar after another drives the file all the way down to machine code.

**The engine has 5 primitives:** PEG matching, `+` (concat/addition), `LET` (binding), `RULE` (invoke grammar on computed text), `REPLACE` (word-boundary find-and-replace). Everything else — arithmetic, label generation, offset allocation, instruction encoding — is defined as grammar rules in `.sbnf` files.

There is no mutable state store. Variable offsets and label counters are embedded in the text itself and threaded through recursive `RULE` calls. No GET, no SET, no IF, no JOIN in the engine.

```
WhileStmt ::= "while" "(" cond ")" body
    => labels + cond + "cmp eax, 0\nje " + exit + "\n"
     + body + "jmp " + start + "\n" + exit + ":\n"
```

The grammar rule emits assembly directly — the grammar IS the code generator. There is no AST, no IR, no separate code generation pass.

## Goals

- Source to machine code using only BNF-style rewrites, applied repeatedly
- Every stage — parsing, codegen, instruction encoding — expressed as grammar rules
- Everything is pure text transformation; state is text, not memory
- Explore whether a single notation can span the entire compiler pipeline

## Key challenge

State must be threaded through the text itself. Every rule that modifies state (offset counter, label counter) returns the updated state alongside its output. This is achieved by encoding state as text fields separated by `\x00` and passing them through recursive `RULE` calls.

Backtracking remains transactional: if a rule fails, position and scope are restored. But since state is in the text (not a mutable dict), the threaded state pattern naturally limits backtracking scope.
