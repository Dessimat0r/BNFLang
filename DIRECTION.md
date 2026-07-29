# Direction

A compiler is a sequence of text transformations:

```
counter.c
    ↓  apply c-to-ir.sbnf
counter.ir
    ↓  apply ir-to-x86.sbnf or ir-to-arm64.sbnf
counter.s
    ↓  apply asm-to-bin.sbnf
counter
```

This project expresses every stage as a **Stateful BNF grammar** — rewrite rules that transform input text into output text (or binary). Applying one grammar after another drives the file all the way down to machine code.

**The engine has 5 primitives:** PEG matching, `+` (concat/addition), `LET` (binding), `RULE` (invoke grammar on computed text), `REPLACE` (word-boundary find-and-replace). Everything else — arithmetic, label generation, offset allocation, instruction encoding — is defined as grammar rules in `.sbnf` files.

There is no mutable state store. Variable offsets and label counters are embedded in the text itself and threaded through recursive `RULE` calls. No GET, no SET, no IF, no JOIN in the engine.

```
WhileStmt ::= "while" "(" cond ")" body
    => labels + cond + "JMP_Z " + cond + ", .L1\n"
     + body + "JMP .L0\nLABEL .L1\n"
```

The grammar rules transform C code into Micro-IR, and Micro-IR into target assembly. There are no Python AST or symbol table objects; everything is driven by pure PEG grammar rewrites.

## Goals

- Source to machine code using only BNF-style rewrites, applied repeatedly
- Every stage — parsing, IR generation, target codegen, instruction encoding — expressed as grammar rules
- Everything is pure text transformation; state is text, not memory
- Explore whether a single notation can span the entire compiler pipeline

## Key challenge

State must be threaded through the text itself. Every rule that modifies state (offset counter, label counter) returns the updated state alongside its output. This is achieved by encoding state as text fields separated by `\x00` and passing them through recursive `RULE` calls.

Backtracking remains transactional: if a rule fails, position and scope are restored. But since state is in the text (not a mutable dict), the threaded state pattern naturally limits backtracking scope.
