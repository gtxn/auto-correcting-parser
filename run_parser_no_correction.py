from lexer import Lexer
from cyk_parser import CYK_Parser
from reverse_parser import Reverse_Parser

import sys

filename = sys.argv[1]

with open(filename) as f:
  conts = f.read()
  lexer = Lexer(conts)
  parser = CYK_Parser('./cnf_grammar.gram', fast_mode=True)
  rev_parser = Reverse_Parser(tab_spaces=2)

  # LEXING
  tokens, values_appeared = lexer.tokenise()
  
  # PARSE 
  # T, back = parser.parse(tokens)
  T, back = parser.parse_beam(tokens)


  corrected_tree = parser.get_parse_tree(tokens, back)

  print(f"Tokens:\n {tokens}")
  print()
  print(f'Tree\n{corrected_tree}')