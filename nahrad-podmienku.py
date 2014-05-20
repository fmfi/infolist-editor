#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse

from common import storage
from common.podmienka import Podmienka
from ilsp import config
import psycopg2

# postgres unicode
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)
from psycopg2.extras import NamedTupleCursor
import re

stlpce = ['podmienujuce_predmety', 'vylucujuce_predmety', 'odporucane_predmety']

parser = argparse.ArgumentParser()
parser.add_argument('username')
parser.add_argument('infolist_id', type=int)
parser.add_argument('stlpec', choices=stlpce)
parser.add_argument('nova_hodnota')

args = parser.parse_args()

nova_hodnota = Podmienka(args.nova_hodnota)

class RawPodmienka(object):
  def __init__(self, raw):
    self.raw = raw
  
  def serialize(self):
    return self.raw
  
  def __repr__(self):
    return 'RawPodmienka({!r})'.format(self.raw)
  
  def idset(self):
    ids = set()
    for token in self.raw.split():
      if re.match(r'^[0-9]+$', token):
        ids.add(int(token))
    return ids

with psycopg2.connect(config.conn_str, cursor_factory=NamedTupleCursor) as conn:
  db = storage.DataStore(conn, podmienka_class=RawPodmienka)
  user = db.load_user(args.username)
  if user is None:
    print 'Invalid username'
    exit()
  
  print args.infolist_id
  
  infolist = db.load_infolist(args.infolist_id)

  print repr(infolist)
  
  infolist[args.stlpec] = nova_hodnota
  
  print repr(infolist)
  
  print db.save_infolist(args.infolist_id, infolist, user=user, system_update=True)
  db.commit()