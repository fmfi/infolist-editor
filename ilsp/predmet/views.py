# -*- coding: utf-8 -*-
from ilsp.common.auth import restrict
from ilsp.predmet import blueprint
from flask import render_template, url_for, redirect, abort, flash, g, request, jsonify
from werkzeug.exceptions import BadRequest

@blueprint.route('/predmet/', defaults={'tab': 'vsetky'})
@blueprint.route('/predmet/moje', defaults={'tab': 'moje'})
@blueprint.route('/predmet/moje-upravy', defaults={'tab': 'moje-upravy'})
@blueprint.route('/predmet/vyucujem', defaults={'tab': 'vyucujem'})
@blueprint.route('/predmet/oblubene', defaults={'tab': 'oblubene'})
@restrict()
def index(tab):
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

@blueprint.route('/predmet/<int:id>')
@restrict()
def show(id):
  predmet = g.db.load_predmet(id)
  if predmet is None:
    abort(404)
  return render_template('predmet.html', predmet=predmet)

@blueprint.route('/predmet/novy', methods=['POST'])
@restrict()
def novy():
  id, skratka = g.db.create_predmet(g.user.id)
  g.db.commit()
  flash((u'Predmet sme úspešne vytvorili s dočasným kódom {}, ' +
        u'finálny kód bude pridelený centrálne').format(skratka),
        'success')
  return redirect(url_for('infolist.show', id=None, predmet_id=id))

@blueprint.route('/predmet/<int:predmet_id>/watch', methods=['POST'])
@restrict()
def watch(predmet_id):
  g.db.predmet_watch(predmet_id, g.user.id)
  g.db.commit()
  flash(u'Predmet bol pridaný medzi obľúbené', 'success')
  return redirect(url_for('.index', tab='oblubene'))

@blueprint.route('/predmet/<int:predmet_id>/unwatch', methods=['POST'])
@restrict()
def unwatch(predmet_id):
  g.db.predmet_unwatch(predmet_id, g.user.id)
  g.db.commit()
  flash(u'Predmet bol odobraný z obľúbených', 'success')
  return redirect(url_for('.index', tab='oblubene'))

@blueprint.route('/predmet/search')
@restrict(api=True)
def search():
  query = request.args['q']
  return jsonify(predmety=g.db.search_predmet(query))
