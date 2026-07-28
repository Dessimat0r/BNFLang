#include <stdio.h>

int main() {
    // 1. Test if / else if / else
    int val = 15;
    if (val < 10) {
        printf("%d\n", 1);
    } else if (val < 20) {
        printf("%d\n", 2);
    } else {
        printf("%d\n", 3);
    }

    // 2. Test for loop
    int sum = 0;
    for (int i = 0; i < 5; i = i + 1) {
        sum = sum + i;
    }
    printf("%d\n", sum);

    // 3. Test do ... while loop
    int count = 0;
    do {
        count = count + 1;
    } while (count < 3);
    printf("%d\n", count);

    // 4. Test break & continue in loop
    int total = 0;
    int k = 0;
    while (k < 10) {
        k = k + 1;
        if (k == 2) {
            continue;
        }
        if (k == 5) {
            break;
        }
        total = total + k;
    }
    printf("%d\n", total);

    // 5. Test switch / case / default
    int mode = 2;
    switch (mode) {
        case 1:
            printf("%d\n", 100);
            break;
        case 2:
            printf("%d\n", 200);
            break;
        default:
            printf("%d\n", 300);
            break;
    }

    return 0;
}
