# -*- coding: utf-8 -*-
from ilsp.common.storage import ConditionBuilder


class PredmetDataStoreMixin(object):
  def load_predmet(self, id):
    predmety = self.fetch_predmety(where=('p.id = %s', (id,)))
    if len(predmety) == 0:
      return None
    return predmety[0]

  def _fetch_predmety_simple(self, where=None, lang='sk'):
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
          WHERE (ivp.jazyk_prekladu = %s OR ivp.jazyk_prekladu IS NULL) {}
          ORDER BY p.skratka, p.id, iv.finalna_verzia desc, ivp.nazov_predmetu'''.format(where_cond)
      cur.execute(sql, [lang] + list(where_params))
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

  def load_predmet_simple(self, id, lang='sk'):
    predmety =  self._fetch_predmety_simple(where=(
      'p.id = %s',
      (id,)
    ), lang=lang)
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