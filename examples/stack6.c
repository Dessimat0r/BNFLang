#include <stdio.h>

int main() {
    int i = 0;
    int total = 0;
    int prev = 0;
    int curr = 1;
    int tmp = 0;
    while (i < 10) {
        total = total + curr;
        tmp = curr;
        curr = prev + curr;
        prev = tmp;
        i = i + 1;
    }
    printf("%d\n", total);
    printf("%d\n", prev);
    printf("%d\n", curr);
    return 0;
}
