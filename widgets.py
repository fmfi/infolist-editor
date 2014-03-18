# -*- coding: utf-8 -*-
from deform.widget import Widget
from colander import null, Invalid
import json
from utils import Podmienka
from flask import g, url_for
import re

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

class PodmienkaTyp(object):
  def serialize(self, node, appstruct):
    if appstruct is null:
      return null
    if not isinstance(appstruct, Podmienka):
      raise Invalid(node, '%r nie je podmienka' % appstruct)
    return appstruct.serialize()
  
  def deserialize(self, node, cstruct):
    if cstruct is null:
      return null
    if not isinstance(cstruct, basestring):
      raise Invalid(node, '%r is not a string' % cstruct)
    try:
      return Podmienka(cstruct)
    except ValueError, e:
      raise Invalid(node, 'Chyba pri parsovani id predmetov (je mozne, ze Vam nefunguje javascriptovy editor?): ' + e.message)
  
  def cstruct_children(self, node, cstruct):
    return []

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
    
    podm = cstruct.split()
    for id in set(int(x) for x in podm if re.match(r'^\d+$', x)):
      predmet = g.db.load_predmet_simple(id)
      if not predmet:
        continue
      option = {
        'value': predmet['id'],
        'skratka': predmet['skratka'],
        'kod': predmet['kod_predmetu'],
        'typ': 'predmet',
        'text': predmet['skratka'] + u' ' + u'/'.join(predmet['nazvy_predmetu']),
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

class BlokInfolistWidget(Widget):
  template = 'blok_infolist'
  null_value = []
  
  def serialize(self, field, cstruct, **kw):
    if cstruct in (null, None):
      cstruct = self.null_value
    kw['il_load'] = g.db.load_infolist
    kw['values'] = json.dumps(cstruct)
    tmpl_values = self.get_template_values(field, cstruct, kw)
    return field.renderer(self.template, **tmpl_values)
    
  def deserialize(self, field, pstruct):
    return pstruct