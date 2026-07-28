import unittest
from engine.msbnf import compile_msbnf, transform_let_block, expand_for_loops, expand_aliases, BUILTIN_ALIASES

class TestMSBNF(unittest.TestCase):
    def test_single_let_desugar(self):
        input_text = "let x = 5;\n x + 1"
        expected = "LET(x, 5, x + 1)"
        self.assertEqual(transform_let_block(input_text), expected)

    def test_multi_let_desugar(self):
        input_text = 'let ref_off = OffOfPtr(ref);\nlet anno = v + "@" + n;\n"lea rax, [rbp-" + ref_off + "]"'
        expected = 'LET(ref_off, OffOfPtr(ref), LET(anno, v + "@" + n, "lea rax, [rbp-" + ref_off + "]"))'
        self.assertEqual(transform_let_block(input_text), expected)

    def test_alias_expansion(self):
        input_text = 'MulExpr ::= $NO_MUL:l "*" $NUM:n => RULE("Expr", l)'
        expanded = expand_aliases(input_text, BUILTIN_ALIASES)
        self.assertIn(r'/(?:[^*/(]+|\((?:[^()]+|\((?:[^()]+|\([^()]*\))*\))*\))+/:l', expanded)
        self.assertIn(r'/[0-9]+/:n', expanded)

    def test_for_loop_expansion(self):
        input_text = (
            '%for val, shift in [("4","2"), ("8","3")] {\n'
            '          | $NO_MUL:l "*" "{val}" => RULE("Expr", l) + "\\nshl eax, {shift}"\n'
            '}'
        )
        expanded = expand_for_loops(input_text)
        self.assertIn('| $NO_MUL:l "*" "4" => RULE("Expr", l) + "\\nshl eax, 2"', expanded)
        self.assertIn('| $NO_MUL:l "*" "8" => RULE("Expr", l) + "\\nshl eax, 3"', expanded)

    def test_full_compile(self):
        msbnf = (
            'MulExpr ::= $NO_MUL:l "*" "2" => RULE("Expr", l) + "\\nadd eax, eax"\n'
            '%for val, shift in [("4","2"), ("8","3")] {\n'
            '          | $NO_MUL:l "*" "{val}" => RULE("Expr", l) + "\\nshl eax, {shift}"\n'
            '}\n'
        )
        compiled = compile_msbnf(msbnf)
        self.assertIn(r'/(?:[^*/(]+|\((?:[^()]+|\((?:[^()]+|\([^()]*\))*\))*\))+/:l "*" "2"', compiled)
        self.assertIn(r'/(?:[^*/(]+|\((?:[^()]+|\((?:[^()]+|\([^()]*\))*\))*\))+/:l "*" "4"', compiled)
        self.assertIn("shl eax, 2", compiled)

if __name__ == "__main__":
    unittest.main()
