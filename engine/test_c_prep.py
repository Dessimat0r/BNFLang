import unittest
from engine.c_prep import preprocess_sbnfc

class TestCPrep(unittest.TestCase):
    def test_include_stdio(self):
        src = '#include <stdio.h>\nint x = 5;'
        out = preprocess_sbnfc(src)
        self.assertNotIn('#include', out)
        self.assertIn('int x = 5;', out)

    def test_typedef_and_struct(self):
        src = '''
#include <stdint.h>
struct Point {
    int32_t x;
    int32_t y;
};

int main() {
    struct Point p;
    p.x = 10;
    p.y = 20;
    printf("%d\\n", p.x);
    return 0;
}
        '''
        out = preprocess_sbnfc(src)
        self.assertIn('int p_x = 0;', out)
        self.assertIn('int p_y = 0;', out)
        self.assertIn('p_x = 10;', out)
        self.assertIn('print p_x;', out)

if __name__ == "__main__":
    unittest.main()
