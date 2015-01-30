# -*- coding: utf-8 -*-
import gettext
from babel import support
from babel.support import NullTranslations
from flask import current_app
from werkzeug.local import LocalStack, LocalProxy
import os.path


_translation_stack = LocalStack()


class TranslationContextBase(object):
  def __init__(self):
    self._refcnt = 0

  def push(self):
    self._refcnt += 1
    _translation_stack.push(self)

  def pop(self):
    self._refcnt -= 1
    rv = _translation_stack.pop()
    assert rv is self, 'Popped wrong translation context.  (%r instead of %r)' \
        % (rv, self)

  def __enter__(self):
    self.push()
    return self

  def __exit__(self, exc_type, exc_value, tb):
    self.pop()

class NullTranslationContext(TranslationContextBase):
  def __init__(self):
    TranslationContextBase.__init__(self)
    self.translations = NullTranslations()


class TranslationContext(TranslationContextBase):
  def __init__(self, locale):
    TranslationContextBase.__init__(self)
    self.translations = support.Translations.load(os.path.join(current_app.root_path, 'translations'), [locale])
    print locale
    print os.path.join(current_app.root_path, 'translations')
    print self.translations


_translation_stack.push(NullTranslationContext())

def _get_context():
  v = _translation_stack.top
  if v is None:
    return NullTranslations()
  return v.translations

current_trans = LocalProxy(_get_context)


def _(msg):
  v = current_trans.gettext(msg)
  if not isinstance(v, unicode):
    v = v.decode('utf-8')
  return v
