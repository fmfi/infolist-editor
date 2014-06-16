#!/usr/bin/env python3
# -*- coding: ascii -*-
from __future__ import print_function
from itertools import takewhile
from io import BytesIO
import re
from copy import copy
from collections import deque
import sys
from six import u, Iterator, PY2, byte2int, unichr, int2byte


# https://docs.python.org/3/howto/pyporting.html#str-unicode
class UnicodeMixin(object):
    """Mixin class to handle defining the proper __str__/__unicode__
    methods in Python 2 or 3."""

    if sys.version_info[0] >= 3:  # Python 3
        def __str__(self):
            return self.__unicode__()
    else:  # Python 2
        def __str__(self):
            return self.__unicode__().encode('utf8')


class Error(Exception):
    pass


class ParseError(Error, UnicodeMixin):
    def __init__(self, position, description):
        self.position = position
        self.description = description

    def __unicode__(self):
        return u('Parse error at position {}: {}').format(self.position, self.description)


class PeekIter(Iterator):
    def __init__(self, iterable):
        self._iterator = iter(iterable)
        self._buf = deque()

    def __iter__(self):
        return self

    def __next__(self):
        if self._buf:
            return self._buf.popleft()
        return next(self._iterator)

    def peek(self, index=0):
        while len(self._buf) <= index:
            try:
                self._buf.append(next(self._iterator))
            except StopIteration:
                return None
        return self._buf[index]

    def has_next(self, index=0):
        while len(self._buf) <= index:
            try:
                self._buf.append(next(self._iterator))
            except StopIteration:
                return False
        return True


def ascii_as_bytes(s):
    if PY2:
        return s
    return s.decode('ascii')


def ascii_as_str(s):
    if PY2:
        return s
    return s.decode('ascii')


def number_as_bytes(num):
    return ascii_as_bytes(str(num))


class ByteStream(object):
    def __init__(self, file):
        if isinstance(file, bytes):
            file = BytesIO(file)
        self._file = file
        self._buf = b''
        self.pos = 0

    def _readbuf(self):
        if self.pos == len(self._buf):
            self._buf = self._file.read(1024)
            self.pos = 0

    def get(self):
        self._readbuf()
        if self.pos == len(self._buf):
            return b''
        ret = self._buf[self.pos:self.pos+1]
        self.pos += 1
        return ret

    def peek(self):
        self._readbuf()
        if self.pos == len(self._buf):
            return b''
        return self._buf[self.pos:self.pos+1]


class Token(object):
    def __init__(self, pos=None):
        self.pos = pos


class ControlWord(Token):
    def __init__(self, word, number=None, pos=None, trailing=None):
        super(ControlWord, self).__init__(pos=pos)
        self.word = word
        self.number = number
        if trailing is None:
            self.trailing = b''
        else:
            self.trailing = trailing

    def __bytes__(self):
        ret = b'\\' + self.word
        if self.number is not None:
            ret += number_as_bytes(self.number)
        ret += self.trailing
        return ret

    def __repr__(self):
        return 'ControlWord({!r}, number={!r}, trailing={!r}, pos={!r})'.format(self.word, self.number,
                                                                                self.trailing, self.pos)

    def __eq__(self, other):
        if not isinstance(other, ControlWord):
            return False
        return self.word == other.word and self.number == other.number

    def __ne__(self, other):
        return not self == other


class BinaryData(Token):
    def __init__(self, data, pos=None, trailing=None):
        self.data = data
        if trailing is None:
            self.trailing = b''
        else:
            self.trailing = trailing

    def __bytes__(self):
        ret = b'\\bin'
        ret += number_as_bytes(len(self.data))
        ret += self.trailing
        ret += self.data
        return ret

    def __eq__(self, other):
        if not isinstance(other, BinaryData):
            return False
        return self.data == other.data

    def __ne__(self, other):
        return not self == other


class ControlSymbol(Token):
    def __init__(self, symbol, pos=None):
        super(ControlSymbol, self).__init__(pos=pos)
        self.symbol = symbol

    def __bytes__(self):
        return b'\\' + self.symbol

    def __repr__(self):
        return 'ControlSymbol({!r}, pos={!r})'.format(self.symbol, self.pos)

    def __eq__(self, other):
        if not isinstance(other, ControlSymbol):
            return False
        return self.symbol == other.symbol

    def __ne__(self, other):
        return not self == other


class Separator(Token):
    def __init__(self, bytes, pos=None):
        super(Separator, self).__init__(pos=pos)
        self.bytes = bytes

    def __bytes__(self):
        return self.bytes

    def __repr__(self):
        return 'Separator({!r}, pos={!r})'.format(self.bytes, self.pos)

    def __eq__(self, other):
        return isinstance(other, Separator)

    def __ne__(self, other):
        return not self == other


class Char(Token):
    def __init__(self, ordinal, pos=None):
        super(Char, self).__init__(pos=pos)
        self.ordinal = ordinal

    def __repr__(self):
        return '{}({!r}, pos={!r})'.format(self.__class__.__name__, self.ordinal, self.pos)


class RawChar(Char):
    def __bytes__(self):
        return int2byte(self.ordinal)


class ANSIEscapedChar(Char):
    def __bytes__(self):
        return b'\\\'' + ascii_as_bytes(hex(self.ordinal)[2:].zfill(2))


class GroupBoundary(Token):
    def __init__(self, opening=True, pos=None):
        super(GroupBoundary, self).__init__(pos=pos)
        self.opening = opening

    def __bytes__(self):
        if self.opening:
            return b'{'
        else:
            return b'}'

    def __eq__(self, other):
        return isinstance(other, GroupBoundary) and self.opening == other.opening

    def __ne__(self, other):
        return not (self == other)


def tokenize(bs):
    if not isinstance(bs, ByteStream):
        bs = ByteStream(bs)
    while True:
        b = bs.peek()
        loop_pos = bs.pos
        if b == b'':
            return
        elif b == b'{':
            bs.get()
            yield GroupBoundary(opening=True, pos=loop_pos)
        elif b == b'}':
            bs.get()
            yield GroupBoundary(opening=False, pos=loop_pos)
        elif b == b'\\':
            bs.get()
            if b'a' <= bs.peek() <= b'z' or b'A' <= bs.peek() <= b'Z':
                # control word
                num = 0
                word = b''
                trailing = b''
                while b'a' <= bs.peek() <= b'z' or b'A' <= bs.peek() <= b'Z':
                    word += bs.get()
                    num += 1
                    if num > 32:
                        raise ParseError(bs.pos, 'Too long control word')
                number = None
                if bs.peek() == b' ':
                    trailing = bs.get()
                elif b'0' <= bs.peek() <= b'9' or bs.peek() == b'-':
                    number = bs.get()
                    while b'0' <= bs.peek() <= b'9':
                        number += bs.get()
                    if bs.peek() == b' ':
                        trailing = bs.get()
                    number = int(ascii_as_str(number))
                if word == b'bin':
                    if number < 0:
                        raise ParseError(loop_pos, 'Negative \\bin')
                    skip = number
                    data = b''
                    while skip > 0:
                        data += bs.get()
                    yield BinaryData(data, pos=loop_pos, trailing=trailing)
                else:
                    yield ControlWord(word, number=number, pos=loop_pos, trailing=trailing)
            elif bs.peek() == b'\'':
                bs.get()
                ordval = int(bs.get() + bs.get(), 16)
                yield ANSIEscapedChar(ordval)
            else:
                yield ControlSymbol(bs.get(), pos=loop_pos)
        elif b == b'\r' or b == b'\n':
            sep = bs.get()
            if (b == b'\r' and bs.peek() == b'\n') or (b == b'\n' and bs.peek() == b'\r'):
                sep += bs.get()
            yield Separator(sep, pos=loop_pos)
        else:
            yield RawChar(byte2int(bs.get()), pos=loop_pos)


class Node(object):
    def __init__(self, parent=None):
        self.parent = parent

    def walk(self):
        yield self


class Text(Node):
    def __init__(self, text, tokens=None, parent=None):
        super(Text, self).__init__(parent=parent)
        self.tokens = tokens
        self._text = text

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, text):
        if text != self._text:
            self._text = text
            self.tokens = None

    def append(self, text, tokens):
        self._text += text
        self.tokens.extend(tokens)

    def __repr__(self):
        return 'Text({!r}, tokens={!r})'.format(self._text, self.tokens)

    def __eq__(self, other):
        return self.text == other.text

    def __ne__(self, other):
        return self.text != other.text


RTF_DESTINATIONS = {
    b'aftncn', b'aftnsep', b'aftnsepc', b'annotation', b'atnauthor', b'atndate',
    b'atnicn', b'atnid', b'atnparent', b'atnref', b'atntime', b'atrfend',
    b'atrfstart', b'author', b'background', b'bkmkend', b'bkmkstart', b'blipuid',
    b'buptim', b'category', b'colorschememapping', b'colortbl', b'comment',
    b'company', b'creatim', b'datafield', b'datastore', b'defchp', b'defpap', b'do',
    b'doccomm', b'docvar', b'dptxbxtext', b'ebcend', b'ebcstart', b'factoidname',
    b'falt', b'fchars', b'ffdeftext', b'ffentrymcr', b'ffexitmcr', b'ffformat',
    b'ffhelptext', b'ffl', b'ffname', b'ffstattext', b'field', b'file', b'filetbl',
    b'fldinst', b'fldrslt', b'fname', b'fontemb', b'fontfile', b'fonttbl',
    b'footer', b'footerf', b'footerl', b'footerr', b'footnote', b'formfield',
    b'ftncn', b'ftnsep', b'ftnsepc', b'g', b'generator', b'gridtbl', b'header',
    b'headerf', b'headerl', b'headerr', b'hl', b'hlfr', b'hlinkbase', b'hlloc',
    b'hlsrc', b'hsv', b'htmltag', b'info', b'keycode', b'keywords', b'latentstyles',
    b'lchars', b'levelnumbers', b'leveltext', b'lfolevel', b'linkval', b'list',
    b'listlevel', b'listname', b'listoverride', b'listoverridetable',
    b'listpicture', b'liststylename', b'listtable', b'listtext', b'lsdlockedexcept',
    b'manager', b'mhtmltag', b'mmaddfieldname', b'mmconnectstr',
    b'mmconnectstrdata', b'mmdatasource', b'mmheadersource', b'mmmailsubject',
    b'mmodso', b'mmodsofilter', b'mmodsofldmpdata', b'mmodsosort', b'mmodsosrc ',
    b'mmodsotable', b'mmodsoudl', b'mmodsoudldata 200', b'mmquery', b'mvfmf',
    b'mvfml', b'mvtof', b'mvtol', b'nesttableprops', b'nextfile', b'nonesttables',
    b'objalias', b'objclass', b'objdata', b'object', b'objname', b'objsect',
    b'objtime', b'oldcprops', b'oldpprops', b'oldsprops', b'oldtprops', b'oleclsid',
    b'operator', b'panose', b'password', b'passwordhash', b'pgp', b'pgptbl',
    b'picprop', b'pict', b'pn', b'pntext', b'pntxta', b'pntxtb', b'printim',
    b'private', b'propname', b'protend', b'protstart', b'protusertbl', b'pxe',
    b'result', b'revtbl', b'revtim', b'rsidtbl', b'rtf', b'rxe', b'shp', b'shpgrp',
    b'shpinst', b'shppict', b'shprslt', b'shptxt', b'sn', b'sp', b'staticval',
    b'stylesheet', b'subject', b'sv', b'svb', b'tc', b'template', b'themedata',
    b'title', b'txe', b'ud', b'upr', b'userprops', b'wgrffmtfilter',
    b'windowcaption', b'writereservation', b'writereservhash', b'xe', b'xform',
    b'xmlattrname', b'xmlattrvalue', b'xmlclose', b'xmlname', b'xmlnstbl',
    b'xmlopen', b'macc', b'maccPr', b'mailmerge', b'maln', b'malnScr', b'margPr',
    b'mbar', b'mbarPr', b'mbaseJc', b'mbegChr', b'mborderBox', b'mborderBoxPr',
    b'mbox', b'mboxPr', b'mchr', b'mcount', b'mctrlPr', b'md', b'mdeg', b'mdegHide',
    b'mden', b'mdiff', b'mdPr', b'me 2', b'mendChr', b'meqArr', b'meqArrPr', b'mf',
    b'mfName', b'mfPr', b'mfunc', b'mfuncPr', b'mgroupChr', b'mgroupChrPr',
    b'mgrow', b'mhideBot', b'mhideLeft', b'mhideRight', b'mhideTop', b'mlim',
    b'mlimloc', b'mlimlow', b'mlimlowPr', b'mlimupp', b'mlimuppPr', b'mm', b'mmath',
    b'mmathPict', b'mmathPr', b'mmaxdist', b'mmc', b'mmcJc', b'mmcPr', b'mmcs',
    b'mmodsoname', b'mmodsorecipdata', b'mmodsouniquetag', b'mmPr', b'mmr',
    b'mnary', b'mnaryPr', b'mnoBreak', b'mnum', b'mobjDist', b'moMath',
    b'moMathPara', b'moMathParaPr', b'mopEmu', b'mphant', b'mphantPr', b'mplcHide',
    b'mpos', b'mr', b'mrad', b'mradPr', b'mrPr', b'msepChr', b'mshow', b'mshp',
    b'msPre', b'msPrePr', b'msSub', b'msSubPr', b'msSubSup', b'msSubSupPr',
    b'msSup', b'msSupPr', b'mstrikeBLTR', b'mstrikeH', b'mstrikeTLBR', b'mstrikeV',
    b'msub', b'msubHide', b'msup', b'msupHide', b'mtransp', b'mtype', b'mvertJc',
    b'mzeroAsc', b'mzeroDesc', b'mzeroWid', b'mmodsomappedname', b'fldtype',
    b'pnseclvl',
}


class Group(Node):
    def __init__(self, content=None, pos=None, parent=None):
        super(Group, self).__init__(parent=parent)
        if content is None:
            self.content = []
        else:
            self.content = content
        self.pos = pos

    def __bytes__(self):
        return b'{' + b''.join(x.__bytes__() for x in self.content) + b'}'

    def walk(self):
        yield self
        for child in self.content:
            for node in child.walk():
                yield node

    def append(self, node):
        if node.parent is not None:
            raise ValueError('A node can only be inserted once')
        node.parent = self
        self.content.append(node)

    @property
    def destination(self):
        invisible = False
        destination = None
        if len(self.content) == 0:
            return destination, invisible
        pos = 0
        if (isinstance(self.content[0], TokenNode) and isinstance(self.content[0].token, ControlSymbol) and
                self.content[0].token.symbol == b'*'):
            invisible = True
            pos += 1
        if len(self.content) <= pos:
            return destination, invisible
        if (isinstance(self.content[pos], TokenNode) and isinstance(self.content[pos].token, ControlWord) and
                self.content[pos].token.word in RTF_DESTINATIONS):
            destination = self.content[pos]
        return destination, invisible

    def __eq__(self, other):
        return self.content == other.content

    def __ne__(self, other):
        return self.content != other.content

    def __repr__(self):
        return '<Group {!r}>'.format(self.content)


class TokenNode(Node):
    def __init__(self, token, parent=None):
        super(TokenNode, self).__init__(parent=parent)
        self.token = token

    def __repr__(self):
        return 'TokenNode({!r})'.format(self.token)

    def __eq__(self, other):
        return isinstance(other, TokenNode) and self.token == other.token

    def __ne__(self, other):
        return not isinstance(other, TokenNode) or self.token != other.token


class Scope(object):
    def __init__(self, group):
        self.group = group
        self.unicode_skip = 1


RTF_ENCODINGS = {
    10000: 'mac_roman',
    10001: 'mac_japan',
    10005: 'mac_greek',
    10007: 'mac_cyrillic',
    10029: 'mac_latin2',
    10081: 'mac_turkish'
}


class Document(Node):
    def __init__(self, root, trailing=None):
        super(Document, self).__init__(parent=None)
        self.root = root
        self.trailing = trailing

    def walk(self):
        return self.root.walk()

    def __eq__(self, other):
        return self.root == other.root

    def __ne__(self, other):
        return self.root != other.root

    def __repr__(self):
        return 'Document({!r}, trailing={!r})'.format(self.root, self.trailing)


def parse(tokens, encoding=None):
    tokens = PeekIter(tokens)
    effective = type("", (), {})()  # http://stackoverflow.com/a/7935984
    effective.encoding = 'ascii' if encoding is None else encoding

    def set_encoding(name):
        if encoding is None:
            effective.encoding = name

    open_brace = next(tokens)
    if open_brace != GroupBoundary(opening=True):
        raise ParseError(open_brace.pos, 'Expecting {')
    root = Group(pos=open_brace.pos)

    stack = [Scope(root)]

    def combine_text(text, tokens):
        if stack[-1].group.content and isinstance(stack[-1].group.content[-1], Text):
            text_node = stack[-1].group.content[-1]
        else:
            text_node = Text('', [])
            stack[-1].group.append(text_node)
        text_node.append(text, tokens)

    for token in tokens:
        if token == GroupBoundary(opening=True):
            new_scope = copy(stack[-1])
            new_scope.group = Group(pos=token.pos)
            stack[-1].group.append(new_scope.group)
            stack.append(new_scope)
        elif token == GroupBoundary(opening=False):
            stack.pop()
            if len(stack) == 0:
                break
        elif isinstance(token, Char):
            try:
                decoded_text = unichr(token.ordinal)
            except UnicodeDecodeError:
                stack[-1].group.append(TokenNode(token))
            else:
                combine_text(decoded_text, [token])
        elif isinstance(token, ControlWord):
            if token.word == b'u':  # unicode text
                ordinal = token.number
                if ordinal < 0:
                    ordinal += 65536
                skipped_tokens = [token]
                for i in range(stack[-1].unicode_skip):
                    to_skip = tokens.peek()
                    if isinstance(to_skip, GroupBoundary):
                        break
                    skipped_tokens.append(next(tokens))
                combine_text(unichr(ordinal), skipped_tokens)
                continue
            elif token.word == b'uc':
                if token.number is None:
                    raise ParseError(token.pos, '\\uc requires argument')
                stack[-1].unicode_skip = token.number
            elif token.word == b'ansi':
                set_encoding('ascii')
            elif token.word == b'pc':
                set_encoding('cp437')
            elif token.word == b'pca':
                set_encoding('cp850')
            elif token.word == b'ansicpg':
                if token.number in RTF_ENCODINGS:
                    set_encoding(RTF_ENCODINGS[token.number])
                else:
                    set_encoding('cp{}'.format(token.number))
            stack[-1].group.append(TokenNode(token))
        elif isinstance(token, ControlSymbol):
            if token.symbol == b'~':
                combine_text('\u00a0', [token])
            elif token.symbol == b'-':
                combine_text('\u00ad', [token])
            elif token.symbol == b'_':
                combine_text('\u2011', [token])
            else:
                stack[-1].group.append(TokenNode(token))
        else:
            stack[-1].group.append(TokenNode(token))

    trailing = []
    for token in tokens:
        if isinstance(token, Separator):
            trailing.append(token)
            continue
        raise ParseError(token.pos, 'Unexpected trailing token {!r}'.format(token))

    return Document(root, trailing=trailing)


def escape_text_tokens(text, encoding=None):
    prevc = None
    for c in text:
        if (c == '\n' and prevc != '\r') or (c == '\r' and prevc != '\n'):
            yield ControlWord(b'line')
        elif (c == '\n' and prevc == '\r') or (c == '\r' and prevc == '\n'):
            pass
        elif c in '\\{}':
            yield ControlSymbol(ascii_as_bytes(c))
        elif c == u('\u00a0'): # non-breaking space
            yield ControlSymbol(b'~')
        elif c == u('\u00ad'): # soft hyphen
            yield ControlSymbol(b'-')
        elif c == u('\u2011'): # non-breaking hyphen
            yield ControlSymbol(b'_')
        elif c in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 :;@/()_-?.,"\'=&%+[]*':
            yield RawChar(c.encode('ascii'))
        else:
            encoded = False
            if encoding:
                try:
                    yield ANSIEscapedChar(c.encode(encoding)[0])
                    encoded = True
                except UnicodeEncodeError:
                    pass
            if not encoded:
                ordinal = ord(c)
                if ordinal > 32768:
                    ordinal -= 65536
                yield ControlWord(b'u', number=ordinal)
                yield RawChar(b'?')
        prevc = c


def escape_text(text, encoding=None):
    return b''.join(bytes(x) for x in escape_text_tokens(text, encoding=encoding))


def flatten(*nodes, **kwargs):
    encoding = kwargs.get('encoding', None)
    for node in nodes:
        if isinstance(node, Group):
            yield GroupBoundary(opening=True)
            for child in node.content:
                for token in flatten(child):
                    yield token
            yield GroupBoundary(opening=False)
        elif isinstance(node, TokenNode):
            yield node.token
        elif isinstance(node, Text):
            tokens = node.tokens
            if tokens is None:
                tokens = escape_text_tokens(node.text, encoding=encoding)
            for token in tokens:
                yield token
        elif isinstance(node, Document):
            for token in flatten(node.root):
                yield token
            if node.trailing:
                for token in node.trailing:
                    yield token


def find_text(root, text):
    for node in root.walk():
        if isinstance(node, Text):
            if text in node.text:
                yield node


def find_re(root, pattern):
    if isinstance(pattern, str):
        pattern = re.compile(pattern)
    for node in root.walk():
        if isinstance(node, Text):
            m = pattern.match(node.text)
            if m:
                yield node, m


def dfs_rtl(node, include_root=True):
    if include_root:
        yield node
    if isinstance(node, Group):
        for child in reversed(node.content):
            for child_node in dfs_rtl(child, include_root=True):
                yield child_node


def dfs_ltr(node, include_root=True):
    if include_root:
        yield node
    if isinstance(node, Group):
        for child in node.content:
            for child_node in dfs_ltr(child, include_root=True):
                yield child_node


def walk_left(node):
    """Generates nodes towards beginning of the document, starting before node"""
    if node.parent is None or not isinstance(node.parent, Group):
        return

    # Find the current node's position
    for index, index_node in enumerate(node.parent.content):
        if index_node is node:
            current_index = index
            break
    else:
        raise AssertionError('A node was not found within its parent')

    current_index -= 1
    while current_index >= 0:
        for other_node in dfs_rtl(node.parent.content[current_index]):
            yield other_node
        current_index -= 1

    yield node.parent

    for other_node in walk_left(node.parent):
        yield other_node


def walk_right(node):
    """Generates nodes towards end of the document, starting after node"""
    if node.parent is None or not isinstance(node.parent, Group):
        return

    # Find the current node's position
    for index, index_node in enumerate(node.parent.content):
        if index_node is node:
            current_index = index
            break
    else:
        raise AssertionError('A node was not found within its parent')

    current_index += 1
    while current_index < len(node.parent.content):
        for other_node in dfs_ltr(node.parent.content[current_index]):
            yield other_node
        current_index += 1

    yield node.parent

    for other_node in walk_right(node.parent):
        yield other_node

_not_specified = object()


def match_control_word(name, number=_not_specified):
    def matcher(node):
        if not isinstance(node, TokenNode):
            return False
        if not isinstance(node.token, ControlWord):
            return False
        if node.token.word != name:
            return False
        if number is not _not_specified:
            if number != node.token.number:
                return False
        return True
    return matcher


def filter_control_word(nodes, *args, **kwargs):
    return filter(match_control_word(*args, **kwargs), nodes)


def node_range(start_node, end_node):
    for node in walk_right(start_node):
        if node is end_node:
            return
        yield node


def as_text(nodes):
    ret = ''
    for node in nodes:
        if isinstance(node, Text):
            ret += node.text
        elif isinstance(node, Group):
            ret += as_text(node.content)
    return ret


def document_content(node):
    if isinstance(node, Group):
        destination, invisible = node.destination
        if destination is not None:
            if destination.token.word in (b'colortbl', b'fonttbl', b'stylesheet', b'themedata',
                                          b'header', b'headerl', b'headerr', b'headerf',
                                          b'footer', b'footerl', b'footerr', b'footerf',
                                          b'footnote', b'info', b'mmathPr'):
                return
            if invisible:
                return
        for child in node.content:
            for child_node in document_content(child):
                yield child_node
    else:
        yield node


def split_by(nodes, matcher):
    nodes = PeekIter(nodes)
    while nodes.has_next():
        yield takewhile(lambda x: not matcher(x), nodes)


def split_end_by(nodes, matcher):
    item = []
    for node in nodes:
        if matcher(node):
            yield item
            item = []
        else:
            item.append(node)


if __name__ == '__main__':
    import sys
    import argparse

    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    bs = ByteStream(sys.stdin.buffer)
    try:
        for token in flatten(parse(tokenize(bs), encoding='cp1250')):
            sys.stdout.buffer.write(bytes(token))
    except:
        sys.stderr.write('Current position: {}\n'.format(bs.pos))
        raise