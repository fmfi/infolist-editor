# -*- coding: utf-8 -*-
import re
from flask import g

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

def kod2skratka(kod):
  return re.match(r'^[^/]+/(.+)/[^/]+$', kod).group(1)

def filter_fakulta(search_kod):
  for kod, nazov in g.db.load_fakulty():
    if search_kod == kod:
      return nazov
  return None

def filter_druh_cinnosti(search_kod):
  for kod, popis in g.db.load_druhy_cinnosti():
    if search_kod == kod:
      return popis
  return None

def filter_obdobie(search_kod):
  for kod, popis in (('S', u'semester'), ('T', u'týždeň')):
    if search_kod == kod:
      return popis
  return None

def filter_metoda_vyucby(search_kod):
  for kod, popis in (('P', u'prezenčná'), ('D', u'dištančná'), ('K', u'kombinovaná')):
    if search_kod == kod:
      return popis
  return None

def filter_typ_vyucujuceho(search_kod):
  for kod, popis in g.db.load_typy_vyucujuceho():
    if search_kod == kod:
      return popis
  return None