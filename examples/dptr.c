#include <stdio.h>

int main() {
    int n = 5;
    int *p = &n;
    int **pp = &p;
    printf("%d\n", **pp);
    **pp = 42;
    printf("%d\n", n);
    return 0;
}
