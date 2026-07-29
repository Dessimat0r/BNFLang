#include <stdio.h>

int add(int a, int b) {
    return a + b;
}

int calc(int a, int b, int c) {
    return a * b + c;
}

int fib(int n) {
    if (n <= 1) {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}

int main() {
    int sum = add(15, 27);
    printf("%d\n", sum);

    int res = calc(6, 7, 10);
    printf("%d\n", res);

    int f6 = fib(6);
    printf("%d\n", f6);

    int f8 = fib(8);
    printf("%d\n", f8);

    return 0;
}
