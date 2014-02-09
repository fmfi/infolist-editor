# -*- coding: utf-8 -*-
from colander import MappingSchema, SchemaNode, String, Integer, Bool, Sequence, Length, Email, Set
import colander
import deform
from chameleon.utils import Markup
import widgets
from flask import url_for, g

def VzdelavaciaCinnost(**kwargs):
  schema = MappingSchema(**kwargs)
  schema.add(SchemaNode(String(),
    name='druh_cinnosti',
    widget=deform.widget.Select2Widget(values=g.db.load_druhy_cinnosti())
  ))
  schema.add(SchemaNode(Integer(),
    name='pocet_hodin',
  ))
  schema.add(SchemaNode(String(),
    name='za_obdobie',
    widget=deform.widget.Select2Widget(values=(('T', 'týždeň'), ('S', 'semester')))
  ))
  schema.add(SchemaNode(String(),
    name='metoda_vyucby',
    widget=deform.widget.Select2Widget(values=(('P', 'prezenčná'), ('D', 'dištančná'), ('K', 'kombinovaná')))
  ))
  return schema

def Vyucujuci(**kwargs):
  schema = MappingSchema(**kwargs)
  schema.add(SchemaNode(Integer(),
    name='osoba',
    widget=widgets.RemoteSelect2Widget(
      search_url=url_for('osoba_search', _external=True),
      item_url=url_for('osoba_get', _external=True),
      template="osoba"
    )
  ))
  schema.add(SchemaNode(Set(),
    name='typy',
    widget=deform.widget.CheckboxChoiceWidget(values=g.db.load_typy_vyucujuceho(iba_povolene=True))
  ))
  return schema

def PodmienkyAbsolvovania(**kwargs):
  schema = MappingSchema(**kwargs)
  schema.add(SchemaNode(Integer(),
    name='percenta_skuska'
  ))
  for x in ['priebezne', 'skuska']:
    schema.add(SchemaNode(String(),
      name=x,
      widget=deform.widget.TextAreaWidget(rows=5)
    ))
  for x in ['A', 'B', 'C', 'D', 'E']:
    schema.add(SchemaNode(Integer(),
      name='percenta_na_{}'.format(x)
    ))
  return schema

def OdporucanaLiteratura(**kwargs):
  schema = MappingSchema(**kwargs)
  schema.add(SchemaNode(Sequence(),
    SchemaNode(Integer(),
      name='literatura',
      widget=widgets.RemoteSelect2Widget(
        search_url=url_for('literatura_search', _external=True),
        item_url=url_for('literatura_get', _external=True),
        template="literatura"
      )
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
    name='fakulta',
    title=u'Fakulta',
    widget=deform.widget.Select2Widget(values=g.db.load_fakulty()),
  ))
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
    name='potrebny_jazyk',
    title=u'Jazyk, ktorého znalosť je potrebná na absolvovanie predmetu',
    readonly=True
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