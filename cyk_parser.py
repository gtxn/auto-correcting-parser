from utils import load_grammar_from_file
from collections import defaultdict

class CYK_Parser():
  def __init__(self, grammar_file):
    self.grammar = load_grammar_from_file(grammar_file)

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
