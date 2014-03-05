#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, Blueprint
app = Flask(__name__)

from flask import render_template, url_for, redirect, jsonify, abort, flash
from flask import request, Request, g
from flask import Response
from werkzeug.exceptions import BadRequest
from werkzeug.datastructures import OrderedMultiDict
from werkzeug.routing import BaseConverter
import re
import os
import deform
deform.widget.SequenceWidget.category = 'structural' #monkey patch fix
from deform import Form
from deform.exception import ValidationFailure
import json
import os
import os.path
from pkg_resources import resource_filename, resource_string
import colander
import time
import jinja2
from utils import kod2skratka, filter_fakulta, filter_druh_cinnosti
from utils import filter_obdobie, filter_typ_vyucujuceho, filter_metoda_vyucby
from utils import filter_podmienka, filter_jazyk_vyucby, filter_literatura
from utils import filter_osoba, format_datetime, space2nbsp, nl2br
from utils import recursive_replace, recursive_update
from utils import render_rtf
import utils
from markupsafe import Markup, soft_unicode
from functools import wraps
import psycopg2
# postgres unicode
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)
from psycopg2.extras import NamedTupleCursor
from decimal import Decimal, ROUND_HALF_EVEN
from utils import Podmienka

class MyRequest(Request):
  parameter_storage_class = OrderedMultiDict

app.request_class = MyRequest

import schema
import storage

if 'INFOLIST_DEBUG' in os.environ:
  app.debug = True

from local_settings import active_config
config = active_config(app)
app.secret_key = config.secret

form_deform_templates = resource_filename('deform', 'templates')
form_my_templates = resource_filename(__name__, 'templates')
form_template_path = (form_my_templates, form_deform_templates)
Form.set_zpt_renderer(form_template_path)

app.jinja_env.filters['skratka'] = kod2skratka
app.jinja_env.filters['fakulta'] = filter_fakulta
app.jinja_env.filters['druh_cinnosti'] = filter_druh_cinnosti
app.jinja_env.filters['obdobie'] = filter_obdobie
app.jinja_env.filters['typ_vyucujuceho'] = filter_typ_vyucujuceho
app.jinja_env.filters['metoda_vyucby'] = filter_metoda_vyucby
app.jinja_env.filters['podmienka'] = filter_podmienka
app.jinja_env.filters['jazyk_vyucby'] = filter_jazyk_vyucby
app.jinja_env.filters['literatura'] = filter_literatura
app.jinja_env.filters['osoba'] = filter_osoba
app.jinja_env.filters['any'] = any
app.jinja_env.filters['datetime'] = format_datetime
app.jinja_env.filters['space2nbsp'] = space2nbsp
app.jinja_env.filters['nl2br'] = nl2br

def restrict(api=False):
  def decorator(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
      if not g.user:
        if api:
          abort(401)
        else:
          if g.username:
            return render_template('unauthorized.html'), 401
          return redirect(url_for('index'))
      return f(*args, **kwargs)
    return wrapper
  return decorator

@app.before_request
def before_request():
  g.db = storage.DataStore(psycopg2.connect(config.conn_str, cursor_factory=NamedTupleCursor))
  
  username = request.remote_user
  if app.debug and 'REMOTE_USER' in os.environ:
    username = os.environ['REMOTE_USER']
  
  g.username = username
  g.user = g.db.load_user(username)

@app.teardown_request
def teardown_request(*args, **kwargs):
  try:
    g.db.conn.close()
  except:
    app.logger.exception('Vynimka pocas uvolnovania spojenia s DB')

@app.route('/', methods=['POST', 'GET'])
def index():
  if not g.user:
    return render_template('login.html')
  return redirect(url_for('predmet_index', tab='moje'))

@app.route('/login')
def login():
  return redirect(url_for('index'))

@app.route('/logout')
def logout():
  logout_link = 'https://login.uniba.sk/logout.cgi?{}'.format(url_for('index', _external=True))
  response = app.make_response(redirect(logout_link))
  if 'COSIGN_SERVICE' in request.environ:
    response.set_cookie(request.environ['COSIGN_SERVICE'], value='',
                        expires=1, path='/', secure=True)
  return response

@app.route('/ping')
def ping():
  return ''

@app.route('/ping.js')
def ping_js():
  return Response(render_template('ping.js'), mimetype='text/javascript')

@app.route('/predmet/', defaults={'tab': 'vsetky'})
@app.route('/predmet/moje', defaults={'tab': 'moje'})
@app.route('/predmet/moje-upravy', defaults={'tab': 'moje-upravy'})
@app.route('/predmet/vyucujem', defaults={'tab': 'vyucujem'})
@app.route('/predmet/oblubene', defaults={'tab': 'oblubene'})
@restrict()
def predmet_index(tab):
  def get_bool(name):
    val = request.args.get(name, None)
    if val != None:
      if val == 'ano':
        val = True
      elif val == 'nie':
        val = False
      elif val == '' or val == 'vsetky':
        val = None
      else:
        raise BadRequest()
    return val
  f = {}
  for name in ['import_z_aisu', 'finalna_verzia', 'obsahuje_varovania', 'zamknute']:
    f[name] = get_bool(name)
  if tab == 'vsetky':
    predmety = g.db.fetch_moje_predmety(g.user.id, **f)
  elif tab == 'moje':
    predmety = g.db.fetch_moje_predmety(g.user.id, upravy=True, uci=True, oblubene=True, **f)
  elif tab == 'moje-upravy':
    predmety = g.db.fetch_moje_predmety(g.user.id, upravy=True, **f)
  elif tab == 'vyucujem':
    predmety = g.db.fetch_moje_predmety(g.user.id, uci=True, **f)
  elif tab == 'oblubene':
    predmety = g.db.fetch_moje_predmety(g.user.id, oblubene=True, **f)
  return render_template('predmet-index.html',
    predmety=predmety,
    tab=tab,
    filtruj=f
  )

@app.route('/predmet/novy', methods=['POST'])
@restrict()
def predmet_novy():
  id, skratka = g.db.create_predmet(g.user.id)
  g.db.commit()
  flash((u'Predmet sme úspešne vytvorili s dočasným kódom {}, ' +
        u'finálny kód bude pridelený centrálne').format(skratka),
        'success')
  return redirect(url_for('show_infolist', id=None, predmet_id=id))

@app.route('/predmet/<int:predmet_id>/watch', methods=['POST'])
@restrict()
def predmet_watch(predmet_id):
  g.db.predmet_watch(predmet_id, g.user.id)
  g.db.commit()
  flash(u'Predmet bol pridaný medzi obľúbené', 'success')
  return redirect(url_for('predmet_index', tab='oblubene'))

@app.route('/predmet/<int:predmet_id>/unwatch', methods=['POST'])
@restrict()
def predmet_unwatch(predmet_id):
  g.db.predmet_unwatch(predmet_id, g.user.id)
  g.db.commit()
  flash(u'Predmet bol odobraný z obľúbených', 'success')
  return redirect(url_for('predmet_index', tab='oblubene'))

def form_messages(form):
  if not form.error:
    return None
  
  def title(exc):
    if exc.positional:
      return u'{}.'.format(exc.pos + 1)
    if exc.node.title == None or exc.node.title == u'':
      return None
    return exc.node.title
  
  errors = []
  for path in form.error.paths():
    titlepath = []
    messages = []
    for exc in path:
      if exc.msg:
        messages.extend(exc.messages())
      tit = title(exc)
      if tit != None:
        titlepath.append(tit)
    errors.append((Markup(u' – ').join(titlepath), messages))
  return errors

def zorad_osoby(o):
  return sorted(o.values(), key=lambda x: x['priezvisko'])

@app.route('/infolist/<int:id>', defaults={'edit': False})
@app.route('/infolist/<int:id>/upravit', defaults={'edit': True}, methods=['GET', 'POST'])
@app.route('/predmet/<int:predmet_id>/novy-infolist', defaults={'id': None, 'edit': True}, methods=['GET', 'POST'])
@app.route('/infolist/novy', defaults={'id': None, 'edit': True, 'predmet_id': None}, methods=['GET', 'POST'])
@restrict()
def show_infolist(id, edit, predmet_id=None):
  if id != None:
    infolist = g.db.load_infolist(id)
  else:
    infolist = {
      'zamknute': False,
      'modifikovali': {},
      'modifikovane': None,
      'hodnotenia_pocet': {'A': None, 'B': None, 'C': None, 'D': None, 'E': None, 'Fx': None},
      'predosla_verzia': None,
      'podm_absolvovania': {'nahrada': ''},
      'fakulta': 'FMFI'
    }
  if infolist['zamknute'] and edit:
    flash(u'Informačný list je zamknutý proti úpravám, vytvorte si vlastnú kópiu', 'danger')
    return redirect(url_for('show_infolist', id=id, edit=False))
  form = Form(schema.Infolist(), buttons=('submit',),
              appstruct=recursive_replace(infolist, None, colander.null))
  error_saving = False
  msg_ns = type("", (), {})() # http://bit.ly/1cPX3G5
  msg_ns.messages_type = 'danger';
  msg_ns.has_warnings = False
  def check_warnings():
    try:
      schema.warning_schema(schema.Infolist()).deserialize(form.cstruct)
    except colander.Invalid as e:
      form.widget.handle_error(form, e)
      msg_ns.messages_type = 'warning'
      msg_ns.has_warnings = True
  if request.method == 'POST':
    controls = request.form.items(multi=True)
    try:
      recursive_update(infolist, recursive_replace(form.validate(controls), colander.null, None))
    except ValidationFailure:
      pass
    else:
      check_warnings()
      infolist['obsahuje_varovania'] = msg_ns.has_warnings
      try:
        nove_id = g.db.save_infolist(id, infolist, user=g.user)
        nova_skratka = None
        if id == None:
          if predmet_id == None:
            predmet_id, nova_skratka = g.db.create_predmet(g.user.id)
          g.db.predmet_add_infolist(predmet_id, nove_id)
        g.db.commit()
        flash(u'Informačný list bol úspešne uložený', 'success')
        if nova_skratka:
          flash((u'Predmet sme úspešne vytvorili s dočasným kódom {}, ' +
            u'finálny kód bude pridelený centrálne').format(nova_skratka),
            'success')
        if msg_ns.has_warnings:
          flash((u'Formulár bol uložený, ale niektoré položky ešte bude treba doplniť, alebo upraviť. ' + 
                 u'Ak ich teraz neviete doplniť, môžete tak spraviť aj neskôr.'), 'warning')
        return redirect(url_for('show_infolist', id=nove_id, edit=msg_ns.has_warnings))
      except:
        app.logger.exception('Vynimka pocas ukladania infolistu')
        g.db.rollback()
        error_saving = True
  else: # GET
    check_warnings()
    
  template = 'infolist-form.html' if edit else 'infolist.html'
  return render_template(template, form=form, data=infolist,
    messages=form_messages(form), messages_type=msg_ns.messages_type,
    infolist_id=id, error_saving=error_saving,
    editing=edit, modifikovali=zorad_osoby(infolist['modifikovali']))

@app.route('/infolist/<int:id>.rtf')
def export_infolist(id):
  infolist = g.db.load_infolist(id)

  tdata = {}
  tdata['IL_NAZOV_SKOLY'] = u'Univerzita Komenského v Bratislave'
  tdata['IL_NAZOV_FAKULTY'] = filter_fakulta(infolist['fakulta'])
  tdata['IL_KOD_PREDMETU'] = infolist['skratka']
  tdata['IL_NAZOV_PREDMETU'] = infolist['nazov_predmetu']

  cinnosti = u''
  for cinn in infolist['cinnosti']:
    cinnosti += u'\n{}, {}h/{}, {}'.format(
      filter_druh_cinnosti(cinn['druh_cinnosti']),
      cinn['pocet_hodin'],
      filter_obdobie(cinn['za_obdobie']),
      filter_metoda_vyucby(cinn['metoda_vyucby'])
    )
  tdata['IL_CINNOSTI'] = cinnosti

  tdata['IL_POCET_KREDITOV'] = infolist['pocet_kreditov']
  tdata['IL_ODPORUCANY_SEMESTER'] = 'TODO'
  tdata['IL_STUPEN_STUDIA'] = 'TODO'

  def fmt_podm(text):
    podm_predmety = u''
    for token in Podmienka(text)._tokens:
      if token in Podmienka.symbols:
        if token == 'OR':
          podm_predmety += ' alebo '
        elif token == 'AND':
          podm_predmety += ' a '
        else:
          podm_predmety += token
      else:
        predmet = g.db.load_predmet_simple(int(token))
        if len(predmet['nazvy_predmetu']) == 0:
          nazov_predmetu = u'TODO'
        else:
          nazov_predmetu = predmet['nazvy_predmetu'][0]
        podm_predmety += u'{} {}'.format(predmet['skratka'], nazov_predmetu)
    return podm_predmety
  podm_predmety = fmt_podm(infolist['podmienujuce_predmety'])
  if infolist['odporucane_predmety'] and len(infolist['odporucane_predmety']) > 0:
    podm_predmety += u'\n\nOdporúčané predmety (nie je nutné ich absolvovať pred zapísaním predmetu):\n'
    podm_predmety += fmt_podm(infolist['odporucane_predmety'])
  tdata['IL_PODMIENUJUCE_PREDMETY'] = podm_predmety

  podm_absol_text = u'\n'
  podm_absol = infolist['podm_absolvovania']
  if podm_absol['nahrada'] != None:
    podm_absol_text = podm_absol['nahrada']
  else:
    if podm_absol['priebezne'] != None:
      podm_absol_text += u'Priebežné hodnotenie: {}\n'.format(podm_absol['priebezne'])
    if podm_absol['skuska'] != None:
      podm_absol_text += u'Skúška: {}\n'.format(podm_absol['skuska'])
    if podm_absol['percenta_skuska'] != None:
      podm_absol_text += u'Váha skúšky v hodnotení: {}%\n'.format(podm_absol['percenta_skuska'])
    if any(podm_absol['percenta_na'].values()) and not podm_absol['nepouzivat_stupnicu']:
      stupnica = podm_absol['percenta_na']
      podm_absol_text += u'Na získanie hodnotenia A je potrebné získať najmenej {}% bodov'.format(stupnica['A'])
      for znamka in ['B', 'C', 'D', 'E']:
        podm_absol_text += u' a ' if znamka == 'E' else u', '
        podm_absol_text += u'na hodnotenie {} najmenej {}% bodov'.format(znamka, stupnica[znamka])
      podm_absol_text += u'.\n'
  podm_absol_text = podm_absol_text.rstrip()
  
  tdata['IL_PODMIENKY_ABSOLVOVANIA'] = podm_absol_text

  tdata['IL_VYSLEDKY_VZDELAVANIA'] = infolist['vysledky_vzdelavania']
  tdata['IL_STRUCNA_OSNOVA'] = infolist['strucna_osnova']

  literatura = u''
  for bib_id in infolist['odporucana_literatura']['zoznam']:
    lit = filter_literatura(bib_id)
    literatura += u'\n{}. {}'.format(lit.dokument, lit.vyd_udaje)
  for popis in infolist['odporucana_literatura']['nove']:
    literatura += u'\n{}'.format(popis)
  tdata['IL_LITERATURA'] = literatura
  
  tdata['IL_POTREBNY_JAZYK'] = filter_jazyk_vyucby(infolist['potrebny_jazyk'])
  tdata['IL_POZNAMKY'] = u''
  
  mame_hodnotenia = True
  hodn = infolist['hodnotenia_pocet']
  for znamka in hodn:
    if hodn[znamka] == None:
      mame_hodnotenia = False
      break
  if mame_hodnotenia:
    celk_pocet = sum(hodn.values())
    tdata['IL_CELKOVY_POCET_STUDENTOV'] = celk_pocet
    for znamka in hodn:
      perc = Decimal(hodn[znamka]) / Decimal(celk_pocet) * Decimal(100)
      perc = perc.quantize(Decimal('.01'), rounding=ROUND_HALF_EVEN)
      tdata['IL_PERC_{}'.format(znamka.upper())] = u'{}%'.format(perc)
  else:
    tdata['IL_CELKOVY_POCET_STUDENTOV'] = ''
    for znamka in ['A', 'B', 'C', 'D', 'E', 'FX']:
      tdata['IL_PERC_{}'.format(znamka)] = ''
  
  vyuc_str = u''
  for vyucujuci in infolist['vyucujuci']:
    vyuc_str += u'\n{} - {}'.format(
      vyucujuci['cele_meno'],
      u', '.join(filter_typ_vyucujuceho(x) for x in vyucujuci['typy'])
    )
  tdata['IL_VYUCUJUCI'] = vyuc_str
  tdata['IL_POSLEDNA_ZMENA'] = format_datetime(infolist['modifikovane'], iba_datum=True)
  tdata['IL_SCHVALIL'] = ''

  rtf_template = resource_string(__name__, 'templates/infolist.rtf')
  rtf = render_rtf(rtf_template, tdata)

  response =  Response(rtf, mimetype='application/rtf')
  response.headers['Content-Disposition'] = 'attachment; filename=infolist-{}.rtf'.format(id)
  return response

@app.route('/infolist/<int:id>/fork', methods=['POST'])
@restrict()
def fork_infolist(id):
  novy_infolist = g.db.fork_infolist(id, vytvoril=g.user.id)
  g.db.commit()
  flash(u'Kópia bola úspešne vytvorená', 'success')
  return redirect(url_for('show_infolist', id=novy_infolist, edit=False))

@app.route('/infolist/<int:id>/lock', methods=['POST'], defaults={'lock': True})
@app.route('/infolist/<int:id>/unlock', methods=['POST'], defaults={'lock': False})
@restrict()
def lock_infolist(id, lock):
  try:
    if lock:
      g.db.lock_infolist(id, g.user.id)
    else:
      g.db.unlock_infolist(id, check_user=g.user)
    g.db.commit()
  except:
    flash(u'Nepodarilo sa {} informačný list!'.format(u'zamknúť' if lock else u'odomknúť'), 'danger')
    app.logger.exception('Vynimka pocas zamykania/odomykania infolistu')
    g.db.rollback()
  if lock:
    flash(u'Informačný list bol zamknutý proti úpravám.', 'success')
  else:
    flash(u'Úpravy v informačnom liste boli povolené.', 'success')
  return redirect(url_for('show_infolist', id=id, edit=False))

@app.route('/studijny-program/')
def studijny_program_index():
  sp = g.db.fetch_studijne_programy()
  return render_template('studprog-index.html', studijne_programy=sp)

@app.route('/studijny-program/<int:id>', defaults={'edit': False})
@app.route('/studijny-program/<int:id>/upravit', defaults={'edit': True}, methods=['GET', 'POST'])
@app.route('/studijny-program/novy', defaults={'id': None, 'edit': True}, methods=['GET', 'POST'])
def studijny_program_show(id, edit):
  if id != None:
    studprog = g.db.load_studprog(id)
  else:
    studprog = {
      'zamknute': None,
      'zamkol': None,
      'predosla_verzia': None,
      'bloky': []
    }
  if studprog['zamknute'] and edit:
    flash(u'Študijný program je zamknutý proti úpravám', 'danger')
    return redirect(url_for('studijny_program_show', id=id, edit=False))
  
  form = Form(schema.Studprog(), buttons=('submit',),
              appstruct=recursive_replace(studprog, None, colander.null))
  error_saving = False
  msg_ns = type("", (), {})() # http://bit.ly/1cPX3G5
  msg_ns.messages_type = 'danger';
  msg_ns.has_warnings = False
  def check_warnings():
    try:
      schema.warning_schema(schema.Studprog()).deserialize(form.cstruct)
    except colander.Invalid as e:
      form.widget.handle_error(form, e)
      msg_ns.messages_type = 'warning'
      msg_ns.has_warnings = True
  
  if request.method == 'POST':
    controls = request.form.items(multi=True)
    try:
      recursive_update(studprog, recursive_replace(form.validate(controls), colander.null, None))
    except ValidationFailure:
      pass
    else:
      check_warnings()
      studprog['obsahuje_varovania'] = msg_ns.has_warnings
      try:
        nove_id = g.db.save_studprog(id, studprog, user=g.user)
        g.db.commit()
        flash(u'Študijný program bol úspešne uložený', 'success')
        if msg_ns.has_warnings:
          flash((u'Formulár bol uložený, ale niektoré položky ešte bude treba doplniť, alebo upraviť. ' + 
                 u'Ak ich teraz neviete doplniť, môžete tak spraviť aj neskôr.'), 'warning')
        return redirect(url_for('studijny_program_show', id=nove_id, edit=msg_ns.has_warnings))
      except:
        app.logger.exception('Vynimka pocas ukladania studijneho programu')
        g.db.rollback()
        error_saving = True
  else: # GET
    if id is not None:
      check_warnings()
  
  vyrob_rozsah = utils.rozsah()
  
  for blok in studprog['bloky']:
    for infolist in blok['infolisty']:
      if 'cinnosti' in infolist:
        infolist['rozsah'] = vyrob_rozsah(infolist['cinnosti'])
  
  template = 'studprog-form.html' if edit else 'studprog.html'
  return render_template(template, form=form, data=studprog,
    messages=form_messages(form), messages_type=msg_ns.messages_type,
    studprog_id=id, error_saving=error_saving, editing=edit)

@app.route('/pouzivatelia')
@restrict()
def pouzivatelia():
  if not g.user.moze_spravovat_pouzivatelov():
    abort(401)
  users = g.db.load_users()
  return render_template('pouzivatelia.html', users=users)

@app.route('/osoba/search')
@restrict(api=True)
def osoba_search():
  query = request.args['q']
  osoby = []
  for id, cele_meno, meno, priezvisko in g.db.search_osoba(query):
    osoby.append({
      'id': id,
      'cele_meno': cele_meno,
      'meno': meno,
      'priezvisko': priezvisko
    })
  return jsonify(osoby=osoby)

@app.route('/osoba/json')
@restrict(api=True)
def osoba_get():
  try:
    id = int(request.args['id'])
  except ValueError:
    raise BadRequest()
  osoba = g.db.load_osoba(id)
  if osoba is None:
    abort(404)
  return jsonify(
      id=osoba.id,
      cele_meno=osoba.cele_meno,
      meno=osoba.meno,
      priezvisko=osoba.priezvisko
    )

@app.route('/literatura/search')
@restrict(api=True)
def literatura_search():
  query = request.args['q']
  literatura = []
  for id, dokument, vyd_udaje, signatura in g.db.search_literatura(query):
    literatura.append({
      'id': int(id),
      'dokument': dokument,
      'vyd_udaje': vyd_udaje,
      'signatura': signatura
    })
  return jsonify(literatura=literatura)

@app.route('/nova-literatura/search')
@restrict(api=True)
def nova_literatura_search():
  query = request.args.get('q', None) or request.args['term']
  return Response(json.dumps(g.db.search_nova_literatura(query)),
    mimetype='application/json')

@app.route('/literatura/json')
@restrict(api=True)
def literatura_get():
  try:
    id = int(request.args['id'])
  except ValueError:
    raise BadRequest()
  literatura = g.db.load_literatura(id)
  if literatura is None:
    abort(404)
  return jsonify(
      id=int(literatura.bib_id),
      dokument=literatura.dokument,
      vyd_udaje=literatura.vyd_udaje,
      signatura=literatura.signatura
    )

@app.route('/predmet/search')
@restrict(api=True)
def predmet_search():
  query = request.args['q']
  return jsonify(predmety=g.db.search_predmet(query))

@app.route('/infolist/search')
@restrict(api=True)
def infolist_search():
  query = request.args['q']
  return jsonify(infolisty=g.db.search_infolist(query, finalna=True))

@app.route('/infolist/json')
@restrict(api=True)
def infolist_get():
  try:
    id = int(request.args['id'])
  except ValueError:
    raise BadRequest()
  infolist = g.db.fetch_infolist(id)
  if infolist is None:
    abort(404)
  for v in infolist['vyucujuci']:
    v['typy'] = list(v['typy'])
  infolist['rozsah'] = utils.rozsah()(infolist['cinnosti'])
  return jsonify(**infolist)

if __name__ == '__main__':
  import sys

  if len(sys.argv) == 2 and sys.argv[1] == 'cherry':
    from cherrypy import wsgiserver
    d = wsgiserver.WSGIPathInfoDispatcher({'/': app})
    server = wsgiserver.CherryPyWSGIServer(('127.0.0.1', 5000), d)
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
  else:
    app.run() # werkzeug