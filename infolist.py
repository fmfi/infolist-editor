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
from pkg_resources import resource_filename
import colander
import time
import jinja2
from utils import kod2skratka, filter_fakulta, filter_druh_cinnosti
from utils import filter_obdobie, filter_typ_vyucujuceho, filter_metoda_vyucby
from utils import filter_podmienka, filter_jazyk_vyucby, filter_literatura
from utils import filter_osoba, format_datetime, space2nbsp
from utils import recursive_replace, recursive_update
from markupsafe import Markup, soft_unicode
from functools import wraps
import psycopg2
# postgres unicode
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)
from psycopg2.extras import NamedTupleCursor

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
  return redirect(url_for('predmet_index'))

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

@app.route('/predmet/', defaults={'tab': 'vsetky'})
@app.route('/predmet/moje', defaults={'tab': 'moje'})
@app.route('/predmet/moje-upravy', defaults={'tab': 'moje-upravy'})
@app.route('/predmet/vyucujem', defaults={'tab': 'vyucujem'})
@restrict()
def predmet_index(tab):
  if tab == 'vsetky':
    predmety = g.db.fetch_predmety()
  elif tab == 'moje':
    predmety = g.db.fetch_moje_predmety(g.user.id)
  elif tab == 'moje-upravy':
    predmety = g.db.fetch_moje_predmety(g.user.id, uci=False)
  elif tab == 'vyucujem':
    predmety = g.db.fetch_moje_predmety(g.user.id, upravy=False)
  return render_template('predmet-index.html',
    predmety=predmety,
    tab=tab
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
  if request.method == 'POST':
    controls = request.form.items(multi=True)
    try:
      recursive_update(infolist, recursive_replace(form.validate(controls), colander.null, None))
      try:
        nove_id = g.db.save_infolist(id, infolist, user=g.user)
        nova_skratka = None
        if predmet_id == None:
          predmet_id, nova_skratka = g.db.create_predmet(g.user.id)
        if id == None and predmet_id != None:
          g.db.predmet_add_infolist(predmet_id, nove_id)
        g.db.commit()
        flash(u'Informačný list bol úspešne uložený', 'success')
        if nova_skratka:
          flash((u'Predmet sme úspešne vytvorili s dočasným kódom {}, ' +
            u'finálny kód bude pridelený centrálne').format(nova_skratka),
            'success')
        return redirect(url_for('show_infolist', id=nove_id, edit=False))
      except:
        app.logger.exception('Vynimka pocas ukladania infolistu')
        g.db.rollback()
        error_saving = True
    except ValidationFailure, e:
      pass
  template = 'infolist-form.html' if edit else 'infolist.html'
  return render_template(template, form=form, data=infolist,
    messages=form_messages(form), infolist_id=id, error_saving=error_saving,
    editing=edit, modifikovali=zorad_osoby(infolist['modifikovali']))

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
      g.db.unlock_infolist(id)
    g.db.commit()
  except:
    flash(u'Nepodarilo sa {} informačný list!'.format(u'zamknúť' if lock else u'odomknúť'), 'danger')
    app.logger.exception('Vynimka pocat zamykania/odomykania infolistu')
    g.db.rollback()
  return redirect(url_for('show_infolist', id=id, edit=False))

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