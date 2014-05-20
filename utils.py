# -*- coding: utf-8 -*-

import re
from flask import g
import colander
from markupsafe import soft_unicode


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
      

def je_profesor_alebo_docent(osoba_id):
  osoba = g.db.load_osoba(osoba_id)
  parts = osoba.cele_meno.lower().split()
  return ('doc.' in parts) or ('prof.' in parts)


def escape_rtf(val):
  if val == colander.null or val == None:
    val = u''
  val = soft_unicode(val)
  r = ''
  prevc = None
  for c in val:
    if (c == '\n' and prevc != '\r') or (c == '\r' and prevc != '\n'):
      r += '\line '
    elif (c == '\n' and prevc == '\r') or (c == '\r' and prevc == '\n'):
      pass
    elif c in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ':
      r += c
    else:
      r += '\u{}?'.format(ord(c))
    prevc = c
  return r

def render_rtf(rtf_template, substitutions):
  replacements = []
  for key, value in substitutions.iteritems():
    replacements.append((key, escape_rtf(value)))
  return multiple_replace(rtf_template, *replacements)

def rozsah():
  poradie_cinnosti = [x[0] for x in g.db.load_druhy_cinnosti()]
  
  def sort_key_cinnosti(cinn):
    try:
      return (0, poradie_cinnosti.index(cinn['druh_cinnosti']))
    except ValueError:
      return (1, cinn['druh_cinnosti'])
  
  def worker(cinnosti):
    return ['{}{}{}'.format(x['pocet_hodin'], '/s' if x['za_obdobie'] == 'S' else '', x['druh_cinnosti']) for x in sorted(cinnosti, key=sort_key_cinnosti)]
  
  return worker

# http://stackoverflow.com/a/15221068
def multiple_replacer(*key_values):
    replace_dict = dict(key_values)
    replacement_function = lambda match: replace_dict[match.group(0)]
    pattern = re.compile("|".join([re.escape(k) for k, v in key_values]), re.M)
    return lambda string: pattern.sub(replacement_function, string)

def multiple_replace(string, *key_values):
    return multiple_replacer(*key_values)(string)
  
# end http://stackoverflow.com/a/15221068

stupen_studia_titul = {
  '1.': 'Bc',
  '2.': 'Mgr',
  '3.': 'PhD'
}

def prilohy_podla_typu(prilohy):
  podla_typu = {}
  podla_typu2 = []

  for row in g.db.load_typy_priloh():
    podla_typu[row.id] = (row, [],)
    podla_typu2.append(podla_typu[row.id])
  for filename, typ, priloha in prilohy:
    podla_typu[typ][1].append([filename, priloha])

  return podla_typu2

class LevelSet(object):
  def __init__(self):
    self.commited = set()
    self.new_level = set()
    self.level = None

  def add(self, level, value):
    if self.level != level:
      self.commit()
      self.level = level
      self.new_level = set()
    self.new_level.add(value)

  def commit(self):
    self.commited.update(self.new_level)

  def __contains__(self, item):
    return item in self.commited

  def current_set(self):
    return self.commited.copy()

