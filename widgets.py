# -*- coding: utf-8 -*-
from deform.widget import Widget
from colander import null
import json
from utils import Podmienka
from flask import g

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
      {'value': 'OR', 'text': 'ALEBO'},
      {'value': 'AND', 'text': 'A'},
      {'value': '(', 'text': '('},
      {'value': ')', 'text': ')'}
    ]
    podm = Podmienka(cstruct)
    for id in podm.idset():
      predmet = g.db.load_predmet(id)
      if not predmet:
        continue
      option = {
        'value': predmet.id,
        'text': predmet.skratka
      }
      options.append(option)
      
    kw['options'] = json.dumps(options)
    tmpl_values = self.get_template_values(field, cstruct, kw)
    return field.renderer(self.template, **tmpl_values)
  
  def deserialize(self, field, pstruct):
    if pstruct in (null, self.null_value):
        return null
    return pstruct