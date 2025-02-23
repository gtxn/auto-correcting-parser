import re
from uuid import uuid4

class Correction:
  def __init__(self):
    pass
  
  def apply_correction(self, corrections, code):
    code_copy = []
    for tok in code:
      code_copy.append(tok)

    for correction in corrections:
      op, ind = correction[0], int(correction[1])
      if op == 'd':
        code_copy.pop(ind)
      elif op == 'i':
        to_insert = (correction[2], uuid4())
        code_copy = code_copy[:ind] + [to_insert] + code_copy[ind:]
      else:
        to_replace = correction[2]
        code_copy[ind] = (to_replace, uuid4())
    
    return code_copy

  def normalise(self, correction_arr):
    # Returns True if elem1 > elem2 according to normalisation rules
    def compare_more_than(elem1, elem2):
      if len(elem1) == 0: return True
      elif len(elem2) == 0: return False

      op1, i1 = elem1[0], elem1[1]
      op2, i2 = elem2[0], elem2[1]

      if op1 == op2:
        return int(i1) < int(i2)
      elif op1 == 'i':
        return True
      elif op1 == 'd' and op2 == 'r':
        return True
      
      return False
    
    # Implements a swap while keeping semantics of correction
    def swap_elem(correction_arr, i, j):
      elem1, elem2 = correction_arr[i], correction_arr[j]
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
        if ind1 < ind2:
          correction_arr[i], correction_arr[j] = self.offset_single_correction(correction_arr[j], 1), correction_arr[i]

      elif op1 == 'i' and op2 == 'r':
        if ind1 == ind2:
          # Directly insert what we were going to replace
          to_replace = elem2[2]
          correction_arr[i] = [op1, str(ind1), to_replace]
          correction_arr[j] = []
        elif ind2 > ind1:
          correction_arr[i], correction_arr[j] = self.offset_single_correction(correction_arr[j], -1), correction_arr[i]
        else:
          correction_arr[i], correction_arr[j] = correction_arr[j], correction_arr[i]  
      elif op1 == 'i' and op2 == 'i':
        correction_arr[i], correction_arr[j] = self.offset_single_correction(correction_arr[j], -1), correction_arr[i]
      elif op1 == 'i' and op2 == 'd':
        if ind1 == ind2:
          correction_arr[i] = []
          correction_arr[j] = []
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
    
    # Merge instructions if possible
    new_correction_arr = []
    for i in range(0, n-1):
      elem1, elem2 = correction_arr[i], correction_arr[i+1]
      if len(elem1) == 0: break
      elif len(elem2) == 0: break

      op1, ind1 = elem1[0], int(elem1[1])
      op2, ind2 = elem2[0], int(elem2[1])

      # Deletion followed by insertion is just a replacement
      if op1 == 'd' and op2 == 'i' and ind1 == ind2:
        new_correction_arr.append(['r', f'{ind1}', elem2[2]])
      # Replacement followed by deletion of same index means we don't do anything
      elif op1 == 'r' and op2 == 'd' and ind1 == ind2:
        new_correction_arr.append(['d', f'{ind1}'])
      else:
        new_correction_arr.append(elem1)
    
    if len(correction_arr) and len(correction_arr[-1]) > 0:
      new_correction_arr.append(correction_arr[-1])

    return new_correction_arr
  
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
    if len(correction) == 2:
      return [correction[0], str(int(correction[1]) + shift)]
    else:
      return [correction[0], str(int(correction[1]) + shift), correction[2]]

  def get_num_insertions(self, p):
    return len(list(filter(lambda x: x[0]=='i', p)))
  
  def get_num_deletions(self, p):
    return len(list(filter(lambda x: x[0]=='d', p)))