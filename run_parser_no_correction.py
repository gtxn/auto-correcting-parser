from lexer import Lexer
from cyk_parser import CYK_Parser
from reverse_parser import Reverse_Parser

import sys

filename = sys.argv[1]

if __name__ == '__main__':
  with open(filename) as f:
    conts = f.read()
    lexer = Lexer(conts)
    parser = CYK_Parser('./cnf_grammar.gram', fast_mode=True, threads=30)
    rev_parser = Reverse_Parser(tab_spaces=2)

    # LEXING
    tokens, values_appeared = lexer.tokenise()
    tokens_with_id, value_map = lexer.get_id_mapped_tokens()
    tokens_with_id = tokens_with_id[:-1]
    print('to parse')
    print(tokens_with_id)
    
    # PARSE 
    # T, back = parser.parse(tokens)
    # T, back = parser.parse_beam(tokens)
    print('PARSING...')
    parser.parse_beam_block(tokens_with_id)

    # corrected_tree = parser.get_parse_tree(tokens_with_id, back)

    # print(f"Tokens:\n {tokens}")
    # print()
    # print(f'Tree\n{corrected_tree}')