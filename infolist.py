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

def restrict(api=False):
  def decorator(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
      if not g.user:
        if api:
          abort(401)
        else:
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
  form = Form(schema.Infolist(), buttons=('submit',))
  return render_template('infolist.html', form=form)

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

@app.route('/infolist/')
@restrict()
def infolist_index():
  with g.db.cursor() as cur:
    cur.execute('''SELECT i.id, ivp.nazov_predmetu, i.povodny_kod_predmetu
      FROM infolist i, infolist_verzia iv, infolist_verzia_preklad ivp
      WHERE i.posledna_verzia = iv.id AND ivp.infolist_verzia = iv.id
      ORDER BY ivp.nazov_predmetu''')
    return render_template('infolist-index.html', infolisty=cur.fetchall())

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

@app.route('/infolist/<int:id>', methods=['GET', 'POST'])
@restrict()
def show_infolist(id):
  infolist = g.db.load_infolist(id)
  if infolist['potrebny_jazyk'] == None:
    infolist['potrebny_jazyk'] = u'slovenský, anglický'
  #return repr(infolist)
  form = Form(schema.Infolist(), buttons=('submit',),
              appstruct=recursive_replace(infolist, None, colander.null))
  error_saving = False
  if request.method == 'POST':
    controls = request.form.items(multi=True)
    try:
      recursive_update(infolist, recursive_replace(form.validate(controls), colander.null, None))
      try:
        g.db.save_infolist(id, infolist)
        g.db.commit()
        flash(u'Informačný list bol úspešne uložený', 'success')
        return redirect(url_for('show_infolist', id=id))
      except:
        app.logger.exception('Vynimka pocas ukladania infolistu')
        g.db.rollback()
        error_saving = True
    except ValidationFailure, e:
      pass
  return render_template('infolist.html', form=form, data=infolist,
    messages=form_messages(form), infolist_id=id, error_saving=error_saving)

@app.route('/infolist/<int:id>/fork', methods=['POST'])
@restrict()
def fork_infolist(id):
  novy_infolist = g.db.fork_infolist(id, vytvoril=g.user.id)
  g.db.commit()
  return redirect(url_for('show_infolist', id=novy_infolist))

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
  for id, dokument, vyd_udaje in g.db.search_literatura(query):
    literatura.append({
      'id': int(id),
      'dokument': dokument,
      'vyd_udaje': vyd_udaje,
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
      vyd_udaje=literatura.vyd_udaje
    )

@app.route('/predmet/search')
@restrict(api=True)
def predmet_search():
  query = request.args['q']
  predmety = []
  for id, kod, skratka in g.db.search_predmet(query):
    predmety.append({
      'id': id,
      'kod': kod,
      'skratka': skratka,
    })
  return jsonify(predmety=predmety)

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