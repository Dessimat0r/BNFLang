#include <stdio.h>

int main() {
    int n = 3;
    int i = 0;
    int j = 0;
    int k = 0;
    int sum = 0;
    while (i < n) {
        j = 0;
        while (j < n) {
            k = 0;
            while (k < n) {
                sum = sum + 1;
                k = k + 1;
            }
            j = j + 1;
        }
        i = i + 1;
    }
    printf("%d\n", sum);
    printf("%d\n", i);
    printf("%d\n", j);
    printf("%d\n", k);
    return 0;
}
