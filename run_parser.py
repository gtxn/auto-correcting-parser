from lexer import Lexer
from cyk_parser import CYK_Parser
from utils import print_table

with open("./file_to_test.py") as f:
  conts = f.read()
  lexer = Lexer(conts)
  parser = CYK_Parser('./cnf_grammar.gram')

  tokens = lexer.tokenise()
  T, back = parser.parse(tokens)

  # print(tokens) 
  # print_table(T, 'Non-terminals')
  # print_table(back, 'Backpointers')


  print(parser.get_parse_tree(tokens, back))