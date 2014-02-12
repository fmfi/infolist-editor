# -*- coding: utf-8 -*-
from werkzeug.exceptions import BadRequest, NotFound

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
        forknute_z, zamknute, povodny_kod_predmetu
        FROM infolist
        WHERE id = %s''',
        (id,))
      data = cur.fetchone()
      if data == None:
        raise NotFound('infolist({})'.format(id))
      posledna_verzia, import_z_aisu, forknute_z, zamknute, povodny_kod_predmetu = data
      i = {
        'posledna_verzia': posledna_verzia,
        'import_z_aisu': import_z_aisu,
        'forknute_z': forknute_z,
        'zamknute': zamknute,
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
      treba_zmenit_kod, predpokladany_semester, finalna_verzia
      FROM infolist_verzia WHERE id = %s''', (id,))
    row = cur.fetchone()
    if row == None:
      raise NotFound('infolist_verzia({})'.format(id))
    
    (pocet_kreditov, percenta_skuska,
    pct_a, pct_b, pct_c, pct_d, pct_e,
    hodn_a, hodn_b, hodn_c, hodn_d, hodn_e, hodn_fx,
    podmienujuce_predmety, odporucane_predmety, vylucujuce_predmety,
    modifikovane, predosla_verzia, fakulta, potrebny_jazyk,
    treba_zmenit_kod, predpokladany_semester, finalna_verzia) = row
    
    iv = {
      'id': id,
      'pocet_kreditov': pocet_kreditov,
      'podm_absolvovania': {
        'percenta_skuska': percenta_skuska,
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
      'finalna_verzia': finalna_verzia
    }
    return iv
  
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
      def select_for_update(id):
        cur.execute('''SELECT posledna_verzia, zamknute
          FROM infolist
          WHERE id = %s
          FOR UPDATE''',
          (id,))
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
      nova_verzia = self.save_infolist_verzia(row.posledna_verzia, data, user=user)
      cur.execute('''UPDATE infolist
        SET posledna_verzia = %s
        WHERE id = %s''',
        (nova_verzia, id))
  
  def save_infolist_verzia(self, predosla_verzia, data, lang='sk', user=None):
    nove_id = self._save_iv_data(predosla_verzia, data, user=user)
    self._save_iv_vyucujuci(nove_id, data['vyucujuci'])
    self._save_iv_cinnosti(nove_id, data['cinnosti'])
    self._save_iv_literatura(nove_id, data['odporucana_literatura'])
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
          modifikoval, finalna_verzia)
        VALUES (''' + ', '.join(['%s'] * 23) + ''')
        RETURNING id''',
        (data['pocet_kreditov'], data['podm_absolvovania']['percenta_skuska'],
        pct['A'], pct['B'], pct['C'], pct['D'], pct['E'],
        hodn['A'], hodn['B'], hodn['C'], hodn['D'], hodn['E'], hodn['Fx'],
        data['podmienujuce_predmety'], data['odporucane_predmety'],
        data['vylucujuce_predmety'], data['predosla_verzia'],
        data['fakulta'], data['potrebny_jazyk'], data['treba_zmenit_kod'],
        data['predpokladany_semester'], user, data['finalna_verzia']))
      return cur.fetchone()[0]
  
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
        OR unaccent(vyd_udaje) ILIKE unaccent(%s))""")
      params.append('%' + part + '%') # TODO escape
      params.append('%' + part + '%')
    
    select = '''SELECT bib_id, dokument, vyd_udaje FROM literatura
      WHERE dostupne AND {} ORDER by dokument'''.format(' AND '.join(conds))
    
    with self.cursor() as cur:
      cur.execute(select, params)
      return cur.fetchall()

  def load_literatura(self, id):
    with self.cursor() as cur:
      cur.execute('SELECT bib_id, dokument, vyd_udaje FROM literatura WHERE bib_id = %s',
        (id,))
      return cur.fetchone()
  
  def search_nova_literatura(self, query):
    with self.cursor() as cur:
      cur.execute('SELECT DISTINCT popis FROM infolist_verzia_nova_literatura WHERE popis LIKE %s ORDER by popis',
        (u'%{}%'.format(query),))
      return [x[0] for x in cur.fetchall()]
  
  def load_predmet(self, id):
    with self.cursor() as cur:
      cur.execute('SELECT id, kod_predmetu, skratka FROM predmet WHERE id = %s',
        (id,))
      return cur.fetchone()
  
  def search_predmet(self, query):
    with self.cursor() as cur:
      cur.execute('SELECT id, kod_predmetu, skratka FROM predmet WHERE kod_predmetu LIKE %s',
        (u'%{}%'.format(query),))
      return cur.fetchall()
  
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
      return cur.fetchone()[0]
  
  def load_user(self, username):
    with self.cursor() as cur:
      cur.execute('SELECT id, login, meno, priezvisko, cele_meno FROM osoba WHERE login = %s', (username,))
      row = cur.fetchone()
      if row == None:
        return None
      return User(row.id, row.login, row.meno, row.priezvisko, row.cele_meno)