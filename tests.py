#!/usr/bin/env python
# -*- coding: utf-8 -*-

from utils import Podmienka

good_inputs = [
  ('', []),
  ('1', [1]),
  ('123', [123]),
  ('123 OR 456', [123, 'OR', 456]),
  ('(123 OR 456)', ['(', 123, 'OR', 456, ')']),
  ('(123 OR 456 OR 567)', ['(', 123, 'OR', 456, 'OR', 567, ')']),
  ('123 OR 456 OR 567', [123, 'OR', 456, 'OR', 567]),
  ('123 AND 456', [123, 'AND', 456]),
  ('(123 AND 456) OR (234 AND 567)', ['(', 123, 'AND', 456, ')', 'OR', '(', 234, 'AND', 567, ')']),
  ('((123 AND 456) AND (321 AND 654)) OR (234 AND 567)', ['(', '(', 123, 'AND', 456, ')', 'AND', '(', 321, 'AND', 654, ')', ')', 'OR', '(', 234, 'AND', 567, ')']),
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

def check_podmienka(text, tokens):
  p = Podmienka(text)
  try:
    assert tokens == p._tokens
  except AssertionError:
    print '{!r} == {!r}'.format(tokens, p._tokens)
    raise
  canonical_repr = text.replace('(', '( ').replace(')', ' )')
  serialized = p.serialize()
  try:
    assert canonical_repr == serialized
  except AssertionError:
    print '{!r} == {!r}'.format(canonical_repr, serialized)
    raise

def test_podmienka():
  for text, tokens in good_inputs:
    yield check_podmienka, text, tokens

def check_podmienka_exc(text):
  try:
    Podmienka(text)
    assert False
  except ValueError:
    pass

def test_podmienka_exc():
  for text in bad_inputs:
    yield check_podmienka_exc, text

if __name__ == "__main__":
  import nose
  nose.main()