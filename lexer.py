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

class Lexer:
  def __init__(self, source_code, tab_spaces=2):
    self.source = source_code
    self.preprocess()
    self.tokens = []
    self.current_char = None
    self.position = -1
    self.tab_spaces = tab_spaces
    self.prev_f = False # To tokenize f-strings
    self.values_appeared = defaultdict(list) # Values of all NAME and NUMBER that appear in code
    self.step()

  # Steps to next token
  def step(self):
    self.position += 1
    self.current_char = self.source[self.position] if self.position < len(self.source) else None

  def tokenise(self):
    while self.current_char is not None:
      if self.current_char in WHITESPACE:
        self.step()
      
      elif self.current_char == "#":
        self.skip_comment()
      
      elif self.current_char == "'" or self.current_char == '"':
        # TODO: deal with format string!! Currently just treating inside as normal string
        if self.prev_f:
          self.tokens.pop()
          self.tokens.append(('FSTRING_START', 'FSTRING_START'))
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
          
          self.tokens.append(("FSTRING_MIDDLE", str_string))
          
          # Step from closing delimiter
          self.step() 

          self.tokens.append(("FSTRING_END", "FSTRING_END"))
        else:
          self.tokens.append(self.process_string())

      elif self.current_char in DIGITS:
        num = self.number()
        self.tokens.append(("NUMBER", num))
        self.values_appeared['NUMBER'].append(num)
      
      elif self.current_char in LETTERS or self.current_char == "_":
        self.prev_f = self.current_char == 'f' or self.current_char == 'F'
        self.tokens.append(self.identifier_or_keyword_or_token())
      
      elif self.current_char in OPERATORS:
        self.tokens.append(self.operator())
      
      elif self.current_char in DELIMITERS:
        self.tokens.append((self.current_char, self.current_char))
        self.step()
      
      else:
        raise ValueError(f"Unexpected character: {self.current_char}")

    # self.tokens.append(('NEWLINE', 'NEWLINE'))
    self.tokens.append(('ENDMARKER', 'ENDMARKER'))
    return self.tokens, self.values_appeared
  
  def get_id_mapped_tokens(self):
    tokens_with_id = []
    value_map = defaultdict()
    for i, t in enumerate(self.tokens):
      tokens_with_id.append((t[0], i))
      value_map[i] = t[1]

    return tokens_with_id, value_map

  def skip_comment(self):
    while self.current_char and self.current_char != "\n":
      self.step()

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
      return (id_str, id_str)
    if id_str in PREPROCESS_TOKENS:
      return (id_str, id_str)
    
    self.values_appeared['NAME'].append(id_str)
    return ("NAME", id_str)

  # TODO: instead of (operator, +) do (PLUS, +) so parser only needs to look at first element
  def operator(self):
    op = self.current_char
    self.step()
    # Handle multi-character operators like `==`, `!=`
    if self.current_char and (op + self.current_char) in OPERATORS:
      op += self.current_char
      self.step()
    return (op, op)
  
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

    return ("STRING", str_string)

  def preprocess(self):    
    # Split into logical lines
    logical_lines = []
    logical_line = ''
    for physical_line in self.source.split('\n'):
      if physical_line.strip().endswith('\\'):
        logical_line += physical_line.replace('\\', '')
      
      # Ensure physical line is not a comment or empty
      elif physical_line.strip() and not physical_line.strip().startswith('#'):
        logical_line += physical_line
        # source_code += logical_line + ' NEWLINE '
        logical_lines.append(logical_line)
        logical_line = ''

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
        try:
          logical_lines[i] = ' DEDENT ' + logical_line
          indent_stack = indent_stack[0:indent_stack.index(current_line_indent)+1]
        except:
          raise Exception(f"INDENTATION ERROR at '{logical_line}' on logical line {i}")

    source = " NEWLINE ".join(logical_lines)

    # Dedent all the indents that were previously made
    if len(indent_stack) > 1:
      for _ in range(len(indent_stack)-1):
        source = source + ' NEWLINE DEDENT '
    else:
      source = source + ' NEWLINE '

    self.source = source