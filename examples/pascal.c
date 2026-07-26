int n = 5;
int row = 0;
int val = 1;
int col = 0;
int sp = 0;
while (row < n) {
    sp = 0;
    while (sp < n - (row + 1)) {
        printsp;
        sp = sp + 1;
    }
    val = 1;
    col = 0;
    while (col < row + 1) {
        printn val;
        val = (val * (row - col)) / (col + 1);
        col = col + 1;
    }
    println;
    row = row + 1;
}
