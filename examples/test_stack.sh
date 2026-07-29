#!/bin/bash
# Intensive stack allocation tests
set -e

GTIMEOUT=$(command -v gtimeout 2>/dev/null || echo "gtimeout")
PASS=0
FAIL=0
ERRORS=""

run_test() {
    local name="$1"
    local src="$2"
    local expected="$3"

    echo "=== $name ==="

    # Stage 1: C -> IR
    if ! python -m engine examples/c-to-ir.sbnf "$src" "/tmp/${name}.ir" 2>/tmp/${name}_compile.log; then
        echo "FAIL: compilation error (c-to-ir)"
        cat /tmp/${name}_compile.log
        FAIL=$((FAIL + 1))
        ERRORS="$ERRORS\n  $name: compilation failed"
        return
    fi

    # Stage 2: IR -> x86-64 ASM
    if ! python -m engine examples/ir-to-x86.sbnf "/tmp/${name}.ir" "/tmp/${name}.s" 2>/tmp/${name}_compile.log; then
        echo "FAIL: compilation error (ir-to-x86)"
        cat /tmp/${name}_compile.log
        FAIL=$((FAIL + 1))
        ERRORS="$ERRORS\n  $name: compilation failed"
        return
    fi

    # Assemble
    if ! clang -arch x86_64 -c "/tmp/${name}.s" -o "/tmp/${name}.o" 2>/tmp/${name}_asm.log; then
        echo "FAIL: assembly error"
        cat /tmp/${name}_asm.log
        echo "--- Generated assembly ---"
        cat "/tmp/${name}.s"
        FAIL=$((FAIL + 1))
        ERRORS="$ERRORS\n  $name: assembly failed"
        return
    fi

    # Link
    if ! clang -arch x86_64 "/tmp/${name}.o" -o "/tmp/${name}" -lSystem 2>/tmp/${name}_link.log; then
        echo "FAIL: link error"
        cat /tmp/${name}_link.log
        FAIL=$((FAIL + 1))
        ERRORS="$ERRORS\n  $name: link failed"
        return
    fi

    # Run
    local actual
    actual=$($GTIMEOUT 2 "/tmp/${name}" 2>&1) || true

    # Compare
    if [ "$actual" = "$expected" ]; then
        echo "PASS"
        PASS=$((PASS + 1))
    else
        echo "FAIL: output mismatch"
        echo "  Expected: $(echo "$expected" | head -20)"
        echo "  Actual:   $(echo "$actual" | head -20)"
        echo "--- Generated assembly ---"
        cat "/tmp/${name}.s"
        FAIL=$((FAIL + 1))
        ERRORS="$ERRORS\n  $name: output mismatch"
    fi

    rm -f "/tmp/${name}.ir" "/tmp/${name}.s" "/tmp/${name}.o" "/tmp/${name}"
}

# 1. Many local variables test
run_test "stack1_many_vars" "examples/stack1.c" "42"

# 2. Cross-scope local variables test
run_test "stack2_cross_scope" "examples/stack2.c" "100"

# 3. Complex expression stack usage test
run_test "stack3_complex_expr" "examples/stack3.c" "777"

# 4. Triple nested loop stack usage test
run_test "stack4_triple_loop" "examples/stack4.c" "1000"

# 5. Pointer layout & stack address arithmetic test
run_test "stack5_ptr_layout" "examples/stack5.c" "555"

# 6. Recursive stack frame test (Fibonacci 10)
run_test "stack6_fibonacci" "examples/stack6.c" "55"

# 7. Multi-operand arithmetic stack test
run_test "stack7_multi_arith" "examples/stack7.c" "1234"

# 8. Integer division & modulo stack test
run_test "stack8_division" "examples/stack8.c" "7"

echo ""
echo "=================================="
echo "Results: $PASS passed, $FAIL failed"

if [ $FAIL -ne 0 ]; then
    echo -e "Failed tests:$ERRORS"
    exit 1
else
    echo "All stack allocation tests PASS"
fi
