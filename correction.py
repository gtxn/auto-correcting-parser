import re
from copy import deepcopy
from uuid import uuid4

class Correction:
  def __init__(self):
    self.replace_regex = "r\|[0-9]+\|[^0-9]+"
    self.insert_regex = "i\|[0-9]+\|[^0-9]+"
    self.delete_regex = "d\|[0-9]+"

  def check_valid_correction_arr(self, correction_arr):
    for corr in correction_arr:
      if not re.match(self.replace_regex, corr) and \
          not re.match(self.insert_regex, corr) and \
          not re.match(self.delete_regex, corr):
        return False
    
    return True
  
  def apply_correction(self, corrections, code):
    code_copy = deepcopy(code)

    for correction in corrections:
      corr_arr = correction.split('|')
      op, ind = corr_arr[0], int(corr_arr[1])
      if op == 'd':
        code_copy.pop(ind)
      elif op == 'i':
        to_insert = (corr_arr[2], uuid4())
        code_copy = code_copy[:ind] + [to_insert] + code_copy[ind:]
      else:
        to_replace = corr_arr[2]
        code_copy[ind] = (to_replace, uuid4())
    
    return code_copy

  def normalise(self, correction_arr):
    # Returns True if elem1 > elem2 according to normalisation rules
    def compare_more_than(elem1, elem2):
      elem1_arr = elem1.split('|')
      elem2_arr = elem2.split('|')

      op1, i1 = elem1_arr[0], elem1_arr[1]
      op2, i2 = elem2_arr[0], elem2_arr[1]

      if op1 == op2:
        return int(i1) < int(i2)
      elif op1 == 'i':
        return True
      elif op1 == 'd' and op2 == 'r':
        return True
      
      return False
    
    # Implements a swap while keeping semantics of correction
    def swap_elem(correction_arr, i, j):
      elem1, elem2 = correction_arr[i].split('|'), correction_arr[j].split('|')
      op1, ind1 = elem1[0], int(elem1[1])
      op2, ind2 = elem2[0], int(elem2[1])

      if op1 == 'r' and op2 == 'r':
        correction_arr[i], correction_arr[j] = correction_arr[j], correction_arr[i]
      
      elif op1 == 'd' and op2 == 'r':
        if ind2 >= ind1:
          correction_arr[i], correction_arr[j] = self.offset_single_correction(correction_arr[j], 1), correction_arr[i]          
        else:
          correction_arr[i], correction_arr[j] = correction_arr[j], correction_arr[i]
      elif op1 == 'd' and op2 == 'd':
        correction_arr[i], correction_arr[j] = self.offset_single_correction(correction_arr[j], 1), correction_arr[i]
      
      elif op1 == 'i' and op2 == 'r':
        # if (ind1 == 8 and ind2 == 17):
        #   print(self.offset_single_correction(correction_arr[j], -1))

        if ind1 == ind2:
          # Directly insert what we were going to replace
          to_replace = elem2[2]
          correction_arr.pop(j)
          correction_arr[i] = '|'.join([op1, ind1, to_replace])
        elif ind2 > ind1:
          correction_arr[i], correction_arr[j] = self.offset_single_correction(correction_arr[j], -1), correction_arr[i]
        else:
          correction_arr[i], correction_arr[j] = correction_arr[j], correction_arr[i]  
      elif op1 == 'i' and op2 == 'i':
        correction_arr[i], correction_arr[j] = self.offset_single_correction(correction_arr[j], -1), correction_arr[i]
      elif op1 == 'i' and op2 == 'd':
        if ind1 == ind2:
          correction_arr.pop(i)
          correction_arr.pop(j)
        elif ind2 > ind1:
          correction_arr[i], correction_arr[j] = self.offset_single_correction(correction_arr[j], -1), correction_arr[i]
        else:
          correction_arr[i], correction_arr[j] = correction_arr[j], self.offset_single_correction(correction_arr[i], -1)
    
    n = len(correction_arr)
    # Traverse through all array elements
    for i in range(n):
      # Last i elements are already in place, so no need to check them
      swapped = False
      
      for j in range(0, n - i - 1):
        if compare_more_than(correction_arr[j], correction_arr[j + 1]):
          swap_elem(correction_arr, j, j+1)
          swapped = True

      if not swapped:
        break
    
    return correction_arr
  
  # Composition of 2 normalised corrections to get a normalised correction
  def compose(self, p1, p2):
    num_insertions_1 = self.get_num_insertions(p1)
    num_deletions_1 = self.get_num_deletions(p1)

    shift = num_insertions_1 - num_deletions_1
    p2_new = self.offset_indices(p2, shift)

    final = self.normalise(p1+p2_new)

    return final
  
  def compose_for_insertion_forward(self, p, sigma, j):
    shift = j + self.get_num_insertions(p) - self.get_num_deletions(p)
    sigma_prime = self.offset_indices(sigma, shift)

    return self.normalise(p + sigma_prime)
  
  def compose_for_insertion_backward(self, p, sigma, j):
    shift = len(sigma)
    p_prime = self.offset_indices(p, shift)

    return self.normalise(sigma + p_prime)
  
  # Offset all indices in correction by a fixed amount
  def offset_indices(self, p, shift):
    p_new = []
    for correction in p:
      p_new.append(self.offset_single_correction(correction, shift))
    
    return p_new
  
  # Offset index of single operation
  def offset_single_correction(self, correction, shift):
    corr_arr = correction.split('|')
    corr_arr[1] = str(int(corr_arr[1]) + shift)
    return '|'.join(corr_arr)

  def get_num_insertions(self, p):
    return len(list(filter(lambda x: 'i|' in x, p)))
  
  def get_num_deletions(self, p):
    return len(list(filter(lambda x: 'd|' in x, p)))