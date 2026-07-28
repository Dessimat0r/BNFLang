import unittest
from engine.msbnf import compile_msbnf, transform_let_block

class TestMSBNF(unittest.TestCase):
    def test_single_let_desugar(self):
        input_text = "let x = 5;\n x + 1"
        expected = "LET(x, 5, x + 1)"
        self.assertEqual(transform_let_block(input_text), expected)

    def test_multi_let_desugar(self):
        input_text = "let ref_off = OffOfPtr(ref);\nlet anno = v + \"@\" + n;\n\"lea rax, [rbp-\" + ref_off + \"]\""
        expected = 'LET(ref_off, OffOfPtr(ref), LET(anno, v + "@" + n, "lea rax, [rbp-" + ref_off + "]"))'
        self.assertEqual(transform_let_block(input_text), expected)

    def test_rule_action_desugar(self):
        msbnf = (
            "TryDecl ::= /[0-9]+/:n \"int\" /[a-zA-Z_]\\w*/:v \";\"\n"
            "    => let new_n = n + \"8\";\n"
            "       let anno = v + \"@\" + n;\n"
            "       RULE(\"Decls\", new_n + anno)\n"
        )
        compiled = compile_msbnf(msbnf)
        self.assertIn('LET(new_n, n + "8", LET(anno, v + "@" + n, RULE("Decls", new_n + anno)))', compiled)

if __name__ == "__main__":
    unittest.main()
