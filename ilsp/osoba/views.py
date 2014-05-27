# -*- coding: utf-8 -*-
from ilsp.common.auth import restrict
from ilsp.common.upload import upload_subor
from flask import request, abort, g, flash, redirect, url_for, jsonify, render_template
from ilsp.osoba import blueprint
from werkzeug.exceptions import BadRequest


@blueprint.route('/osoba/<int:osoba_id>/upload/vpchar', methods=['GET', 'POST'])
@blueprint.route('/osoba/upload/vpchar', methods=['GET', 'POST'], defaults={'osoba_id': None})
@restrict()
def upload_vpchar(osoba_id):
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
      return redirect(url_for('.upload_vpchar', osoba_id=route_osoba_id))
    else:
      flash(u'VPCHAR sa nepodarilo nahrať, nezabudli ste vybrať súbor?', 'danger')

  return render_template('osoba-vpchar-upload.html', subor_id=subor_id, osoba=osoba, osoba_id=route_osoba_id)


@blueprint.route('/osoba/search')
@restrict(api=True)
def search():
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


@blueprint.route('/osoba/json')
@restrict(api=True)
def get():
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