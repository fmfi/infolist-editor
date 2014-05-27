#!/usr/bin/env python
# -*- coding: utf-8 -*-
from common import storage
from common.auth import login_get_next_url, restrict
import common.auth as auth
from common.commands import register_commands
from common.filters import register_filters
from common.proxies import db, register_proxies
from common.upload import upload_subor
from flask import Flask
from flask.ext.script import Manager, Server
import infolist
import predmet
import studprog
from flask import render_template, url_for, redirect, jsonify, abort, flash
from flask import request, Request, g, Response
from werkzeug.exceptions import BadRequest
from werkzeug.datastructures import OrderedMultiDict
import deform
deform.widget.SequenceWidget.category = 'structural' #monkey patch fix
from deform import Form
import json
import os
import os.path
from pkg_resources import resource_filename
from werkzeug import secure_filename
import export

class MyRequest(Request):
  parameter_storage_class = OrderedMultiDict

app = Flask(__name__, instance_relative_config=True)
app.request_class = MyRequest
app.register_blueprint(infolist.blueprint)
app.register_blueprint(studprog.blueprint)
app.register_blueprint(predmet.blueprint)

if 'INFOLIST_DEBUG' in os.environ:
  app.debug = True

app.config.from_pyfile('local_settings.py')

if not app.debug and app.config['ADMIN_EMAILS']:
  import logging
  from logging.handlers import SMTPHandler
  from logging import Formatter

  mail_handler = SMTPHandler(app.config['SMTP_SERVER'],
                            app.config['EMAIL_FROM'],
                            app.config['ADMIN_EMAILS'],
                            'ILSP - error')
  mail_handler.setLevel(logging.ERROR)
  mail_handler.setFormatter(Formatter('''
Message type:       %(levelname)s
Location:           %(pathname)s:%(lineno)d
Module:             %(module)s
Function:           %(funcName)s
Time:               %(asctime)s

Message:

%(message)s
'''))
  app.logger.addHandler(mail_handler)

template_packages = [__name__] + [bp.import_name for _, bp in app.blueprints.iteritems()] + ['deform']
Form.set_zpt_renderer([resource_filename(x, 'templates') for x in template_packages])

register_filters(app)
app.jinja_env.filters['secure_filename'] = secure_filename

register_proxies(app)

manager = Manager(app)
register_commands(manager)

@app.before_request
def before_request():
  g.db = storage.DataStore(db)

app.register_blueprint(auth.blueprint)

@app.route('/', methods=['POST', 'GET'])
def index():
  if not g.user:
    goto, goto_enc = login_get_next_url()
    return render_template('login.html', next=goto_enc, next_url=goto)
  return redirect(url_for('predmet.index', tab='moje'))


@app.route('/osoba/<int:osoba_id>/upload/vpchar', methods=['GET', 'POST'])
@app.route('/osoba/upload/vpchar', methods=['GET', 'POST'], defaults={'osoba_id': None})
@restrict()
def osoba_upload_vpchar(osoba_id):
  route_osoba_id = osoba_id
  if osoba_id is None:
    if request.method == 'POST':
      osoba_id = request.form['osoba_id']
  if osoba_id is not None:
    osoba=g.db.load_osoba(osoba_id)
    if osoba is None:
      abort(404)
  else:
    osoba = None
  subor_id = g.db.osoba_load_vpchar_subor_id(osoba_id)

  nazov = 'vpchar-{}'.format(osoba_id)

  if request.method == 'POST':
    novy_subor_id = upload_subor(subor_id, nazov=nazov)
    if novy_subor_id is not None:
      if subor_id is None:
        g.db.osoba_save_vpchar_subor_id(osoba_id, novy_subor_id)
      g.db.commit()
      flash(u'VPCHAR bola úspešne nahratá', 'success')
      return redirect(url_for('osoba_upload_vpchar', osoba_id=route_osoba_id))
    else:
      flash(u'VPCHAR sa nepodarilo nahrať, nezabudli ste vybrať súbor?', 'danger')

  return render_template('osoba-vpchar-upload.html', subor_id=subor_id, osoba=osoba, osoba_id=route_osoba_id)


@app.route('/stav-vyplnania')
@restrict()
def stav_vyplnania():
  if not g.user.vidi_stav_vyplnania():
    abort(401)
  sp_warnings = g.db.find_sp_warnings()
  return render_template('stav-vyplnania.html',
    sp_warnings=sp_warnings)

@app.route('/exporty')
@restrict()
def exporty():
  if not g.user.vidi_exporty():
    abort(401)
  return render_template('exporty.html')

@app.route('/exporty/vsetky-sp.zip', defaults={'infolisty_samostatne': True})
@app.route('/exporty/vsetky-sp-spojene-infolisty.zip', defaults={'infolisty_samostatne': False})
@restrict()
def export_vsetkych_sp(infolisty_samostatne):
  if not g.user.vidi_exporty():
    abort(401)

  prilohy = export.prilohy_vsetky(export.PrilohaContext(), infolisty_samostatne=infolisty_samostatne)

  if infolisty_samostatne:
    return prilohy.send_zip('vsetky-sp.zip')
  else:
    return prilohy.send_zip('vsetky-sp-spojene-infolisty.zip')

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


if __name__ == '__main__':
  manager.run()
