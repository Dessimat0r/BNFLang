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

    # Compile C -> ASM
    if ! python -m engine examples/c-to-asm.sbnf "$src" "/tmp/${name}.s" 2>/tmp/${name}_compile.log; then
        echo "FAIL: compilation error"
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
}

# ── Test 1: 8 variables at different offsets ──
# a=1..h=8, then a+b+c+d=10, e+f+g+h=26
run_test "stack1_many_vars" "examples/stack1.c" "$(printf '1\n2\n3\n4\n5\n6\n7\n8\n10\n26')"

# ── Test 2: Cross-scope mutation ──
# a=10,b=20,c=30 -> a=30,b=50,c=110 (inside block) -> same outside
# a-b = 30-50 = -20, c-a = 110-(-20) = 130
run_test "stack2_cross_scope" "examples/stack2.c" "$(printf '30\n50\n110\n30\n50\n110\n-20\n130')"

# ── Test 3: Complex expressions ──
# a=100,b=3,c=7
# (100-3)*7 = 679
# 100-(3*7) = 79
# (100+3)*(7+1) = 103*8 = 824
# (100-3*7) + (3+7)*2 = 79 + 20 = 99
# 100/3 = 33
# (100+3)/(7-2) = 103/5 = 20
# 100*2 + 3*4 + 7*8 = 200+12+56 = 268
run_test "stack3_complex_expr" "examples/stack3.c" "$(printf '679\n79\n824\n99\n33\n20\n268')"

# ── Test 4: Triple nested loops ──
# 3^3 = 27 iterations, sum=27, i=3, j=3, k=3
run_test "stack4_triple_loop" "examples/stack4.c" "$(printf '27\n3\n3\n3')"

# ── Test 5: Mixed pointer/int stack layout ──
# a=5, b=10, *p=&a, *q=&b
# *p=5, *q=10, *p=*q -> *p=10, a=10, *q=42, b=42
# **pp (pp=&p, *p=a) -> a=10, **pp=99 -> a=99, *p=99
run_test "stack5_ptr_layout" "examples/stack5.c" "$(printf '5\n10\n10\n10\n42\n42\n10\n99\n99')"

# ── Test 6: Fibonacci accumulator ──
# fib: 1,1,2,3,5,8,13,21,34,55 — sum of first 10 = 143
# After 10 iterations: prev=55, curr=89
run_test "stack6_fibonacci" "examples/stack6.c" "$(printf '143\n55\n89')"

# ── Test 7: Multi-variable arithmetic ──
# a=2,b=3,c=4,d=5
# a*b + c*d = 6+20 = 26
# (a+b)*(c+d) = 5*9 = 45
# (a*b)-(c*d) = 6-20 = -14
# a*(b+c)*d = 2*7*5 = 70
# (a+b+c)*(d-a) = 9*3 = 27
# a*b*c*d = 120
# ((a+b)*c - d)*2 = (5*4-5)*2 = 15*2 = 30
run_test "stack7_multi_arith" "examples/stack7.c" "$(printf '26\n45\n-14\n70\n27\n120\n30')"

# ── Test 8: Division stress ──
# a=50,b=7,c=3
# 50/7 = 7
# 50/3 = 16
# (50+7)/3 = 57/3 = 19
# 50/(7-3) = 50/4 = 12
# (50*2)/(7+3) = 100/10 = 10
# 50/7 + 50/3 = 7+16 = 23
# (50+1)/(7-1) = 51/6 = 8
run_test "stack8_division" "examples/stack8.c" "$(printf '7\n16\n19\n12\n10\n23\n8')"

# ── Summary ──
echo ""
echo "=================================="
echo "Results: $PASS passed, $FAIL failed"
if [ $FAIL -gt 0 ]; then
    echo -e "Failures:$ERRORS"
    exit 1
else
    echo "All stack allocation tests PASS"
fi
