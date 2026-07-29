#include <stdio.h>

int main() {
    int a = 50;
    int b = 7;
    int c = 3;
    int r = 0;
    r = a / b;
    printf("%d\n", r);
    r = a / c;
    printf("%d\n", r);
    r = (a + b) / c;
    printf("%d\n", r);
    r = a / (b - c);
    printf("%d\n", r);
    r = (a * 2) / (b + c);
    printf("%d\n", r);
    r = a / b + a / c;
    printf("%d\n", r);
    r = (a + 1) / (b - 1);
    printf("%d\n", r);
    return 0;
}
