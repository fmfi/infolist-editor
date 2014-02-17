# -*- coding: utf-8 -*-
from werkzeug.exceptions import BadRequest, NotFound
from utils import Podmienka

def dict_rec_update(d1, d2):
  for key in d2:
    if isinstance(d2[key], dict):
      d1[key] = dict_rec_update(d1.get(key, {}), d2[key])
    else:
      d1[key] = d2[key]
  return d1

class User(object):
  def __init__(self, id, login, meno, priezvisko, cele_meno):
    self.id = id
    self.login = login
    self.meno = meno
    self.priezvisko = priezvisko
    self.cele_meno = cele_meno
    self.opravnenia = {}

class DataStore(object):
  def __init__(self, conn):
    self.conn = conn
    self._typy_vyucujuceho = None
    self._druhy_cinnosti = None
    self._fakulty = None
    self._jazyky_vyucby = None
  
  def cursor(self):
    return self.conn.cursor()
  
  def commit(self):
    return self.conn.commit()
  
  def rollback(self):
    return self.conn.rollback()
  
  def load_infolist(self, id, lang='sk'):
    with self.cursor() as cur:
      cur.execute('''SELECT posledna_verzia, import_z_aisu,
        forknute_z, zamknute, zamkol, povodny_kod_predmetu
        FROM infolist
        WHERE id = %s''',
        (id,))
      data = cur.fetchone()
      if data == None:
        raise NotFound('infolist({})'.format(id))
      posledna_verzia, import_z_aisu, forknute_z, zamknute, zamkol, povodny_kod_predmetu = data
      i = {
        'posledna_verzia': posledna_verzia,
        'import_z_aisu': import_z_aisu,
        'forknute_z': forknute_z,
        'zamknute': zamknute,
        'zamkol': zamkol,
        'povodny_kod_predmetu': povodny_kod_predmetu
      }
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
      'podmienujuce_predmety': podmienujuce_predmety,
      'odporucane_predmety': odporucane_predmety,
      'vylucujuce_predmety': vylucujuce_predmety,
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
      o.cele_meno, ivvt.typ_vyucujuceho
      FROM osoba o, infolist_verzia_vyucujuci ivv
      LEFT JOIN infolist_verzia_vyucujuci_typ ivvt
      ON ivv.infolist_verzia = ivvt.infolist_verzia AND ivv.osoba = ivvt.osoba
      WHERE ivv.osoba = o.id AND ivv.infolist_verzia = %s
      ORDER BY ivv.poradie''',
      (id,))
    ivv = []
    vyucujuci = None
    for osoba, cele_meno, typ_vyucujuceho in cur:
      if vyucujuci == None or vyucujuci['osoba'] != osoba:
        vyucujuci = {'osoba': osoba,
                     'cele_meno': cele_meno,
                     'typy': set()}
        ivv.append(vyucujuci)
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
  
  def save_infolist(self, id, data, user=None):
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
        if row.zamknute:
          id = self.fork_infolist(id)
          select_for_update(id)
          row = cur.fetchone()
          if row == None:
            raise NotFound('infolist({})'.format(id))
          if row.zamknute:
            raise ValueError('Zamknuty novo vytvoreny infolist')
        posledna_verzia = row.posledna_verzia
      nova_verzia = self.save_infolist_verzia(posledna_verzia, data, user=user)
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
  
  def save_infolist_verzia(self, predosla_verzia, data, lang='sk', user=None):
    nove_id = self._save_iv_data(predosla_verzia, data, user=user)
    self._save_iv_suvisiace_predmety(nove_id, data)
    self._save_iv_vyucujuci(nove_id, data['vyucujuci'])
    self._save_iv_cinnosti(nove_id, data['cinnosti'])
    self._save_iv_literatura(nove_id, data['odporucana_literatura'])
    self._save_iv_modifikovali(nove_id, data['modifikovali'])
    self._save_iv_trans(nove_id, data, lang=lang)
    return nove_id
    
  def _save_iv_data(self, predosla_verzia, data, user=None):
    pct = data['podm_absolvovania']['percenta_na']
    hodn = data['hodnotenia_pocet']
    with self.cursor() as cur:
      cur.execute('''INSERT INTO infolist_verzia (
          pocet_kreditov,
          podm_absol_percenta_skuska, podm_absol_percenta_na_a,
          podm_absol_percenta_na_b, podm_absol_percenta_na_c,
          podm_absol_percenta_na_d, podm_absol_percenta_na_e,
          hodnotenia_a_pocet, hodnotenia_b_pocet, hodnotenia_c_pocet,
          hodnotenia_d_pocet, hodnotenia_e_pocet, hodnotenia_fx_pocet,
          podmienujuce_predmety, odporucane_predmety, vylucujuce_predmety,
          predosla_verzia, fakulta, potrebny_jazyk,
          treba_zmenit_kod, predpokladany_semester,
          modifikoval, finalna_verzia, bude_v_povinnom,
          predpokladany_stupen_studia, nepouzivat_stupnicu,
          obsahuje_varovania)
        VALUES (''' + ', '.join(['%s'] * 27) + ''')
        RETURNING id''',
        (data['pocet_kreditov'], data['podm_absolvovania']['percenta_skuska'],
        pct['A'], pct['B'], pct['C'], pct['D'], pct['E'],
        hodn['A'], hodn['B'], hodn['C'], hodn['D'], hodn['E'], hodn['Fx'],
        data['podmienujuce_predmety'], data['odporucane_predmety'],
        data['vylucujuce_predmety'], data['predosla_verzia'],
        data['fakulta'], data['potrebny_jazyk'], data['treba_zmenit_kod'],
        data['predpokladany_semester'], None if user is None else user.id,
        data['finalna_verzia'], data['bude_v_povinnom'],
        data['predpokladany_stupen_studia'],
        data['podm_absolvovania']['nepouzivat_stupnicu'],
        data['obsahuje_varovania']))
      return cur.fetchone()[0]
  
  def _save_iv_suvisiace_predmety(self, iv_id, data):
    suvisiace_predmety = set()
    suvisiace_predmety.update(Podmienka(data['podmienujuce_predmety']).idset())
    suvisiace_predmety.update(Podmienka(data['odporucane_predmety']).idset())
    suvisiace_predmety.update(Podmienka(data['vylucujuce_predmety']).idset())
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
    if len(query) < 2:
      raise NotFound()
    
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
    if len(query) < 2:
      raise NotFound()
    
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
      sql = '''SELECT DISTINCT p.id, p.kod_predmetu, p.skratka, ivp.nazov_predmetu
          FROM predmet p
          LEFT JOIN predmet_infolist pi ON p.id = pi.predmet
          LEFT JOIN infolist i ON pi.infolist = i.id
          INNER JOIN infolist_verzia iv ON i.posledna_verzia = iv.id
          INNER JOIN infolist_verzia_preklad ivp ON iv.id = ivp.infolist_verzia
          WHERE ivp.jazyk_prekladu = 'sk' {}
          ORDER BY p.skratka, p.id, ivp.nazov_predmetu'''.format(where_cond)
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
        if row.nazov_predmetu:
          predmety[-1]['nazvy_predmetu'].append(row.nazov_predmetu)
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

  def fetch_predmety(self, where=None):
    if where != None:
      where_cond = ' AND ' + where[0]
      where_params = where[1]
    else:
      where_cond = ''
      where_params = []
    
    with self.cursor() as cur:
      sql = '''SELECT p.id as predmet_id, p.kod_predmetu, p.skratka,
          i.id as infolist_id, i.zamknute, i.zamkol, i.import_z_aisu, i.vytvoril,
          oz.cele_meno as zamkol_cele_meno,
          ov.cele_meno as vytvoril_cele_meno,
          iv.modifikovane, iv.finalna_verzia, iv.obsahuje_varovania,
          ivp.nazov_predmetu,
          o.id as osoba_id, o.cele_meno
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
          ORDER BY p.skratka, p.id, i.id, iv.id, o.cele_meno'''.format(where_cond)
      cur.execute(sql, where_params)
      predmety = []
      for row in cur:
        if len(predmety) == 0 or predmety[-1]['id'] != row.predmet_id:
          predmety.append({
            'id': row.predmet_id,
            'kod_predmetu': row.kod_predmetu,
            'skratka': row.skratka,
            'infolisty': []
          })
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
  
  def fetch_moje_predmety(self, osoba_id, upravy=True, uci=True, vytvoril=False):
    if not upravy and not uci:
      raise ValueError('Podla niecoho musime selectovat')
    
    il_params = []
    il_conds = []
    
    if upravy:
      il_conds.append(
        '''
          ri.vytvoril = %s
          OR EXISTS (
            SELECT id
            FROM infolist_verzia_modifikovali rivm
            WHERE rivm.infolist_verzia = ri.posledna_verzia
              AND rivm.osoba = %s
          )
        ''')
      il_params.append(osoba_id)
      il_params.append(osoba_id)
      vytvoril = True
    
    if uci:
      il_conds.append(
        '''
          EXISTS (
            SELECT id
            FROM infolist_verzia_vyucujuci rivv
            WHERE rivv.infolist_verzia = ri.posledna_verzia
              AND rivv.osoba = %s
          )
        ''')
      il_params.append(osoba_id)
    
    params = []
    conds = []
    
    if il_conds:
      conds.append(
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
        '''.format(' OR ' .join(il_conds))
      )
      params.extend(il_params)
    
    if vytvoril:
      conds.append('p.vytvoril = %s')
      params.append(osoba_id)
    
    return self.fetch_predmety(where=(
      ' OR '.join(conds),
      params
    ))
  
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
    with self.cursor() as cur:
      cur.execute('''SELECT o.id, o.login, o.meno, o.priezvisko, o.cele_meno, op.organizacna_jednotka, op.je_admin
        FROM osoba o
        INNER JOIN ilsp_opravnenia op ON o.id = op.osoba
        WHERE o.login = %s'''
        , (username,))
      user = None
      for row in cur:
        if user == None:
          user = User(row.id, row.login, row.meno, row.priezvisko, row.cele_meno)
        elif user.id != row.id:
            raise ValueError('SELECT vratil viacerych pouzivatelov... WTF')
        user.opravnenia[row.organizacna_jednotka] = {
          'admin': row.je_admin
        }
      return user
  
  def lock_infolist(self, id, user):
    with self.cursor() as cur:
      cur.execute('SELECT zamknute, zamkol FROM infolist WHERE id = %s FOR UPDATE', (id,))
      row = cur.fetchone()
      if row == None:
        raise NotFound('infolist({})'.format(id))
      if row.zamknute:
        raise ValueError('Infolist je uz zamknuty')
      cur.execute('UPDATE infolist SET zamknute = now(), zamkol = %s WHERE id = %s', (user, id))
  
  def unlock_infolist(self, id):
    with self.cursor() as cur:
      cur.execute('SELECT zamknute, zamkol FROM infolist WHERE id = %s FOR UPDATE', (id,))
      row = cur.fetchone()
      if row == None:
        raise NotFound('infolist({})'.format(id))
      if not row.zamknute:
        raise ValueError('Infolist je uz odomknuty')
      cur.execute('UPDATE infolist SET zamknute = NULL, zamkol = NULL WHERE id = %s', (id,))
  
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