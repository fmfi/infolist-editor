#!/usr/bin/env python
# -*- coding: utf-8 -*-
from infolist import config
import argparse
import psycopg2

parser = argparse.ArgumentParser()
parser.add_argument('old', type=int)
parser.add_argument('new', type=int)

args = parser.parse_args()

with psycopg2.connect(config.conn_str) as conn:
  def nahrad_v_podmienke(iv_id):
    stlpce = ['podmienujuce_predmety', 'vylucujuce_predmety', 'odporucane_predmety']
    with conn.cursor() as cur:
      cur.execute('''
        SELECT ''' + ', '.join(stlpce) + '''
        FROM infolist_verzia
        WHERE id = %s
        ''',
        (iv_id,))
      for stlpec, hodn in zip(stlpce, cur.fetchone()):
        if str(args.old) in hodn.split():
          nova = ' '.join([x if x != str(args.old) else str(args.new) for x in hodn.split()])
          print '''-- Povodna hodnota pre {} je '{}'.'''.format(stlpec, hodn)
          print '''UPDATE infolist_verzia SET {} = '{}' WHERE id = {};'''.format(stlpec, nova, iv_id)
      def suvisi(predmet):
        cur.execute('''
          SELECT 1
          FROM infolist_verzia_suvisiace_predmety
          WHERE infolist_verzia = %s AND predmet = %s
          ''',
          (iv_id, predmet))
        return bool(cur.fetchone())
      stary_suvisi = suvisi(args.old)
      novy_suvisi = suvisi(args.new)
      if stary_suvisi and not novy_suvisi:
        print 'UPDATE infolist_verzia_suvisiace_predmety SET predmet = {} where infolist_verzia = {} AND predmet = {};'.format(
          args.new, iv_id, args.old
        )
      
  with conn.cursor() as cur:
    cur.execute('''
      SELECT infolist_verzia
      FROM infolist_verzia_suvisiace_predmety
      WHERE predmet = %s
      ''',
      (args.old,))
    for iv_id, in cur:
      print '-- Predmet {} je odkazovany z verzie infolistu {}'.format(args.old, iv_id)
      with conn.cursor() as cur2:
        nahrad_v_podmienke(iv_id)
      print