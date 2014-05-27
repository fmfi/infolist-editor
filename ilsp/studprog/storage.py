# -*- coding: utf-8 -*-
from ilsp import utils
from ilsp.common.podmienka import Podmienka
from ilsp.common.storage import ConditionBuilder
from ilsp.export import PrilohaFormularSP, PrilohaSubor
from werkzeug.exceptions import NotFound


class StudprogDataStoreMixin(object):
  def lock_studprog(self, id, user):
    self._lock('studprog', id, user)

  def unlock_studprog(self, id, check_user=None):
    if check_user:
      def check(zamkol):
        return check_user.moze_odomknut_studprog({'zamkol': zamkol})
    else:
      check = None
    self._unlock('studprog', id, check)

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
          iv.obsahuje_varovania,
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
            'obsahuje_varovania': row.obsahuje_varovania
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

  def load_typy_bloku(self):
    return self._typy_bloku

  def find_sp_warnings(self, limit_sp=None):
    with self.cursor() as cur:
      sql = '''SELECT sq.* FROM (SELECT sp.id, sp.skratka,
          spvp.nazov,
          i.id as infolist_id,
          p.id as predmet_id, p.skratka as skratka_predmetu,
          ivp.nazov_predmetu,
          iv.podmienujuce_predmety,
          spvbi.rocnik,
          spvbi.semester,
          CASE spvbi.semester WHEN 'Z' THEN 0 WHEN 'L' THEN 1 ELSE 2 END as semester_poradie,
          spvb.typ as typ_bloku,
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
          (i.zahodeny) as w_zahodeny,
          (spvb.typ IN ('A', 'B') AND NOT iv.bude_v_povinnom) as w_pov,
          (iv.obsahuje_varovania) as w_varovania,
          (unaccent(ivp.vysledky_vzdelavania) ILIKE '%%tento obsah bol automaticky importovany%%') as w_automaticky,
          (SELECT COUNT(*)
            FROM infolist_verzia_nova_literatura ivnl
            WHERE ivnl.infolist_verzia = iv.id AND NOT (
              unaccent(popis) ilike '%%vyucujuc%%' or unaccent(popis) ilike 'vlastn%%'
              or popis like '%%fmph.uniba.sk%%' or unaccent(popis) ilike '%%vyber aktualnych%%'
              or popis like '%%www.%%' or unaccent(popis) ilike '%%clanky%%'
              or popis ilike '%%online%%' or unaccent(popis) ilike '%%literatura%%'
              or unaccent(popis) ilike '%%elektronicke%%' or popis like '%%.com'
              )
          ) as w_nova_literatura
        FROM studprog sp
        LEFT JOIN studprog sp2 ON sp2.id = sp.spolocne_bloky
        INNER JOIN studprog_verzia spv ON sp.posledna_verzia = spv.id OR sp2.posledna_verzia = spv.id
        INNER JOIN studprog_verzia_blok spvb ON spv.id = spvb.studprog_verzia
        INNER JOIN studprog_verzia_blok_infolist spvbi ON spv.id = spvbi.studprog_verzia AND spvb.poradie_blok = spvbi.poradie_blok
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
        ORDER BY id, rocnik NULLS LAST, semester_poradie, infolist_id
      '''
      if limit_sp is not None:
        sql = sql.format(' AND sp.id = %s')
        params = [limit_sp]
      else:
        sql = sql.format('')
        params = []
      cur.execute(sql, params)
      sp = []
      splnene_predmety = {'A': utils.LevelSet(), 'B': utils.LevelSet(), 'C': utils.LevelSet()}
      for row in cur:
        if len(sp) == 0 or row.id != sp[-1]['id']:
          if len(sp) > 0 and len(sp[-1]['messages']) == 0:
            sp.pop()
          sp.append({
            'id': row.id,
            'skratka': row.skratka,
            'nazov': row.nazov,
            'messages': []
          })
          splnene_predmety = {'A': utils.LevelSet(), 'B': utils.LevelSet(), 'C': utils.LevelSet()}
        def add_infolist_warning(typ, **kwargs):
          d = {
            'typ': typ,
            'infolist': row.infolist_id,
            'nazov_predmetu': row.nazov_predmetu,
            'skratka_predmetu': row.skratka_predmetu,
            'predmet_id': row.predmet_id,
          }
          d.update(kwargs)
          sp[-1]['messages'].append(d)
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
        if row.w_pov:
          add_infolist_warning('pov')
        if row.w_varovania:
          add_infolist_warning('varovania')
        if row.w_automaticky:
          add_infolist_warning('automaticky')
        if row.w_nova_literatura > 2:
          add_infolist_warning('nova_literatura', pocet=row.w_nova_literatura)

        for ityp in ['A', 'B', 'C']:
          if row.typ_bloku <= ityp:
            splnene_predmety[ityp].add((row.rocnik, row.semester), row.predmet_id)
        podm = Podmienka(row.podmienujuce_predmety)
        print row.skratka_predmetu, podm, splnene_predmety[row.typ_bloku].current_set(), podm.vyhodnot(splnene_predmety)
        if not podm.vyhodnot(splnene_predmety[row.typ_bloku]):
          add_infolist_warning('nesplnitelne', podmienky=podm, splnene=splnene_predmety[row.typ_bloku].current_set())
      return sp

  def load_studprog_formulare_id(self, studprog_id):
    with self.cursor() as cur:
      cur.execute('''
        SELECT formular, formular_konverzny
        FROM studprog
        WHERE id = %s
      ''', (studprog_id,))
      return cur.fetchone()

  def save_studprog_formular_id(self, studprog_id, subor_id, konverzny=False):
    if konverzny:
      column = 'formular_konverzny'
    else:
      column = 'formular'
    with self.cursor() as cur:
      cur.execute('''
        UPDATE studprog SET {} = %s WHERE id = %s
      '''.format(column), (subor_id, studprog_id))

  def load_studprog_formulare(self, context, studprog_id):
    with self.cursor() as cur:
      formular, formular_konverzny = self.load_studprog_formulare_id(studprog_id)
      def nacitaj_subor(subor_id, konverzny):
        cur.execute('''
          SELECT s.id as subor_id, s.posledna_verzia,
            sv.id as subor_verzia_id, sv.nazov, sv.sha256, sv.modifikoval, sv.modifikovane,
            sv.predosla_verzia, sv.filename, sv.mimetype
          FROM subor s
          INNER JOIN subor_verzia sv ON sv.id = s.posledna_verzia
          WHERE s.id = %s
        ''', (subor_id,))
        row = cur.fetchone()
        priloha = PrilohaFormularSP(context=context, id=row.subor_id,
          posledna_verzia=row.posledna_verzia, nazov=row.nazov, filename=row.filename,
          sha256=row.sha256, modifikoval=row.modifikoval, modifikovane=row.modifikovane,
          predosla_verzia=row.predosla_verzia, studprog_id=studprog_id, mimetype=row.mimetype,
          konverzny=konverzny)
        return priloha
      if formular is not None:
        formular = nacitaj_subor(formular, False)
      if formular_konverzny is not None:
        formular_konverzny = nacitaj_subor(formular_konverzny, True)
      return formular, formular_konverzny

  def load_studprog_spolocne_bloky(self, studprog_id, konverzny):
    if konverzny:
      col = 'spolocne_bloky_konverzny'
    else:
      col = 'spolocne_bloky'

    with self.cursor() as cur:
      cur.execute('SELECT {} FROM studprog WHERE id = %s'.format(col), (studprog_id,))
      row = cur.fetchone()
      if row is None:
        return None
      return row[0]

  def resolve_spolocne_bloky(self, sp_id, val):
    if isinstance(val, int):
      return val
    return self.load_studprog_spolocne_bloky(sp_id, val == 'konverzny')

  def cond_spolocne_bloky(self, sp_id, column, val):
    spolocne = self.resolve_spolocne_bloky(sp_id, val)
    sp_filter = ConditionBuilder('OR')
    sp_filter.append('{} = %s'.format(column), sp_id)
    if spolocne is not None:
      sp_filter.append('{} = %s'.format(column), spolocne)
    return sp_filter

  def load_studprog_prilohy_subory(self, context, studprog_id, spolocne='normalny'):
    sp_filter = self.cond_spolocne_bloky(studprog_id, 'sp.studprog', spolocne)
    with self.cursor() as cur:
      cur.execute('''SELECT sp.typ_prilohy,
        s.id as subor_id, s.posledna_verzia,
        sv.id as subor_verzia_id, sv.nazov, sv.sha256, sv.modifikoval, sv.modifikovane,
        sv.predosla_verzia, sv.filename, sv.mimetype
        FROM studprog_priloha sp
        INNER JOIN subor s ON sp.subor = s.id
        INNER JOIN subor_verzia sv ON s.posledna_verzia = sv.id
        WHERE {}
        ORDER BY typ_prilohy
        '''.format(sp_filter), sp_filter.params)
      subory = {}
      for row in cur:
        if row.typ_prilohy not in subory:
          subory[row.typ_prilohy] = []
        priloha = PrilohaSubor(context=context, id=row.subor_id,
          posledna_verzia=row.posledna_verzia, nazov=row.nazov, filename=row.filename,
          sha256=row.sha256, modifikoval=row.modifikoval, modifikovane=row.modifikovane,
          predosla_verzia=row.predosla_verzia, studprog_id=studprog_id, mimetype=row.mimetype,
          typ_prilohy=row.typ_prilohy)

        subory[row.typ_prilohy].append(priloha)
      return subory

  def add_studprog_priloha(self, studprog_id, typ_prilohy, subor_id):
    with self.cursor() as cur:
      cur.execute('''INSERT INTO studprog_priloha (studprog, typ_prilohy, subor)
        VALUES (%s, %s, %s)
        ''',
        (studprog_id, typ_prilohy, subor_id))

  def load_studprog_infolisty(self, sp_id, spolocne='normalny'):
    sp_filter = self.cond_spolocne_bloky(sp_id, 'sp.id', spolocne)
    with self.cursor() as cur:
      cur.execute('''
        SELECT DISTINCT spvbi.predmet_jadra, i.id as infolist, ivp.nazov_predmetu COLLATE "sk_SK" as nazov_predmetu,
          p.skratka, iv.modifikovane
        FROM studprog sp
        INNER JOIN studprog_verzia_blok spvb ON sp.posledna_verzia = spvb.studprog_verzia
        INNER JOIN studprog_verzia_blok_infolist spvbi ON sp.posledna_verzia = spvbi.studprog_verzia AND spvb.poradie_blok = spvbi.poradie_blok
        INNER JOIN infolist i ON spvbi.infolist = i.id
        INNER JOIN infolist_verzia iv ON i.posledna_verzia = iv.id
        INNER JOIN infolist_verzia_preklad ivp ON i.posledna_verzia = ivp.infolist_verzia
        INNER JOIN predmet_infolist pi ON pi.infolist = i.id
        INNER JOIN predmet p ON p.id = pi.predmet
        WHERE ({}) AND ivp.jazyk_prekladu = 'sk'
        ORDER BY nazov_predmetu, i.id
      '''.format(sp_filter),
      sp_filter.params)
      return cur.fetchall()

  def load_studprog_vpchar(self, sp_id, spolocne='normalny'):
    sp_filter = self.cond_spolocne_bloky(sp_id, 'sp.id', spolocne)
    with self.cursor() as cur:
      cur.execute('''
        SELECT DISTINCT o.id as osoba, o.priezvisko COLLATE "sk_SK", o.meno COLLATE "sk_SK", o.cele_meno, o.login,
          ou.funkcia IS NOT NULL as mame_funkciu, ovp.token, ovp.uploadnuty_subor
        FROM studprog sp
        INNER JOIN studprog_verzia_blok spvb ON sp.posledna_verzia = spvb.studprog_verzia
        INNER JOIN studprog_verzia_blok_infolist spvbi ON sp.posledna_verzia = spvbi.studprog_verzia AND spvb.poradie_blok = spvbi.poradie_blok
        INNER JOIN infolist i ON spvbi.infolist = i.id
        INNER JOIN infolist_verzia_vyucujuci ivv ON i.posledna_verzia = ivv.infolist_verzia
        INNER JOIN osoba o ON ivv.osoba = o.id
        INNER JOIN infolist_verzia_preklad ivp ON i.posledna_verzia = ivp.infolist_verzia
        LEFT JOIN osoba_uvazok ou ON ivv.osoba = ou.osoba
        LEFT JOIN osoba_vpchar ovp ON ivv.osoba = ovp.osoba
        WHERE ({}) AND spvb.typ in ('A', 'B') AND ivp.jazyk_prekladu = 'sk'
          AND (ou.funkcia IS NULL or ou.funkcia IN ('1P', '1H', '2D') or o.cele_meno ilike %s or o.cele_meno ilike %s or o.cele_meno ilike %s or o.cele_meno ilike %s)
        ORDER BY o.priezvisko COLLATE "sk_SK", o.meno COLLATE "sk_SK", o.id
      '''.format(sp_filter),
      sp_filter.params + ['%prof.%', '%doc.%', 'prof %', 'doc %'])
      return cur.fetchall()

  def load_studprog_skolitelia(self, sp_id):
    with self.cursor() as cur:
      cur.execute('''
        SELECT DISTINCT o.id as osoba, o.priezvisko COLLATE "sk_SK", o.meno COLLATE "sk_SK", o.cele_meno,
          EXISTS (SELECT 1 FROM studprog_skolitel sps WHERE sps.osoba = o.id AND studprog = %s) as je_skolitel
        FROM osoba o
        WHERE EXISTS (SELECT 1 FROM studprog_skolitel sps WHERE sps.osoba = o.id AND studprog = %s)
        OR EXISTS(
          SELECT 1
          FROM studprog sp
          INNER JOIN studprog_verzia_blok spvb ON sp.posledna_verzia = spvb.studprog_verzia
          INNER JOIN studprog_verzia_blok_infolist spvbi ON sp.posledna_verzia = spvbi.studprog_verzia AND spvb.poradie_blok = spvbi.poradie_blok
          INNER JOIN infolist i ON spvbi.infolist = i.id
          INNER JOIN infolist_verzia_vyucujuci ivv ON i.posledna_verzia = ivv.infolist_verzia
          WHERE sp.id = %s AND ivv.osoba = o.id
        )
        ORDER BY o.priezvisko COLLATE "sk_SK", o.meno COLLATE "sk_SK", o.id
      ''', (sp_id, sp_id, sp_id))
      return cur.fetchall()

  def save_studprog_skolitelia(self, sp_id, skolitelia):
    with self.cursor() as cur:
      cur.execute('DELETE FROM studprog_skolitel WHERE studprog = %s', (sp_id,))
      for skolitel in skolitelia:
        cur.execute('INSERT INTO studprog_skolitel(studprog, osoba) VALUES (%s, %s)', (sp_id, skolitel))

  def load_studprog_skolitelia_vpchar(self, sp_id):
    with self.cursor() as cur:
      cur.execute('''
        SELECT DISTINCT o.id as osoba, o.priezvisko COLLATE "sk_SK", o.meno COLLATE "sk_SK", o.cele_meno, o.login,
          ovp.token, ovp.uploadnuty_subor
        FROM studprog sp
        INNER JOIN studprog_skolitel sps ON sps.studprog = sp.id
        INNER JOIN osoba o ON sps.osoba = o.id
        LEFT JOIN osoba_vpchar ovp ON o.id = ovp.osoba
        WHERE sp.id = %s
        ORDER BY o.priezvisko COLLATE "sk_SK", o.meno COLLATE "sk_SK", o.id
      ''',
      (sp_id,))
      return cur.fetchall()