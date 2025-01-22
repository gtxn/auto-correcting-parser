import json
from utils import load_grammar_from_file
from collections import defaultdict
from terminal_productions import terminal_productions
from correction import Correction

class CYK_Parser():
  def __init__(self, grammar_file):
    self.grammar = load_grammar_from_file(grammar_file)
    self.insertion_map = self.load_insertion_map('I.json')
    self.correction_service = Correction()

    # Mapping from productions to heads
    self.rev_grammar = self.reverse_parse()

  def reverse_parse(self):
    reversed_mapping = {}
    for head, productions in self.grammar.items():
      for production in productions:
        production_tuple = tuple(production.split(' '))
        if production_tuple in reversed_mapping:
          reversed_mapping[production_tuple].append(head)
        else:
          reversed_mapping[production_tuple] = [head]
    
    return reversed_mapping

  def load_insertion_map(self, filename):
    with open(filename) as f:
      return json.load(f)

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
    
    for i, token in enumerate(to_parse):
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
        for p in range(1,l+1): # Partition
          for A, productions in self.grammar.items():
            for production in productions:
              production_arr = production.split(' ')
              if len(production_arr) == 2:
                B, C = production_arr

                # Composed correction
                if B in T[s][p] and C in T[s+p][l-p]:
                  p1, p2 = T[s][p][B][0], T[s+p][l-p][C][0]

                  correction = self.correction_service.compose(p1,p2)

                  if A not in T[s][l] or len(correction) < len(T[s][l][A][0]):
                    T[s][l][A] = (correction, (p,B,C))
                    back[s][l][A].append((p,B,C))

                # Insertion correction case 1
                if B in T[s][l] and C in self.insertion_map:
                  p_list = T[s][l][B][0]
                  sigma = self.insertion_map[C]

                  correction = self.correction_service.compose_for_insertion_forward(p_list, sigma,s+l)
                  if A not in T[s][l] or len(correction) < len(T[s][l][A][0]):
                    T[s][l][A] = (correction, (None, B, None))
                
                # Insertion correction case 2
                if C in T[s][l] and B in self.insertion_map:
                  p_list = T[s][l][C][0]
                  sigma = self.insertion_map[B]
                  sigma = self.correction_service.offset_indices(sigma, s)

                  correction = self.correction_service.compose_for_insertion_backward(p_list, sigma,s+l)
                  if A not in T[s][l] or len(correction) < len(T[s][l][A][0]):
                    T[s][l][A] = (correction, (None, None, C))

    return T, back

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

    # print(f"Correction: {T[0][-1]['start']}")
    return corrected_code
