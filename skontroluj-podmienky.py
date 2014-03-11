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

parser = argparse.ArgumentParser()

args = parser.parse_args()

stlpce = ['podmienujuce_predmety', 'vylucujuce_predmety', 'odporucane_predmety']

with psycopg2.connect(config.conn_str, cursor_factory=NamedTupleCursor) as conn:
  with conn.cursor() as cur:
    cur.execute('SELECT id, ' + ', '.join(stlpce) + ' FROM infolist_verzia')
    for row in cur:
      d = row._asdict()
      for stlpec in stlpce:
        try:
          Podmienka(d[stlpec])
        except ValueError as e:
          print row.id, stlpec, repr(d[stlpec]), e.message