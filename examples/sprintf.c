#include <stdio.h>

int main() {
    int val = 42;
    int buf = 0;
    sprintf(buf, "%d", val);
    printf("%d\n", val);
    return 0;
}
