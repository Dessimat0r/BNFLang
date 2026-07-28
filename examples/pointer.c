#include <stdio.h>

int main() {
    int n = 5;
    int i = 0;
    int *p = &n;
    while (i < 3) {
        printf("%d\n", *p);
        *p = *p - 1;
        i = i + 1;
    }
    return 0;
}
