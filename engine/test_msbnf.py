import unittest
from engine.msbnf import compile_msbnf, transform_let_block, expand_for_loops, expand_aliases, desugar_newline_concat, desugar_decl_helpers, BUILTIN_ALIASES

class TestMSBNF(unittest.TestCase):
    def test_single_let_desugar(self):
        input_text = "let x = 5;\n x + 1"
        expected = "LET(x, 5, x + 1)"
        self.assertEqual(transform_let_block(input_text), expected)

    def test_multi_let_desugar(self):
        input_text = 'let ref_off = OffOfPtr(ref);\nlet anno = v + "@" + n;\n"lea rax, [rbp-" + ref_off + "]"'
        expected = 'LET(ref_off, OffOfPtr(ref), LET(anno, v + "@" + n, "lea rax, [rbp-" + ref_off + "]"))'
        self.assertEqual(transform_let_block(input_text), expected)

    def test_decl_helper_desugar(self):
        input_text = 'DECL(v, n, i, c, "mov DWORD PTR [rbp-" + n + "], 0\\n")'
        desugared = desugar_decl_helpers(input_text)
        self.assertIn('LET(new_n, n + "8"', desugared)
        self.assertIn('LET(anno, v + "@" + n', desugared)
        self.assertIn('RULE("Decls"', desugared)

    def test_alias_expansion(self):
        input_text = 'MulExpr ::= $NO_MUL:l "*" $NUM:n => RULE("Expr", l)'
        expanded = expand_aliases(input_text, BUILTIN_ALIASES)
        self.assertIn(r'/(?:[^*/(]+|\((?:[^()]+|\((?:[^()]+|\([^()]*\))*\))*\))+/:l', expanded)
        self.assertIn(r'/[0-9]+/:n', expanded)

    def test_for_loop_expansion(self):
        input_text = (
            '%for val, shift in [("4","2"), ("8","3")] {\n'
            '          | $NO_MUL:l "*" "{val}" => RULE("Expr", l) \\+ "shl eax, {shift}"\n'
            '}'
        )
        expanded = expand_for_loops(input_text)
        self.assertIn('| $NO_MUL:l "*" "4" => RULE("Expr", l) \\+ "shl eax, 2"', expanded)

    def test_newline_concat(self):
        input_text = 'RULE("Expr", l) \\+ "mov ecx, eax" \\+ RULE("Expr", r)'
        desugared = desugar_newline_concat(input_text)
        self.assertEqual(desugared, 'RULE("Expr", l) + "\\n" + "mov ecx, eax" + "\\n" + RULE("Expr", r)')

    def test_full_compile(self):
        msbnf = (
            'MulExpr ::= $NO_MUL:l "*" "2" => RULE("Expr", l) \\+ "add eax, eax"\n'
            '%for val, shift in [("4","2"), ("8","3")] {\n'
            '          | $NO_MUL:l "*" "{val}" => RULE("Expr", l) \\+ "shl eax, {shift}"\n'
            '}\n'
        )
        compiled = compile_msbnf(msbnf)
        self.assertIn(r'/(?:[^*/(]+|\((?:[^()]+|\((?:[^()]+|\([^()]*\))*\))*\))+/:l "*" "2"', compiled)
        self.assertIn('+ "\\n" + "add eax, eax"', compiled)

if __name__ == "__main__":
    unittest.main()
