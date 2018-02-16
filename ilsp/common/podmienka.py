# -*- coding: utf-8 -*-
from decimal import Decimal
from flask import g
from ilsp.common.translations import _, current_trans
import re


class PodmienkaASTGroup(object):
  def __init__(self, typ, *nodes):
    self.typ = typ
    if not self.typ in ['AND', 'OR']:
      raise ValueError('Unknown typ')
    self.nodes = nodes

  def __eq__(self, other):
    if not isinstance(other, PodmienkaASTGroup):
      return NotImplemented
    return self.typ == other.typ and self.nodes == other.nodes

  def __ne__(self, other):
    if not isinstance(other, PodmienkaASTGroup):
      return NotImplemented
    return not self.__eq__(other)

  def __repr__(self):
    return 'PodmienkaASTGroup({})'.format(', '.join(repr(x) for x in [self.typ] + list(self.nodes)))

  def vyhodnot(self, predmety):
    hodnoty = [x.vyhodnot(predmety) for x in self.nodes]
    return any(hodnoty) if self.typ == 'OR' else all(hodnoty)


class PodmienkaASTLiteral(object):
  def __init__(self, predmet_id):
    self.predmet_id = predmet_id
    self._predmet = None

  def __eq__(self, other):
    if not isinstance(other, PodmienkaASTLiteral):
      return NotImplemented
    return self.predmet_id == other.predmet_id

  def __ne__(self, other):
    if not isinstance(other, PodmienkaASTLiteral):
      return NotImplemented
    return not self.__eq__(other)

  def __repr__(self):
    return 'PodmienkaASTLiteral({!r})'.format(self.predmet_id)

  def vyhodnot(self, predmety):
    return self.predmet_id in predmety

  @property
  def predmet(self):
    if self._predmet is None:
      self._predmet = g.db.load_predmet_simple(self.predmet_id)
    return self._predmet


class PodmienkaASTEmpty(object):
  def __eq__(self, other):
    if not isinstance(other, PodmienkaASTEmpty):
      return NotImplemented
    return True

  def __ne__(self, other):
    if not isinstance(other, PodmienkaASTEmpty):
      return NotImplemented
    return not self.__eq__(other)

  def __repr__(self):
    return 'PodmienkaASTEmpty()'

  def vyhodnot(self, predmety):
    return True


class Podmienka(object):
  symbols = ('(', ')', 'OR', 'AND')

  def __init__(self, text):
    self._tokens = []
    self._predmety = {}
    rawtok = self._tokenize(text)
    if len(rawtok) == 0:
      self._tokens = []
      self._ast = PodmienkaASTEmpty()
    else:
      self._tokens, self._ast = Podmienka._parse_expr_in(rawtok)

  @classmethod
  def _parse_expr(cls, tokens):
    if len(tokens) == 0:
      raise ValueError('Expecting expression')

    if tokens[0] == '(':
      ret = [tokens.pop(0)]
      expr_tok, expr_ast = cls._parse_expr_in(tokens)
      ret.extend(expr_tok)
      if not tokens or tokens[0] != ')':
        raise ValueError('Expecting )')
      ret.append(tokens.pop(0))
      return ret, expr_ast
    elif re.match('^[0-9]+$', tokens[0]):
      predmet_id = int(tokens.pop(0))
      return [predmet_id], PodmienkaASTLiteral(predmet_id)
    else:
      raise ValueError('Expecting ID or (')

  @classmethod
  def _parse_expr_in(cls, tokens):
    ret, ast = cls._parse_expr(tokens)

    if not tokens or tokens[0] == ')':
      return ret, ast

    if tokens[0].upper() not in ['OR', 'AND', 'A', 'ALEBO']:
      raise ValueError('Expecting AND or OR')

    typ = tokens.pop(0).upper()
    if typ == 'A':
      typ = 'AND'
    elif typ == 'ALEBO':
      typ = 'OR'

    ret.append(typ)
    nodes = [ast]

    while True:
      subexpr_tokens, subexpr_ast = cls._parse_expr(tokens)
      ret.extend(subexpr_tokens)
      nodes.append(subexpr_ast)

      if not tokens or tokens[0] == ')':
        return ret, PodmienkaASTGroup(typ, *nodes)

      if tokens[0].upper() != typ:
        raise ValueError('Expecting ' + typ)

      ret.append(tokens.pop(0).upper())

  @staticmethod
  def _tokenize(text):
    tokens = []
    last = None
    for c in text:
      if c in '()':
        tokens.append(c)
        last = c
      elif c in '0123456789':
        if last == 'num':
          tokens[-1] += c
        else:
          tokens.append(c)
        last = 'num'
      elif (c >= 'a' and c <= 'z') or (c >= 'A' and c <= 'Z'):
        if last == 'alpha':
          tokens[-1] += c
        else:
          tokens.append(c)
        last = 'alpha'
      elif c in ' \t\n\r\v':
        last = 'space'
      else:
        raise ValueError(u'Invalid token character: ' + c)
    return tokens

  def _load_predmety(self, lang='sk'):
    to_load = self.idset().difference(set(self._predmety))
    if not to_load:
      return self._predmety
    for p in to_load:
      data = g.db.load_predmet_simple(p, lang=lang)
      if data == None and lang != 'sk':
        data = g.db.load_predmet_simple(p, lang='sk')
      if data == None:
        raise ValueError('Predmet {} neexistuje v databaze'.format(p))
      self._predmety[p] = data
    return self._predmety

  @property
  def tokens(self):
    return self.load_tokens()

  def load_tokens(self, lang='sk'):
    ret = []
    pred = self._load_predmety(lang=lang)
    for tok in self._tokens:
      if tok in self.symbols:
        ret.append(tok)
      else:
        ret.append(pred[tok])
    return ret

  def idset(self):
    ret = set()
    for token in self._tokens:
      if token not in self.symbols:
        ret.add(int(token))
    return ret

  def __unicode__(self):
    ret = u''
    for token in self.load_tokens(lang=current_trans.lang):
      if token in Podmienka.symbols:
        if token == 'OR':
          ret += _(' alebo ')
        elif token == 'AND':
          ret += _(' a ')
        else:
          ret += token
      else:
        if len(token['nazvy_predmetu']) == 0:
          nazov_predmetu = u'TODO'
        else:
          nazov_predmetu = u'/'.join(token['nazvy_predmetu'])
        ret += u'{} {}'.format(token['skratka'], nazov_predmetu)
    return ret

  def __str__(self):
    return unicode(self).encode('UTF-8')

  def __repr__(self):
    return 'Podmienka({!r})'.format(self.serialize())

  def serialize(self):
    return ' '.join(str(x) for x in self._tokens)

  def __len__(self):
    return len(self._tokens)

  def vyhodnot(self, predmety):
    return self._ast.vyhodnot(predmety)

  @property
  def ast(self):
    return self._ast

class RawPodmienka(object):
  def __init__(self, raw):
    self.raw = raw

  def serialize(self):
    return self.raw

  def __repr__(self):
    return 'RawPodmienka({!r})'.format(self.raw)

  def idset(self):
    ids = set()
    for token in self.raw.split():
      if re.match(r'^[0-9]+$', token):
        ids.add(int(token))
    return ids
