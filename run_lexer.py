from lexer import Lexer

with open("./file_to_test.py") as f:
  conts = f.read()
  lexer = Lexer(conts)
  tokens = lexer.tokenise()
  print(tokens)