# -*- coding: utf-8 -*-
from decimal import Decimal
import colander
from common.auth import restrict
from common.filters import filter_osoba
from common.schema import warning_schema, form_messages, zorad_osoby
from common.upload import upload_subor
from deform import Form, ValidationFailure
import export
from studprog.schema import Studprog
from studprog.statistiky import PocitadloStruktura
from studprog import blueprint
from flask import render_template, url_for, redirect, abort, flash, g, request, current_app, send_from_directory
from utils import recursive_replace, recursive_update
import utils
from werkzeug.exceptions import BadRequest


@blueprint.route('/studijny-program/')
@restrict()
def index():
  if not g.user.vidi_studijne_programy():
    abort(401)
  sp = g.db.fetch_studijne_programy()
  return render_template('studprog-index.html', studijne_programy=sp)

@blueprint.route('/studijny-program/<int:id>', defaults={'edit': False, 'spv_id': None})
@blueprint.route('/studijny-program/<int:id>/historia/<int:spv_id>', defaults={'edit': False})
@blueprint.route('/studijny-program/<int:id>/upravit', defaults={'edit': True, 'spv_id': None}, methods=['GET', 'POST'])
@blueprint.route('/studijny-program/novy', defaults={'id': None, 'edit': True, 'spv_id': None}, methods=['GET', 'POST'])
@restrict()
def show(id, edit, spv_id):
  if not g.user.vidi_studijne_programy():
    abort(401)
  if id != None:
    studprog = g.db.load_studprog(id, verzia=spv_id)
  else:
    if not g.user.moze_vytvarat_studijne_programy():
      abort(401)
    studprog = {
      'zamknute': None,
      'zamkol': None,
      'predosla_verzia': None,
      'bloky': [],
      'modifikovali': {},
    }
  if studprog['zamknute'] and edit:
    flash(u'Študijný program je zamknutý proti úpravám používateľom {}'
      .format(filter_osoba(studprog['zamkol']).cele_meno), 'danger')
    if request.method != 'POST':
      return redirect(url_for('.show', id=id, edit=False))
  
  if edit and not g.user.moze_menit_studprog():
    abort(401)
  
  form = Form(Studprog(), buttons=('submit',),
              appstruct=recursive_replace(studprog, None, colander.null))
  error_saving = False
  msg_ns = type("", (), {})() # http://bit.ly/1cPX3G5
  msg_ns.messages_type = 'danger';
  msg_ns.has_warnings = False
  msg_ns.add_warnings = {}
  def check_warnings():
    try:
      warning_schema(Studprog()).deserialize(form.cstruct)
    except colander.Invalid as e:
      form.widget.handle_error(form, e)
      msg_ns.messages_type = 'warning'
      msg_ns.has_warnings = True
    for warning in g.db.find_sp_warnings(limit_sp=id):
      msg_ns.add_warnings = warning['messages']
  
  if request.method == 'POST':
    controls = request.form.items(multi=True)
    try:
      recursive_update(studprog, recursive_replace(form.validate(controls), colander.null, None))
    except ValidationFailure:
      pass
    else:
      check_warnings()
      studprog['obsahuje_varovania'] = msg_ns.has_warnings
      if studprog['zamknute']:
        error_saving = True
      else:
        try:
          nove_id = g.db.save_studprog(id, studprog, user=g.user)
          g.db.commit()
          flash(u'Študijný program bol úspešne uložený', 'success')
          if msg_ns.has_warnings:
            flash((u'Formulár bol uložený, ale niektoré položky ešte bude treba doplniť, alebo upraviť. ' + 
                  u'Ak ich teraz neviete doplniť, môžete tak spraviť aj neskôr.'), 'warning')
          return redirect(url_for('.show', id=nove_id, edit=msg_ns.has_warnings))
        except:
          current_app.logger.exception('Vynimka pocas ukladania studijneho programu')
          g.db.rollback()
          error_saving = True
  else: # GET
    if id is not None:
      check_warnings()
  

  
  template = 'studprog-form.html' if edit else 'studprog.html'
  return render_template(template, form=form, data=studprog,
    messages=form_messages(form), messages_type=msg_ns.messages_type,
    add_warnings=msg_ns.add_warnings,
    studprog_id=id, error_saving=error_saving, editing=edit,
    modifikovali=zorad_osoby(studprog['modifikovali']),
    tab='sp')

@blueprint.route('/studijny-program/<int:id>/statistiky')
@restrict()
def show_statistiky(id):
  if not g.user.vidi_studijne_programy():
    abort(403)
  
  osoby = g.db.load_studprog_osoby_struktura(id)
  
  ps = PocitadloStruktura()

  chybajuci = set()
  for osoba in osoby:
    if len(osoba['uvazky']) == 0 or osoba['uvazky'][0]['uvazok'] is None:
      chybajuci.add(osoba['cele_meno'])
      continue
    for uvazok in osoba['uvazky']:
      # pridaj(id, funkcia, kvalifikacia, vaha)
      ps.pridaj(osoba['id'], uvazok['funkcia'], osoba['kvalifikacia'],
        Decimal(uvazok['uvazok']) / Decimal(100))

  zoznam = g.db.load_studprog_osoby_zoznam(id)

  studprog = g.db.load_studprog(id)
  return render_template('studprog-statistiky.html', pocty_osob=ps, chybajuci=chybajuci,
      data=studprog, studprog_id=id, editing=False, tab='statistiky', zoznam=zoznam)

@blueprint.route('/studijny-program/<int:id>/skolitelia', methods=['GET', 'POST'])
@restrict()
def skolitelia(id):
  if not g.user.vidi_studijne_programy():
    abort(403)

  if request.method == 'POST':
    novi_skolitelia = set(request.form.getlist('skolitelia', type=int))
    g.db.save_studprog_skolitelia(id, novi_skolitelia)
    g.db.commit()
    flash(u'Zoznam školitelov bol úspešne uložený', 'success')

  osoby = g.db.load_studprog_skolitelia(id)

  studprog = g.db.load_studprog(id)
  return render_template('studprog-skolitelia.html', osoby=osoby,
      data=studprog, studprog_id=id, editing=False, tab='skolitelia')

@blueprint.route('/studijny-program/<int:id>/dokumenty')
@restrict()
def prilohy(id):
  if not g.user.vidi_dokumenty_sp():
    abort(403)
  
  studprog = g.db.load_studprog(id)


  context = export.PrilohaContext()
  prilohy = export.prilohy_pre_studijny_program(context, id, None)

  return render_template('studprog-prilohy.html', prilohy=utils.prilohy_podla_typu(prilohy), data=studprog, studprog_id=id, editing=False,
                         tab='dokumenty', context=context)

@blueprint.route('/studijny-program/<int:id>/dokumenty/stiahni/<subor>')
@restrict()
def priloha_stiahni(id, subor):
  if not g.user.vidi_dokumenty_sp():
    abort(403)
  
  prilohy = export.prilohy_pre_studijny_program(export.PrilohaContext(), id, None)
  if subor not in prilohy.podla_nazvu_suboru:
    abort(404)
  
  return prilohy.podla_nazvu_suboru[subor].send()

@blueprint.route('/studijny-program/<int:id>/dokumenty/typ/<int:typ_prilohy>/zmaz/<int:subor>', methods=['POST'])
@restrict()
def priloha_zmaz(id, typ_prilohy, subor):
  if not g.user.moze_mazat_dokumenty():
    abort(403)

  if g.db.zmaz_dokument(id, typ_prilohy, subor):
    flash(u'Príloha bola úspešne odstránená', 'success')
    g.db.commit()

  return redirect(url_for('.prilohy', id=id))

@blueprint.route('/studijny-program/<int:id>/dokumenty/infolisty.rtf')
@restrict()
def priloha_stiahni_infolisty_v_jednom_subore(id):
  if not g.user.vidi_dokumenty_sp():
    abort(403)

  infolisty = g.db.load_studprog_infolisty(id)
  priloha = export.PrilohaInfolisty([x.infolist for x in infolisty], context=export.PrilohaContext(), nazov='Infolisty', filename=u'infolisty.rtf')

  return priloha.send()

@blueprint.route('/studijny-program/<int:id>/dokumenty/vsetky.zip', defaults={'spolocne': 'normalny'})
@blueprint.route('/studijny-program/<int:id>/dokumenty/vsetky-konverzny.zip', defaults={'spolocne': 'konverzny'})
@restrict()
def priloha_stiahni_zip(id, spolocne):
  if not g.user.vidi_dokumenty_sp():
    abort(403)

  prilohy = export.prilohy_pre_studijny_program(export.PrilohaContext(), id, spolocne)
  
  return prilohy.send_zip()


@blueprint.route('/studijny-program/<int:studprog_id>/dokumenty/formular/upload', methods=['GET', 'POST'], defaults={'konverzny': False})
@blueprint.route('/studijny-program/<int:studprog_id>/dokumenty/formular-konverzny/upload', methods=['GET', 'POST'], defaults={'konverzny': True})
@restrict()
def upload_formular(studprog_id, konverzny):
  formular, formular_konverzny = g.db.load_studprog_formulare_id(studprog_id)
  if not konverzny:
    subor_id = formular
  else:
    subor_id = formular_konverzny

  studprog = g.db.load_studprog(studprog_id)

  nazov_dokumentu = export.formular_nazov(studprog, konverzny=konverzny)
  nazov_suboru = export.formular_filename(studprog, konverzny=konverzny)

  if request.method == 'POST':
    novy_subor_id = upload_subor(subor_id, nazov=nazov_dokumentu, filename=nazov_suboru)
    if novy_subor_id is not None:
      g.db.save_studprog_formular_id(studprog_id, novy_subor_id, konverzny=konverzny)
      g.db.commit()
      flash(u'Formulár bol úspešne nahratý', 'success')
      return redirect(url_for('.prilohy', id=studprog_id))
    else:
      flash(u'Formulár sa nepodarilo nahrať, nezabudli ste vybrať súbor?', 'danger')

  return render_template('studprog-formular-upload.html', data=studprog,
    studprog_id=studprog_id, editing=True, subor_id=subor_id,
    subor=g.db.load_subor(subor_id), nazov_dokumentu=nazov_dokumentu, nazov_suboru=nazov_suboru,
    konverzny=konverzny
  )

@blueprint.route('/studijny-program/<int:studprog_id>/dokumenty/formular/zmaz', methods=['POST'], defaults={'konverzny': False})
@blueprint.route('/studijny-program/<int:studprog_id>/dokumenty/formular-konverzny/zmaz', methods=['POST'], defaults={'konverzny': True})
@restrict()
def zmaz_formular(studprog_id, konverzny):
  if not g.user.moze_mazat_dokumenty():
    abort(403)
  g.db.save_studprog_formular_id(studprog_id, None, konverzny=konverzny)
  g.db.commit()
  flash(u'Formulár úspešne zmazaný', 'success')
  return redirect(url_for('.prilohy', id=studprog_id))

@blueprint.route('/studijny-program/<int:studprog_id>/dokumenty/upload', methods=['GET','POST'], defaults={'subor_id': None})
@blueprint.route('/studijny-program/<int:studprog_id>/dokumenty/<int:subor_id>/upload', methods=['GET','POST'])
@restrict()
def prilohy_upload(studprog_id, subor_id):
  if not (g.user.vidi_dokumenty_sp() and g.user.moze_menit_studprog()):
    abort(403)

  typ_prilohy = None
  
  if request.method == 'POST':
    if 'typ_prilohy' in request.form:
      typ_prilohy = int(request.form['typ_prilohy'])

    novy_subor_id = upload_subor(subor_id)
    if novy_subor_id is not None:
      if subor_id is None:
        if typ_prilohy is None:
          raise BadRequest()
        g.db.add_studprog_priloha(studprog_id, typ_prilohy, novy_subor_id)
      g.db.commit()

      if subor_id is None:
        flash(u'Dokument bol úspešne nahratý', 'success')
      else:
        flash(u'Dokument bol úspešne aktualizovaný', 'success')

      return redirect(url_for('.prilohy', id=studprog_id))
    else:
      flash(u'Súbor sa nepodarilo nahrať, nezabudli ste vybrať súbor?', 'danger')
  
  studprog = g.db.load_studprog(studprog_id)
  return render_template('studprog-priloha-upload.html', data=studprog,
    studprog_id=studprog_id, editing=True, subor_id=subor_id,
    typy_priloh=g.db.load_typy_priloh(iba_moze_vybrat=True), subor=g.db.load_subor(subor_id)
  )

@blueprint.route('/subor/<int:id>')
@restrict()
def download_subor(id):
  if not g.user.vidi_dokumenty_sp():
    abort(403)
  
  s = g.db.load_subor(id)
  if s is None:
    abort(404)
  
  return send_from_directory(current_app.config['FILES_DIR'], s.sha256, as_attachment=True,
                             attachment_filename=s.nazov)


@blueprint.route('/studprog/<int:id>/lock', methods=['POST'], defaults={'lock': True})
@blueprint.route('/studprog/<int:id>/unlock', methods=['POST'], defaults={'lock': False})
@restrict()
def lock(id, lock):
  try:
    if lock:
      if not g.user.moze_menit_studprog():
        abort(401)
      g.db.lock_studprog(id, g.user.id)
    else:
      g.db.unlock_studprog(id, check_user=g.user)
    g.db.commit()
  except:
    flash(u'Nepodarilo sa {} študijný program list!'.format(u'zamknúť' if lock else u'odomknúť'), 'danger')
    current_app.logger.exception('Vynimka pocas zamykania/odomykania studprogu')
    g.db.rollback()
  if lock:
    flash(u'Študijný program bol zamknutý proti úpravám.', 'success')
  else:
    flash(u'Úpravy v študijnom programe boli povolené.', 'success')
  return redirect(url_for('.show', id=id, edit=False))

@blueprint.route('/studijny-program/<int:id>.rtf')
@restrict()
def export_rtf(id):
  studplan_rtf = export.PrilohaStudPlan(id, context=export.PrilohaContext(), filename='studprog-{}.rtf'.format(id))
  return studplan_rtf.send()
