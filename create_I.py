import json
from collections import defaultdict
from utils import load_grammar_from_file
from terminal_productions import terminal_productions

grammar = load_grammar_from_file('./cnf_grammar.gram')
terminals = terminal_productions.values()

# Tracks which non terminals are currently involved in the loop
visiting = []

I_map = defaultdict(list)

def get_minimal_terminal_insertions(head):
  if head in terminal_productions:
    return [terminal_productions[head]]
  elif head in I_map:
    return I_map[head]

  productions = sorted(grammar[head], key=lambda x: len(x))

  # Keeps track of the minimal insertion for the non terminal
  minimal_for_nonterminal = []
  visiting.append(head)

  for production in productions:
    prod_arr = production.split(" ")

    if len(prod_arr) == 1:
      I_map[head] = [prod_arr[0]]
      minimal_for_prod = [prod_arr[0]]
    else:
      # If production rule is recursive, ignore
      if prod_arr[0] in visiting or prod_arr[1] in visiting:
        continue

      try:
        minimal_for_prod = get_minimal_terminal_insertions(prod_arr[0]) + get_minimal_terminal_insertions(prod_arr[1])
      except: # If one of the rules were recursive go to the next
        # 'Undo' the visit 
        visiting.pop()
        continue

    if len(minimal_for_nonterminal)==0 or len(minimal_for_prod) < len(minimal_for_nonterminal):
      minimal_for_nonterminal = minimal_for_prod
  
  # No non cyclic rules were found for the non terminal
  if len(minimal_for_nonterminal) == 0:
    raise Exception('Cycle')

  visiting.pop()
  I_map[head] = minimal_for_nonterminal
  return minimal_for_nonterminal



get_minimal_terminal_insertions('start')

I_map_corrections = {}
for nonterminal, minimal_insertion in I_map.items():
  minimal_insertion.reverse()
  I_map_corrections[nonterminal] = [f"i|0|{term}" for term in minimal_insertion]

with open("I.json", 'w') as f:
  json.dump(I_map_corrections, f)

print("Successfully created I")