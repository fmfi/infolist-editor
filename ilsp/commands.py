# -*- coding: utf-8 -*-
from contextlib import closing
import json
import sys
from ilsp import export

from ilsp.export import PrilohaVPChar
from ilsp.storage import DataStore
import re
from flask import current_app, g
import os
from ilsp.common.podmienka import Podmienka, RawPodmienka
from ilsp.common.proxies import db
from flask.ext.script import Command, Option
import unicodecsv


try:
  from termcolor import colored
except ImportError:
  def colored(text, *args, **kwargs):
    return text

podmienkove_stlpce = ['podmienujuce_predmety', 'vylucujuce_predmety', 'odporucane_predmety']

class NahradPodmienkuCommand(Command):
  """Nahradi podmienku nejakou inou"""

  option_list = (
    Option('username'),
    Option('infolist_id', type=int),
    Option('stlpec', choices=podmienkove_stlpce),
    Option('nova_hodnota'),
  )

  def run(self, username, infolist_id, stlpec, nova_hodnota):
    nova_hodnota = Podmienka(nova_hodnota)
    store = DataStore(db, podmienka_class=RawPodmienka)
    user = store.load_user(username)
    if user is None:
      print 'Invalid username'
      exit()

    print infolist_id

    infolist = store.load_infolist(infolist_id)

    print repr(infolist)

    infolist[stlpec] = nova_hodnota

    print repr(infolist)

    print store.save_infolist(infolist_id, infolist, user=user, system_update=True)
    store.commit()


class NahradPredmetCommand(Command):
  """Nahradi predmet nejakym inym"""

  option_list = (
    Option('old', type=int),
    Option('new', type=int),
  )

  def run(self, old, new):
    def nahrad_v_podmienke(iv_id):
      with db.cursor() as cur:
        cur.execute('''
          SELECT ''' + ', '.join(podmienkove_stlpce) + '''
          FROM infolist_verzia
          WHERE id = %s
          ''',
          (iv_id,))
        for stlpec, hodn in zip(podmienkove_stlpce, cur.fetchone()):
          if str(old) in hodn.split():
            nova = ' '.join([x if x != str(old) else str(new) for x in hodn.split()])
            print '''-- Povodna hodnota pre {} je '{}'.'''.format(stlpec, hodn)
            print '''UPDATE infolist_verzia SET {} = '{}' WHERE id = {};'''.format(stlpec, nova, iv_id)
        def suvisi(predmet):
          cur.execute('''
            SELECT 1 as existuje
            FROM infolist_verzia_suvisiace_predmety
            WHERE infolist_verzia = %s AND predmet = %s
            ''',
            (iv_id, predmet))
          return bool(cur.fetchone())
        stary_suvisi = suvisi(old)
        novy_suvisi = suvisi(new)
        if stary_suvisi and not novy_suvisi:
          print 'UPDATE infolist_verzia_suvisiace_predmety SET predmet = {} where infolist_verzia = {} AND predmet = {};'.format(
            new, iv_id, old
          )

    with db.cursor() as cur:
      cur.execute('''
        SELECT infolist_verzia
        FROM infolist_verzia_suvisiace_predmety
        WHERE predmet = %s
        ''',
        (old,))
      for iv_id, in cur:
        with db.cursor() as cur2:
          cur2.execute('SELECT id FROM infolist WHERE posledna_verzia = %s', (iv_id,))
          infolisty = [x[0] for x in cur2.fetchall()]
        print '-- Predmet {} je odkazovany z verzie infolistu {} (infolist {})'.format(old, iv_id, ', '.join(str(x) for x in infolisty))
        with db.cursor() as cur2:
          nahrad_v_podmienke(iv_id)
        print

    db.commit()

osoba_tabulky = (
  ('ilsp_opravnenia', ('osoba',)),
  ('infolist_verzia', ('modifikoval',)),
  ('infolist_verzia_vyucujuci', ('osoba',)),
  ('infolist_verzia_vyucujuci_typ', ('osoba',)),
  ('infolist_verzia_modifikovali', ('osoba',)),
  ('infolist', ('zamkol','vytvoril',)),
  ('predmet', ('vytvoril',)),
  ('oblubene_predmety', ('osoba',)),
  ('studprog_verzia', ('garant','modifikoval',)),
  ('studprog_verzia_modifikovali', ('osoba',)),
  ('studprog', ('zamkol','vytvoril',)),
  ('subor_verzia', ('modifikoval',)),
)

class NajdiOsobuCommand(Command):
  """Najde osobu v roznych tabulkach"""

  option_list = (
    Option('id', type=int, nargs='+'),
  )

  @staticmethod
  def print_row(row, stlpce, hodnoty):
    d = row._asdict()
    for stlpec in d:
      val = d[stlpec]
      if stlpec in stlpce and d[stlpec] in hodnoty:
        val = colored(unicode(val), 'red', attrs=['bold'])
      print u'    {}: {}'.format(stlpec, val).encode('UTF-8')

  def run(self, id):
    with db.cursor() as cur:
      cur.execute('''SELECT * FROM osoba WHERE id IN ({})'''.format(', '.join('%s' for x in range(len(id)))), id)
      print 'Najdene osoby:'
      for osoba in cur:
        self.print_row(osoba, ('id',), id)
        print
        with db.cursor() as cur2:
          for tabulka, stlpce in osoba_tabulky:
            where = ' OR '.join('{} = %s'.format(stlpec) for stlpec in stlpce)
            cur2.execute('''SELECT * from {} WHERE {}'''.format(tabulka, where), [osoba.id] * len(stlpce))
            if cur2.rowcount > 0:
              print '  {}:'.format(tabulka)
              for row in cur2:
                self.print_row(row, stlpce, (osoba.id,))
                print


class SkontrolujPodmienkyCommand(Command):
  """Skontroluje podmienky infolistov"""

  def run(self):
    with db.cursor() as cur:
      cur.execute('SELECT i.id as i_id, iv.id as iv_id, ' + ', '.join(podmienkove_stlpce) + '''
        FROM infolist_verzia iv, infolist i
        WHERE i.posledna_verzia = iv.id
        ''')
      for row in cur:
        d = row._asdict()
        for stlpec in podmienkove_stlpce:
          try:
            Podmienka(d[stlpec])
          except ValueError as e:
            print row.i_id, row.iv_id, stlpec, repr(d[stlpec]), e.message

class SkontrolujTitulyCommand(Command):
  """Skontroluje, ci tituly sedia s vp charakteristikami"""

  def run(self):
    with db.cursor() as cur:
      charakteristiky = [x for x in os.listdir(current_app.config['VPCHAR_DIR']) if x.endswith('.json')]
      vysledky = []
      for filename in charakteristiky:
        tokmatch = re.match(r'^token-(.*)\.json$', filename)
        loginmatch = re.match(r'^user-(.*)\.json$', filename)
        if not (tokmatch or loginmatch):
          continue
        with open(os.path.join(current_app.config['VPCHAR_DIR'], filename), 'r') as f:
          doc = json.load(f, object_hook=PrilohaVPChar._json_object_hook)
        cele_meno = u' '.join(unicode(doc['cstruct'][x]) for x in ['titul_pred', 'meno', 'priezvisko'] if doc['cstruct'][x] is not None)
        if doc['cstruct']['titul_za'] is not None:
          cele_meno = u', '.join([cele_meno, doc['cstruct']['titul_za']])
        if tokmatch:
          cur.execute('SELECT o.id, o.cele_meno, o.priezvisko FROM osoba o, osoba_vpchar ovp WHERE o.id = ovp.osoba AND ovp.token = %s', (tokmatch.group(1),))
          row = cur.fetchone()
          if row is None:
            sys.stderr.write('VP charakteristika s tokenom {} nie je priradena k ziadnej osobe\n'.format(tokmatch.group(1)))
            continue
        else:
          cur.execute('SELECT o.id, o.cele_meno, o.priezvisko FROM osoba o WHERE o.login = %s', (loginmatch.group(1),))
          row = cur.fetchone()
          if row is None:
            sys.stderr.write('Nenasiel som osobu s loginom {}'.format(loginmatch.group(1,)))
            continue
        if row.cele_meno != cele_meno:
          vysledky.append([row.id, row.cele_meno, cele_meno, filename, row.priezvisko])
      vysledky.sort(key=lambda x: x[4])
      for x in vysledky:
        print u'{} | {} | {} | {}'.format(*x[:4]).encode('UTF-8')

class RunCherry(Command):
  """Spusti aplikaciu lokalne pomocou cherrypy servera"""
  def run(self):
    from cherrypy import wsgiserver
    d = wsgiserver.WSGIPathInfoDispatcher({'/': current_app._get_current_object()})
    server = wsgiserver.CherryPyWSGIServer(('127.0.0.1', 5000), d)
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()

class Export(Command):
  """Vyexportuje data o studijnych programoch do ZIP archivu"""

  option_list = (
    Option('--infolisty-samostatne', dest='infolisty_samostatne', action='store_true'),
    Option('--infolisty-spolu', dest='infolisty_samostatne', action='store_false'),
    Option('--charakteristiky-samostatne', dest='charakteristiky_samostatne', action='store_true'),
    Option('--charakteristiky-spolu', dest='charakteristiky_samostatne', action='store_false'),
    Option('--lang', dest='lang', default='sk'),
    Option('filename', help='Destination zip file name (will be overwritten)')
  )

  def run(self, filename, infolisty_samostatne, charakteristiky_samostatne, lang):
    g.db = DataStore(db)
    with open(filename, 'wb') as f:
      prilohy = export.prilohy_vsetky(export.PrilohaContext(lang=lang), infolisty_samostatne=infolisty_samostatne, charakteristiky_samostatne=charakteristiky_samostatne)
      prilohy.save_zip(f)

def normalize_val(val):
  val = val.strip()
  if val == '':
    return None
  return val

def normalize_optional(line, *columns):
  for column in columns:
    if column in line:
      return normalize_val(line[column])
  else:
    return None

class ImportOsoby(Command):
  """Naimportuje osoby z AISoveho CSV suboru (ak osoba s danym UOC existuje, urobi update)"""

  option_list = (
    Option('--nie-su-vyucujuci', action='store_false', dest='vyucujuci', help='Neoznacovat osoby ako vyucujucich'),
  )

  def run(self, vyucujuci):
    csv = unicodecsv.DictReader(sys.stdin, encoding='UTF-8')

    #Skontrolujeme udaje
    with closing(db.cursor()) as cursor:
      for line in csv:
        ais_id = normalize_val(line['ID'])
        meno = normalize_val(line['Meno'])
        priezvisko = normalize_val(line['Priezvisko'])
        plne_meno = normalize_optional(line, u'Plné meno')
        login = normalize_optional(line, 'Login')
        rodne_priezvisko = normalize_optional(line, u'Rodné', u'Pôvodné')
        uoc = normalize_optional(line, u'UOČ')
        if uoc is None:
          karty = normalize_val(line['Karty'])
          if karty == None:
            karty = []
          else:
            karty = [x.split(' - ') for x in karty.split(', ')]

          for x in karty:
            if len(x) != 2:
              print x
              continue
            typ, ident = x
            if typ == 'UOC':
              uoc = ident

        print ais_id, uoc, meno, priezvisko, plne_meno, rodne_priezvisko
        cursor.execute('SELECT uoc FROM osoba WHERE uoc = %s', (uoc,))
        if cursor.fetchone():
          cursor.execute('UPDATE osoba SET ais_id=%s, meno=%s, priezvisko=%s, cele_meno=%s, rodne_priezvisko=%s, vyucujuci=%s, login=%s WHERE uoc = %s',
                         (ais_id, meno, priezvisko, plne_meno, rodne_priezvisko, vyucujuci, login, uoc))
        else:
          cursor.execute('INSERT INTO osoba (ais_id, uoc, meno, priezvisko, cele_meno, rodne_priezvisko, vyucujuci, login) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                         (ais_id, uoc, meno, priezvisko, plne_meno, rodne_priezvisko, vyucujuci, login))

    db.commit()

class ImportOsobyUvazky(Command):
  def run(self):
    csv = unicodecsv.DictReader(sys.stdin, encoding='UTF-8')
    with closing(db.cursor()) as cursor:
      for line in csv:
        meno = normalize_optional(line, 'Meno')
        priezvisko = normalize_optional(line, 'Priezvisko')
        pracovisko = normalize_optional(line, 'Pracovisko')
        funkcia = normalize_optional(line, 'Funkcia')
        kvalifikacia = normalize_optional(line, u'Kvalifikácia')
        uvazok = normalize_optional(line, u'Prac .úv.')
        uoc = normalize_optional(line, u'UOČ')
        ais_id = normalize_optional(line, 'ID', u'ID osoby AIS')

        if uoc is not None:
          cursor.execute('''DELETE FROM osoba_uvazok ou USING osoba o where ou.osoba=o.id and uoc=%s and pracovisko=%s''', (uoc,pracovisko))
          cursor.execute('''INSERT INTO osoba_uvazok (osoba, pracovisko, funkcia, kvalifikacia, uvazok)
            SELECT o.id, %s, %s, %s, %s FROM osoba o WHERE o.uoc = %s
            ''', (pracovisko, funkcia, kvalifikacia, uvazok, uoc))
        elif ais_id is not None:
          cursor.execute('''INSERT INTO osoba_uvazok (osoba, pracovisko, funkcia, kvalifikacia, uvazok)
            SELECT o.id, %s, %s, %s, %s FROM osoba o WHERE o.ais_id = %s
            ''', (pracovisko, funkcia, kvalifikacia, uvazok, ais_id))
        else:
          print 'riadok {}: Neviem ako pridat osobu'.format(csv.line_num), meno, priezvisko, uoc, ais_id
    db.commit()

class ImportLiteraturaKniznica(Command):
  """Naimportuje literaturu dostupnu v kniznici"""

  def run(self):
    csv = unicodecsv.DictReader(sys.stdin, encoding='UTF-8')

    ok = True
    by_bibid = {}
    signatury = {}
    for line in csv:
      bib_id = normalize_val(line['BIBID'])
      dokument = normalize_val(line['Dokument'])
      vyd_udaje = normalize_val(line[u'Vyd. údaje'])
      signatura = normalize_val(line[u'Signatúra'])

      print "Citam zo suboru: ",bib_id

      t = (dokument, vyd_udaje)

      if bib_id in by_bibid:
        if by_bibid[bib_id] != t:
          print bib_id, by_bibid[bib_id], '!=', t
          ok = False
        signatury[bib_id] += u', ' + signatura
      else:
        by_bibid[bib_id] = t
        signatury[bib_id] = signatura

    if not ok:
      print 'Udaje nie su uplne v poriadku, koncim'
      return 1

    with closing(db.cursor()) as cursor:
      for bib_id, (dokument, vyd_udaje) in by_bibid.iteritems():
        signatura = signatury[bib_id]
        print "Zapisujem do databazy: ",bib_id
        cursor.execute('INSERT INTO literatura (bib_id, dokument, vyd_udaje, signatura, dostupne) VALUES (%s, %s, %s, %s, true)',
                       (bib_id, dokument, vyd_udaje, signatura))
    db.commit()

class PridajOpravnenie(Command):
  """Prida opravnenia danej osobe"""

  option_list = (
    Option('login', help='Login osoby, ktorej chceme pridat opravnenie pouzivat aplikaciu'),
    Option('--organizacna-jednotka', dest='organizacna_jednotka', default='FMFI'),
    Option('--je-admin', dest='je_admin', action='store_true', help='Nastavme aj ze je admin'),
    Option('--je-garant', dest='je_garant', action='store_true', help='Nastavme aj ze je garant'),
  )

  def run(self, login, organizacna_jednotka, je_admin, je_garant):
    with closing(db.cursor()) as cursor:
      cursor.execute('SELECT id FROM osoba WHERE login = %s', (login,))
      osoba = cursor.fetchone()
      if osoba is None:
        print 'Dana osoba v databaze neexistuje!'
        return 1

      cursor.execute('SELECT je_admin, je_garant FROM ilsp_opravnenia WHERE osoba = %s and organizacna_jednotka = %s',
        (osoba.id, organizacna_jednotka))
      opravnenia = cursor.fetchone()
      if opravnenia is None:
        cursor.execute('INSERT INTO ilsp_opravnenia (osoba, organizacna_jednotka, je_admin, je_garant) VALUES (%s, %s, %s, %s)',
          (osoba.id, organizacna_jednotka, je_admin, je_garant))
      else:
        if je_admin or je_garant:
          parts = []
          if je_admin:
            parts.append('je_admin = true')
          if je_garant:
            parts.append('je_garant = true')

          sql = 'UPDATE ilsp_opravnenia SET '
          sql += ', '.join(parts)
          sql += ' WHERE osoba = %s AND organizacna_jednotka = %s'

          cursor.execute(sql, (osoba.id, organizacna_jednotka))

    db.commit()

def register_commands(manager):
  manager.add_command('nahrad-podmienku', NahradPodmienkuCommand())
  manager.add_command('nahrad-predmet', NahradPredmetCommand())
  manager.add_command('najdi-osobu', NajdiOsobuCommand())
  manager.add_command('skontroluj-podmienky', SkontrolujPodmienkyCommand())
  manager.add_command('skontroluj-tituly', SkontrolujTitulyCommand())
  manager.add_command('runcherry', RunCherry())
  manager.add_command('export', Export())
  manager.add_command('import-osoby', ImportOsoby())
  manager.add_command('import-osoby-uvazky', ImportOsobyUvazky())
  manager.add_command('import-literatura-kniznica', ImportLiteraturaKniznica())
  manager.add_command('pridaj-opravnenie', PridajOpravnenie())
