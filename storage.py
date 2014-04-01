# -*- coding: utf-8 -*-
import utils
from werkzeug.exceptions import BadRequest, NotFound
from utils import Podmienka
from export import *

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

class DataStore(object):
  def __init__(self, conn, podmienka_class=Podmienka):
    self.conn = conn
    self._typy_vyucujuceho = None
    self._druhy_cinnosti = None
    self._fakulty = None
    self._jazyky_vyucby = None
    self._typy_bloku = [('A', u'A: povinné predmety'), ('B', u'B: povinne voliteľné predmety'), ('C', u'C: výberové predmety')]
    self._podmienka_class = podmienka_class
  
  def cursor(self):
    return self.conn.cursor()
  
  def commit(self):
    return self.conn.commit()
  
  def rollback(self):
    return self.conn.rollback()
  
  def load_infolist(self, id, lang='sk'):
    with self.cursor() as cur:
      cur.execute('''SELECT i.posledna_verzia, i.import_z_aisu,
        i.forknute_z, i.zamknute, i.zamkol, i.zahodeny,
        p.kod_predmetu, p.povodny_kod,
        p.skratka, p.povodna_skratka
        FROM infolist i
        LEFT JOIN predmet_infolist pi ON i.id = pi.infolist
        LEFT JOIN predmet p ON pi.predmet = p.id
        WHERE i.id = %s''',
        (id,))
      data = cur.fetchone()
      if data == None:
        raise NotFound('infolist({})'.format(id))
      posledna_verzia, import_z_aisu, forknute_z, zamknute, zamkol, zahodeny, kod_predmetu, povodny_kod, skratka, povodna_skratka = data
      i = {
        'posledna_verzia': posledna_verzia,
        'import_z_aisu': import_z_aisu,
        'forknute_z': forknute_z,
        'zamknute': zamknute,
        'zamkol': zamkol,
        'zahodeny': zahodeny,
        'kod_predmetu': kod_predmetu,
        'skratka': skratka,
        'povodny_kod_predmetu': povodny_kod,
        'povodna_skratka': povodna_skratka
      }
      cur.execute('''SELECT DISTINCT sp.id as studprog, sp.skratka as studprog_skratka,
        spv.stupen_studia,
        spvp.nazov as studprog_nazov,
        spvbi.rocnik, spvbi.semester,
        CASE semester WHEN 'Z' THEN 0 WHEN 'L' THEN 1 ELSE 2 END as semester_poradie
        FROM studprog_verzia_blok_infolist spvbi
        INNER JOIN studprog sp ON sp.posledna_verzia = spvbi.studprog_verzia
        INNER JOIN studprog_verzia spv ON spv.id = spvbi.studprog_verzia
        LEFT JOIN studprog_verzia_preklad spvp ON spvp.studprog_verzia = spvbi.studprog_verzia
        WHERE spvbi.infolist = %s
        AND (spvp.jazyk_prekladu = 'sk' OR spvp.jazyk_prekladu IS NULL)
        ORDER BY rocnik NULLS LAST, semester_poradie, studprog_nazov
        ''', (id,))
      odp = []
      i['odporucane_semestre'] = [x._asdict() for x in cur.fetchall()]
      
    i.update(self.load_infolist_verzia(posledna_verzia, lang))
    return i
  
  def load_infolist_verzia(self, id, lang='sk'):
    with self.cursor() as cur:
      data = self._load_iv_data(cur, id)
      data['vyucujuci'] = self._load_iv_vyucujuci(cur, id)
      data['cinnosti'] = self._load_iv_cinnosti(cur, id)
      data['odporucana_literatura'] = self._load_iv_literatura(cur, id)
      data['modifikovali'] = self._load_iv_modifikovali(cur, id)
      data['suvisiace_predmety'] = self._load_iv_suvisiace_predmety(id)
      dict_rec_update(data, self._load_iv_trans(cur, id, lang))
    return data
  
  def _load_iv_data(self, cur, id):
    cur.execute('''SELECT pocet_kreditov,
      podm_absol_percenta_skuska, podm_absol_percenta_na_a,
      podm_absol_percenta_na_b, podm_absol_percenta_na_c,
      podm_absol_percenta_na_d, podm_absol_percenta_na_e,
      podm_absol_percenta_zapocet,
      hodnotenia_a_pocet, hodnotenia_b_pocet, hodnotenia_c_pocet,
      hodnotenia_d_pocet, hodnotenia_e_pocet, hodnotenia_fx_pocet,
      podmienujuce_predmety, odporucane_predmety, vylucujuce_predmety,
      modifikovane, predosla_verzia, fakulta, potrebny_jazyk,
      treba_zmenit_kod, predpokladany_semester, finalna_verzia,
      bude_v_povinnom, predpokladany_stupen_studia, nepouzivat_stupnicu,
      obsahuje_varovania
      FROM infolist_verzia WHERE id = %s''', (id,))
    row = cur.fetchone()
    if row == None:
      raise NotFound('infolist_verzia({})'.format(id))
    
    (pocet_kreditov, percenta_skuska,
    pct_a, pct_b, pct_c, pct_d, pct_e,
    percenta_zapocet,
    hodn_a, hodn_b, hodn_c, hodn_d, hodn_e, hodn_fx,
    podmienujuce_predmety, odporucane_predmety, vylucujuce_predmety,
    modifikovane, predosla_verzia, fakulta, potrebny_jazyk,
    treba_zmenit_kod, predpokladany_semester, finalna_verzia,
    bude_v_povinnom, predpokladany_stupen_studia, nepouzivat_stupnicu,
    obsahuje_varovania) = row
    
    iv = {
      'id': id,
      'pocet_kreditov': pocet_kreditov,
      'podm_absolvovania': {
        'percenta_skuska': percenta_skuska,
        'percenta_zapocet': percenta_zapocet,
        'nepouzivat_stupnicu': nepouzivat_stupnicu,
        'percenta_na': {
          'A': pct_a,
          'B': pct_b,
          'C': pct_c,
          'D': pct_d,
          'E': pct_e
        },
      },
      'hodnotenia_pocet': {
        'A': hodn_a,
        'B': hodn_b,
        'C': hodn_c,
        'D': hodn_d,
        'E': hodn_e,
        'Fx': hodn_fx
      },
      'podmienujuce_predmety': self._podmienka_class(podmienujuce_predmety),
      'odporucane_predmety': self._podmienka_class(odporucane_predmety),
      'vylucujuce_predmety': self._podmienka_class(vylucujuce_predmety),
      'modifikovane': modifikovane,
      'predosla_verzia': predosla_verzia,
      'fakulta': fakulta,
      'potrebny_jazyk': potrebny_jazyk,
      'treba_zmenit_kod': treba_zmenit_kod,
      'predpokladany_semester': predpokladany_semester,
      'predpokladany_stupen_studia': predpokladany_stupen_studia,
      'finalna_verzia': finalna_verzia,
      'bude_v_povinnom': bude_v_povinnom,
      'obsahuje_varovania': obsahuje_varovania
    }
    return iv
  
  def _load_iv_suvisiace_predmety(self, id):
    return self.fetch_predmety(where=(
      '''p.id IN (
          SELECT predmet
          FROM infolist_verzia_suvisiace_predmety ivsp
          WHERE ivsp.infolist_verzia = %s
         )
         OR p.id IN (
          SELECT rpi2.predmet 
          FROM infolist ri, predmet_infolist rpi,
            infolist_verzia_suvisiace_predmety rivsp,
            infolist ri2, predmet_infolist rpi2
          WHERE ri.posledna_verzia = %s
            AND rpi.infolist = ri.id
            AND rivsp.predmet = rpi.predmet
            AND rivsp.infolist_verzia = ri2.posledna_verzia
            AND ri2.id = rpi2.infolist
         )
      ''',
      (id,id)))
  
  def _load_iv_vyucujuci(self, cur, id):
    cur.execute('''SELECT ivv.osoba,
      o.cele_meno, o.meno, o.priezvisko, ivvt.typ_vyucujuceho
      FROM osoba o, infolist_verzia_vyucujuci ivv
      LEFT JOIN infolist_verzia_vyucujuci_typ ivvt
      ON ivv.infolist_verzia = ivvt.infolist_verzia AND ivv.osoba = ivvt.osoba
      WHERE ivv.osoba = o.id AND ivv.infolist_verzia = %s
      ORDER BY ivv.poradie''',
      (id,))
    ivv = []
    vyucujuci = None
    for osoba, cele_meno, meno, priezvisko, typ_vyucujuceho in cur:
      if vyucujuci == None or vyucujuci['osoba'] != osoba:
        vyucujuci = {'osoba': osoba,
                     'cele_meno': cele_meno,
                     'meno': meno,
                     'priezvisko': priezvisko,
                     'kratke_meno': kratke_meno(meno, priezvisko),
                     'typy': set()}
        ivv.append(vyucujuci)
      if typ_vyucujuceho is not None:
        vyucujuci['typy'].add(typ_vyucujuceho)
    return ivv
  
  def _load_iv_cinnosti(self, cur, id):
    cur.execute('''SELECT druh_cinnosti, metoda_vyucby,
      pocet_hodin, za_obdobie
      FROM infolist_verzia_cinnosti
      WHERE infolist_verzia = %s''',
      (id,))
    cinnosti = []
    for druh_cinnosti, metoda_vyucby, pocet_hodin, za_obdobie in cur:
      cinnosti.append({
        'druh_cinnosti': druh_cinnosti,
        'metoda_vyucby': metoda_vyucby,
        'pocet_hodin': pocet_hodin,
        'za_obdobie': za_obdobie,
      })
    return cinnosti
  
  def _load_iv_literatura(self, cur, id):
    cur.execute('''SELECT bib_id
      FROM infolist_verzia_literatura
      WHERE infolist_verzia = %s
      ORDER BY poradie''',
      (id,))
    literatura = []
    for bib_id, in cur:
      literatura.append(bib_id)
    
    cur.execute('''SELECT popis
      FROM infolist_verzia_nova_literatura
      WHERE infolist_verzia = %s
      ORDER BY poradie''',
      (id,))
    nove = []
    for popis, in cur:
      nove.append(popis)
    return {'zoznam': literatura, 'nove': nove}

  def _load_iv_modifikovali(self, cur, id):
    cur.execute('''SELECT o.id, o.cele_meno, o.meno, o.priezvisko
      FROM infolist_verzia_modifikovali ivm
      INNER JOIN osoba o ON ivm.osoba = o.id
      WHERE infolist_verzia = %s''',
      (id,))
    osoby = {}
    for row in cur:
      osoby[row.id] = {
        'cele_meno': row.cele_meno,
        'meno': row.meno,
        'priezvisko': row.priezvisko,
      }
    return osoby
  
  def _load_iv_trans(self, cur, id, lang='sk'):
    cur.execute('''SELECT nazov_predmetu, podm_absol_priebezne,
      podm_absol_skuska, podm_absol_nahrada, vysledky_vzdelavania,
      strucna_osnova
      FROM infolist_verzia_preklad
      WHERE infolist_verzia = %s AND jazyk_prekladu = %s''',
      (id, lang))
    data = cur.fetchone()
    if data == None:
      raise NotFound('infolist_verzia_preklad({}, {})'.format(id, lang))
    
    return {
      'nazov_predmetu': data.nazov_predmetu,
      'podm_absolvovania': {
        'skuska': data.podm_absol_skuska,
        'priebezne': data.podm_absol_priebezne,
        'nahrada': data.podm_absol_nahrada,
      },
      'vysledky_vzdelavania': data.vysledky_vzdelavania,
      'strucna_osnova': data.strucna_osnova,
      'jazyk_prekladu': lang,
    }
  
  def save_infolist(self, id, data, user=None, system_update=False):
    with self.cursor() as cur:
      if user.id not in data['modifikovali']:
        data['modifikovali'][user.id] = {
          'meno': user.meno,
          'priezvisko': user.priezvisko,
          'cele_meno': user.cele_meno
        }
      def select_for_update(id):
        cur.execute('''SELECT posledna_verzia, zamknute
          FROM infolist
          WHERE id = %s
          FOR UPDATE''',
          (id,))
      posledna_verzia = None
      if id != None:
        select_for_update(id)
        row = cur.fetchone()
        if row == None:
          raise NotFound('infolist({})'.format(id))
        if row.zamknute and not system_update:
          id = self.fork_infolist(id)
          select_for_update(id)
          row = cur.fetchone()
          if row == None:
            raise NotFound('infolist({})'.format(id))
          if row.zamknute:
            raise ValueError('Zamknuty novo vytvoreny infolist')
        posledna_verzia = row.posledna_verzia
      nova_verzia = self.save_infolist_verzia(posledna_verzia, data, user=user, system_update=system_update)
      if id != None:
        cur.execute('''UPDATE infolist
          SET posledna_verzia = %s
          WHERE id = %s''',
          (nova_verzia, id))
      else:
        cur.execute('''INSERT INTO infolist (posledna_verzia, vytvoril)
          VALUES (%s, %s)
          RETURNING id''',
          (nova_verzia, user.id if user else None)
        )
        id = cur.fetchone()[0]
      return id
  
  def save_infolist_verzia(self, predosla_verzia, data, lang='sk', user=None,
      system_update=False):
    nove_id = self._save_iv_data(predosla_verzia, data, user=user, system_update=system_update)
    self._save_iv_suvisiace_predmety(nove_id, data)
    self._save_iv_vyucujuci(nove_id, data['vyucujuci'])
    self._save_iv_cinnosti(nove_id, data['cinnosti'])
    self._save_iv_literatura(nove_id, data['odporucana_literatura'])
    self._save_iv_modifikovali(nove_id, data['modifikovali'])
    self._save_iv_trans(nove_id, data, lang=lang)
    return nove_id
    
  def _save_iv_data(self, predosla_verzia, data, user=None, system_update=False):
    pct = data['podm_absolvovania']['percenta_na']
    hodn = data['hodnotenia_pocet']
    with self.cursor() as cur:
      cur.execute('''INSERT INTO infolist_verzia (
          pocet_kreditov,
          podm_absol_percenta_skuska, podm_absol_percenta_na_a,
          podm_absol_percenta_na_b, podm_absol_percenta_na_c,
          podm_absol_percenta_na_d, podm_absol_percenta_na_e,
          podm_absol_percenta_zapocet,
          hodnotenia_a_pocet, hodnotenia_b_pocet, hodnotenia_c_pocet,
          hodnotenia_d_pocet, hodnotenia_e_pocet, hodnotenia_fx_pocet,
          podmienujuce_predmety, odporucane_predmety, vylucujuce_predmety,
          predosla_verzia, fakulta, potrebny_jazyk,
          treba_zmenit_kod, predpokladany_semester,
          modifikoval, finalna_verzia, bude_v_povinnom,
          predpokladany_stupen_studia, nepouzivat_stupnicu,
          obsahuje_varovania, hromadna_zmena)
        VALUES (''' + ', '.join(['%s'] * 29) + ''')
        RETURNING id''',
        (data['pocet_kreditov'], data['podm_absolvovania']['percenta_skuska'],
        pct['A'], pct['B'], pct['C'], pct['D'], pct['E'],
        data['podm_absolvovania']['percenta_zapocet'],
        hodn['A'], hodn['B'], hodn['C'], hodn['D'], hodn['E'], hodn['Fx'],
        data['podmienujuce_predmety'].serialize(), data['odporucane_predmety'].serialize(),
        data['vylucujuce_predmety'].serialize(), predosla_verzia,
        data['fakulta'], data['potrebny_jazyk'], data['treba_zmenit_kod'],
        data['predpokladany_semester'], None if user is None else user.id,
        data['finalna_verzia'], data['bude_v_povinnom'],
        data['predpokladany_stupen_studia'],
        data['podm_absolvovania']['nepouzivat_stupnicu'],
        data['obsahuje_varovania'], system_update))
      return cur.fetchone()[0]
  
  def _save_iv_suvisiace_predmety(self, iv_id, data):
    suvisiace_predmety = set()
    suvisiace_predmety.update(data['podmienujuce_predmety'].idset())
    suvisiace_predmety.update(data['odporucane_predmety'].idset())
    suvisiace_predmety.update(data['vylucujuce_predmety'].idset())
    with self.cursor() as cur:
      for predmet in suvisiace_predmety:
        cur.execute('''INSERT INTO infolist_verzia_suvisiace_predmety (infolist_verzia, predmet)
          VALUES (%s, %s)''',
          (iv_id, predmet))
  
  def _save_iv_vyucujuci(self, iv_id, vyucujuci):
    with self.cursor() as cur:
      for poradie, polozka in enumerate(vyucujuci, start=1):
        cur.execute('''INSERT INTO infolist_verzia_vyucujuci
          (infolist_verzia, poradie, osoba)
          VALUES (%s, %s, %s)''',
          (iv_id, poradie, polozka['osoba']))
        for typ in polozka['typy']:
          cur.execute('''INSERT INTO infolist_verzia_vyucujuci_typ
            (infolist_verzia, osoba, typ_vyucujuceho)
            VALUES (%s, %s, %s)''',
            (iv_id, polozka['osoba'], typ))
  
  def _save_iv_cinnosti(self, iv_id, cinnosti):
    with self.cursor() as cur:
      for cinnost in cinnosti:
        cur.execute('''INSERT INTO infolist_verzia_cinnosti
          (infolist_verzia, metoda_vyucby, druh_cinnosti, pocet_hodin,
          za_obdobie)
          VALUES (%s, %s, %s, %s, %s)''',
          (iv_id, cinnost['metoda_vyucby'], cinnost['druh_cinnosti'],
           cinnost['pocet_hodin'], cinnost['za_obdobie']))
  
  def _save_iv_literatura(self, iv_id, literatura):
    with self.cursor() as cur:
      for poradie, bib_id in enumerate(literatura['zoznam'], start=1):
        cur.execute('''INSERT INTO infolist_verzia_literatura
          (infolist_verzia, bib_id, poradie) VALUES (%s, %s, %s)''',
          (iv_id, bib_id, poradie))
      for poradie, popis in enumerate(literatura['nove'], start=1):
        cur.execute('''INSERT INTO infolist_verzia_nova_literatura
          (infolist_verzia, popis, poradie) VALUES (%s, %s, %s)''',
          (iv_id, popis, poradie))
  
  def _save_iv_modifikovali(self, iv_id, modifikovali):
    with self.cursor() as cur:
      for osoba in modifikovali:
        cur.execute('''INSERT INTO infolist_verzia_modifikovali
          (infolist_verzia, osoba) VALUES (%s, %s)''',
          (iv_id, osoba))
  
  def _save_iv_trans(self, iv_id, data, lang='sk'):
    with self.cursor() as cur:
      podm = data['podm_absolvovania']
      cur.execute('''INSERT INTO infolist_verzia_preklad
        (infolist_verzia, jazyk_prekladu,
         nazov_predmetu, podm_absol_priebezne, podm_absol_skuska,
         podm_absol_nahrada, vysledky_vzdelavania, strucna_osnova)
       VALUES (''' + ', '.join(['%s']*8) + ''')''',
       (iv_id, lang, data['nazov_predmetu'], podm['priebezne'], podm['skuska'],
        podm['nahrada'], data['vysledky_vzdelavania'], data['strucna_osnova']))
  
  def search_osoba(self, query):
    if len(query.strip()) < 2:
      return []
    
    conds = []
    params = []
    for part in query.split():
      conds.append("""(unaccent(meno) ILIKE unaccent(%s)
        OR unaccent(priezvisko) ILIKE unaccent(%s))""")
      params.append(part + '%') # TODO escape
      params.append(part + '%')
    
    select = '''SELECT id, cele_meno, meno, priezvisko FROM osoba
      WHERE vyucujuci AND {}'''.format(' AND '.join(conds))
    
    with self.cursor() as cur:
      cur.execute(select, params)
      return cur.fetchall()
  
  def load_osoba(self, id):
    with self.cursor() as cur:
      cur.execute('SELECT id, cele_meno, meno, priezvisko FROM osoba WHERE id = %s',
        (id,))
      return cur.fetchone()
  
  def load_typy_vyucujuceho(self, iba_povolene=False):
    if self._typy_vyucujuceho == None:
      with self.cursor() as cur:
        cur.execute('SELECT kod, popis, povolit_vyber FROM typ_vyucujuceho ORDER BY poradie')
        self._typy_vyucujuceho = cur.fetchall()
    return [(kod, popis) for kod, popis, povolene in self._typy_vyucujuceho if not iba_povolene or povolene]
  
  def load_druhy_cinnosti(self):
    if self._druhy_cinnosti == None:
      with self.cursor() as cur:
        cur.execute('SELECT kod, popis FROM druh_cinnosti ORDER BY poradie')
        self._druhy_cinnosti = cur.fetchall()
    return self._druhy_cinnosti
  
  def load_fakulty(self):
    if self._fakulty == None:
      with self.cursor() as cur:
        cur.execute('''SELECT kod, nazov FROM organizacna_jednotka
          WHERE nadriadena_kod = 'UK' AND typ = 'Fakul' ORDER BY nazov''')
        self._fakulty = cur.fetchall()
    return self._fakulty
  
  def search_literatura(self, query):
    if len(query.strip()) < 2:
      return []
    
    conds = []
    params = []
    for part in query.split():
      conds.append("""(unaccent(dokument) ILIKE unaccent(%s)
        OR unaccent(vyd_udaje) ILIKE unaccent(%s)
        OR unaccent(signatura) ILIKE unaccent(%s))""")
      params.append('%' + part + '%') # TODO escape
      params.append('%' + part + '%')
      params.append('%' + part + '%')
    
    select = '''SELECT bib_id, dokument, vyd_udaje, signatura FROM literatura
      WHERE {} ORDER by dokument'''.format(' AND '.join(conds))
    
    with self.cursor() as cur:
      cur.execute(select, params)
      return cur.fetchall()

  def load_literatura(self, id):
    with self.cursor() as cur:
      cur.execute('SELECT bib_id, dokument, vyd_udaje, signatura FROM literatura WHERE bib_id = %s',
        (id,))
      return cur.fetchone()
  
  def search_nova_literatura(self, query):
    with self.cursor() as cur:
      cur.execute('SELECT DISTINCT popis FROM infolist_verzia_nova_literatura WHERE popis LIKE %s ORDER by popis',
        (u'%{}%'.format(query),))
      return [x[0] for x in cur.fetchall()]

  def load_predmet(self, id):
    predmety = self.fetch_predmety(where=('p.id = %s', (id,)))
    if len(predmety) == 0:
      return None
    return predmety[0]

  def _fetch_predmety_simple(self, where=None):
    if where == None:
      where_cond = ''
      where_params = []
    else:
      where_cond, where_params = where
      where_cond = ' AND ' + where_cond

    with self.cursor() as cur:
      sql = '''SELECT DISTINCT p.id, p.kod_predmetu, p.skratka, iv.finalna_verzia, ivp.nazov_predmetu
          FROM predmet p
          LEFT JOIN predmet_infolist pi ON p.id = pi.predmet
          LEFT JOIN infolist i ON pi.infolist = i.id
          LEFT JOIN infolist_verzia iv ON i.posledna_verzia = iv.id
          LEFT JOIN infolist_verzia_preklad ivp ON iv.id = ivp.infolist_verzia
          WHERE (ivp.jazyk_prekladu = 'sk' OR ivp.jazyk_prekladu IS NULL) {}
          ORDER BY p.skratka, p.id, iv.finalna_verzia desc, ivp.nazov_predmetu'''.format(where_cond)
      cur.execute(sql, where_params)
      predmety = []
      for row in cur:
        if len(predmety) == 0 or predmety[-1]['id'] != row.id:
          predmety.append({
            'id': row.id,
            'kod_predmetu': row.kod_predmetu,
            'skratka': row.skratka,
            'nazvy_predmetu': []
          })
          finalna_verzia = None
        if row.nazov_predmetu:
          if finalna_verzia is not None and row.finalna_verzia != finalna_verzia:
            continue
          predmety[-1]['nazvy_predmetu'].append(row.nazov_predmetu)
          finalna_verzia = row.finalna_verzia
      return predmety

  def search_predmet(self, query):
    return self._fetch_predmety_simple(where=(
      'p.kod_predmetu LIKE %s OR ivp.nazov_predmetu LIKE %s',
      (u'%{}%'.format(query),u'%{}%'.format(query))
    ))

  def load_predmet_simple(self, id):
    predmety =  self._fetch_predmety_simple(where=(
      'p.id = %s',
      (id,)
    ))
    if len(predmety) == 0:
      return None
    return predmety[0]

  def fetch_predmety(self, where=None, osoba_id=None):
    params = []
    
    if osoba_id != None:
      params.append(osoba_id)
      oblubeny_sql = ', exists(SELECT 1 FROM oblubene_predmety WHERE predmet = p.id AND osoba = %s) as oblubeny'
    else:
      oblubeny_sql = ''
    
    if where != None:
      where_cond = ' AND ' + where[0]
      params.extend(where[1])
    else:
      where_cond = ''
    
    with self.cursor() as cur:
      sql = '''SELECT p.id as predmet_id, p.kod_predmetu, p.skratka,
          i.id as infolist_id, i.zamknute, i.zamkol, i.import_z_aisu, i.vytvoril, i.zahodeny,
          oz.cele_meno as zamkol_cele_meno,
          ov.cele_meno as vytvoril_cele_meno,
          iv.modifikovane, iv.finalna_verzia, iv.obsahuje_varovania,
          ivp.nazov_predmetu,
          o.id as osoba_id, o.cele_meno {}
          FROM predmet p
          LEFT JOIN predmet_infolist pi ON p.id = pi.predmet
          LEFT JOIN infolist i ON pi.infolist = i.id
          LEFT JOIN infolist_verzia iv ON i.posledna_verzia = iv.id
          LEFT JOIN osoba oz ON i.zamkol = oz.id
          LEFT JOIN osoba ov ON i.vytvoril = ov.id
          LEFT JOIN infolist_verzia_preklad ivp ON iv.id = ivp.infolist_verzia
          LEFT JOIN infolist_verzia_modifikovali ivm ON iv.id = ivm.infolist_verzia
          LEFT JOIN osoba o ON ivm.osoba = o.id
          WHERE ivp.jazyk_prekladu = 'sk' {}
          ORDER BY p.skratka, p.id, i.id, iv.id, o.cele_meno'''.format(oblubeny_sql, where_cond)
      cur.execute(sql, params)
      predmety = []
      for row in cur:
        if len(predmety) == 0 or predmety[-1]['id'] != row.predmet_id:
          predmet = {
            'id': row.predmet_id,
            'kod_predmetu': row.kod_predmetu,
            'skratka': row.skratka,
            'infolisty': []
          }
          if oblubeny_sql:
            predmet['oblubeny'] = row.oblubeny
          predmety.append(predmet)
        if row.infolist_id:
          infolisty = predmety[-1]['infolisty']
          if len(infolisty) == 0 or infolisty[-1]['id'] != row.infolist_id:
            infolisty.append({
              'id': row.infolist_id,
              'zamknute': row.zamknute,
              'zamkol': row.zamkol,
              'zamkol_cele_meno': row.zamkol_cele_meno,
              'vytvoril': row.vytvoril,
              'vytvoril_cele_meno': row.vytvoril_cele_meno,
              'zahodeny': row.zahodeny,
              'import_z_aisu': row.import_z_aisu,
              'modifikovane': row.modifikovane,
              'finalna_verzia': row.finalna_verzia,
              'obsahuje_varovania': row.obsahuje_varovania,
              'nazov_predmetu': row.nazov_predmetu,
              'modifikovali': []
            })
          if row.osoba_id:
            infolisty[-1]['modifikovali'].append({
              'id': row.osoba_id,
              'cele_meno': row.cele_meno
            })
      return predmety
  
  def fetch_moje_predmety(self, osoba_id=None, upravy=None, uci=None, vytvoril=None,
      oblubene=None, obsahuje_varovania=None, import_z_aisu=None,
      finalna_verzia=None, zamknute=None):
    
    def potrebujeme_osobu():
      if osoba_id == None:
        raise ValueError('Na tento filter treba mat osoba_id')
    
    il_cond = ConditionBuilder('OR')
    
    if upravy != None:
      potrebujeme_osobu()
      il_cond(
        '''
          ri.vytvoril = %s
          OR EXISTS (
            SELECT 1
            FROM infolist_verzia_modifikovali rivm
            WHERE rivm.infolist_verzia = ri.posledna_verzia
              AND rivm.osoba = %s
          )
        ''', osoba_id, osoba_id, positive=upravy)
      vytvoril = True
    
    if uci != None:
      potrebujeme_osobu()
      il_cond(
        '''
          EXISTS (
            SELECT 1
            FROM infolist_verzia_vyucujuci rivv
            WHERE rivv.infolist_verzia = ri.posledna_verzia
              AND rivv.osoba = %s
          )
        ''', osoba_id, positive=uci)
    
    il_filter = ConditionBuilder('AND')
    if obsahuje_varovania != None:
      il_filter('riv.obsahuje_varovania', positive=obsahuje_varovania)
    
    if finalna_verzia != None:
      il_filter('riv.finalna_verzia', positive=finalna_verzia)
    
    if import_z_aisu != None:
      il_filter('ri.import_z_aisu', positive=import_z_aisu)
    
    if zamknute != None:
      il_filter('ri.zamknute IS NOT NULL', positive=zamknute)
    
    cond = ConditionBuilder('OR')
    
    if il_cond:
      cond(
        '''
          EXISTS (
            SELECT ri.id
            FROM predmet_infolist rpi, infolist ri
            WHERE rpi.predmet = p.id AND rpi.infolist = ri.id
              AND 
              (
                {}
              )
          )
        '''.format(il_cond), *il_cond.params)
    
    if vytvoril != None:
      potrebujeme_osobu()
      cond('p.vytvoril = %s', osoba_id, positive=vytvoril)
    
    if oblubene != None:
      potrebujeme_osobu()
      cond('p.id IN (SELECT predmet FROM oblubene_predmety WHERE osoba = %s)',
           osoba_id, positive=oblubene)
    
    filt = ConditionBuilder('AND')
    if cond:
      filt(cond)
    
    if il_filter:
      filt(
        '''
          EXISTS (
            SELECT ri.id
            FROM predmet_infolist rpi, infolist ri, infolist_verzia riv
            WHERE rpi.predmet = p.id AND rpi.infolist = ri.id AND ri.posledna_verzia = riv.id
              AND 
              (
                {}
              )
          )
        '''.format(il_filter), *il_filter.params)
    
    if filt:
      where = (str(filt), filt.params)
    else:
      where = None
    return self.fetch_predmety(osoba_id=osoba_id, where=where)
  
  def load_jazyky_vyucby(self):
    if self._jazyky_vyucby == None:
      with self.cursor() as cur:
        cur.execute('SELECT kod, popis FROM jazyk_vyucby')
        self._jazyky_vyucby = cur.fetchall()
    return self._jazyky_vyucby
  
  def fork_infolist(self, id, verzia=None, vytvoril=None):
    with self.cursor() as cur:
      cur.execute('SELECT povodny_kod_predmetu, posledna_verzia FROM infolist WHERE id = %s', (id,))
      row = cur.fetchone()
      if row == None:
        raise NotFound('infolist({})'.format(id))
      povodny_kod_predmetu = row.povodny_kod_predmetu
      if verzia == None:
        verzia = row.posledna_verzia
      cur.execute('''INSERT INTO infolist (posledna_verzia, forknute_z, povodny_kod_predmetu, vytvoril)
        VALUES (%s, %s, %s, %s) RETURNING id''',
        (verzia, id, povodny_kod_predmetu, vytvoril))
      nove_id = cur.fetchone()[0]
      cur.execute('''INSERT INTO predmet_infolist (predmet, infolist)
        SELECT predmet, %s
        FROM predmet_infolist
        WHERE infolist = %s''',
        (nove_id, id))
      return nove_id
  
  def load_user(self, username):
    users = self.load_users(where=('o.login = %s', (username,)))
    if len(users) == 0:
      return None
    elif len(users) > 1:
      raise ValueError('SELECT vratil viacerych pouzivatelov... WTF')
    return users[0]
  
  def load_users(self, where=None):
    if where == None:
      where_cond = ''
      where_params = []
    else:
      where_cond = 'WHERE {}'.format(where[0])
      where_params = where[1]
    
    with self.cursor() as cur:
      cur.execute('''SELECT o.id, o.login, o.meno, o.priezvisko, o.cele_meno,
          op.organizacna_jednotka, op.je_admin, op.je_garant
        FROM osoba o
        INNER JOIN ilsp_opravnenia op ON o.id = op.osoba
        {}
        ORDER BY o.priezvisko'''.format(where_cond)
        , where_params)
      users = []
      for row in cur:
        if len(users) == 0 or users[-1].id != row.id:
          users.append(User(row.id, row.login, row.meno, row.priezvisko, row.cele_meno))
        
        users[-1].opravnenia[row.organizacna_jednotka] = {
          'admin': row.je_admin,
          'garant': row.je_garant,
        }
      return users
  
  def trash_infolist(self, id, trashed=True):
    with self.cursor() as cur:
      cur.execute('SELECT zahodeny, zamknute, zamkol FROM infolist WHERE id = %s FOR UPDATE', (id,))
      row = cur.fetchone()
      if row == None:
        raise NotFound('infolist({})'.format(id))
      sql = SQLBuilder()
      sql.append('UPDATE infolist SET')

      sqlset = SQLBuilder(', ')
      sqlset.append('zahodeny = %s', trashed)
      if trashed:
        if row.zamknute is None:
          sqlset.append('zamknute = now()')
      else:
        if row.zamknute is not None and row.zamkol is None:
          sqlset.append('zamknute = NULL')

      sql.append(sqlset)
      sql.append('WHERE id = %s', id)
      cur.execute(*sql.query())
  
  def lock_infolist(self, id, user):
    self._lock('infolist', id, user)

  def lock_studprog(self, id, user):
    self._lock('studprog', id, user)

  def _lock(self, table, id, user):
    with self.cursor() as cur:
      cur.execute('SELECT zamknute, zamkol FROM {} WHERE id = %s FOR UPDATE'.format(table), (id,))
      row = cur.fetchone()
      if row == None:
        raise NotFound('{}({})'.format(table, id))
      if row.zamknute:
        raise ValueError('{} {} je uz zamknuty'.format(table, id))
      cur.execute('UPDATE {} SET zamknute = now(), zamkol = %s WHERE id = %s'.format(table), (user, id))
  
  def unlock_infolist(self, id, check_user=None):
    if check_user:
      def check(zamkol):
        return check_user.moze_odomknut_infolist({'zamkol': zamkol})
    else:
      check = None
    self._unlock('infolist', id, check)
  
  def unlock_studprog(self, id, check_user=None):
    if check_user:
      def check(zamkol):
        return check_user.moze_odomknut_studprog({'zamkol': zamkol})
    else:
      check = None
    self._unlock('studprog', id, check)

  def _unlock(self, table, id, check=None):
    with self.cursor() as cur:
      cur.execute('SELECT zamknute, zamkol FROM {} WHERE id = %s FOR UPDATE'.format(table), (id,))
      row = cur.fetchone()
      if row == None:
        raise NotFound('{}({})'.format(table, id))
      if not row.zamknute:
        raise ValueError('{} {} je uz odomknuty'.format(table, id))
      if check != None:
        if not check(row.zamkol):
          raise ValueError('Nema opravnenie odomknut {} {}'.format(table, id))
      cur.execute('UPDATE {} SET zamknute = NULL, zamkol = NULL WHERE id = %s'.format(table), (id,))
  
  def create_predmet(self, osoba_id=None):
    with self.cursor() as cur:
      cur.execute(
        '''
          WITH kod AS (SELECT 'TEMP-' || nextval('predmet_novy_kod') AS skratka)
          INSERT INTO predmet(kod_predmetu, skratka, zmenit_kod, vytvoril)
          SELECT skratka, skratka, true, %s FROM kod
          RETURNING id, skratka
        ''',
        (osoba_id,)
      )
      return cur.fetchone()
  
  def predmet_add_infolist(self, predmet_id, infolist_id):
    with self.cursor() as cur:
      cur.execute('INSERT INTO predmet_infolist (predmet, infolist) VALUES (%s, %s)',
                  (predmet_id, infolist_id))
  
  def predmet_watch(self, predmet_id, osoba_id):
    with self.cursor() as cur:
      cur.execute('INSERT INTO oblubene_predmety (predmet, osoba) VALUES (%s, %s)',
                  (predmet_id, osoba_id))
  
  def predmet_unwatch(self, predmet_id, osoba_id):
    with self.cursor() as cur:
      cur.execute('DELETE FROM oblubene_predmety WHERE predmet = %s AND osoba = %s',
                  (predmet_id, osoba_id))
  
  def load_studprog(self, id, lang='sk', verzia=None):
    with self.cursor() as cur:
      cur.execute('''SELECT sp.skratka, sp.posledna_verzia, sp.zamknute, sp.zamkol, sp.vytvorene, sp.vytvoril,
          sp.oblast_vyskumu
        FROM studprog sp
        WHERE sp.id = %s
        ''',
        (id,))
      data = cur.fetchone()
      if data is None:
        raise NotFound('studprog({})'.format(id))
      if verzia is None:
        verzia = data.posledna_verzia
      sp = {
        'id': id,
        'skratka': data.skratka,
        'posledna_verzia': data.posledna_verzia,
        'zamknute': data.zamknute,
        'zamkol': data.zamkol,
        'vytvorene': data.vytvorene,
        'vytvoril': data.vytvoril,
        'verzia': verzia,
        'oblast_vyskumu': data.oblast_vyskumu
      }
      sp.update(self.load_studprog_verzia(verzia, lang))
      vyrob_rozsah = utils.rozsah()

      for blok in sp['bloky']:
        blok['poznamky'] = []
        for infolist in blok['infolisty']:
          if 'cinnosti' in infolist:
            infolist['rozsah'] = vyrob_rozsah(infolist['cinnosti'])
          if infolist['poznamka']:
            try:
              infolist['poznamka_cislo'] = blok['poznamky'].index(infolist['poznamka'])
            except ValueError:
              infolist['poznamka_cislo'] = len(blok['poznamky'])
              blok['poznamky'].append(infolist['poznamka'])
          else:
            infolist['poznamka_cislo'] = None

      return sp
  
  def load_studprog_verzia(self, id, lang='sk'):
    data = self._load_spv_data(id)
    dict_rec_update(data, self._load_spv_trans(id, lang))
    data['bloky'] = self._load_spv_bloky(id, lang)
    data['modifikovali'] = self._load_spv_modifikovali(id)
    return data
  
  def _load_spv_data(self, id):
    with self.cursor() as cur:
      cur.execute('''SELECT aj_konverzny_program, stupen_studia, garant,
          modifikovane, modifikoval, obsahuje_varovania, finalna_verzia
        FROM studprog_verzia
        WHERE id = %s
        ''',
        (id,))
      data = cur.fetchone()
      if data is None:
        raise NotFound('studprog_verzia({})'.format(id))
      return {
        'aj_konverzny_program': data.aj_konverzny_program,
        'stupen_studia': data.stupen_studia,
        'garant': data.garant,
        'modifikoval': data.modifikoval,
        'modifikovane': data.modifikovane,
        'obsahuje_varovania': data.obsahuje_varovania,
        'finalna_verzia': data.finalna_verzia,
      }
  
  def _load_spv_trans(self, id, lang='sk'):
    with self.cursor() as cur:
      cur.execute('''SELECT nazov, podmienky_absolvovania, poznamka_konverzny
        FROM studprog_verzia_preklad
        WHERE studprog_verzia = %s AND jazyk_prekladu = %s
        ''',
        (id, lang))
      data = cur.fetchone()
      if data is None:
        raise NotFound('studprog_verzia_preklad({}, {})'.format(id, lang))
      return {
        'nazov': data.nazov,
        'podmienky_absolvovania': data.podmienky_absolvovania,
        'poznamka_konverzny': data.poznamka_konverzny
      }
  
  def _load_spv_bloky(self, id, lang='sk'):
    with self.cursor() as cur:
      cur.execute('''SELECT spvb.poradie_blok, spvb.typ, spvbp.nazov, spvbp.podmienky,
          spvbi.infolist, spvbi.semester, spvbi.rocnik, spvbi.poznamka, spvbi.predmet_jadra,
          p.kod_predmetu, p.skratka, ivp.nazov_predmetu, i.posledna_verzia as infolist_verzia, iv.pocet_kreditov,
          CASE spvbi.semester WHEN 'Z' THEN 0 WHEN 'L' THEN 1 ELSE 2 END as semester_poradie
        FROM studprog_verzia_blok spvb
        LEFT JOIN studprog_verzia_blok_preklad spvbp ON spvbp.studprog_verzia = spvb.studprog_verzia AND spvbp.poradie_blok = spvb.poradie_blok
        LEFT JOIN studprog_verzia_blok_infolist spvbi ON spvbi.studprog_verzia = spvb.studprog_verzia AND spvbi.poradie_blok = spvb.poradie_blok
        LEFT JOIN predmet_infolist pi ON spvbi.infolist = pi.infolist
        LEFT JOIN predmet p ON pi.predmet = p.id
        LEFT JOIN infolist i ON spvbi.infolist = i.id
        LEFT JOIN infolist_verzia iv ON i.posledna_verzia = iv.id
        LEFT JOIN infolist_verzia_preklad ivp ON i.posledna_verzia = ivp.infolist_verzia
        WHERE spvb.studprog_verzia = %s
        AND (spvbp.jazyk_prekladu = %s OR spvbp.jazyk_prekladu IS NULL)
        AND (ivp.jazyk_prekladu = %s OR ivp.jazyk_prekladu IS NULL)
        ORDER BY spvbp.studprog_verzia, spvbp.poradie_blok, spvbi.rocnik NULLS LAST, semester_poradie, spvbi.semester desc, ivp.nazov_predmetu
        ''',
        (id, lang, lang))
      bloky = []
      for row in cur:
        if len(bloky) == 0 or bloky[-1]['poradie_blok'] != row.poradie_blok:
          blok = {
            'poradie_blok': row.poradie_blok,
            'nazov': row.nazov,
            'podmienky': row.podmienky,
            'typ': row.typ,
            'infolisty': []
          }
          bloky.append(blok)
        if row.infolist is not None:
          infolist = {
            'infolist': row.infolist,
            'posledna_verzia': row.infolist_verzia,
            'semester': row.semester,
            'rocnik': row.rocnik,
            'poznamka': row.poznamka,
            'kod_predmetu': row.kod_predmetu,
            'skratka_predmetu': row.skratka,
            'nazov_predmetu': row.nazov_predmetu,
            'pocet_kreditov': row.pocet_kreditov,
            'predmet_jadra': row.predmet_jadra,
          }
          with self.cursor() as cur2:
            infolist['vyucujuci'] = self._load_iv_vyucujuci(cur2, row.infolist_verzia)
            infolist['cinnosti'] = self._load_iv_cinnosti(cur2, row.infolist_verzia)
          bloky[-1]['infolisty'].append(infolist)
      return bloky

  def _load_spv_modifikovali(self, id):
    with self.cursor() as cur:
      cur.execute('''SELECT o.id, o.cele_meno, o.meno, o.priezvisko
        FROM studprog_verzia_modifikovali spvm
        INNER JOIN osoba o ON spvm.osoba = o.id
        WHERE studprog_verzia = %s''',
        (id,))
      osoby = {}
      for row in cur:
        osoby[row.id] = {
          'cele_meno': row.cele_meno,
          'meno': row.meno,
          'priezvisko': row.priezvisko,
        }
      return osoby

  def save_studprog(self, id, data, user):
    with self.cursor() as cur:
      if user.id not in data['modifikovali']:
        data['modifikovali'][user.id] = {
          'meno': user.meno,
          'priezvisko': user.priezvisko,
          'cele_meno': user.cele_meno
        }
      def select_for_update(id):
        cur.execute('''SELECT posledna_verzia, zamknute
          FROM studprog
          WHERE id = %s
          FOR UPDATE''',
          (id,))
      posledna_verzia = None
      if id != None:
        select_for_update(id)
        row = cur.fetchone()
        if row == None:
          raise NotFound('studprog({})'.format(id))
        if row.zamknute:
          raise ValueError('Zamknuty studijny program')
        posledna_verzia = row.posledna_verzia
      nova_verzia = self.save_studprog_verzia(posledna_verzia, data, user=user)
      if id != None:
        sql = 'UPDATE studprog SET posledna_verzia = %s'
        params = [nova_verzia]
        if 'skratka' in data:
          sql += ', skratka = %s'
          params.append(data['skratka'])
        sql += ' WHERE id = %s'
        params.append(id)
        cur.execute(sql, params)
      else:
        cur.execute('''INSERT INTO studprog (posledna_verzia, vytvoril, skratka)
          VALUES (%s, %s, %s)
          RETURNING id''',
          (nova_verzia, user.id if user else None, data.get('skratka'))
        )
        id = cur.fetchone()[0]
      return id
  
  def save_studprog_verzia(self, predosla_verzia, data, lang='sk', user=None):
    nove_id = self._save_spv_data(predosla_verzia, data, user=user)
    self._save_spv_trans(nove_id, data, lang=lang)
    self._save_spv_bloky(nove_id, data['bloky'], lang=lang)
    self._save_spv_modifikovali(nove_id, data['modifikovali'])
    return nove_id
  
  def _save_spv_data(self, predosla_verzia, data, user=None):
    with self.cursor() as cur:
      cur.execute('''INSERT INTO studprog_verzia (
          aj_konverzny_program, stupen_studia, garant,
          modifikoval, obsahuje_varovania, finalna_verzia,
          predosla_verzia
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id''',
        (data['aj_konverzny_program'], data['stupen_studia'],
         data['garant'], user.id if user else None, data['obsahuje_varovania'],
         data['finalna_verzia'], predosla_verzia))
      return cur.fetchone()[0]
  
  def _save_spv_trans(self, spv_id, data, lang='sk'):
    with self.cursor() as cur:
      cur.execute('''INSERT INTO studprog_verzia_preklad
        (studprog_verzia, jazyk_prekladu, nazov, podmienky_absolvovania,
         poznamka_konverzny)
        VALUES (''' + ', '.join(['%s']*5) + ''')''',
        (spv_id, lang, data['nazov'], data['podmienky_absolvovania'],
         data['poznamka_konverzny']))
  
  def _save_spv_bloky(self, spv_id, bloky, lang='sk'):
    with self.cursor() as cur:
      for poradie, blok in enumerate(bloky, start=1):
        cur.execute('''INSERT INTO studprog_verzia_blok
          (studprog_verzia, poradie_blok, typ)
          VALUES (%s, %s, %s)''',
          (spv_id, poradie, blok['typ']))
        cur.execute('''INSERT INTO studprog_verzia_blok_preklad
          (studprog_verzia, jazyk_prekladu, poradie_blok,
          nazov, podmienky)
          VALUES (%s, %s, %s, %s, %s)''',
          (spv_id, lang, poradie, blok['nazov'], blok['podmienky']))
        for infolist in blok['infolisty']:
          cur.execute('''INSERT INTO studprog_verzia_blok_infolist
            (studprog_verzia, poradie_blok, infolist, semester, rocnik,
            poznamka, predmet_jadra)
            VALUES (%s, %s, %s, %s, %s, %s, %s)''',
            (spv_id, poradie, infolist['infolist'], infolist['semester'],
             infolist['rocnik'], infolist['poznamka'], infolist['predmet_jadra']))
  
  def _save_spv_modifikovali(self, spv_id, modifikovali):
    with self.cursor() as cur:
      for osoba in modifikovali:
        cur.execute('''INSERT INTO studprog_verzia_modifikovali
          (studprog_verzia, osoba) VALUES (%s, %s)''',
          (spv_id, osoba))
  
  def fetch_studijne_programy(self, lang='sk'):
    with self.cursor() as cur:
      cur.execute('''SELECT sp.id, sp.skratka, sp.zamknute, sp.zamkol, sp.vytvorene, sp.vytvoril, sp.oblast_vyskumu,
          spv.aj_konverzny_program, spv.stupen_studia, spv.modifikovane, spv.modifikoval, spv.obsahuje_varovania, spv.finalna_verzia,
          spvp.nazov, spvp.podmienky_absolvovania, spvp.poznamka_konverzny,
          ov.cele_meno as vytvoril_cele_meno,
          om.cele_meno as modifikoval_cele_meno,
          oml.cele_meno as mlist_cele_meno, oml.id as mlist_id
        FROM studprog sp
        INNER JOIN studprog_verzia spv ON sp.posledna_verzia = spv.id
        LEFT JOIN studprog_verzia_preklad spvp ON spv.id = spvp.studprog_verzia AND spvp.jazyk_prekladu = %s
        LEFT JOIN osoba ov ON sp.vytvoril = ov.id
        LEFT JOIN osoba om ON spv.modifikoval = om.id
        LEFT JOIN studprog_verzia_modifikovali spvm ON spv.id = spvm.studprog_verzia
        LEFT JOIN osoba oml ON spvm.osoba = oml.id
        ORDER BY spvp.nazov, spv.stupen_studia
        ''',
        (lang,))
      results = []
      for row in cur:
        if len(results) == 0 or results[-1]['id'] != row.id:
          sp = {}
          rdict = row._asdict()
          for col in rdict:
            if not col.startswith('mlist_'):
              sp[col] = rdict[col]
          sp['modifikovali'] = []
          results.append(sp)
        if row.mlist_cele_meno:
          results[-1]['modifikovali'].append({
            'cele_meno': row.mlist_cele_meno,
            'id': row.mlist_id
          })
      return results
  
  def search_infolist(self, query, finalna=False):
    cond = ConditionBuilder('AND')
    like = ConditionBuilder('OR')
    like('p.kod_predmetu ILIKE %s', u'%{}%'.format(query))
    like('ivp.nazov_predmetu ILIKE %s', u'%{}%'.format(query))
    cond(like)
    if finalna:
        cond('iv.finalna_verzia')
        cond('not i.zahodeny')
    return self.fetch_infolisty(cond)
  
  def fetch_infolisty(self, cond=None):
    with self.cursor() as cur:
      if cond:
        where = ' AND ({})'.format(cond)
        where_params = cond.params
      else:
        where = ''
        where_params = []
      
      sql = '''SELECT i.id, i.zahodeny,
          iv.id as infolist_verzia, iv.pocet_kreditov,
          iv.modifikovane, iv.finalna_verzia, iv.obsahuje_varovania,
          oz.cele_meno as zamkol_cele_meno,
          ov.cele_meno as vytvoril_cele_meno,
          ivp.nazov_predmetu,
          p.kod_predmetu, p.skratka
          FROM infolist i
          LEFT JOIN osoba oz ON i.zamkol = oz.id
          LEFT JOIN osoba ov ON i.vytvoril = ov.id
          INNER JOIN infolist_verzia iv ON i.posledna_verzia = iv.id
          LEFT JOIN infolist_verzia_preklad ivp ON i.posledna_verzia = ivp.infolist_verzia
          LEFT JOIN predmet_infolist pi ON i.id = pi.infolist
          LEFT JOIN predmet p ON pi.predmet = p.id
          WHERE (ivp.jazyk_prekladu = 'sk' OR ivp.jazyk_prekladu IS NULL)
          {}
          ORDER BY p.skratka, p.id, ivp.nazov_predmetu'''.format(where)
      cur.execute(sql, where_params)
      infolisty = []
      for row in cur:
        infolist = {
          'id': row.id,
          'kod_predmetu': row.kod_predmetu,
          'skratka': row.skratka,
          'nazov_predmetu': row.nazov_predmetu,
          'pocet_kreditov': row.pocet_kreditov,
          'modifikovane': row.modifikovane,
          'finalna_verzia': row.finalna_verzia,
          'obsahuje_varovania': row.obsahuje_varovania,
          'zamkol': row.zamkol_cele_meno,
          'vytvoril': row.vytvoril_cele_meno,
          'zahodeny': row.zahodeny
        }
        with self.cursor() as cur2:
          infolist['vyucujuci'] = self._load_iv_vyucujuci(cur2, row.infolist_verzia)
          infolist['cinnosti'] = self._load_iv_cinnosti(cur2, row.infolist_verzia)
        infolisty.append(infolist)
      return infolisty
  
  def fetch_infolist(self, id):
    cond = ConditionBuilder('AND')
    cond('i.id = %s', id)
    infolisty = self.fetch_infolisty(cond)
    if len(infolisty) == 0:
      return None
    return infolisty[0]
  
  def load_typy_bloku(self):
    return self._typy_bloku
  
  def find_sp_warnings(self, limit_sp=None):
    with self.cursor() as cur:
      sql = '''SELECT sq.* FROM (SELECT sp.id, sp.skratka,
          spvp.nazov,
          i.id as infolist_id,
          p.id as predmet_id, p.skratka as skratka_predmetu,
          ivp.nazov_predmetu,
          (NOT iv.finalna_verzia) as w_finalna,
          (spv.stupen_studia <> iv.predpokladany_stupen_studia) as w_stupen_studia,
          (spvbi.semester <> iv.predpokladany_semester) as w_semester,
          (EXISTS (
            SELECT 1 
            FROM predmet_infolist pi2,
              infolist i2, infolist_verzia iv2
            WHERE pi.predmet = pi2.predmet
            AND pi2.infolist <> pi.infolist AND pi2.infolist = i2.id AND
            i2.posledna_verzia = iv2.id AND iv2.finalna_verzia)) as w_finalna2,
          (i.zahodeny) as w_zahodeny
        FROM studprog sp
        INNER JOIN studprog_verzia spv ON sp.posledna_verzia = spv.id
        INNER JOIN studprog_verzia_blok_infolist spvbi ON spv.id = spvbi.studprog_verzia
        INNER JOIN infolist i ON spvbi.infolist = i.id
        INNER JOIN infolist_verzia iv ON i.posledna_verzia = iv.id
        LEFT JOIN studprog_verzia_preklad spvp ON spvp.studprog_verzia = spv.id
        LEFT JOIN infolist_verzia_preklad ivp ON ivp.infolist_verzia = iv.id
        LEFT JOIN predmet_infolist pi ON pi.infolist = i.id
        LEFT JOIN predmet p ON pi.predmet = p.id
        WHERE (spvp.jazyk_prekladu = 'sk' OR spvp.jazyk_prekladu IS NULL)
        AND (ivp.jazyk_prekladu = 'sk' OR ivp.jazyk_prekladu IS NULL)
        {}
        ) AS sq
        WHERE (w_finalna OR w_stupen_studia OR w_semester OR w_finalna2 OR w_zahodeny)
        ORDER BY id, infolist_id
      '''
      if limit_sp is not None:
        sql = sql.format(' AND sp.id = %s')
        params = [limit_sp]
      else:
        sql = sql.format('')
        params = []
      cur.execute(sql, params)
      sp = []
      for row in cur:
        if len(sp) == 0 or row.id != sp[-1]['id']:
          sp.append({
            'id': row.id,
            'skratka': row.skratka,
            'nazov': row.nazov,
            'messages': []
          })
        def add_infolist_warning(typ):
          sp[-1]['messages'].append({
            'typ': typ,
            'infolist': row.infolist_id,
            'nazov_predmetu': row.nazov_predmetu,
            'skratka_predmetu': row.skratka_predmetu,
            'predmet_id': row.predmet_id,
          })
        if row.w_finalna:
          add_infolist_warning('finalna')
        if row.w_finalna2:
          add_infolist_warning('finalna2')
        if row.w_semester:
          add_infolist_warning('semester')
        if row.w_stupen_studia:
          add_infolist_warning('stupen_studia')
        if row.w_zahodeny:
          add_infolist_warning('zahodeny')
      return sp
  
  def load_studprog_prilohy_subory(self, context, studprog_id):
    with self.cursor() as cur:
      cur.execute('''SELECT sp.typ_prilohy,
        s.id as subor_id, s.posledna_verzia,
        sv.id as subor_verzia_id, sv.nazov, sv.sha256, sv.modifikoval, sv.modifikovane,
        sv.predosla_verzia, sv.filename, sv.mimetype
        FROM studprog_priloha sp
        INNER JOIN subor s ON sp.subor = s.id
        INNER JOIN subor_verzia sv ON s.posledna_verzia = sv.id
        WHERE sp.studprog = %s
        ORDER BY typ_prilohy
        ''', (studprog_id,))
      subory = {}
      for row in cur:
        if row.typ_prilohy not in subory:
          subory[row.typ_prilohy] = []
        subory[row.typ_prilohy].append(PrilohaSubor(context=context, id=row.subor_id,
          posledna_verzia=row.posledna_verzia, nazov=row.nazov, filename=row.filename,
          sha256=row.sha256, modifikoval=row.modifikoval, modifikovane=row.modifikovane,
          predosla_verzia=row.predosla_verzia, studprog_id=studprog_id, mimetype=row.mimetype))
      return subory
  
  def add_subor(self, sha256, nazov_suboru, filename, mimetype, osoba_id, subor_id=None):
    with self.cursor() as cur:
      predosla_verzia = None
      if subor_id is not None:
        cur.execute('''SELECT posledna_verzia
          FROM subor
          WHERE id = %s
          FOR UPDATE''',
          (subor_id,))
        predosla_verzia = cur.fetchone()[0]
      
      cur.execute('''INSERT INTO subor_verzia (modifikoval, sha256, nazov, predosla_verzia, filename, mimetype)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        ''',
        (osoba_id, sha256, nazov_suboru, predosla_verzia, filename, mimetype))
      sv_id = cur.fetchone()[0]
      if subor_id is None:
        cur.execute('''INSERT INTO subor (posledna_verzia)
          VALUES (%s)
          RETURNING id
          ''',
          (sv_id,))
        subor_id = cur.fetchone()[0]
      else:
        cur.execute('''UPDATE subor SET posledna_verzia = %s WHERE id = %s''',
                    (sv_id, subor_id))
    return subor_id
  
  def add_studprog_priloha(self, studprog_id, typ_prilohy, subor_id):
    with self.cursor() as cur:
      cur.execute('''INSERT INTO studprog_priloha (studprog, typ_prilohy, subor)
        VALUES (%s, %s, %s)
        ''',
        (studprog_id, typ_prilohy, subor_id))
  
  def load_subor(self, subor_id):
    with self.cursor() as cur:
      cur.execute('''SELECT sv.id as subor_verzia, sv.predosla_verzia,
        sv.modifikovane, sv.modifikoval, sv.sha256, sv.nazov, sv.filename, sv.mimetype
        FROM subor s
        INNER JOIN subor_verzia sv ON s.posledna_verzia = sv.id
        WHERE s.id = %s
        ''',
        (subor_id,))
      return cur.fetchone()
  
  def load_typy_priloh(self, iba_moze_vybrat=False):
    with self.cursor() as cur:
      where = ''
      if iba_moze_vybrat:
        where = 'WHERE moze_vybrat'
      cur.execute('''SELECT id, nazov, kriterium
        FROM studprog_priloha_typ
        {}
        ORDER BY id
        '''.format(where))
      return cur.fetchall()

  def load_studprog_osoby_struktura(self, sp_id):
    with self.cursor() as cur:
      cur.execute('''
        SELECT o.id, o.cele_meno, ou.funkcia, ou.kvalifikacia, ou.uvazok
        FROM studprog sp, osoba o
        LEFT JOIN osoba_uvazok ou ON ou.osoba = o.id
        WHERE EXISTS (SELECT 1
            FROM infolist_verzia_vyucujuci ivv, infolist i, studprog_verzia_blok_infolist spvbi,
              studprog_verzia_blok spvb
            WHERE ivv.osoba = o.id AND ivv.infolist_verzia = i.posledna_verzia AND spvbi.infolist = i.id
            AND spvbi.studprog_verzia = sp.posledna_verzia AND spvb.studprog_verzia = sp.posledna_verzia
            AND spvbi.poradie_blok = spvb.poradie_blok AND spvb.typ IN ('A', 'B')
          )
        AND sp.id = %s
        ORDER BY o.priezvisko, o.meno, o.id
      ''',
      (sp_id,))
      result = []
      for row in cur:
        if len(result) == 0 or result[-1]['id'] != row.id:
          result.append({
            'id': row.id,
            'cele_meno': row.cele_meno,
            'kvalifikacia': row.kvalifikacia,
            'uvazky': []
          })
        if row.funkcia is not None or row.kvalifikacia is not None or row.uvazok is not None:
          result[-1]['uvazky'].append({
            'funkcia': row.funkcia,
            'uvazok': row.uvazok
          })
      return result

  def load_studprog_osoby_zoznam(self, sp_id):
    with self.cursor() as cur:
      cur.execute('''
        SELECT DISTINCT spvbi.predmet_jadra, i.id as infolist, ivp.nazov_predmetu COLLATE "sk_SK" as nazov_predmetu,
          o.id as osoba, o.priezvisko, o.meno, ou.funkcia, ou.kvalifikacia, ou.uvazok,
          ivvt.typ_vyucujuceho, spvb.typ, ivv.poradie
        FROM studprog sp
        INNER JOIN studprog_verzia_blok spvb ON sp.posledna_verzia = spvb.studprog_verzia
        INNER JOIN studprog_verzia_blok_infolist spvbi ON sp.posledna_verzia = spvbi.studprog_verzia AND spvb.poradie_blok = spvbi.poradie_blok
        INNER JOIN infolist i ON spvbi.infolist = i.id
        INNER JOIN infolist_verzia_vyucujuci ivv ON i.posledna_verzia = ivv.infolist_verzia
        INNER JOIN osoba o ON ivv.osoba = o.id
        INNER JOIN infolist_verzia_preklad ivp ON i.posledna_verzia = ivp.infolist_verzia
        LEFT JOIN osoba_uvazok ou ON ivv.osoba = ou.osoba
        LEFT JOIN infolist_verzia_vyucujuci_typ ivvt ON ivvt.infolist_verzia = ivv.infolist_verzia AND ivvt.osoba = ivv.osoba
        WHERE sp.id = %s AND spvb.typ in ('A', 'B') AND ivp.jazyk_prekladu = 'sk'
        ORDER BY spvb.typ, nazov_predmetu, i.id, ivv.poradie, ivvt.typ_vyucujuceho
      ''',
      (sp_id,))
      result = []
      for row in cur:
        if (len(result) == 0 or result[-1]['infolist'] != row.infolist or result[-1]['osoba'] != row.osoba or
            result[-1]['funkcia'] != row.funkcia or result[-1]['kvalifikacia'] != row.kvalifikacia or
            result[-1]['uvazok'] != row.uvazok):
          result.append({
            'predmet_jadra': row.predmet_jadra,
            'infolist': row.infolist,
            'nazov_predmetu': row.nazov_predmetu,
            'osoba': row.osoba,
            'priezvisko': row.priezvisko,
            'meno': row.meno,
            'funkcia': row.funkcia,
            'kvalifikacia': row.kvalifikacia,
            'uvazok': row.uvazok,
            'typy_vyucujuceho': []
          })
        if row.typ_vyucujuceho:
          result[-1]['typy_vyucujuceho'].append(row.typ_vyucujuceho)
      return result

  def load_studprog_infolisty(self, sp_id):
    with self.cursor() as cur:
      cur.execute('''
        SELECT DISTINCT spvbi.predmet_jadra, i.id as infolist, ivp.nazov_predmetu COLLATE "sk_SK" as nazov_predmetu,
          p.skratka
        FROM studprog sp
        INNER JOIN studprog_verzia_blok spvb ON sp.posledna_verzia = spvb.studprog_verzia
        INNER JOIN studprog_verzia_blok_infolist spvbi ON sp.posledna_verzia = spvbi.studprog_verzia AND spvb.poradie_blok = spvbi.poradie_blok
        INNER JOIN infolist i ON spvbi.infolist = i.id
        INNER JOIN infolist_verzia_preklad ivp ON i.posledna_verzia = ivp.infolist_verzia
        INNER JOIN predmet_infolist pi ON pi.infolist = i.id
        INNER JOIN predmet p ON p.id = pi.predmet
        WHERE sp.id = %s AND ivp.jazyk_prekladu = 'sk'
        ORDER BY nazov_predmetu, i.id
      ''',
      (sp_id,))
      return cur.fetchall()

  def load_studprog_vpchar(self, sp_id):
    with self.cursor() as cur:
      cur.execute('''
        SELECT DISTINCT o.id as osoba, o.priezvisko COLLATE "sk_SK", o.meno COLLATE "sk_SK", o.cele_meno, o.login,
          ou.funkcia IS NOT NULL as mame_funkciu, ovp.token
        FROM studprog sp
        INNER JOIN studprog_verzia_blok spvb ON sp.posledna_verzia = spvb.studprog_verzia
        INNER JOIN studprog_verzia_blok_infolist spvbi ON sp.posledna_verzia = spvbi.studprog_verzia AND spvb.poradie_blok = spvbi.poradie_blok
        INNER JOIN infolist i ON spvbi.infolist = i.id
        INNER JOIN infolist_verzia_vyucujuci ivv ON i.posledna_verzia = ivv.infolist_verzia
        INNER JOIN osoba o ON ivv.osoba = o.id
        INNER JOIN infolist_verzia_preklad ivp ON i.posledna_verzia = ivp.infolist_verzia
        LEFT JOIN osoba_uvazok ou ON ivv.osoba = ou.osoba
        LEFT JOIN osoba_vpchar ovp ON ivv.osoba = ovp.osoba
        WHERE sp.id = %s AND spvb.typ in ('A', 'B') AND ivp.jazyk_prekladu = 'sk'
          AND (ou.funkcia IS NULL or ou.funkcia IN ('1P', '1H', '2D'))
        ORDER BY o.priezvisko COLLATE "sk_SK", o.meno COLLATE "sk_SK", o.id
      ''',
      (sp_id,))
      return cur.fetchall()