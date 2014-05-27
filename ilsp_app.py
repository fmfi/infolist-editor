#!/usr/bin/env python
# -*- coding: utf-8 -*-
from ilsp import infolist, osoba, predmet, studprog, export
from ilsp.common import storage
from ilsp.common.auth import login_get_next_url, restrict
import ilsp.common.auth as auth
from ilsp.commands import register_commands
from ilsp.common.filters import register_filters
from ilsp.common.proxies import db, register_proxies
from flask import Flask
from flask.ext.script import Manager
from flask import render_template, url_for, redirect, abort
from flask import Request, g
from ilsp.storage import DataStore
from werkzeug.datastructures import OrderedMultiDict
import deform
deform.widget.SequenceWidget.category = 'structural' #monkey patch fix
from deform import Form
import os
import os.path
from pkg_resources import resource_filename
from werkzeug import secure_filename


class MyRequest(Request):
  parameter_storage_class = OrderedMultiDict

app = Flask('ilsp', instance_relative_config=True)
app.request_class = MyRequest
app.register_blueprint(infolist.blueprint)
app.register_blueprint(studprog.blueprint)
app.register_blueprint(predmet.blueprint)
app.register_blueprint(osoba.blueprint)

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

template_packages = ['ilsp'] + [bp.import_name for bp in app.blueprints.itervalues()] + ['deform']
Form.set_zpt_renderer([resource_filename(x, 'templates') for x in template_packages])

register_filters(app)
app.jinja_env.filters['secure_filename'] = secure_filename

register_proxies(app)

manager = Manager(app)
register_commands(manager)

@app.before_request
def before_request():
  g.db = DataStore(db)

app.register_blueprint(auth.blueprint)

@app.route('/', methods=['POST', 'GET'])
def index():
  if not g.user:
    goto, goto_enc = login_get_next_url()
    return render_template('login.html', next=goto_enc, next_url=goto)
  return redirect(url_for('predmet.index', tab='moje'))


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




if __name__ == '__main__':
  manager.run()
