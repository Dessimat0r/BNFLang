#include <stdio.h>

int main() {
    int n = 5;
    int i = 10;
    {
        printf("%d\n", i);
        n = 3;
        i = 0;
    }
    while (i < n) {
        printf("%d\n", i);
        i = i + 1;
    }
    return 0;
}
