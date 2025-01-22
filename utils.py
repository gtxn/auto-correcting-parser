import re

def load_grammar_from_file(file):
  grammar = {}
  current_non_terminal = ''

  with open(file, 'r') as f:
    conts = f.read().split('\n')
    for line in conts:
      # Ignore empty lines and comments 
      if not line or line.startswith('#'):
        continue

      line_to_consider = line.strip()
      
      if re.match(r'(\w+):', line_to_consider):
        split_colon_arr = line_to_consider.split(':')

        current_non_terminal = split_colon_arr[0].strip()
        if (split_colon_arr[1]):
          grammar[current_non_terminal] = [':'.join(split_colon_arr[1:]).strip()]

      elif (line_to_consider.startswith('|')):
        rule = line_to_consider[1:].strip()
        if current_non_terminal not in grammar:
          grammar[current_non_terminal] = [rule]
        else:
          grammar[current_non_terminal].append(rule)
  
    return grammar

def deepcopy(grammar_obj):
  copied = {}
  for key, rules in grammar_obj.items():
    copied[key] = rules.copy()
  
  return copied

def check_grammar_obj_for_regex(grammar_obj, regex_expr):
  for rules in grammar_obj.values():
    for rule in rules:
      if re.search(regex_expr, rule+'\n'):
        return True
      
  return False

def print_table(table, table_name):
  for tindex, table_entry in enumerate(table):
    print(f'{table_name} {tindex}')
    for i, b in enumerate(table_entry):
      print(i, b)
    print()