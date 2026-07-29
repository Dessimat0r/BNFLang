#include <stdio.h>

int main() {
    int a = 5;
    int b = 10;
    int *p = &a;
    int *q = &b;
    int **pp = &p;
    printf("%d\n", *p);
    printf("%d\n", *q);
    *p = *q;
    printf("%d\n", *p);
    printf("%d\n", a);
    *q = 42;
    printf("%d\n", *q);
    printf("%d\n", b);
    printf("%d\n", **pp);
    **pp = 99;
    printf("%d\n", a);
    printf("%d\n", *p);
    return 0;
}
