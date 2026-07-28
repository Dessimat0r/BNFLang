int a = 10;
int b = 20;
int c = 30;
{
    a = a + b;
    b = b + c;
    c = a + b + c;
    print a;
    print b;
    print c;
}
print a;
print b;
print c;
a = a - b;
print a;
b = c - a;
print b;
