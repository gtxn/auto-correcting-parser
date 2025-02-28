from lexer import Lexer
from cyk_parser import CYK_Parser
from reverse_parser import Reverse_Parser
import sys
from uuid import UUID

filename = sys.argv[1]
beam_search_n = int(sys.argv[2]) if len(sys.argv)>=3 else -1

if __name__ == '__main__':
  with open(filename) as f:
    conts = f.read()
    lexer = Lexer(conts)
    # Probabilities approximated from grammar
    # parser = CYK_Parser('./cnf_grammar.gram', fast_mode=True, beam_search_n=beam_search_n, threads=30, grammar_mode='approx_from_grammar')
    
    # Probabilities obtained from analysis on code
    parser = CYK_Parser('./additional_files/grammar_probabilities.json', fast_mode=True, beam_search_n=beam_search_n, threads=30, grammar_mode='from_data')

    rev_parser = Reverse_Parser(tab_spaces=2)
    
    # LEXING
    print('Lexing...')
    tokens_with_code_pos, values_appeared = lexer.tokenise()
    tokens_with_id, value_map = lexer.get_id_mapped_tokens()
    tokens_with_id = tokens_with_id[:-1]
    print(f'CODE TO CORRECT\n{tokens_with_id}')
    print()
    
    # PARSE WITH ERR CORRECTION
    print('Parsing...')
    T = []
    if beam_search_n > -1:
      # corrected_code = parser.correct_code_with_err_correction_beam_block(tokens_with_id)
      corrected_code = parser.correct_code_with_err_correction_beam_block_optimised(tokens_with_id)
      corrected_final_code = lexer.reverse_lex(corrected_code, value_map, values_appeared)
      print()
      print(f'CORRECTED CODE\n{corrected_final_code}')
      
    else:
      T = parser.parse_with_err_correction(tokens_with_id)
