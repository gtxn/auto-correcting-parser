from lexer import Lexer
from cyk_parser import CYK_Parser
from reverse_parser import Reverse_Parser

import sys

filename = sys.argv[1]

with open(filename) as f:
  conts = f.read()
  lexer = Lexer(conts)
  parser = CYK_Parser('./cnf_grammar.gram', fast_mode=True, beam_search_n=20)
  rev_parser = Reverse_Parser(tab_spaces=2)

  # LEXING
  print('Lexing...')
  tokens, values_appeared = lexer.tokenise()
  tokens_with_id, value_map = lexer.get_id_mapped_tokens()
  print(f'CODE TO CORRECT\n{tokens_with_id}')
  print()
  
  # PARSE WITH ERR CORRECTION
  # T, back = parser.parse_with_err_correction(tokens_with_id)
  print('Parsing...')
  T, T_probs = parser.parse_with_err_correction_beam(tokens_with_id)
  print()

  corrected_code = parser.get_corrected_code(tokens_with_id, T)

  T_corrected, back_corrected = parser.parse(corrected_code)

  corrected_tree = parser.get_parse_tree(corrected_code, back_corrected)
  print(f'CORRECTED TREE\n{corrected_tree}')
  print()
  print(f'CORRECTION\n{T[0][-1]["start"][0]}')
  print()

  # REVERSE PARSE -- get code from tree
  rev_code = rev_parser.reverse_parse(corrected_tree, value_map, values_appeared)
  print(f'CORRECTED CODE\n{rev_code}')
