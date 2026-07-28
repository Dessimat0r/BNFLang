#include <stdio.h>
#include <stdint.h>
#include <stddef.h>

struct Point {
    int32_t x;
    int32_t y;
};

int main() {
    int32_t a = 10;
    int64_t b = 32;
    struct Point p;
    p.x = a;
    p.y = b;
    int32_t sum = p.x + p.y;
    printf("%d\n", sum);
    return 0;
}
