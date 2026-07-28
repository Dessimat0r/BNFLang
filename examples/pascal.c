#include <stdio.h>

int main() {
    int n = 5;
    int row = 0;
    int val = 1;
    int col = 0;
    int sp = 0;
    while (row < n) {
        sp = 0;
        while (sp < n - (row + 1)) {
            printf(" ");
            sp = sp + 1;
        }
        val = 1;
        col = 0;
        while (col < row + 1) {
            printf("%d ", val);
            val = (val * (row - col)) / (col + 1);
            col = col + 1;
        }
        printf("\n");
        row = row + 1;
    }
    return 0;
}
