# -*- coding: utf-8 -*-

class Podmienka(object):
  symbols = ('(', ')', 'OR', 'AND')
  
  def __init__(self, text):
    self._tokens = text.split()
  
  def idset(self):
    ret = set()
    for token in self._tokens:
      if token not in self.symbols:
        ret.add(int(token))
    return ret