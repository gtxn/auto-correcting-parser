import json
from collections import defaultdict
from utils import load_grammar_from_file, get_nullable
from terminal_productions import terminal_productions

grammar = load_grammar_from_file('./cnf_grammar.gram')
terminals = terminal_productions.values()
nullable = get_nullable(grammar)

# Tracks which non terminals are currently involved in the head's loop
# visiting[A] = [B, C, D] means that while traversing A -> B C, we visited nodes B, C, D
# visiting = {}
# comes_from = defaultdict(list)

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
      # visiting[head].add(prod_arr[0])
      # visiting[head].add(prod_arr[1])
      # comes_from[prod_arr[0]] += comes_from[head] + [head]
      # comes_from[prod_arr[1]] += comes_from[head] + [head]

      # continue_main_loop = False
      # for comes_from_nt in comes_from[head]:
      #   visiting[comes_from_nt].add(prod_arr[0])
      #   visiting[comes_from_nt].add(prod_arr[1])
      #   if comes_from_nt in visiting[comes_from_nt] and comes_from_nt not in I_map and comes_from_nt not in nullable:
      #     continue_main_loop = True
      #     visiting[comes_from_nt].remove(prod_arr[0])
      #     visiting[comes_from_nt].remove(prod_arr[1])
      #     failed_heads.add(comes_from_nt)
      #     # break
      # if continue_main_loop:
      #   continue

      # If production rule is recursive, ignore
      # for v_head in visiting:
      #   if v_head in visiting[v_head]:
      #     continue
        
      # if head in visiting[head]:
      #   continue

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
        # print(head, f'err: {e}\n')

    if minimal_for_nonterminal is None or len(minimal_for_prod) < len(minimal_for_nonterminal):
      minimal_for_nonterminal = minimal_for_prod
  
  path.remove(head)
  
  # No non cyclic rules were found for the non terminal
  if minimal_for_nonterminal is None:
    raise Exception(f'Cycle for {head}. Productions: {productions}.')

  I_map[head] = minimal_for_nonterminal
  return minimal_for_nonterminal

get_minimal_terminal_insertions('start')

for head in grammar:
  if head not in I_map:
    get_minimal_terminal_insertions(head)

for head in grammar:
  if head not in I_map:
    print(f'not in: {head}')

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