# -*- coding: utf-8 -*-
from deform.widget import Widget
from colander import null
import json
from utils import Podmienka
from flask import g, url_for

class RemoteSelect2Widget(Widget):
  null_value = ''
  
  def serialize(self, field, cstruct, **kw):
    if cstruct in (null, None):
      cstruct = self.null_value
    kw['search_url'] = self.search_url
    kw['item_url'] = self.item_url
    tmpl_values = self.get_template_values(field, cstruct, kw)
    return field.renderer(self.template, **tmpl_values)
  
  def deserialize(self, field, pstruct):
    if pstruct in (null, self.null_value):
        return null
    return pstruct

class PodmienkaWidget(Widget):
  null_value = ''
  template = 'podmienka'
  
  def serialize(self, field, cstruct, **kw):
    if cstruct in (null, None):
      cstruct = self.null_value
    options = [
      {'typ': 'spojka', 'value': 'OR', 'text': 'alebo'},
      {'typ': 'spojka', 'value': 'AND', 'text': 'a'},
      {'typ': 'zatvorka', 'value': '(', 'text': '('},
      {'typ': 'zatvorka', 'value': ')', 'text': ')'}
    ]
    podm = Podmienka(cstruct)
    for id in podm.idset():
      predmet = g.db.load_predmet_simple(id)
      if not predmet:
        continue
      option = {
        'value': predmet['id'],
        'skratka': predmet['skratka'],
        'kod': predmet['kod_predmetu'],
        'typ': 'predmet',
        'text': predmet['skratka'] + u'|'.join(predmet['nazvy_predmetu']),
        'nazvy': predmet['nazvy_predmetu']
      }
      options.append(option)
      
    kw['options'] = json.dumps(options)
    kw['search_url'] = url_for('predmet_search', _external=True)
    tmpl_values = self.get_template_values(field, cstruct, kw)
    return field.renderer(self.template, **tmpl_values)
  
  def deserialize(self, field, pstruct):
    if pstruct in (null, self.null_value):
        return null
    return pstruct