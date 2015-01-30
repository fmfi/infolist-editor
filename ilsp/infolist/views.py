# -*- coding: utf-8 -*-
import colander
from ilsp import export, utils
from ilsp.common.auth import restrict
from ilsp.common.filters import format_datetime
from ilsp.common.schema import warning_schema, form_messages, zorad_osoby
from deform import Form, ValidationFailure
from ilsp.infolist.schema import Infolist
from ilsp.infolist import blueprint
from flask import render_template, url_for, redirect, abort, flash, g, request, current_app, jsonify
from ilsp.utils import recursive_replace, recursive_update
from werkzeug.exceptions import BadRequest


@blueprint.route('/infolist/<int:id>', defaults={'edit': False})
@blueprint.route('/infolist/<int:id>/upravit', defaults={'edit': True}, methods=['GET', 'POST'])
@blueprint.route('/predmet/<int:predmet_id>/novy-infolist', defaults={'id': None, 'edit': True}, methods=['GET', 'POST'])
@blueprint.route('/infolist/novy', defaults={'id': None, 'edit': True, 'predmet_id': None}, methods=['GET', 'POST'])
@restrict()
def show(id, edit, predmet_id=None):
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
  if infolist['zamknute'] and edit and request.method != 'POST':
    flash(u'Informačný list je zamknutý proti úpravám, vytvorte si vlastnú kópiu', 'danger')
    return redirect(url_for('.show', id=id, edit=False))
  form = Form(Infolist(infolist), buttons=('submit',),
              appstruct=recursive_replace(infolist, None, colander.null))
  error_saving = False
  msg_ns = type("", (), {})() # http://bit.ly/1cPX3G5
  msg_ns.messages_type = 'danger';
  msg_ns.has_warnings = False
  def check_warnings():
    try:
      warning_schema(Infolist(infolist)).deserialize(form.cstruct)
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
        if id is not None and nove_id != id:
          flash(u'Informačný list medzičasom niekto zamkol, vaše zmeny sme uložili do novej kópie', 'warning')
        else:
          flash(u'Informačný list bol úspešne uložený', 'success')
        if nova_skratka:
          flash((u'Predmet sme úspešne vytvorili s dočasným kódom {}, ' +
            u'finálny kód bude pridelený centrálne').format(nova_skratka),
            'success')
        if msg_ns.has_warnings:
          flash((u'Formulár bol uložený, ale niektoré položky ešte bude treba doplniť, alebo upraviť. ' +
                 u'Ak ich teraz neviete doplniť, môžete tak spraviť aj neskôr.'), 'warning')
        return redirect(url_for('.show', id=nove_id, edit=msg_ns.has_warnings))
      except:
        current_app.logger.exception('Vynimka pocas ukladania infolistu')
        g.db.rollback()
        error_saving = True
  else: # GET
    check_warnings()

  template = 'infolist-form.html' if edit else 'infolist.html'
  return render_template(template, form=form, data=infolist,
    messages=form_messages(form), messages_type=msg_ns.messages_type,
    infolist_id=id, error_saving=error_saving,
    editing=edit, modifikovali=zorad_osoby(infolist['modifikovali']))

@blueprint.route('/infolist/<int:id>.rtf')
@restrict()
def export_rtf(id):
  infolist_rtf = export.PrilohaInfolist(id, context=export.PrilohaContext(), filename='infolist-{}.rtf'.format(id))
  return infolist_rtf.send()

@blueprint.route('/infolist/<int:id>-en.rtf')
@restrict()
def export_rtf_en(id):
  infolist_rtf = export.PrilohaInfolist(id, context=export.PrilohaContext(lang='en'), filename='infolist-{}-en.rtf'.format(id))
  return infolist_rtf.send()

@blueprint.route('/infolist/<int:id>/fork', methods=['POST'])
@restrict()
def fork(id):
  novy_infolist = g.db.fork_infolist(id, vytvoril=g.user.id)
  g.db.commit()
  flash(u'Kópia bola úspešne vytvorená', 'success')
  return redirect(url_for('.show', id=novy_infolist, edit=False))

@blueprint.route('/infolist/<int:id>/lock', methods=['POST'], defaults={'lock': True})
@blueprint.route('/infolist/<int:id>/unlock', methods=['POST'], defaults={'lock': False})
@restrict()
def lock(id, lock):
  try:
    if lock:
      g.db.lock_infolist(id, g.user.id)
    else:
      g.db.unlock_infolist(id, check_user=g.user)
    g.db.commit()
  except:
    flash(u'Nepodarilo sa {} informačný list!'.format(u'zamknúť' if lock else u'odomknúť'), 'danger')
    current_app.logger.exception('Vynimka pocas zamykania/odomykania infolistu')
    g.db.rollback()
  else:
    if lock:
      flash(u'Informačný list bol zamknutý proti úpravám.', 'success')
    else:
      flash(u'Úpravy v informačnom liste boli povolené.', 'success')
  return redirect(url_for('.show', id=id, edit=False))

@blueprint.route('/infolist/<int:id>/trash', methods=['POST'], defaults={'trash': True})
@blueprint.route('/infolist/<int:id>/untrash', methods=['POST'], defaults={'trash': False})
@restrict()
def trash(id, trash):
  if not g.user.moze_zahadzovat_infolisty():
    abort(401)
  try:
    g.db.trash_infolist(id, trash)
    g.db.commit()
  except:
    flash(u'Nepodarilo sa {} informačný list!'.format(u'zahodiť' if trash else u'vrátiť'), 'danger')
    current_app.logger.exception('Vynimka pocas zahadzovania/vracania infolistu')
    g.db.rollback()
  else:
    if trash:
      flash(u'Informačný list bol zahodený.', 'success')
    else:
      flash(u'Informačný list bol vrátený', 'success')
  return redirect(url_for('.show', id=id, edit=False))

@blueprint.route('/infolist/search')
@restrict(api=True)
def search():
  query = request.args['q']
  infolisty = g.db.search_infolist(query, finalna=True)
  vyrob_rozsah = utils.rozsah()
  for infolist in infolisty:
    for v in infolist['vyucujuci']:
      v['typy'] = list(v['typy'])
    infolist['rozsah'] = vyrob_rozsah(infolist['cinnosti'])
    infolist['modifikovane'] = format_datetime(infolist['modifikovane'])
  return jsonify(infolisty=infolisty)

@blueprint.route('/infolist/json')
@restrict(api=True)
def get():
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
  infolist['modifikovane'] = format_datetime(infolist['modifikovane'])
  return jsonify(**infolist)