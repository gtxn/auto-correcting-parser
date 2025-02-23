import json
from collections import defaultdict
from utils import load_grammar_from_file, get_empty
from terminal_productions import terminal_productions

grammar = load_grammar_from_file('./cnf_grammar.gram')
terminals = terminal_productions.values()
nullable = get_empty(grammar)

I_map = defaultdict(list)
failed_nodes = set()

def get_minimal_terminal_insertions(head, path=None):
  if path is None:
    path = set()
  
  if head in terminal_productions:
    if head == 'terminal_1':
      print('head terminal1')
    I_map[head] = [terminal_productions[head]]
    return [terminal_productions[head]]
  elif head in nullable:
    I_map[head] = []
    return []
  elif head in I_map:
    return I_map[head]

  if head in path:
    return I_map[head] if head in I_map else None

  path.add(head)

  productions = sorted(grammar[head], key=lambda x: len(x))

  # Keeps track of the minimal insertion for the non terminal
  minimal_for_nonterminal = None

  for production in productions:
    prod_arr = production.split(" ")

    if len(prod_arr) == 1:
      if prod_arr[0] == "''":
        I_map[head] = []
        minimal_for_prod = []
      elif head not in I_map:
        I_map[head] = [prod_arr[0]]
        minimal_for_prod = [prod_arr[0]]
    else:
      try:
        left_insertion = get_minimal_terminal_insertions(prod_arr[0], path)
        right_insertion = get_minimal_terminal_insertions(prod_arr[1], path)

        if left_insertion is None:
          continue
        if right_insertion is None:
          continue

        minimal_for_prod = left_insertion + right_insertion
      except Exception as e: # If one of the rules were recursive go to the next rule
        continue

    if minimal_for_nonterminal is None or len(minimal_for_prod) < len(minimal_for_nonterminal):
      minimal_for_nonterminal = minimal_for_prod
  
  path.remove(head)
  
  # No non cyclic rules were found for the non terminal
  if minimal_for_nonterminal is None:
    raise Exception(f'Cycle for {head}. Productions: {productions}.')

  I_map[head] = minimal_for_nonterminal
  return minimal_for_nonterminal

# Start the traversal from the start node
get_minimal_terminal_insertions('start')

# If there are non terminals in the grammar that haven't been traversed, traverse them
for head in grammar:
  if head not in I_map:
    get_minimal_terminal_insertions(head)

# Check to make sure all non terminals have been considered
for head in grammar:
  if head not in I_map:
    print(f'not in: {head}')

# Convert terminals to insert into insertion corrections
I_map_corrections = {}
for nonterminal, minimal_insertion in I_map.items():
  if len(minimal_insertion) == 0:
    I_map_corrections[nonterminal] = []
  else:
    minimal_insertion.reverse()
    I_map_corrections[nonterminal] = [["i", '0', term] for term in minimal_insertion]

with open("I.json", 'w') as f:
  json.dump(I_map_corrections, f)

print("Successfully created I")