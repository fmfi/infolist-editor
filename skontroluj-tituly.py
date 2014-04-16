#!/usr/bin/env python
# -*- coding: utf-8 -*-
from export import PrilohaVPChar
from flask import json
import os
from infolist import config
import argparse
import psycopg2
# postgres unicode
import re

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

args = parser.parse_args()

with psycopg2.connect(config.conn_str, cursor_factory=NamedTupleCursor) as conn:
  with conn.cursor() as cur:
     charakteristiky = [x for x in os.listdir(config.vpchar_dir) if x.endswith('.json')]
     for filename in charakteristiky:
        tokmatch = re.match(r'^token-(.*)\.json$', filename)
        loginmatch = re.match(r'^user-(.*)\.json$', filename)
        if not (tokmatch or loginmatch):
          continue
        with open(os.path.join(config.vpchar_dir, filename), 'r') as f:
         doc = json.load(f, object_hook=PrilohaVPChar._json_object_hook)
        cele_meno = u' '.join(unicode(doc['cstruct'][x]) for x in ['titul_pred', 'meno', 'priezvisko'] if doc['cstruct'][x] is not None)
        if doc['cstruct']['titul_za'] is not None:
          cele_meno = u', '.join([cele_meno, doc['cstruct']['titul_za']])
        if tokmatch:
          cur.execute('SELECT o.id, o.cele_meno FROM osoba o, osoba_vpchar ovp WHERE o.id = ovp.osoba AND ovp.token = %s', (tokmatch.group(1),))
          row = cur.fetchone()
          if row is None:
            print 'VP charakteristika s tokenom {} nie je priradena k ziadnej osobe'.format(tokmatch.group(1))
            continue
        else:
          cur.execute('SELECT o.id, o.cele_meno FROM osoba o WHERE o.login = %s', (loginmatch.group(1),))
          row = cur.fetchone()
          if row is None:
            print 'Nenasiel som osobu s loginom {}'.format(loginmatch.group(1,))
            continue
        if row.cele_meno != cele_meno:
          print u'{} | {} | {} | {}'.format(row.id, row.cele_meno, cele_meno, filename).encode('UTF-8')
