# -*- coding: utf-8 -*-
import re
from flask import g
from jinja2 import evalcontextfilter, Markup, escape
import colander
from markupsafe import soft_unicode

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
      result.append(g.db.load_predmet_simple(int(token)))
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
  if value == None:
    return ''
  if iba_datum:
    return value.strftime('%d.%m.%Y')
  return value.strftime('%d.%m.%Y %H:%M:%S')

def space2nbsp(value):
  return value.replace(u' ', u'\u00A0')

def je_profesor_alebo_docent(osoba_id):
  osoba = g.db.load_osoba(osoba_id)
  parts = osoba.cele_meno.lower().split()
  return ('doc.' in parts) or ('prof.' in parts)

_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')

@evalcontextfilter
def nl2br(eval_ctx, value):
    result = u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', '<br />\n')
                          for p in _paragraph_re.split(escape(value)))
    if eval_ctx.autoescape:
        result = Markup(result)
    return result

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