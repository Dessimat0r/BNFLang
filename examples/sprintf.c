#include <stdio.h>

int main() {
    int val = 42;
    char buf[64];
    sprintf(buf, "%d", val);
    printf("%d\n", val);
    return 0;
}
