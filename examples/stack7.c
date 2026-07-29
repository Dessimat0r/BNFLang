#include <stdio.h>

int main() {
    int a = 2;
    int b = 3;
    int c = 4;
    int d = 5;
    int r = 0;
    r = a * b + c * d;
    printf("%d\n", r);
    r = (a + b) * (c + d);
    printf("%d\n", r);
    r = (a * b) - (c * d);
    printf("%d\n", r);
    r = a * (b + c) * d;
    printf("%d\n", r);
    r = (a + b + c) * (d - a);
    printf("%d\n", r);
    r = a * b * c * d;
    printf("%d\n", r);
    r = ((a + b) * c - d) * 2;
    printf("%d\n", r);
    return 0;
}
