#include <stdio.h>

int main() {
    int a = 10;
    int b = 20;
    int c = 30;
    {
        a = a + b;
        b = b + c;
        c = a + b + c;
        printf("%d\n", a);
        printf("%d\n", b);
        printf("%d\n", c);
    }
    printf("%d\n", a);
    printf("%d\n", b);
    printf("%d\n", c);
    a = a - b;
    printf("%d\n", a);
    b = c - a;
    printf("%d\n", b);
    return 0;
}
