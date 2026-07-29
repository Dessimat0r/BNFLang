#include <stdio.h>

int main() {
    // 1. Equality & Comparisons
    int a = 15;
    int b = 10;
    int eq = (a == 15);
    int ne = (a != b);
    int gt = (a > 20);
    int ge = (a >= 15);
    printf("%d\n", eq + ne + gt + ge);

    // 2. Logical Operators
    int l1 = ((a > 10) && (b < 20));
    int l2 = ((a < 10) || (b < 20));
    int l3 = !(a == 15);
    printf("%d\n", l1 + l2 + l3);

    // 3. Bitwise Operators
    int x = 12;
    int y = 5;
    int band = x & y;
    int bor = x | y;
    int bxor = x ^ y;
    int bshl = y << 2;
    int bshr = x >> 1;
    printf("%d\n", band + bor + bxor + bshl + bshr);

    // 4. Compound Assignment
    int c = 10;
    c += 5;
    c -= 3;
    c *= 2;
    c /= 4;
    c %= 4;
    printf("%d\n", c);

    // 5. Increment / Decrement
    int d = 5;
    d++;
    ++d;
    d--;
    --d;
    printf("%d\n", d);

    // 6. Modulo Operator
    int m1 = 17 % 5;
    int m2 = 20 % 4;
    printf("%d\n", m1 + m2);

    // 7. Ternary Operator
    int val = 10;
    int res1 = (val > 5) ? 100 : 200;
    int res2 = (val < 5) ? 100 : 200;
    printf("%d\n", res1 + res2);

    return 0;
}
