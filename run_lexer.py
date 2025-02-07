from lexer import Lexer
import sys

filename = sys.argv[1]

with open(filename) as f:
  conts = f.read()
  lexer = Lexer(conts)
  tokens = lexer.tokenise()
  print(tokens)