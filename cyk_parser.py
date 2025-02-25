import json
from utils import load_grammar_from_file, split_into_blocks, reconstruct_blocks
from collections import defaultdict
from correction import Correction
import heapq
from concurrent.futures import ProcessPoolExecutor
from functools import partial

class CYK_Parser():
  # grammar_mode either 'from_data' or 'approx_from_grammar'
  def __init__(self, grammar_file, fast_mode=True, beam_search_n=50, threads=0, grammar_mode='approx_from_grammar'):
    self.fast_mode = fast_mode
    self.beam_search_n = beam_search_n
    self.threads = threads

    if grammar_mode == 'approx_from_grammar':
      self.grammar = load_grammar_from_file(grammar_file)
      with open('grammar_from_loading.json', 'w') as f:
        json.dump(self.grammar, f)
    elif grammar_mode == 'from_data':
      with open(grammar_file) as f:
        self.grammar = json.load(f)
        for head, productions in self.grammar.items():
          for production in productions.keys():
            production_tuple = tuple(production.split(' '))
            print(head, production_tuple)

    self.insertion_map = self.load_map('additional_files/I.json')
    self.bigram_probabilities = self.load_map('additional_files/bigram_probabilities.json')
    self.correction_service = Correction()
    
    # Nullable
    self.nullable = self.get_nullable(self.insertion_map)

    # Mapping from productions to heads
    self.rev_grammar = self.get_reverse_grammar()


  def get_nullable(self, insertion_map):
    nullable = set()
    for non_terminal, insertion in insertion_map.items():
      if len(insertion) == 0:
        nullable.add(non_terminal)
    return nullable

  def get_reverse_grammar(self):
    reversed_mapping = {}
    for head, productions in self.grammar.items():
      for production in productions.keys():
        production_tuple = tuple(production.split(' '))

        if production_tuple in reversed_mapping:
          reversed_mapping[production_tuple].append(head)
        else:
          reversed_mapping[production_tuple] = [head]
        
        # Take care of event that productions are nullable
        if len(production_tuple) > 1:
          if production_tuple[0] in self.nullable:
            if (production_tuple[1], ) in reversed_mapping:
              reversed_mapping[(production_tuple[1], )].append(head)
            else:
              reversed_mapping[(production_tuple[1], )] = [head]
          
          if production_tuple[1] in self.nullable:
            if (production_tuple[0], ) in reversed_mapping:
              reversed_mapping[(production_tuple[0], )].append(head)
            else:
              reversed_mapping[(production_tuple[0], )] = [head]
    
    return reversed_mapping

  def load_map(self, filename):
    with open(filename) as f:
      return json.load(f)

  def calc_probability_of_sequence(self, sequence, bigram_prob, smooth = 1e-10):
    total_prob = 1
    for i in range(len(sequence)-1):
      bigram = f"{sequence[i][0]}-{sequence[i+1][0]}"
      if bigram in bigram_prob:
        total_prob *= bigram_prob[bigram]
      else:
        total_prob *= smooth

    return total_prob

  # Parsing algorithm referencing Wikipedia
  def parse(self, to_parse):
    len_input = len(to_parse)

    T = [[set() for _ in range(len_input+1)] for _ in range(len_input)]
    back = [[defaultdict(list) for _ in range(len_input+1)] for _ in range(len_input)]
    
    for i, (token, value) in enumerate(to_parse):
      # If token is stub-block, we take it as a block
      if token == 'STUB-BLOCK':
        T[i][1]['statements'] = 1
        T[i][1]['statements'] = ([], None)
        continue

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

  # Parsing with beam search
  def parse_beam(self, to_parse):
    len_input = len(to_parse)

    T = [[defaultdict(float) for _ in range(len_input+1)] for _ in range(len_input)]
    back = [[defaultdict(list) for _ in range(len_input+1)] for _ in range(len_input)]

    def update_tables_with_beam(candidates, s, l):
      beam_candidates = []
      for _ in range(self.beam_search_n):
        if candidates:
          curr = heapq.heappop(candidates)
          top_val = curr[0]
          beam_candidates.append(curr)
          
          while candidates and candidates[0][0] == top_val:
            beam_candidates.append(heapq.heappop(candidates))

      if beam_candidates:          
        for neg_prob, (lhs, backpointer) in beam_candidates:
          if lhs not in T[s][l]:
            T[s][l][lhs] = -neg_prob
            back[s][l][lhs] = backpointer
    
    for i, (token, value) in enumerate(to_parse):
      if token == 'STUB-BLOCK':
        T[i][1]['statements'] = 1
      else:
        for lhs in self.rev_grammar.get((token,), []):
          T[i][1][lhs] = 1

    for l in range(1, len_input+1): # Length of span
      for s in range(len_input-l+1): # Start of span
        candidates = []

        for A, productions in self.grammar.items():
          for p in range(1,l): # Partition
            for production, rule_prob in productions.items():
              production_arr = production.split(' ')
              if len(production_arr) == 2:
                B, C = production_arr
                if B in T[s][p] and C in T[s+p][l-p] and rule_prob > 0:
                  total_prob = T[s][p][B] * T[s+p][l-p][C] * rule_prob
                  heapq.heappush(candidates, (-total_prob, (A, (p, B, C))))

        update_tables_with_beam(candidates, s, l)
      
        for A, productions in self.grammar.items():
          for production, rule_prob in productions.items():
            production_arr = production.split(' ')
            if len(production_arr) == 2:
              B, C = production_arr

              if B in T[s][l] and C in self.nullable:
                total_prob = T[s][l][B] * rule_prob
                heapq.heappush(candidates, (-total_prob, (A, (-1, B, 'NONE'))))
              
              elif C in T[s][l] and B in self.nullable:
                total_prob = T[s][l][C] * rule_prob
                heapq.heappush(candidates, (-total_prob, (A, (-1, 'NONE', C))))

        update_tables_with_beam(candidates, s, l)

    return T, back
  
  # Returns whether we can parse some code as a given non_terminal
  def is_parse_successful(self, to_parse, non_terminal = 'statements'):
    T, back = self.parse_beam(to_parse)
    # print('dict', T[10][11]['dict'])

    return T[0][len(to_parse)][non_terminal] > 0
  
  # Parses block collection based on number of threads
  def parse_block_collection(self, blocks):
    if self.threads <= 1:
      for block in blocks:
        return self.is_parse_successful(block)
    else:
      with ProcessPoolExecutor(self.threads) as executor2:
        func = partial(self.is_parse_successful)
        is_block_successful = list(executor2.map(func, blocks))

        return is_block_successful

  # Parse with beam search and block parsing, keep track of grammar rules used
  def is_parse_successful_parse_beam_block(self, to_parse): 
    with ProcessPoolExecutor(self.threads) as executor:
      # Collection of blocks for each indentation level
      blocks_collection = split_into_blocks(to_parse)
      if self.threads <= 1:
        parsed_block_coll = []
        for indent in range(len(blocks_collection)):
          block_collection = blocks_collection[indent]
          print('block collection', block_collection)
          parsed_block_coll.append(self.parse_block_collection(block_collection))
      else:
          func = partial(self.parse_block_collection)
          result = list(executor.map(func, blocks_collection))

          for indent_b in result:
            for b_result in indent_b:
              if b_result == False:
                return False, result
      
          return True, result

  # Parsing algorithm adapted for error correction referencing MartinLange
  def parse_with_err_correction(self, to_parse):
    len_input = len(to_parse)

    T = [[defaultdict(list) for _ in range(len_input+1)] for _ in range(len_input+1)]
    
    for i, (token, token_id) in enumerate(to_parse):
      # If token is stub-block, we take it as a block
      if token == 'STUB-BLOCK':
        T[i][1]['statements'] = ([], None)
        continue
      for head, productions in self.grammar.items():
        for production in productions.keys():
          if len(production.split(' ')) == 1:
            for lhs in self.rev_grammar.get((token,), []):
              if head != lhs and head not in T[i][1]:
                T[i][1][head] = ([['r', str(i), {production}]], None)
              elif head == lhs:
                T[i][1][head] = ([], None)

    for l in range(2, len_input+1): # Length of span
      for s in range(len_input - l + 1): # Start of span
        for A, productions in self.grammar.items():
          if self.fast_mode and A in T[s][l] and len(T[s][l][A][0])==0:
            continue
          
          for p in range(1,l+1): # Partition
            for production in productions.keys():
              production_arr = production.split(' ')
              if len(production_arr) == 2:
                B, C = production_arr

                # Composed correction
                if B in T[s][p] and C in T[s+p][l-p]:
                  p1, p2 = T[s][p][B][0], T[s+p][l-p][C][0]
                  
                  if self.fast_mode and (len(p1)>3 or len(p2)>3):
                    pass
                  else:
                    correction = self.correction_service.compose(p1,p2)

                    # if A not in T[s][l] or len(correction) < len(T[s][l][A][0]):
                    if A not in T[s][l] or self.compare_corrections(correction, T[s][l][A][0], to_parse):
                      T[s][l][A] = (correction, (p,B,C))

                # Insertion correction case 1
                if B in T[s][l] and C in self.insertion_map:
                  p_list = T[s][l][B][0]
                  sigma = self.insertion_map[C]

                  if self.fast_mode and (len(p_list)>3 or len(sigma)>3):
                    pass
                  else:
                    correction = self.correction_service.compose_for_insertion_forward(p_list, sigma, s+l)
                    # if A not in T[s][l] or len(correction) < len(T[s][l][A][0]):
                    if A not in T[s][l] or self.compare_corrections(correction, T[s][l][A][0], to_parse):
                      T[s][l][A] = (correction, (None, B, None))
                
                # Insertion correction case 2
                if C in T[s][l] and B in self.insertion_map:
                  p_list = T[s][l][C][0]
                    
                  sigma = self.insertion_map[B]
                  sigma = self.correction_service.offset_indices(sigma, s)

                  if self.fast_mode and (len(p_list)>3 or len(sigma)>3):
                    pass
                  else:
                    correction = self.correction_service.compose_for_insertion_backward(p_list, sigma, s)
                    # if A not in T[s][l] or len(correction) < len(T[s][l][A][0]):
                    if A not in T[s][l] or self.compare_corrections(correction, T[s][l][A][0], to_parse):
                      T[s][l][A] = (correction, (None, None, C))

    return T
  
  # Beam with error correction
  def parse_with_err_correction_beam(self, to_parse):
    len_input = len(to_parse)

    T = [[defaultdict(float) for _ in range(len_input+1)] for _ in range(len_input+1)]
    table_w_corrections = [[defaultdict(list) for _ in range(len_input+1)] for _ in range(len_input)]

    # Update T and table_w_corrections based on candidates
    def update_tables_with_beam(candidates, s, l):
      beam_candidates = []
      for _ in range(self.beam_search_n):
        if candidates:
          curr = heapq.heappop(candidates)
          top_val = curr[0]
          beam_candidates.append(curr)
          
          while candidates and candidates[0][0] == top_val:
            beam_candidates.append(heapq.heappop(candidates))

      if beam_candidates:          
        for neg_prob, (lhs, correction, backpointer) in beam_candidates:
          if len(table_w_corrections[s][l][lhs])==0 or len(correction) <= len(table_w_corrections[s][l][lhs][0]):
            T[s][l][lhs] = -neg_prob
            table_w_corrections[s][l][lhs] = (correction, backpointer)
    
    # Update length 1
    for i, (token, token_id) in enumerate(to_parse):
      # If token is stub-block, we take it as a block
      if token == 'STUB-BLOCK':
        T[i][1]['statements'] = 1
        table_w_corrections[i][1]['statements'] = ([], None)
        continue

      for head, productions in self.grammar.items():
        for production in productions.keys():
          if len(production.split(' ')) == 1:
            for lhs in self.rev_grammar.get((token,), []):
              if head != lhs and head not in T[i][1]:
                if production == "''":
                  table_w_corrections[i][1][head] = ([['d', str(i)]], None)
                else:
                  table_w_corrections[i][1][head] = ([['r', str(i), production]], None)
                
                # TODO: update the probability of each based on prior distribution?
                T[i][1][head] = 1e-2
              elif head == lhs:
                table_w_corrections[i][1][head] = ([], None)
                T[i][1][head] = 1

    for l in range(1, len_input+1): # Length of span
      for s in range(len_input-l+1): # Start of span
        candidates = []

        for A, productions in self.grammar.items():
          for p in range(0,l+1): # Partition
            for production, rule_prob in productions.items():
              production_arr = production.split(' ')
              if len(production_arr) == 2:
                B, C = production_arr
              
                # Composed correction
                if T[s][p][B] > 0 and T[s+p][l-p][C] > 0:
                  p1, p2 = table_w_corrections[s][p][B][0], table_w_corrections[s+p][l-p][C][0]
                  
                  if self.fast_mode and (len(p1)>3 or len(p2)>3):
                    pass
                  else:
                    correction = self.correction_service.compose(p1,p2)
                    if T[s][l][A] == 0 or (T[s][l][A] > 0 and self.compare_corrections(correction, table_w_corrections[s][l][A][0], to_parse)):
                      total_prob = T[s][p][B] * T[s+p][l-p][C] * rule_prob
                      heapq.heappush(candidates, (-total_prob, (A, correction, (p, B, C))))

        update_tables_with_beam(candidates, s, l)

        # Update insertions
        for A, productions in self.grammar.items():
          for production, rule_prob in productions.items():
            production_arr = production.split(' ')
            if len(production_arr) == 2:
              B, C = production_arr

              # Insertion correction case 1
              if T[s][l][B] > 0 and C in self.insertion_map:
                p_list = table_w_corrections[s][l][B][0]
                sigma = self.insertion_map[C]

                if self.fast_mode and (len(p_list)>3 or len(sigma)>3):
                  pass
                else:
                  correction = self.correction_service.compose_for_insertion_forward(p_list, sigma, s+l)
                  if T[s][l][A] == 0 or (T[s][l][A] > 0 and self.compare_corrections(correction, table_w_corrections[s][l][A][0], to_parse)):
                    # Total prob is probability of B, probability of there being such an insertion for C, and probability of A->BC
                    total_prob = T[s][l][B] * self.correction_to_prob(sigma) * rule_prob
                    heapq.heappush(candidates, (-total_prob, (A, correction, (-1, B, 'NONE'))))
              
              # Insertion correction case 2
              if T[s][l][C] > 0 and B in self.insertion_map:
                p_list = table_w_corrections[s][l][C][0]
                  
                sigma = self.insertion_map[B]
                sigma = self.correction_service.offset_indices(sigma, s)

                if self.fast_mode and (len(p_list)>3 or len(sigma)>3):
                  pass
                else:
                  correction = self.correction_service.compose_for_insertion_backward(p_list, sigma, s)
                  if T[s][l][A] == 0 or (T[s][l][A] > 0 and self.compare_corrections(correction, table_w_corrections[s][l][A][0], to_parse)):
                    # Total prob is probability of there being such an insertion for B, probability of C, and probability of A->BC
                    total_prob = T[s][l][C] * self.correction_to_prob(sigma) * rule_prob
                    heapq.heappush(candidates, (-total_prob, (A, correction, (-1, 'NONE', C))))      

        update_tables_with_beam(candidates, s, l)
        
    return table_w_corrections, T
  
  def correct_single_block(self, block):
    if len(block) > 0:
      T_with_corr, T_prob = self.parse_with_err_correction_beam(block)
      return self.get_corrected_block(block, T_with_corr)
    return []
  
  def correct_block_collection(self, blocks):
    with ProcessPoolExecutor(self.threads) as executor2:
      func = partial(self.correct_single_block)
      result = list(executor2.map(func, blocks))

      return result
  
  # Run the correction algorithm on each block
  def correct_code_with_err_correction_beam_block(self, to_parse):          
    with ProcessPoolExecutor(self.threads) as executor1:
      # Collection of blocks for each indentation level
      blocks_collection = split_into_blocks(to_parse)
      
      if self.threads:
        func = partial(self.correct_block_collection)
        corrected_blocks = list(executor1.map(func, blocks_collection))
      else:
        # Correcting the blocks
        corrected_blocks = []
        for indent_level in range(len(blocks_collection)):
          corrected_blocks.append([])

        for indent_level in range(len(blocks_collection)-1, -1, -1):
          blocks = blocks_collection[indent_level]
        for block in blocks:
          T_with_corr, T_prob = self.parse_with_err_correction_beam(block)
          if T_with_corr:
            print(f'correction: {T_with_corr[0][-1]["statements"][0]}')
            corrected_blocks[indent_level].append(self.get_corrected_block(block, T_with_corr))

      print('CORRECTED BLOCKS --- ')
      for i in range(len(corrected_blocks)):
        print (i)
        for block in corrected_blocks[i]:
          print(block)
        print()

      # Transforming transformed blocks so consecutive statements are combined
      updated_corrected_blocks = []
      for blocks in corrected_blocks:
        updated_blocks = []
        curr_block_i = 0
        while curr_block_i < len(blocks):
          updated_block = blocks[curr_block_i]

          while curr_block_i < len(blocks)-1 and blocks[curr_block_i][-1][-1]+1 == blocks[curr_block_i+1][0][-1]:
            updated_block += blocks[curr_block_i+1]
            curr_block_i += 1

          updated_blocks.append(updated_block)
          curr_block_i += 1
        
        updated_corrected_blocks.append(updated_blocks)
        
      print('UPDATED BLOCKS --- ')
      for i in range(len(updated_corrected_blocks)):
        print (i)
        for block in updated_corrected_blocks[i]:
          print(block)
        print()

      print()

      corrected_code = reconstruct_blocks(updated_corrected_blocks)[0]

      print()
      print('CORRECTED LEXED CODE --')
      print(corrected_code + [('ENDMARKER', -1)])
      return corrected_code + [('ENDMARKER', -1)]
  
  # Optimise correction of many blocks by only running correction algorithm on blocks that are not correct

  # Given a correction, figure out the probability
  def correction_to_prob(self, correction):
    return 1/pow(10, len(correction))

  # How to prioritise corrections 
  def compare_corrections(self, corr1, corr2, code):
    # We always pick the shortest correction
    if len(corr1) < len(corr2):
      return True
    elif len(corr1) > len(corr2):
      return False
    
    # If more insertions and deletions it's preferred over replacements
    num_one_operation_corr_1 = self.correction_service.get_num_deletions(corr1)+self.correction_service.get_num_insertions(corr1)
    num_one_operation_corr_2 = self.correction_service.get_num_deletions(corr2)+self.correction_service.get_num_insertions(corr2)
    if num_one_operation_corr_1 > num_one_operation_corr_2:
      return True
    elif num_one_operation_corr_1 < num_one_operation_corr_2:
      return False

    # print(corr1, corr2, code)
    # If the corrections are the same length, we calculate the probabilities
    code_corr_1 = self.correction_service.apply_correction(corr1, code)
    code_corr_2 = self.correction_service.apply_correction(corr2, code)

    prob_1 = self.calc_probability_of_sequence(code_corr_1, self.bigram_probabilities)
    prob_2 = self.calc_probability_of_sequence(code_corr_2, self.bigram_probabilities)

    # corr_1 > corr_2 if the probability of code from 1 is higher
    return prob_1 > prob_2

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

  def get_corrected_code(self, code, T):
    corrected_code = self.correction_service.apply_correction(T[0][-1]['start'][0], code)

    return corrected_code
  
  def get_corrected_block(self, code, T):
    try: 
      corrected_code = self.correction_service.apply_correction(T[0][-1]['statements'][0], code)
    except:
      raise Exception(f'FAILED TO PARSE AS STATEMENT. Try raising the number of beams. \ncode failed: {code}')

    return corrected_code

