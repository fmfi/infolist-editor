#!/usr/bin/env python
# -*- coding: utf-8 -*-
from infolist import config
import argparse
import psycopg2
# postgres unicode
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)
from psycopg2.extras import NamedTupleCursor
from utils import Podmienka

try:
  from termcolor import colored
except ImportError:
  def colored(text, *args, **kwargs):
    return text

parser = argparse.ArgumentParser()
parser.add_argument('id', type=int, nargs='+')

args = parser.parse_args()

def print_row(row, stlpce, hodnoty):
  d = row._asdict()
  for stlpec in d:
    val = d[stlpec]
    if stlpec in stlpce and d[stlpec] in hodnoty:
      val = colored(unicode(val), 'red', attrs=['bold'])
    print u'    {}: {}'.format(stlpec, val).encode('UTF-8')

tabulky = (
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

with psycopg2.connect(config.conn_str, cursor_factory=NamedTupleCursor) as conn:
  with conn.cursor() as cur:
    cur.execute('''SELECT * FROM osoba WHERE id IN ({})'''.format(', '.join('%s' for x in range(len(args.id)))), args.id)
    print 'Najdene osoby:'
    for osoba in cur:
      print_row(osoba, ('id',), args.id)
      print
      with conn.cursor() as cur2:
        for tabulka, stlpce in tabulky:
          where = ' OR '.join('{} = %s'.format(stlpec) for stlpec in stlpce)
          cur2.execute('''SELECT * from {} WHERE {}'''.format(tabulka, where), [osoba.id] * len(stlpce))
          if cur2.rowcount > 0:
            print '  {}:'.format(tabulka)
            for row in cur2:
              print_row(row, stlpce, (osoba.id,))
              print
