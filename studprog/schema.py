# -*- coding: utf-8 -*-
import colander
from colander import MappingSchema, SchemaNode, String, Integer, Bool, Sequence
from common import widgets
from common.schema import DuplicitnyValidator
import deform
from flask import g, url_for


def infolisty_v_bloku_nie_su_duplicitne_validator(node, infolisty):
  videne = set()
  root_exc = colander.Invalid(node)
  err = False
  for pos, i in enumerate(infolisty):
    if i['infolist'] in videne:
      subnode = node.children[0]
      exc = colander.Invalid(subnode)
      exc['infolist'] = u'''Informačný list sa už v bloku nachádza, prosím zadajte ho iba raz'''
      root_exc.add(exc, pos)
      err = True
    videne.add(i['infolist'])
  if err:
    raise root_exc


def Blok(**kwargs):
  schema = MappingSchema(**kwargs)
  schema.add(SchemaNode(String(),
    name='nazov',
    title=u'Názov bloku',
    description=u'Napr. S1: Astrológia',
  ))
  schema.add(SchemaNode(String(),
    name='typ',
    title=u'Typ bloku',
    widget=deform.widget.Select2Widget(values=[('', '')] + g.db.load_typy_bloku(), placeholder=u'Vyberte typ bloku'),
  ))
  schema.add(SchemaNode(String(),
    name='podmienky',
    title=u'Podmienky absolvovania bloku',
    description=u'Napr. "výber aspoň 27 kreditov", "všetky predmety z bloku", "výber 1 predmetu" a pod.',
    missing=u''
  ))
  infolist_schema = MappingSchema(name='infolist')
  infolist_schema.add(SchemaNode(Integer(),
    name='infolist',
    title=u'Infolist',
    description=u'''Ak nenájdete vami požadovaný predmet v zozname, môže to byť
    z dôvodu, že predmet nebol označený ako finálna verzia. Vyhľadajte v editore
    infolistov príslušný informačný list, skontrolujte jeho rozpracovanosť a
    označte ho ako finálna verzia.''',
    widget=widgets.RemoteSelect2Widget(
      search_url=url_for('infolist.search', _external=True),
      item_url=url_for('infolist.get', _external=True),
      template="infolist"
    )
  ))
  infolist_schema.add(SchemaNode(Bool(),
    name='predmet_jadra',
    title=u'Predmet je v jadre študijného programu',
  ))
  infolist_schema.add(SchemaNode(Integer(),
    name='rocnik',
    title=u'Ročník',
    missing=colander.null
  ))
  infolist_schema.add(SchemaNode(String(),
    name='semester',
    title=u'Semester',
    widget=deform.widget.Select2Widget(values=(('', ''), ('Z', 'zimný'), ('L', 'letný'), ('N', 'neurčený')), placeholder=u'Vyberte semester'),
  ))
  infolist_schema.add(SchemaNode(String(),
    name='poznamka',
    title=u'Poznámka',
    missing=''
  ))
  schema.add(SchemaNode(Sequence(),
    infolist_schema,
    name='infolisty',
    title=u'Informačné listy',
    #widget=widgets.BlokInfolistWidget(),
    validator=DuplicitnyValidator('infolist', u'''Informačný list sa už v bloku nachádza, prosím zadajte ho iba raz''')
  ))
  return schema


def Studprog():
  schema = MappingSchema()
  if (g.user.moze_menit_kody_sp()):
    schema.add(SchemaNode(String(),
      name=u'skratka',
      title=u'Kód študijného programu'
    ))
  schema.add(SchemaNode(String(),
    name=u'nazov',
    title=u'Názov študijného programu'
  ))
  schema.add(SchemaNode(Bool(),
    name=u'aj_konverzny_program',
    title=u'Aj konverzný program'
  ))
  schema.add(SchemaNode(Integer(),
    name=u'garant',
    title=u'Garant študijného programu',
    widget=widgets.RemoteSelect2Widget(
      search_url=url_for('osoba_search', _external=True),
      item_url=url_for('osoba_get', _external=True),
      template="osoba"
    ),
    missing=colander.null,
    warn_if_missing=True
  ))
  schema.add(SchemaNode(String(),
    name=u'stupen_studia',
    title=u'Stupeň štúdia',
    widget=deform.widget.Select2Widget(values=(('', ''), ('1.', '1. - bakalárske štúdium'), ('2.', '2. - magisterské štúdium'), ('3.', '3. - doktorandské štúdium')), placeholder=u'Vyberte stupeň štúdia'),
  ))
  schema.add(SchemaNode(String(),
    name=u'podmienky_absolvovania',
    title=u'Podmienky absolvovania študijného programu',
    description=u'''Napr. Pre úspešné absolvovanie študijného programu musí
      študent okrem povinných predmetov absolvovať jeden celý špecializačný blok
      povinne voliteľných predmetov S1-S10 a zo všetkých povinne voliteľných
      predmetov musí z ostatných blokov absolvovať aspoň 15 kreditov.''',
    widget=deform.widget.TextAreaWidget(rows=5),
    missing=u'',
    warn_if_missing=True
  ))
  schema.add(SchemaNode(Sequence(),
    Blok(
      name='blok',
      title=u'Blok',
      widget=deform.widget.MappingWidget(template='blok_mapping')
    ),
    name='bloky',
    title=u'Bloky',
    widget=deform.widget.SequenceWidget(orderable=True),
  ))
  schema.add(SchemaNode(String(),
    name=u'poznamka_konverzny',
    title=u'Poznámka ku konverznému programu',
    description=u'Táto poznámka sa zobrazuje len v prípade, že je zaškrtnuté políčko "aj konverzný program"',
    missing=u'',
    default=u'''Konverzný študijný program je určený pre absolventov bakalárskeho
      štúdia, na ktoré tento program nenadväzuje, resp. rozsah a kvalita ich
      vedomostí nenapĺňa dostatočne predpoklady pre úspešné dvojročné magisterské
      štúdium. Študent navyše oproti uvedenému absolvuje úvodný ročník, v ktorom
      absolvuje predmety z bakalárskeho štúdia, ktoré sú potrebné ako prerekvizita
      k úspešnému absolvovaniu magisterského štúdia. Tieto predmety určuje
      individuálne garant študijného programu na základe dokladov o absolvovanom
      bakalárskom štúdiu a na základe výsledkov prijímacích skúšok.
      Po absolvovaní úvodného ročníka budú študenti pokračovať podľa
      štandardného odporúčaného študijného plánu.'''.replace('\n      ', ' '),
    widget=deform.widget.TextAreaWidget(rows=5),
  ))
  schema.add(SchemaNode(Bool(),
    name='finalna_verzia',
    title=u'Táto verzia je finálna a dá sa použiť do akreditačného spisu'
  ))
  return schema