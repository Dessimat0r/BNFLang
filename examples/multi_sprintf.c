#include <stdio.h>

int main() {
    int a = 10;
    int b = 20;
    int c = 30;
    char buf[64];
    sprintf(buf, "%d %d %d", a, b, c);
    printf("%d %d %d\n", a, b, c);
    return 0;
}
