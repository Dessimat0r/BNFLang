int n = 5;
int i = 0;
int *p = &n;
while (i < 3) {
    print *p;
    *p = *p - 1;
    i = i + 1;
}
