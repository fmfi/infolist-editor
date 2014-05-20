# -*- coding: utf-8 -*-
from decimal import Decimal

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

  def sum(self, attr):
    return sum(getattr(x, attr) for x in self.pocitadla)

  @property
  def fyzicky(self):
    return self.sum('fyzicky')

  @property
  def fyzicky_tyzdenne(self):
    return self.sum('fyzicky_tyzdenne')

  @property
  def fyzicky_podskupina(self):
    return self.sum('fyzicky_podskupina')

  @property
  def prepocitany(self):
    return self.sum('prepocitany')

  @property
  def prepocitany_podskupina(self):
    return self.sum('prepocitany_podskupina')

class PocitadloSucetSpecial(PocitadloSucet):
  def __init__(self, prof, doc, *ostat):
    self.profdoc = PocitadloSucet(prof, doc)
    self.ostat = PocitadloSucet(*ostat)
  
  def sum(self, attr):
    v = self.ostat.sum(attr)
    if attr == 'fyzicky_podskupina':
      v += self.profdoc.fyzicky
    elif attr == 'prepocitany_podskupina':
      v += self.profdoc.prepocitany
    else:
      v += self.profdoc.sum(attr)
    return v

class PocitadloStruktura(object):
  def __init__(self):
    self.profesor = Pocitadlo()
    self.docent = Pocitadlo()
    self.hostujuci_profesor = Pocitadlo()
    self.odborny_asistent = Pocitadlo()
    self.asistent = Pocitadlo()
    self.lektor = Pocitadlo()
    self.ucitelia_spolu = PocitadloSucetSpecial(self.profesor, self.docent, self.hostujuci_profesor, self.odborny_asistent, self.lektor)
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
    if funkcia in ['1P', '1H']:
      self.profesor.pridaj(id, vaha, not kvalifikacia.startswith('1'))
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

