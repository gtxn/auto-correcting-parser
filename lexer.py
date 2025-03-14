from terminals import *
from collections import defaultdict

operator_map = {
  '=': 'ASSIGN',
  '+': 'PLUS',
  '-': 'MINUS',
  '*': 'TIMES',
  '/': 'DIVIDE',
  '**': 'POWER',
  '%': 'MODULO',
  '//': 'QUOTIENT',
  '==': 'EQUAL',
  '!=': 'NOTEQUAL',
  '<': 'LESSTHAN',
  '>': 'MORETHAN',
  '~': 'TILDE',
  '...': 'ELLIPSIS',
}

# TODO: fix the bug for block parsing with dedents not working
class Lexer:
  def __init__(self, source_code, tab_spaces=2):
    self.source = source_code
    self.logical_line_to_physical_line_map = [] # Keeps track of mapping between logical and physical lines
    self.preprocess()
    self.tokens = []
    self.current_char = None
    self.position = -1
    self.x_position = -1
    self.current_logical_line = 0
    self.tab_spaces = tab_spaces
    self.prev_f = False # To tokenize f-strings
    self.values_appeared = defaultdict(list) # Values of all NAME and NUMBER that appear in code
    self.step()

  # Steps to next token
  def step(self):
    self.position += 1
    self.current_char = self.source[self.position] if self.position < len(self.source) else None
    self.x_position += 1

  def tokenise(self):
    while self.current_char is not None:
      if self.current_char in WHITESPACE:
        self.step()
      
      elif self.current_char == "'" or self.current_char == '"':
        # TODO: deal with format string!! Currently just treating inside as normal string
        if self.prev_f:
          self.tokens.pop()
          self.tokens.append(('FSTRING_START', 'FSTRING_START', (self.x_position, self.logical_line_to_physical_line_map[self.current_logical_line])))
          delimiter = self.current_char
          str_string = ""

          # Step from opening delimiter
          self.step()

          # Go through whole string
          while self.current_char and self.current_char != delimiter:
            str_string += self.current_char
            self.step()

          if not self.current_char:
            raise Exception(f"UNCLOSED {delimiter}")
          
          self.tokens.append(("FSTRING_MIDDLE", str_string, (self.x_position, self.logical_line_to_physical_line_map[self.current_logical_line])))
          
          # Step from closing delimiter
          self.step() 

          self.tokens.append(("FSTRING_END", "FSTRING_END", (self.x_position, self.logical_line_to_physical_line_map[self.current_logical_line])))
        else:
          self.tokens.append(self.process_string())

      elif self.current_char in DIGITS:
        num = self.number()
        self.tokens.append(("NUMBER", num, (self.x_position-1, self.logical_line_to_physical_line_map[self.current_logical_line])))
        self.values_appeared['NUMBER'].append(num)
      
      elif self.current_char in LETTERS or self.current_char == "_":
        self.prev_f = self.current_char == 'f' or self.current_char == 'F'
        self.tokens.append(self.identifier_or_keyword_or_token())
      
      elif self.current_char in OPERATORS:
        self.tokens.append(self.operator())
      
      elif self.current_char in DELIMITERS:
        self.tokens.append((self.current_char, self.current_char, (self.x_position, self.logical_line_to_physical_line_map[self.current_logical_line])))
        self.step()
      
      else:
        self.step()
        # raise ValueError(f"Unexpected character: {self.current_char}")

    # self.tokens.append(('NEWLINE', 'NEWLINE'))
    self.tokens.append(('ENDMARKER', 'ENDMARKER', (self.x_position, self.logical_line_to_physical_line_map[self.current_logical_line])))
    return self.tokens, self.values_appeared
  
  def get_id_mapped_tokens(self):
    tokens_with_id = []
    value_map = defaultdict()

    for i, t in enumerate(self.tokens):
      tokens_with_id.append((t[0], i, t[-1]))
      value_map[i] = t[1]

    return tokens_with_id, value_map

  def number(self):
    num = ""
    while self.current_char and self.current_char in DIGITS:
      num += self.current_char
      self.step()
    return num

  def identifier_or_keyword_or_token(self):
    id_str = ""
    while self.current_char and (self.current_char in LETTERS or self.current_char in DIGITS or self.current_char == "_"):
      id_str += self.current_char
      self.step()

    if id_str in KEYWORDS:
      return (id_str, id_str, (self.x_position-1, self.logical_line_to_physical_line_map[self.current_logical_line]))
    if id_str in PREPROCESS_TOKENS:
      if id_str == 'NEWLINE':
        self.x_position = -1
        self.current_logical_line += 1
      elif id_str == 'INDENT':
        self.x_position -= len(' INDENT ')
      elif id_str == 'DEDENT':
        self.x_position -= len(' DEDENT ')
      to_return = id_str, id_str, (self.x_position, self.logical_line_to_physical_line_map[self.current_logical_line])

      return to_return
    
    self.values_appeared['NAME'].append(id_str)
    
    return ("NAME", id_str, (self.x_position-1, self.logical_line_to_physical_line_map[self.current_logical_line]))

  def operator(self):
    op = self.current_char
    self.step()
    # Handle multi-character operators like `==`, `!=`
    if self.current_char and (op + self.current_char) in OPERATORS:
      op += self.current_char
      self.step()
    return (op, op, (self.x_position-1, self.logical_line_to_physical_line_map[self.current_logical_line]))
  
  def process_string(self):
    delimiter = self.current_char
    str_string = ""

    # Step from opening delimiter
    self.step()

    # Go through whole string
    while self.current_char and self.current_char != delimiter:
      str_string += self.current_char
      self.step()

    if not self.current_char:
      raise Exception(f"UNCLOSED {delimiter}")
    
    # Step from closing delimiter
    self.step() 

    return ("STRING", str_string, (self.x_position-1, self.logical_line_to_physical_line_map[self.current_logical_line]))

  def preprocess(self):    
    # Split into logical lines
    logical_lines = []
    logical_line = ''
    physical_line_num = 0

    for physical_line in self.source.split('\n'):
      if physical_line.strip().endswith('\\'):
        logical_line += physical_line.replace('\\', '')
      
      # Ensure physical line is not a comment or empty
      elif physical_line.strip() and not physical_line.strip().startswith('#'):
        # If comment in the middle of a line, remove it 
        logical_line += physical_line.split('#')[0]
        logical_lines.append(logical_line)
        logical_line = ''
        self.logical_line_to_physical_line_map.append(physical_line_num)

      physical_line_num += 1

    # Calculate dedent and indents
    # Stack to keep track of indentations
    indent_stack = [0]
    for i, logical_line in enumerate(logical_lines):
      # Get indentation of current line
      current_line_indent = 0
      
      num_preceding_space_characters = len(logical_line) - len(logical_line.lstrip())
      for space_char_i in range(num_preceding_space_characters):
        space_char = logical_line[space_char_i]
        if space_char == '\t':
          current_line_indent += self.tab_spaces
        elif space_char == ' ':
          current_line_indent += 1

      # Check level compared to stack
      current_indent_level = indent_stack[-1] 

      # INDENT
      if current_line_indent > current_indent_level:
        logical_lines[i] = ' INDENT ' + logical_line
        indent_stack.append(current_line_indent)
      
      # DEDENT
      if current_line_indent < current_indent_level:
        num_dedent = 0
        while current_line_indent < current_indent_level:
          try:
            num_dedent += 1
            indent_stack.pop()
            current_indent_level = indent_stack[-1]
          except:
            raise Exception(f"INDENTATION ERROR at '{logical_line}' on logical line {i}")
        
        logical_lines[i] = ' DEDENT '*num_dedent + logical_line

    # Link all DEDENTs together 
    new_logical_lines = []
    i = 0
    while i<len(logical_lines):
      curr_logical_line = logical_lines[i]
      while logical_lines[i][-1] == ' DEDENT ':
        curr_logical_line += logical_lines[i+1]
        i += 1
      new_logical_lines.append(curr_logical_line)

      curr_logical_line = []
      i += 1

    # TODO: update the self.logical to physical line mapping to take care of NEWLINE 
    source = " NEWLINE ".join(new_logical_lines)

    # Dedent all the indents that were previously made
    if len(indent_stack) > 1:
      for _ in range(len(indent_stack)-1):
        source = source + ' NEWLINE DEDENT '
        self.logical_line_to_physical_line_map.append(-1)
    elif indent_stack[-1] == 0:
      source = source + ' NEWLINE '
      self.logical_line_to_physical_line_map.append(-1)

    print('added dedent ', source)
    print(self.logical_line_to_physical_line_map)
    self.source = source

  def reverse_lex(self, lexed_code, value_map, values_appeared, tab_spaces=2):
    final_code = []
    curr_line = []
    curr_indent = 0
    logical_line_num = 0
    curr_x_pos = 0
    for (token, _id, code_pos) in lexed_code:
      final_line_code = []
      added_chars = 0
      if token == 'NEWLINE':
        curr_x_pos = 0
        for (token2, _id2, code_pos) in curr_line:
          # If we need to insert some value
          if token2 in ['NAME', 'NUMBER', 'FSTRING_MIDDLE', 'STRING']:
            if _id2 in value_map:
              if token2 == 'STRING':
                to_append = F"'{value_map[_id2]}'"
              elif token2 == 'FSTRING_MIDDLE':
                to_append = F"f'{value_map[_id2]}'"
              else:
                to_append = value_map[_id2]
            else:
              to_append = values_appeared[token2][0]
          else:
            to_append = token2

          if code_pos:
            print(logical_line_num, code_pos[-1], to_append)
            print(f'codepos: {code_pos[0]-len(to_append)+added_chars} | len_to_append: {len(to_append)} | added chars: {added_chars} | curr x pos: {curr_x_pos} | toappend: {to_append}')

          # Pad start if its a new line
          if code_pos[-1] >= logical_line_num:
            while len(code_pos) and code_pos[0]-len(to_append)+added_chars > curr_x_pos:
              final_line_code.append(' ')
              curr_x_pos += 1

          # Update x position
          if len(code_pos):
            curr_x_pos = code_pos[0]
          else:
            to_append = ' ' + to_append + ' '
            added_chars += len(to_append)
            curr_x_pos += len(to_append)
        
          final_line_code.append(to_append)

        # Account for lines difference
        lines_diff = "\n" * (code_pos[-1] - logical_line_num -1) if len(code_pos) else ''
        logical_line_num = max(code_pos[-1], logical_line_num+1) if len(code_pos) else logical_line_num+1

        # final_line_code = lines_diff + ' ' * tab_spaces * curr_indent + ''.join(final_line_code)
        final_line_code = lines_diff + ''.join(final_line_code)
        final_code.append(final_line_code)
        curr_line = []
      elif token == 'INDENT':
        curr_indent += 1
      elif token == 'DEDENT':
        curr_indent -= 1
      else:
        curr_line.append((token, _id, code_pos))

    return '\n'.join(final_code)