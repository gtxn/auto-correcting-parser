import json
from utils import load_grammar_from_file
from collections import defaultdict
from terminal_productions import terminal_productions
from correction import Correction

class CYK_Parser():
  def __init__(self, grammar_file, fast_mode = True):
    self.fast_mode = fast_mode
    self.grammar = load_grammar_from_file(grammar_file)
    self.insertion_map = self.load_map('additional_files/I.json')
    self.bigram_probabilities = self.load_map('additional_files/bigram_probabilities.json')
    self.correction_service = Correction()

    # Mapping from productions to heads
    self.rev_grammar = self.get_reverse_grammar()

  def get_reverse_grammar(self):
    reversed_mapping = {}
    for head, productions in self.grammar.items():
      for production in productions:
        production_tuple = tuple(production.split(' '))
        if production_tuple in reversed_mapping:
          reversed_mapping[production_tuple].append(head)
        else:
          reversed_mapping[production_tuple] = [head]
    
    return reversed_mapping

  def load_map(self, filename):
    with open(filename) as f:
      return json.load(f)

  def calc_probability_of_sequence(self, sequence, bigram_prob, smooth = 1e-10):
    total_prob = 1
    for i in range(len(sequence)-1):
      bigram = f"{sequence[i][0]}-{sequence[i+1][0]}"
      if bigram in bigram_prob:
        total_prob *= bigram_prob[bigram]
      else:
        total_prob *= smooth

    return total_prob

  # Parsing algorithm referencing Wikipedia
  def parse(self, to_parse):
    len_input = len(to_parse)

    T = [[set() for _ in range(len_input+1)] for _ in range(len_input)]
    back = [[defaultdict(list) for _ in range(len_input+1)] for _ in range(len_input)]
    
    for i, (token, value) in enumerate(to_parse):
      for lhs in self.rev_grammar.get((token,), []):
        T[i][1].add(lhs)

    for l in range(2, len_input+1): # Length of span
      for s in range(len_input - l + 1): # Start of span
        for p in range(1,l+1): # Partition
          for A, productions in self.grammar.items():
            for production in productions:
              production_arr = production.split(' ')
              if len(production_arr) == 2:
                B, C = production_arr

                if B in T[s][p] and C in T[s+p][l-p]:
                  T[s][l].add(A)
                  back[s][l][A].append((p,B,C))

    return T, back
  
  # Parsing algorithm adapted for error correction referencing MartinLange
  def parse_with_err_correction(self, to_parse):
    len_input = len(to_parse)

    T = [[defaultdict(list) for _ in range(len_input+1)] for _ in range(len_input+1)]
    back = [[defaultdict(list) for _ in range(len_input+1)] for _ in range(len_input)]
    
    for i, (token, token_id) in enumerate(to_parse):
      for head, productions in self.grammar.items():
        for production in productions:
          if len(production.split(' ')) == 1:
            for lhs in self.rev_grammar.get((token,), []):
              if head != lhs and head not in T[i][1]:
                T[i][1][head] = ([f"r|{i}|{production}"], None)
              elif head == lhs:
                T[i][1][head] = ([], None)

    for l in range(2, len_input+1): # Length of span
      for s in range(len_input - l + 1): # Start of span
        for A, productions in self.grammar.items():
          if self.fast_mode and A in T[s][l] and len(T[s][l][A][0])==0:
            continue
          
          for p in range(1,l+1): # Partition
            for production in productions:
              production_arr = production.split(' ')
              if len(production_arr) == 2:
                B, C = production_arr

                # Composed correction
                if B in T[s][p] and C in T[s+p][l-p]:
                  p1, p2 = T[s][p][B][0], T[s+p][l-p][C][0]
                  
                  if self.fast_mode and (len(p1)>3 or len(p2)>3):
                    pass
                  else:
                    correction = self.correction_service.compose(p1,p2)

                    # if A not in T[s][l] or len(correction) < len(T[s][l][A][0]):
                    if A not in T[s][l] or self.compare_corrections(correction, T[s][l][A][0], to_parse):
                      T[s][l][A] = (correction, (p,B,C))
                      back[s][l][A].append((p,B,C))

                # Insertion correction case 1
                if B in T[s][l] and C in self.insertion_map:
                  p_list = T[s][l][B][0]
                  sigma = self.insertion_map[C]

                  if self.fast_mode and (len(p_list)>3 or len(sigma)>3):
                    pass
                  else:
                    correction = self.correction_service.compose_for_insertion_forward(p_list, sigma, s+l)
                    # if A not in T[s][l] or len(correction) < len(T[s][l][A][0]):
                    if A not in T[s][l] or self.compare_corrections(correction, T[s][l][A][0], to_parse):
                      T[s][l][A] = (correction, (None, B, None))
                
                # Insertion correction case 2
                if C in T[s][l] and B in self.insertion_map:
                  p_list = T[s][l][C][0]
                    
                  sigma = self.insertion_map[B]
                  sigma = self.correction_service.offset_indices(sigma, s)

                  if self.fast_mode and (len(p_list)>3 or len(sigma)>3):
                    pass
                  else:
                    correction = self.correction_service.compose_for_insertion_backward(p_list, sigma, s)
                    # if A not in T[s][l] or len(correction) < len(T[s][l][A][0]):
                    if A not in T[s][l] or self.compare_corrections(correction, T[s][l][A][0], to_parse):
                      T[s][l][A] = (correction, (None, None, C))

    return T, back
  
  # How to prioritise corrections 
  def compare_corrections(self, corr1, corr2, code):
    # We always pick the shortest correction
    if len(corr1) < len(corr2):
      return True
    elif len(corr1) > len(corr2):
      return False
    
    # If the corrections are the same length, we calculate the probabilities
    code_corr_1 = self.correction_service.apply_correction(corr1, code)
    code_corr_2 = self.correction_service.apply_correction(corr2, code)

    prob_1 = self.calc_probability_of_sequence(code_corr_1, self.bigram_probabilities)
    prob_2 = self.calc_probability_of_sequence(code_corr_2, self.bigram_probabilities)

    # corr_1 > corr_2 if the probability of code from 1 is higher
    return prob_1 > prob_2

  def get_parse_tree(self, input_string, back):
    return self.get_parse_tree_aux(0, len(input_string), 'start', back, input_string)

  def get_parse_tree_aux(self, s, l, non_terminal, back, input_string):
    if l == 1 and not back[s][l][non_terminal]:
      return (non_terminal, input_string[s])
    
    for p,B,C in back[s][l][non_terminal]:
      left = self.get_parse_tree_aux(s, p, B, back, input_string)
      right = self.get_parse_tree_aux(s+p, l-p, C, back, input_string)

      return (non_terminal, [left, right])
    
    return None

  def get_corrected_code(self, code, T):
    corrected_code = self.correction_service.apply_correction(T[0][-1]['start'][0], code)

    return corrected_code
