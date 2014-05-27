# -*- coding: utf-8 -*-
import re
from flask import g
from jinja2 import evalcontextfilter, Markup, escape


def kod2skratka(kod):
  return re.match(r'^[^/]+/(.+)/[^/]+$', kod).group(1)


def filter_fakulta(search_kod):
  for kod, nazov in g.db.load_fakulty():
    if search_kod == kod:
      return nazov
  return None


def filter_druh_cinnosti(search_kod):
  for kod, popis in g.db.load_druhy_cinnosti():
    if search_kod == kod:
      return popis
  return None


def filter_obdobie(search_kod):
  for kod, popis in (('S', u'semester'), ('T', u'týždeň')):
    if search_kod == kod:
      return popis
  return None


def filter_metoda_vyucby(search_kod):
  for kod, popis in (('P', u'prezenčná'), ('D', u'dištančná'), ('K', u'kombinovaná')):
    if search_kod == kod:
      return popis
  return None


def filter_typ_vyucujuceho(search_kod):
  for kod, popis in g.db.load_typy_vyucujuceho():
    if search_kod == kod:
      return popis
  return None


def filter_jazyk_vyucby(search_kod):
  for kod, popis in g.db.load_jazyky_vyucby():
    if search_kod == kod:
      return popis
  return None


def filter_typ_bloku(search_kod):
  for kod, popis in g.db.load_typy_bloku():
    if search_kod == kod:
      return popis
  return None


def filter_literatura(id):
  return g.db.load_literatura(id)


def filter_osoba(id):
  return g.db.load_osoba(id)


def filter_stupen_studia(stupen):
  stupne = {
    '1.': u'1. - bakalárske štúdium',
    '2.': u'2. - magisterské štúdium',
    '3.': u'3. - doktorandské štúdium',
  }
  if stupen in stupne:
    return stupne[stupen]
  return stupen


def format_datetime(value, iba_datum=False):
  if value == None:
    return ''
  if iba_datum:
    return value.strftime('%d.%m.%Y')
  return value.strftime('%d.%m.%Y %H:%M:%S')


def space2nbsp(value):
  return value.replace(u' ', u'\u00A0')


_paragraph_re = re.compile(r'(?:\r\n|\r|\n){2,}')


@evalcontextfilter
def nl2br(eval_ctx, value):
    result = u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', '<br />\n')
                          for p in _paragraph_re.split(escape(value)))
    if eval_ctx.autoescape:
        result = Markup(result)
    return result


def register_filters(app):
  app.jinja_env.filters['skratka'] = kod2skratka
  app.jinja_env.filters['fakulta'] = filter_fakulta
  app.jinja_env.filters['druh_cinnosti'] = filter_druh_cinnosti
  app.jinja_env.filters['obdobie'] = filter_obdobie
  app.jinja_env.filters['typ_vyucujuceho'] = filter_typ_vyucujuceho
  app.jinja_env.filters['typ_bloku'] = filter_typ_bloku
  app.jinja_env.filters['metoda_vyucby'] = filter_metoda_vyucby
  app.jinja_env.filters['jazyk_vyucby'] = filter_jazyk_vyucby
  app.jinja_env.filters['literatura'] = filter_literatura
  app.jinja_env.filters['osoba'] = filter_osoba
  app.jinja_env.filters['any'] = any
  app.jinja_env.filters['datetime'] = format_datetime
  app.jinja_env.filters['space2nbsp'] = space2nbsp
  app.jinja_env.filters['nl2br'] = nl2br
  app.jinja_env.filters['stupen_studia'] = filter_stupen_studia