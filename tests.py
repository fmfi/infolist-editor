#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils import Podmienka, PodmienkaASTEmpty as E, PodmienkaASTGroup as G, PodmienkaASTLiteral as L

good_inputs = [
  ('', [], E()),
  ('1', [1], L(1)),
  ('123', [123], L(123)),
  ('123 OR 456', [123, 'OR', 456], G('OR', L(123), L(456))),
  ('(123 OR 456)', ['(', 123, 'OR', 456, ')'], G('OR', L(123), L(456))),
  ('(123 OR 456 OR 567)', ['(', 123, 'OR', 456, 'OR', 567, ')'], G('OR', L(123), L(456), L(567))),
  ('123 OR 456 OR 567', [123, 'OR', 456, 'OR', 567], G('OR', L(123), L(456), L(567))),
  ('123 AND 456', [123, 'AND', 456], G('AND', L(123), L(456))),
  ('(123 AND 456) OR (234 AND 567)', ['(', 123, 'AND', 456, ')', 'OR', '(', 234, 'AND', 567, ')'],
      G('OR', G('AND', L(123), L(456)), G('AND', L(234), L(567)))
  ),
  ('((123 AND 456) AND (321 AND 654)) OR (234 AND 567)',
      ['(', '(', 123, 'AND', 456, ')', 'AND', '(', 321, 'AND', 654, ')', ')', 'OR', '(', 234, 'AND', 567, ')'],
      G('OR', G('AND', G('AND', L(123), L(456)), G('AND', L(321), L(654))), G('AND', L(234), L(567)))
  ),
]

bad_inputs = [
  'a',
  'OR',
  '(',
  ')',
  '()',
  '(AND)',
  ')(',
  '(1 AND)',
  '(1 AND',
  '(1 1)',
  '1 2',
]

vyhodnot = [
  ('', [], True),
  ('', [1], True),
  ('1', [1], True),
  ('1', [2], False),
  ('1 OR 2', [], False),
  ('1 OR 2', [1], True),
  ('1 OR 2', [2], True),
  ('1 OR 2', [1, 2], True),
  ('1 OR 2', [1, 2, 3], True),
  ('1 AND 2', [], False),
  ('1 AND 2', [1], False),
  ('1 AND 2', [2], False),
  ('1 AND 2', [1, 2], True),
  ('1 AND 2', [1, 2, 3], True),
]

def check_podmienka(text, tokens, ast):
  p = Podmienka(text)
  try:
    assert tokens == p._tokens
  except AssertionError:
    print '{!r} == {!r}'.format(tokens, p._tokens)
    raise
  try:
    assert ast == p._ast
  except AssertionError:
    print '{!r} == {!r}'.format(ast, p._ast)
    raise
  canonical_repr = text.replace('(', '( ').replace(')', ' )')
  serialized = p.serialize()
  try:
    assert canonical_repr == serialized
  except AssertionError:
    print '{!r} == {!r}'.format(canonical_repr, serialized)
    raise

def test_podmienka():
  for text, tokens, ast in good_inputs:
    yield check_podmienka, text, tokens, ast

def check_podmienka_exc(text):
  try:
    Podmienka(text)
    assert False
  except ValueError:
    pass

def test_podmienka_exc():
  for text in bad_inputs:
    yield check_podmienka_exc, text

def check_vyhodnot(podm, predmety, expected):
  p = Podmienka(podm)
  assert p.vyhodnot(predmety) == expected

def test_vyhodnot():
  for podm, predmety, expected in vyhodnot:
    yield check_vyhodnot, podm, predmety, expected

if __name__ == "__main__":
  import nose
  nose.main()