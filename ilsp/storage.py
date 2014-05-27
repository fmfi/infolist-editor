# -*- coding: utf-8 -*-
from flask import current_app
from ilsp.common.podmienka import Podmienka
from ilsp.common.storage import User
from ilsp.infolist.storage import InfolistDataStoreMixin
from ilsp.predmet.storage import PredmetDataStoreMixin
from ilsp.studprog.storage import StudprogDataStoreMixin
from ilsp.utils import to_list
from werkzeug.exceptions import NotFound


class DataStore(InfolistDataStoreMixin, PredmetDataStoreMixin, StudprogDataStoreMixin):
  def __init__(self, conn, podmienka_class=Podmienka):
    self.conn = conn
    self._typy_vyucujuceho = None
    self._druhy_cinnosti = None
    self._fakulty = None
    self._jazyky_vyucby = None
    self._typy_bloku = [('A', u'A: povinné predmety'), ('B', u'B: povinne voliteľné predmety'), ('C', u'C: výberové predmety')]
    self._podmienka_class = podmienka_class
    self._typy_priloh = None

  def cursor(self):
    return self.conn.cursor()

  def commit(self):
    return self.conn.commit()

  def rollback(self):
    return self.conn.rollback()

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

  def load_jazyky_vyucby(self):
    if self._jazyky_vyucby == None:
      with self.cursor() as cur:
        cur.execute('SELECT kod, popis FROM jazyk_vyucby')
        self._jazyky_vyucby = cur.fetchall()
    return self._jazyky_vyucby

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

  def _lock(self, table, id, user):
    with self.cursor() as cur:
      cur.execute('SELECT zamknute, zamkol FROM {} WHERE id = %s FOR UPDATE'.format(table), (id,))
      row = cur.fetchone()
      if row == None:
        raise NotFound('{}({})'.format(table, id))
      if row.zamknute:
        raise ValueError('{} {} je uz zamknuty'.format(table, id))
      cur.execute('UPDATE {} SET zamknute = now(), zamkol = %s WHERE id = %s'.format(table), (user, id))


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

  def load_subor(self, subor_id):
    with self.cursor() as cur:
      cur.execute('''SELECT sv.id as subor_verzia, s.posledna_verzia, sv.predosla_verzia,
        sv.modifikovane, sv.modifikoval, sv.sha256, sv.nazov, sv.filename, sv.mimetype
        FROM subor s
        INNER JOIN subor_verzia sv ON s.posledna_verzia = sv.id
        WHERE s.id = %s
        ''',
        (subor_id,))
      return cur.fetchone()

  def load_typy_priloh(self, iba_moze_vybrat=False):
    if self._typy_priloh is None:
      with self.cursor() as cur:
        cur.execute('''SELECT id, nazov, kriterium, moze_vybrat
          FROM studprog_priloha_typ
          ORDER BY id
          ''')
        self._typy_priloh = cur.fetchall()
    if iba_moze_vybrat:
      return [x for x in self._typy_priloh if x.moze_vybrat]
    return self._typy_priloh

  def load_studprog_osoby_struktura(self, sp_id, spolocne='normalny'):
    sp_filter = self.cond_spolocne_bloky(sp_id, 'sp.id', spolocne)
    with self.cursor() as cur:
      cur.execute('''
        SELECT o.id, o.cele_meno, ou.funkcia, ou.kvalifikacia, ou.uvazok
        FROM osoba o
        LEFT JOIN osoba_uvazok ou ON ou.osoba = o.id
        WHERE EXISTS (SELECT 1
            FROM infolist_verzia_vyucujuci ivv, infolist i, studprog_verzia_blok_infolist spvbi,
              studprog_verzia_blok spvb, studprog sp
            WHERE ivv.osoba = o.id AND ivv.infolist_verzia = i.posledna_verzia AND spvbi.infolist = i.id
            AND spvbi.studprog_verzia = sp.posledna_verzia AND spvb.studprog_verzia = sp.posledna_verzia
            AND spvbi.poradie_blok = spvb.poradie_blok AND spvb.typ IN ('A', 'B')
            AND ({})
          )
        ORDER BY o.priezvisko, o.meno, o.id
      '''.format(sp_filter),
      sp_filter.params)
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

  def load_studprog_osoby_zoznam(self, sp_id, spolocne='normalny'):
    sp_filter = self.cond_spolocne_bloky(sp_id, 'sp.id', spolocne)
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
        WHERE ({}) AND spvb.typ in ('A', 'B') AND ivp.jazyk_prekladu = 'sk'
        ORDER BY spvb.typ, nazov_predmetu, i.id, ivv.poradie, ivvt.typ_vyucujuceho
      '''.format(sp_filter),
      sp_filter.params)
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

  def zmaz_dokument(self, sp_id, typ_prilohy, subor_id):
    with self.cursor() as cur:
      cur.execute('''
        DELETE FROM studprog_priloha
        WHERE studprog=%s AND typ_prilohy = %s AND subor = %s''',
        (sp_id, typ_prilohy, subor_id))
      return cur.rowcount > 0

  def osoba_load_vpchar_subor_id(self, osoba_id):
    with self.cursor() as cur:
      cur.execute('''
       SELECT uploadnuty_subor FROM osoba_vpchar WHERE osoba = %s
      ''', (osoba_id,))
      row = cur.fetchone()
      if row is None:
        return None
      return row.uploadnuty_subor

  def osoba_save_vpchar_subor_id(self, osoba_id, subor_id):
    with self.cursor() as cur:
      cur.execute('SELECT 1 FROM osoba_vpchar WHERE osoba = %s', (osoba_id,))
      row = cur.fetchone()
      if row is None:
        cur.execute('INSERT INTO osoba_vpchar (osoba, uploadnuty_subor) VALUES (%s, %s)',
          (osoba_id, subor_id))
      else:
        cur.execute('UPDATE osoba_vpchar SET uploadnuty_subor = %s WHERE osoba = %s',
          (subor_id, osoba_id))


  def resolve_lang(self, lang):
    if lang is None:
      return current_app.config['LANGUAGES']
    else:
      return to_list(lang)