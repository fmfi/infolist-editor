# -*- coding: utf-8 -*-
from deform.widget import Widget
from colander import null

class RemoteSelect2Widget(Widget):
  null_value = ''
  
  def serialize(self, field, cstruct, **kw):
    if cstruct in (null, None):
      cstruct = self.null_value
    kw['url'] = self.url
    tmpl_values = self.get_template_values(field, cstruct, kw)
    return field.renderer(self.template, **tmpl_values)
  
  def deserialize(self, field, pstruct):
    if pstruct in (null, self.null_value):
        return null
    return pstruct