import re

# def save_grammar(grammar, filename_to_save):
#   with open(filename_to_save, 'w') as f:
#     for key, rules in grammar.items():
#       f.write(f"{key}: ")

#       rules_copy = rules
#       # If rules are in list form, join them into string first
#       if rules and type(rules[0]) == list:
#         rules_copy = rules.copy()
#         for i, rule in enumerate(rules):
#           rules_copy[i] = ' '.join(rule)
      
#       if len(rules_copy) == 1:
#         f.write(f"{rules_copy[0]}")
#       else:  
#         f.write(f"\n\t| {'\n\t| '.join(rules_copy)}")

#       f.write('\n\n')

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