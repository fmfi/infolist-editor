# -*- coding: utf-8 -*-
from colander import MappingSchema, SchemaNode, String, Integer, Bool, Sequence, Length, Email
import colander
import deform
from chameleon.utils import Markup
import widgets
from flask import url_for

class VzdelavaciaCinnost(MappingSchema):
  druh_cinnosti = SchemaNode(String())
  pocet_hodin_tyzdenne = SchemaNode(Integer())
  metoda_vyucby = SchemaNode(String(),
    widget=deform.widget.Select2Widget(values=(('P', 'prezenčná'), ('D', 'dištančná'), ('K', 'kombinovaná')))
  )

def Vyucujuci(**kwargs):
  schema = MappingSchema(**kwargs)
  schema.add(SchemaNode(Integer(),
    name='osoba',
    widget=widgets.RemoteSelect2Widget(url=url_for('osoba_search', _external=True), template="osoba")
  ))
  return schema

def PodmienkyAbsolvovania(**kwargs):
  schema = MappingSchema(**kwargs)
  typ_hodn = ['priebezne', 'skuska']
  for x in typ_hodn:
    schema.add(SchemaNode(Integer(),
      name='pomer_{}'.format(x)
    ))
  for x in typ_hodn:
    schema.add(SchemaNode(String(),
      name=x
    ))
  for x in ['A', 'B', 'C', 'D', 'E']:
    schema.add(SchemaNode(Integer(),
      name='percenta_na_{}'.format(x)
    ))
  return schema

def OdporucanaLiteratura(**kwargs):
  schema = MappingSchema(**kwargs)
  schema.add(SchemaNode(Sequence(),
    SchemaNode(String(),
      name='id'
    ),
    name='zoznam'
  ))
  schema.add(SchemaNode(Sequence(),
    SchemaNode(String(),
      name='bibl'
    ),
    name='nove'
  ))
  return schema

def Infolist():
  schema = MappingSchema()
  schema.add(SchemaNode(String(),
    name='nazov_predmetu',
    title=u'Názov predmetu'
  ))
  schema.add(SchemaNode(Sequence(),
    VzdelavaciaCinnost(
      name='vzdelavacia_cinnost',
      title=u''
    ),
    name='cinnosti',
    title=u'Druh, rozsah a metóda vzdelávacích činností',
  ))
  schema.add(SchemaNode(Integer(),
    name='pocet_kreditov',
    title=u'Počet kreditov'
  ))
  schema.add(SchemaNode(Sequence(),
    SchemaNode(Sequence(),
      SchemaNode(String(),
        name='podm_and'
      ),
      name='podm_or'
    ),
    name='podmienujuce_predmety',
    title=u'Podmieňujúce predmety'
  ))
  schema.add(PodmienkyAbsolvovania(
    name='podm_absolvovania',
    title=u'Podmienky absolvovania predmetu'
  ))
  schema.add(SchemaNode(String(),
    name='vysledky_vzdelavania',
    title=u'Výsledky vzdelávania',
    widget=deform.widget.TextAreaWidget(rows=5)
  ))
  schema.add(SchemaNode(String(),
    name='strucna_osnova',
    title=u'Stručná osnova predmetu',
    widget=deform.widget.TextAreaWidget(rows=5)
  ))
  schema.add(OdporucanaLiteratura(
    name='odporucana_literatura',
    title=u'Odporúčaná literatúra'
  ))
  schema.add(SchemaNode(String(),
    name='jazyk',
    title=u'Jazyk, ktorého znalosť je potrebná na absolvovanie predmetu'
  ))
  schema.add(SchemaNode(Sequence(),
    Vyucujuci(name='vyucujuci'),
    name='vyucujuci',
    title=u'Vyučujúci'
  ))
  schema.add(SchemaNode(Bool(),
    name='finalna_verzia',
    title=u'Táto verzia je finálna a dá sa použiť do akreditačného spisu'
  ))
  return schema