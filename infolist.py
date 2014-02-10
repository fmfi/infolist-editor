#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, Blueprint
app = Flask(__name__)

from flask import render_template, url_for, redirect, jsonify, abort
from flask import request, Request, g
from flask import Response
from werkzeug.exceptions import BadRequest
from werkzeug.datastructures import OrderedMultiDict
from werkzeug.routing import BaseConverter
import re
import os
from deform import Form
from deform.exception import ValidationFailure
import json
import os
import os.path
from pkg_resources import resource_filename
import colander
import time
import jinja2
from markupsafe import Markup, soft_unicode
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

def load_user(username):
  with g.db.cursor() as cur:
    pass
  return username

@app.before_request
def before_request():
  g.db = storage.DataStore(psycopg2.connect(config.conn_str, cursor_factory=NamedTupleCursor))
  
  username = request.remote_user
  if app.debug and 'REMOTE_USER' in os.environ:
    username = os.environ['REMOTE_USER']
  
  g.user = load_user(username)

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

@app.route('/infolist/<int:id>')
def show_infolist(id):
  infolist = g.db.load_infolist(id)
  if infolist['potrebny_jazyk'] == None:
    infolist['potrebny_jazyk'] = u'slovenský, anglický'
  #return repr(infolist)
  form = Form(schema.Infolist(), buttons=('submit',), appstruct=infolist)
  return render_template('infolist.html', form=form)

@app.route('/osoba/search')
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

@app.route('/literatura/json')
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