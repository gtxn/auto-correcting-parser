import re
import json
from collections import defaultdict
from terminals import *

def load_grammar_from_file(file):
  grammar = {}
  current_non_terminal = ''

  rule_counts = defaultdict(int)
  lhs_counts = defaultdict(int)

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
        if (split_colon_arr[1].strip()):
          rule = ':'.join(split_colon_arr[1:]).strip()
          grammar[current_non_terminal] = [rule]
          rule_counts[(current_non_terminal, rule)] += 1
          lhs_counts[current_non_terminal] += 1
        
        # Handle case for colon terminal
        elif len(split_colon_arr)>2:
          grammar[current_non_terminal] = [':']
          rule_counts[(current_non_terminal, ':')] += 1
          lhs_counts[current_non_terminal] += 1

      elif (line_to_consider.startswith('|')):
        rule = line_to_consider[1:].strip()
        if current_non_terminal not in grammar:
          grammar[current_non_terminal] = [rule]
        else:
          grammar[current_non_terminal].append(rule)
        rule_counts[(current_non_terminal, rule)] += 1
        lhs_counts[current_non_terminal] += 1

    rule_probabilities = {
      lhs: {rhs: rule_counts[(lhs, rhs)] / lhs_counts[lhs] for (lhs_rule, rhs) in rule_counts if lhs_rule == lhs}
      for lhs in lhs_counts
    }

    return rule_probabilities

def get_empty(grammar):
  nullable = set()
  # find nullable non terminals
  for head, productions in grammar.items():
    for production in productions.keys():
      if production == "''":
        nullable.add(head)
  
  for head, productions in grammar.items():
    for production in productions.keys():
      prod_arr = production.split(' ')
      if len(prod_arr) > 1:
        if prod_arr[0] in nullable and prod_arr[1] in nullable:
          nullable.add(head)

  return nullable

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

def split_into_blocks(lexed_code):
  with open('./additional_files/reliant_blocks.json') as f:
    reliant_blocks = json.load(f)
  
  # For each indent level, maintain the blocks at that level
  indent_block_map = [[]]

  # Parallel array that tracks the indent level of each line
  indent_line_parallel_arr = []
  curr_indent = 0
  
  # Initialise indent block map and indent map
  for (token, _id, code_pos) in lexed_code:
    if token == 'NEWLINE':
      indent_line_parallel_arr.append(curr_indent)
      indent_block_map[curr_indent] = [[]]
    elif token == 'INDENT':
      curr_indent += 1
      if curr_indent >= len(indent_block_map):
        indent_block_map.append([])
    elif token == 'DEDENT':
      curr_indent -= 1
  
  curr_indent = 0
  curr_line = 0

  # Tracks if prev token is a dedent token
  prev_token_dedent = False

  # Adds to block map
  for (token, _id, code_pos) in lexed_code:
    if token == 'DEDENT':
      # Start new block
      indent_block_map[curr_indent].append([])
      curr_indent -= 1

      # Append dedent to end of indented block
      indent_block_map[curr_indent][-1].append((token, _id, code_pos))

      # Start new dedent block
      indent_block_map[curr_indent].append([])
      prev_token_dedent = True
    elif token == 'NEWLINE':
      if not prev_token_dedent:
        # If we didn't just dedent, add the NEWLINE to current indent
        indent_block_map[curr_indent][-1].append((token, _id, code_pos))

        # If the next line is at the same indent level we can split into a diff block
        if curr_line+1 < len(indent_line_parallel_arr) and indent_line_parallel_arr[curr_line+1] == curr_indent:
          indent_block_map[curr_indent].append([])
        prev_token_dedent = False
      else:
        prev_token_dedent = True
        
      curr_line += 1
    elif token == 'INDENT':
      indent_block_map[curr_indent][-1].append((token, _id, code_pos))
      indent_block_map[curr_indent][-1].append(('STUB-BLOCK', _id+1, ()))
      curr_indent += 1
      prev_token_dedent = False
    else:
      indent_block_map[curr_indent][-1].append((token, _id, code_pos))
      prev_token_dedent = False

  # Filter out [] at the end of some indents, and join reliant blocks
  indent_block_map_update = []

  for b_indent in indent_block_map:
    curr_indent = []
    i = 0
    while i < len(b_indent):
      b = b_indent[i]
      if len(b) > 0:
        to_append = b
        
        # Keep coalescing 2 blocks if they are reliant
        while i < len(b_indent)-2:
          next_b = b_indent[i+1]
          if len(next_b):
            is_reliant = False
            if next_b[0][0] in reliant_blocks and b[0][0] in reliant_blocks[next_b[0][0]]:
              is_reliant = True
            
            if is_reliant:
              to_append += next_b
              i += 1
            else:
              break
          else:
            break
        
        curr_indent.append(to_append)
      i += 1

    indent_block_map_update.append(curr_indent)

  print('BLOCKS --')
  for i, blocks in enumerate(indent_block_map_update):
    print(i)
    for b in blocks:
      print(b)
    print()

  return indent_block_map_update

def reconstruct_blocks(corrected_blocks):
  reconstructed_blocks = corrected_blocks

  for indent_num in range(len(corrected_blocks)-2, -1, -1):
    blocks = reconstructed_blocks[indent_num]

    for block_num, block in enumerate(blocks):
      total_replacements = 0 
      for token_num, (token, _id, code_pos) in enumerate(block):
        # Tracks updated token number, incase we have multiple replacements
        updated_token_num = token_num + total_replacements
        if token == 'STUB-BLOCK':
          # Get replacement block for stub
          replacement = reconstructed_blocks[indent_num+1][-1]
          for block_ in reconstructed_blocks[indent_num+1]:
            if block_[0][1] == _id:
              replacement = block_
              continue

          # Perform the replacement
          blocks[block_num] = blocks[block_num][:updated_token_num] + replacement + blocks[block_num][updated_token_num+1:]
          # Update length of replacement we made
          total_replacements += len(replacement)-1

  # Flatten the statements at indent 0
  reconstructed_code = [
    x
    for xs in reconstructed_blocks[0]
    for x in xs
  ]

  return reconstructed_code