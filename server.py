from flask import Flask, request, jsonify
import subprocess
from flask_cors import CORS
from lexer import Lexer
from cyk_parser import CYK_Parser

app = Flask(__name__)
CORS(app)


@app.route("/run", methods=["POST"])
def run_code():
    data = request.json
    code = data.get("code", "")
    beam_search_n = data.get("beam_search_n", 5)
    
    parser = CYK_Parser('./additional_files/grammar_probabilities.json', fast_mode=True, beam_search_n=int(beam_search_n), threads=30, grammar_mode='from_data')
    lexer = Lexer(code)

    try:
      print('Lexing...')
      tokens_with_code_pos, values_appeared = lexer.tokenise()
      tokens_with_id, value_map = lexer.get_id_mapped_tokens()
      tokens_with_id = tokens_with_id[:-1]

      print(f'CODE TO CORRECT\n{tokens_with_id}')
      print()
      
      # PARSE WITH ERR CORRECTION
      print('Parsing...')
      T = []
      if int(beam_search_n) > 0:
        corrected_code = parser.correct_code_with_err_correction_beam_block_optimised(tokens_with_id)
        corrected_final_code = lexer.reverse_lex(corrected_code, value_map, values_appeared)

        print()
        print(f'CORRECTED CODE\n{corrected_final_code}')
        return jsonify({"output": corrected_final_code})
    
    except Exception as e:
      print(f"ERROR: {str(e)}")
      return jsonify({"output": "", "error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
