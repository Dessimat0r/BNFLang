#include <stdio.h>

int g_counter = 50;

int count_calls() {
    static int c = 0;
    c = c + 1;
    return c;
}

int main() {
    printf("%d\n", g_counter);

    g_counter = g_counter + 25;
    printf("%d\n", g_counter);

    int arr[5];
    int i = 0;
    while (i < 5) {
        arr[i] = (i + 1) * 10;
        i = i + 1;
    }

    i = 0;
    int sum = 0;
    while (i < 5) {
        printf("%d\n", arr[i]);
        sum = sum + arr[i];
        i = i + 1;
    }
    printf("%d\n", sum);

    int c1 = count_calls();
    int c2 = count_calls();
    int c3 = count_calls();
    printf("%d\n", c1);
    printf("%d\n", c2);
    printf("%d\n", c3);

    return 0;
}
