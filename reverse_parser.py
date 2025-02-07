# Reverse parser takes a parse tree and generates code from it
class Reverse_Parser():
  def __init__(self, tab_spaces):
    self.tab_spaces = tab_spaces

  def reverse_parse(self, tree, value_mapping, values):
    raw_code = self.get_raw_code(tree, value_mapping, values)
    code = ''
    num_indent = 0

    for line in raw_code.split('NEWLINE'):
      line = line.strip().split(' ')
      new_line = []
      for token in line:
        if token == 'INDENT':
          num_indent += 1
        elif token == 'DEDENT':
          num_indent -= 1
        elif token == 'ENDMARKER':
          pass
        else:
          new_line.append(token)
    
      code += ' '*self.tab_spaces*num_indent + ' '.join(new_line) + '\n'

    return code
      

  def get_raw_code(self, tree, value_mapping, values):
    if type(tree[1]) == tuple:
      node = tree[1][0]
      if node == 'FSTRING_MIDDLE' or node == 'NUMBER' or node == 'NAME':
        if tree[1][1] in value_mapping:
          node = value_mapping[tree[1][1]]
        else:
          node = self.get_value_for_node(tree[1][0], values)

      return node
    else:
      left, right = tree[1]
      left_node_code = self.get_raw_code(left, value_mapping, values)
      right_node_code = self.get_raw_code(right, value_mapping, values)

      return left_node_code + ' ' + right_node_code

  # Gets a random value already in the value list 
  def get_value_for_node(self, node_type, values):
    return values[node_type][0]