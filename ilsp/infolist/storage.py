# -*- coding: utf-8 -*-
from ilsp.common.storage import kratke_meno, SQLBuilder, ConditionBuilder, dict_rec_update
from ilsp.utils import to_lang, from_lang
from werkzeug.exceptions import NotFound


class InfolistDataStoreMixin(object):
  def load_infolist(self, id, lang=None):
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

      cur.execute('''SELECT DISTINCT spv.garant as garant, o.cele_meno, o.priezvisko COLLATE "sk_SK", o.meno COLLATE "sk_SK"
        FROM studprog_verzia_blok_infolist spvbi
        INNER JOIN studprog sp ON sp.posledna_verzia = spvbi.studprog_verzia
        INNER JOIN studprog_verzia spv ON spv.id = spvbi.studprog_verzia
        INNER JOIN osoba o ON o.id = spv.garant
        WHERE spvbi.infolist = %s
        ORDER BY o.priezvisko COLLATE "sk_SK", o.meno COLLATE "sk_SK"
        ''', (id,))
      i['garanti'] = [x._asdict() for x in cur.fetchall()]

    i.update(self.load_infolist_verzia(posledna_verzia, lang))
    return i

  def load_infolist_verzia(self, id, lang=None):
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

  def _load_iv_trans(self, cur, id, lang=None):
    lang = self.resolve_lang(lang)
    trans = {}
    cur.execute('''SELECT nazov_predmetu, podm_absol_priebezne,
      podm_absol_skuska, podm_absol_nahrada, vysledky_vzdelavania,
      strucna_osnova, jazyk_prekladu
      FROM infolist_verzia_preklad
      WHERE infolist_verzia = %s AND jazyk_prekladu IN ({})'''.format(', '.join(['%s']*len(lang))),
      [id] + lang)
    done_lang = set()
    for data in cur:
      dict_rec_update(trans, to_lang({
        'nazov_predmetu': data.nazov_predmetu,
        'podm_absolvovania': {
          'skuska': data.podm_absol_skuska,
          'priebezne': data.podm_absol_priebezne,
          'nahrada': data.podm_absol_nahrada,
        },
        'vysledky_vzdelavania': data.vysledky_vzdelavania,
        'strucna_osnova': data.strucna_osnova,
      }, data.jazyk_prekladu))
      done_lang.add(data.jazyk_prekladu)
    for chybajuci_jazyk in (jazyk for jazyk in lang if jazyk not in done_lang):
      dict_rec_update(trans, to_lang({
        'nazov_predmetu': u'',
        'podm_absolvovania': {
          'skuska': None,
          'priebezne': None,
          'nahrada': None,
        },
        'vysledky_vzdelavania': None,
        'strucna_osnova': None,
      }, chybajuci_jazyk))
    return trans

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

  def save_infolist_verzia(self, predosla_verzia, data, lang=None, user=None,
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

  def _save_iv_trans(self, iv_id, all_data, lang=None):
    lang = self.resolve_lang(lang)
    with self.cursor() as cur:
      for l in lang:
        data = from_lang(all_data, l)
        podm = data['podm_absolvovania']
        cur.execute('''INSERT INTO infolist_verzia_preklad
          (infolist_verzia, jazyk_prekladu,
           nazov_predmetu, podm_absol_priebezne, podm_absol_skuska,
           podm_absol_nahrada, vysledky_vzdelavania, strucna_osnova)
         VALUES (''' + ', '.join(['%s']*8) + ''')''',
         (iv_id, l, data['nazov_predmetu'], podm['priebezne'], podm['skuska'],
          podm['nahrada'], data['vysledky_vzdelavania'], data['strucna_osnova']))

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

  def unlock_infolist(self, id, check_user=None):
    if check_user:
      def check(zamkol):
        return check_user.moze_odomknut_infolist({'zamkol': zamkol})
    else:
      check = None
    self._unlock('infolist', id, check)

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
