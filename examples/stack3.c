#include <stdio.h>

int main() {
    int a = 100;
    int b = 3;
    int c = 7;
    int d = 0;
    d = (a - b) * c;
    printf("%d\n", d);
    d = a - (b * c);
    printf("%d\n", d);
    d = (a + b) * (c + 1);
    printf("%d\n", d);
    d = (a - b * c) + (b + c) * 2;
    printf("%d\n", d);
    d = a / b;
    printf("%d\n", d);
    d = (a + b) / (c - 2);
    printf("%d\n", d);
    d = a * 2 + b * 4 + c * 8;
    printf("%d\n", d);
    return 0;
}
