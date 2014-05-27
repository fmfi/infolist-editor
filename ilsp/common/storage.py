# -*- coding: utf-8 -*-

def dict_rec_update(d1, d2):
  for key in d2:
    if isinstance(d2[key], dict):
      d1[key] = dict_rec_update(d1.get(key, {}), d2[key])
    else:
      d1[key] = d2[key]
  return d1

def kratke_meno(meno, priezvisko):
  ret = u''
  if meno is not None and len(meno) > 0:
    ret += u'{}. '.format(meno[0])
  ret += priezvisko
  return ret

class User(object):
  def __init__(self, id, login, meno, priezvisko, cele_meno):
    self.id = id
    self.login = login
    self.meno = meno
    self.priezvisko = priezvisko
    self.cele_meno = cele_meno
    self.opravnenia = {}
  
  def opravnenie(self, fakulta, opr):
    v = self.opravnenia.get(fakulta)
    if v == None:
      return v
    return v.get(opr)
  
  def moze_zahadzovat_infolisty(self):
    return self.opravnenie('FMFI', 'admin')
  
  def moze_odomknut_infolist(self, il):
    return self.opravnenie('FMFI', 'admin') or (il['zamkol'] == self.id)
  
  def moze_spravovat_pouzivatelov(self):
    return self.opravnenie('FMFI', 'admin')
  
  def vidi_studijne_programy(self):
    return True
  
  def moze_vytvarat_studijne_programy(self):
    return self.opravnenie('FMFI', 'admin')
  
  def moze_menit_kody_sp(self):
    return self.opravnenie('FMFI', 'admin')
  
  def moze_menit_studprog(self):
    return self.opravnenie('FMFI', 'admin') or self.opravnenie('FMFI', 'garant')
  
  def moze_odomknut_studprog(self, sp):
    return self.opravnenie('FMFI', 'admin') or (self.moze_menit_studprog() and sp['zamkol'] == self.id)
  
  def vidi_stav_vyplnania(self):
    return self.vidi_studijne_programy()
  
  def vidi_dokumenty_sp(self):
    return self.vidi_studijne_programy()
  
  def moze_pridat_nahradu_hodnotenia(self):
    return self.opravnenie('FMFI', 'admin')

  def vidi_exporty(self):
    return self.opravnenie('FMFI', 'admin')

  def moze_mazat_dokumenty(self):
    return self.opravnenie('FMFI', 'admin')

  def moze_uploadovat_vpchar(self):
    return self.opravnenie('FMFI', 'admin')

class SQLBuilder(object):
  def __init__(self, join_with=' ', item_format='{}'):
    self.parts = []
    self.params = []
    self.join_with = join_with
    self.item_format = item_format
    
  def __call__(self, text, *params, **kwargs):
    self.append(text, *params, **kwargs)
  
  def _unpack_args(self, text, *params):
    if isinstance(text, SQLBuilder):
      if len(params) != 0:
        raise ValueError('No params allowed with SQLBuilder arg')
      return text.query()
    return text, params
  
  def append(self, text, *params, **kwargs):
    text, params = self._unpack_args(text, *params)
    
    self.parts.append(text)
    if text.count('%s') != len(params):
      raise ValueError('Got {} placeholders but {} parameters'.format(text.count('%s'), len(params)))
    self.params.extend(params)
  
  def query(self):
    return str(self), self.params
  
  def __str__(self):
    return self.join_with.join(self.item_format.format(x) for x in self.parts)
  
  def __len__(self):
    return len(self.parts)

class ConditionBuilder(SQLBuilder):
  def __init__(self, join_with):
    super(ConditionBuilder, self).__init__(join_with=' {} '.format(join_with), item_format='({})')
    
  def append(self, text, *params, **kwargs):
    text, params = self._unpack_args(text, *params)
    
    positive = True
    if 'positive' in kwargs:
      positive = kwargs['positive']
    if not positive:
      text = ('NOT ({})'.format(text))
    super(ConditionBuilder, self).append(text, *params, **kwargs)
  
  @property
  def conds(self):
    return self.parts

