import json
from lexer import Lexer
from cyk_parser import CYK_Parser
from utils import print_table

with open("./file_to_test.py") as f:
  conts = f.read()
  lexer = Lexer(conts)
  parser = CYK_Parser('./cnf_grammar.gram')

  tokens = lexer.tokenise()

  to_parse = [t for (t, val) in tokens]
  T, back = parser.parse_with_err_correction(to_parse)

  print(f'Old parsed: {to_parse}') 
  
  with open('./output.json', 'w') as f2:
    json.dump(T, f2)

  corrected_code = parser.get_corrected_code(to_parse, T)

  print(f"Corrected: {corrected_code}")
