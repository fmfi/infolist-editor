# -*- coding: utf-8 -*-
import re
from flask import g
from jinja2 import evalcontextfilter, Markup, escape
import colander
from markupsafe import soft_unicode
from decimal import Decimal

class Podmienka(object):
  symbols = ('(', ')', 'OR', 'AND')
  
  def __init__(self, text):
    self._tokens = []
    self._predmety = {}
    rawtok = self._tokenize(text)
    if len(rawtok) == 0:
      self._tokens = []
    else:
      self._tokens = Podmienka._parse_expr_in(rawtok)
  
  @classmethod
  def _parse_expr(cls, tokens):
    if len(tokens) == 0:
      raise ValueError('Expecting expression')
    
    if tokens[0] == '(':
      ret = [tokens.pop(0)]
      ret.extend(cls._parse_expr_in(tokens))
      if not tokens or tokens[0] != ')':
        raise ValueError('Expecting )')
      ret.append(tokens.pop(0))
      return ret
    elif re.match('^[0-9]+$', tokens[0]):
      return [int(tokens.pop(0))]
    else:
      raise ValueError('Expecting ID or (')
  
  @classmethod
  def _parse_expr_in(cls, tokens):
    ret = cls._parse_expr(tokens)
    
    if not tokens or tokens[0] == ')':
      return ret
    
    if tokens[0].upper() not in ['OR', 'AND']:
      raise ValueError('Expecting AND or OR')
    
    typ = tokens.pop(0).upper()
    ret.append(typ)
    
    while True:
      ret.extend(cls._parse_expr(tokens))
      
      if not tokens or tokens[0] == ')':
        return ret
      
      if tokens[0].upper() != typ:
        raise ValueError('Expecting ' + typ)
      
      ret.append(tokens.pop(0).upper())
  
  @staticmethod
  def _tokenize(text):
    tokens = []
    last = None
    for c in text:
      if c in '()':
        tokens.append(c)
        last = c
      elif c in '0123456789':
        if last == 'num':
          tokens[-1] += c
        else:
          tokens.append(c)
        last = 'num'
      elif (c >= 'a' and c <= 'z') or (c >= 'A' and c <= 'Z'):
        if last == 'alpha':
          tokens[-1] += c
        else:
          tokens.append(c)
        last = 'alpha'
      elif c in ' \t\n\r\v':
        last = 'space'
      else:
        raise ValueError(u'Invalid token character: ' + c)
    return tokens
  
  def _load_predmety(self):
    to_load = self.idset().difference(set(self._predmety))
    if not to_load:
      return self._predmety
    for p in to_load:
      data = g.db.load_predmet_simple(p)
      if data == None:
        raise ValueError('Predmet {} neexistuje v databaze'.format(p))
      self._predmety[p] = data
    return self._predmety
  
  @property
  def tokens(self):
    ret = []
    pred = self._load_predmety()
    for tok in self._tokens:
      if tok in self.symbols:
        ret.append(tok)
      else:
        ret.append(pred[tok])
    return ret
  
  def idset(self):
    ret = set()
    for token in self._tokens:
      if token not in self.symbols:
        ret.add(int(token))
    return ret
  
  def __unicode__(self):
    ret = u''
    for token in self.tokens:
      if token in Podmienka.symbols:
        if token == 'OR':
          ret += ' alebo '
        elif token == 'AND':
          ret += ' a '
        else:
          ret += token
      else:
        if len(token['nazvy_predmetu']) == 0:
          nazov_predmetu = u'TODO'
        else:
          nazov_predmetu = u'/'.join(token['nazvy_predmetu'])
        ret += u'{} {}'.format(token['skratka'], nazov_predmetu)
    return ret
  
  def __str__(self):
    return unicode(self).encode('UTF-8')
  
  def __repr__(self):
    return 'Podmienka({!r})'.format(self.serialize())
  
  def serialize(self):
    return ' '.join(str(x) for x in self._tokens)
  
  def __len__(self):
    return len(self._tokens)

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

def filter_typ_bloku(search_kod):
  for kod, popis in g.db.load_typy_bloku():
    if search_kod == kod:
      return popis
  return None

def filter_literatura(id):
  return g.db.load_literatura(id)

def filter_osoba(id):
  return g.db.load_osoba(id)

def filter_stupen_studia(stupen):
  stupne = {
    '1.': u'1. - bakalárske štúdium',
    '2.': u'2. - magisterské štúdium',
    '3.': u'3. - doktorandské štúdium',
  }
  if stupen in stupne:
    return stupne[stupen]
  return stupen

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
  
# end http://stackoverflow.com/a/15221068

class Pocitadlo(object):
  def __init__(self):
    self._fyzicky = set()
    self._fyzicky_tyzdenne = set() # ustanoveny tyzdenny prac cas
    self._fyzicky_podskupina = set() # mimoriadny/3st.
    self.prepocitany = Decimal(0)
    self.prepocitany_podskupina = 0 # mimoriadny/3st.
  
  def pridaj(self, id, vaha, podskupina):
    self._fyzicky.add(id)
    self.prepocitany += vaha
    if podskupina:
      self._fyzicky_podskupina.add(id)
      self.prepocitany_podskupina += vaha
    if vaha == Decimal(1):
      self._fyzicky_tyzdenne.add(id)
  
  @property
  def fyzicky(self):
    return len(self._fyzicky)
  
  @property
  def fyzicky_tyzdenne(self):
    return len(self._fyzicky_tyzdenne)
  
  @property
  def fyzicky_podskupina(self):
    return len(self._fyzicky_podskupina)
  
  def __str__(self):
    return '{} {} {} {} {}'.format(self.fyzicky, self.fyzicky_podskupina,
      self.prepocitany, self.prepocitany_podskupina, self.fyzicky_tyzdenne)

class PocitadloSucet(object):
  def __init__(self, *pocitadla):
    self.pocitadla = pocitadla

  @property
  def fyzicky(self):
    return sum(getattr(x, 'fyzicky') for x in self.pocitadla)

  @property
  def fyzicky_tyzdenne(self):
    return sum(getattr(x, 'fyzicky_tyzdenne') for x in self.pocitadla)

  @property
  def fyzicky_podskupina(self):
    return sum(getattr(x, 'fyzicky_podskupina') for x in self.pocitadla)

  @property
  def prepocitany(self):
    return sum(getattr(x, 'prepocitany') for x in self.pocitadla)

  @property
  def prepocitany_podskupina(self):
    return sum(getattr(x, 'prepocitany_podskupina') for x in self.pocitadla)

class PocitadloStruktura(object):
  def __init__(self):
    self.profesor = Pocitadlo()
    self.docent = Pocitadlo()
    self.hostujuci_profesor = Pocitadlo()
    self.odborny_asistent = Pocitadlo()
    self.asistent = Pocitadlo()
    self.lektor = Pocitadlo()
    self.ucitelia_spolu = PocitadloSucet(self.profesor, self.docent, self.hostujuci_profesor, self.odborny_asistent, self.lektor)
    self.vyskumny_pracovnik = Pocitadlo()
    self.zamestnanci_spolu = PocitadloSucet(self.ucitelia_spolu, self.vyskumny_pracovnik)
    self.doktorand = Pocitadlo()
    self.zamestanci_mimo_pomeru = Pocitadlo()
    self.spolu = PocitadloSucet(self.zamestnanci_spolu, self.doktorand, self.zamestanci_mimo_pomeru)
    self.pocitadla = ['profesor', 'docent', 'hostujuci_profesor',
      'odborny_asistent', 'asistent', 'lektor', 'ucitelia_spolu', 'vyskumny_pracovnik',
      'zamestnanci_spolu', 'doktorand', 'zamestnanci_mimo_pomeru', 'spolu']
    
  def pridaj(self, id, funkcia, kvalifikacia, vaha):
    treti_stupen = ['10', '11', '12', '20', '21', '30', '31']
    if funkcia == '1P':
      self.profesor.pridaj(id, vaha, kvalifikacia != '12')
    elif funkcia == '2D':
      self.docent.pridaj(id, vaha, False)
    elif funkcia == '3O':
      self.odborny_asistent.pridaj(id, vaha, kvalifikacia in treti_stupen)
    elif funkcia == '4A':
      self.asistent.pridaj(id, vaha, kvalifikacia in treti_stupen)
    elif funkcia == '5L':
      self.lektor.pridaj(id, vaha, kvalifikacia in treti_stupen)
    elif funkcia in ['6V', '6T', '6P']:
      self.vyskumny_pracovnik.pridaj(id, vaha, kvalifikacia in treti_stupen)
    elif funkcia == '0S':
      self.doktorand.pridaj(id, vaha, kvalifikacia in treti_stupen)
    elif funkcia in ['9U', '9V']:
      self.zamestanci_mimo_pomeru.pridaj(id, vaha, kvalifikacia in treti_stupen)
    
  def __str__(self):
    return 'fyzicky z_toho prepocitany z_toho fyz_tyzdenny\n'+'\n'.join('{}: {}'.format(x.rjust(20), getattr(self, x)) for x in self.pocitadla)