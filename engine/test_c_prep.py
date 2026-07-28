import unittest
from engine.c_prep import preprocess_sbnfc

class TestCPrep(unittest.TestCase):
    def test_strip_include(self):
        src = '#include <stdio.h>\nint x = 5;'
        out = preprocess_sbnfc(src)
        self.assertNotIn('#include', out)
        self.assertIn('int x = 5;', out)

    def test_printf_desugar(self):
        src = 'printf("%d\\n", x);\nprintf("%d ", y);\nprintf("\\n");'
        out = preprocess_sbnfc(src)
        self.assertIn('print x;', out)
        self.assertIn('printn y;', out)
        self.assertIn('println;', out)

    def test_sprintf_desugar(self):
        src = 'sprintf(buf, "%d", 42);'
        out = preprocess_sbnfc(src)
        self.assertEqual(out, 'sprintf buf 42;')

if __name__ == "__main__":
    unittest.main()
