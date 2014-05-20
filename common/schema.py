# -*- coding: utf-8 -*-
import colander
from markupsafe import Markup


class DuplicitnyValidator(object):
  def __init__(self, idkey, msg):
    self.idkey = idkey
    self.msg = msg

  def __call__(self, node, items):
    seen_items = set()
    root_exc = colander.Invalid(node)
    err = False
    for pos, i in enumerate(items):
      if self.idkey:
        val = i[self.idkey]
      else:
        val = i
      if val in seen_items:
        subnode = node.children[0]
        if self.idkey:
          exc = colander.Invalid(subnode)
          exc[self.idkey] = self.msg
        else:
          exc = colander.Invalid(subnode, self.msg)
        root_exc.add(exc, pos)
        err = True
      seen_items.add(val)
    if err:
      raise root_exc


def warning_schema(node):
  warning_validator = getattr(node, 'warning_validator', None)
  if warning_validator:
    node.validator = warning_validator
  if getattr(node, 'warn_if_missing', False):
    node.missing = colander.required
  for child in node:
    warning_schema(child)
  return node


def form_messages(form):
  if not form.error:
    return None

  def title(exc):
    if exc.positional:
      return u'{}.'.format(exc.pos + 1)
    if exc.node.title == None or exc.node.title == u'':
      return None
    return exc.node.title

  errors = []
  for path in form.error.paths():
    titlepath = []
    messages = []
    for exc in path:
      if exc.msg:
        messages.extend(exc.messages())
      tit = title(exc)
      if tit != None:
        titlepath.append(tit)
    errors.append((Markup(u' – ').join(titlepath), messages))
  return errors


def zorad_osoby(o):
  return sorted(o.values(), key=lambda x: x['priezvisko'])