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

def filter_jazyk_vyucby(search_kod):
  for kod, popis in g.db.load_jazyky_vyucby():
    if search_kod == kod:
      return popis
  return None

def filter_literatura(id):
  return g.db.load_literatura(id)

def filter_osoba(id):
  return g.db.load_osoba(id)

def filter_podmienka(podmienka):
  result = []
  for token in Podmienka(podmienka)._tokens:
    if token in Podmienka.symbols:
      if token == 'OR':
        token = 'alebo'
      elif token == 'AND':
        token = 'a'
      result.append(token)
    else:
      result.append(g.db.load_predmet(int(token)))
  return result

def recursive_replace(d, value, replacement):
  if isinstance(d, dict):
    return {key: recursive_replace(d[key], value, replacement) for key in d}
  elif isinstance(d, list):
    return [recursive_replace(x, value, replacement) for x in d]
  elif d == value:
    return replacement
  else:
    return d

def recursive_update(d, otherd):
  if not isinstance(d, dict) or not isinstance(otherd, dict):
    raise TypeError()
  for key in otherd:
    if key in d and isinstance(d[key], dict):
      recursive_update(d[key], otherd[key])
    else:
      d[key] = otherd[key]
      
def format_datetime(value, iba_datum=False):
  if iba_datum:
    return value.strftime('%d.%m.%Y')
  return value.strftime('%d.%m.%Y %H:%M:%S')

def space2nbsp(value):
  return value.replace(u' ', u'\u00A0')