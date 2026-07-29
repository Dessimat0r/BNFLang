#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.grammar import Grammar
from engine.matcher import match_grammar
from engine.c_prep import preprocess_sbnfc


def main():
    if len(sys.argv) < 3:
        print("Usage: python -m engine <grammar.sbnf> <input.c> [output.s]")
        sys.exit(1)

    grammar_path = sys.argv[1]
    input_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else None

    with open(grammar_path) as f:
        grammar = Grammar.parse(f.read())

    with open(input_path) as f:
        input_text = f.read()

    # Preprocess C source files (.c)
    if input_path.endswith('.c') or input_path.endswith('.sbnfc'):
        input_text = preprocess_sbnfc(input_text)
    else:
        # Escape null bytes so \x00 can be used as field separator
        input_text = input_text.replace('\x00', '\\x00')

    state = {'_grammar': grammar}
    result = match_grammar(grammar, input_text, state)

    if result is None:
        print("Error: parse failed", file=sys.stderr)
        sys.exit(1)

    if isinstance(result, bytes):
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(result)
        else:
            sys.stdout.buffer.write(result)
    else:
        output = str(result)
        if output_path:
            with open(output_path, 'w') as f:
                f.write(output)
        else:
            sys.stdout.write(output)


if __name__ == '__main__':
    main()
