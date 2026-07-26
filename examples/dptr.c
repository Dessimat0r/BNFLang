
int n = 5;
int *p = &n;
int **pp = &p;
print **pp;
**pp = 42;
print n;
