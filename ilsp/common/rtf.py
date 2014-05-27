from markupsafe import soft_unicode
import colander
import re


def escape_rtf(val):
  if val == colander.null or val == None:
    val = u''
  val = soft_unicode(val)
  r = ''
  prevc = None
  for c in val:
    if (c == '\n' and prevc != '\r') or (c == '\r' and prevc != '\n'):
      r += '\line '
    elif (c == '\n' and prevc == '\r') or (c == '\r' and prevc == '\n'):
      pass
    elif c in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ':
      r += c
    else:
      r += '\u{}?'.format(ord(c))
    prevc = c
  return r


def render_rtf(rtf_template, substitutions):
  replacements = []
  for key, value in substitutions.iteritems():
    replacements.append((key, escape_rtf(value)))
  return multiple_replace(rtf_template, *replacements)

# http://stackoverflow.com/a/15221068
def multiple_replacer(*key_values):
    replace_dict = dict(key_values)
    replacement_function = lambda match: replace_dict[match.group(0)]
    pattern = re.compile("|".join([re.escape(k) for k, v in key_values]), re.M)
    return lambda string: pattern.sub(replacement_function, string)


def multiple_replace(string, *key_values):
    return multiple_replacer(*key_values)(string)

# end http://stackoverflow.com/a/15221068


class RTFHyperlink():
  def __init__(self, target, content):
    self.target = target
    self.content = content


class RTFBookmark():
  def  __init__(self, name):
    self.name = name

  def to_rtf(self):
    ret = ''
    ret += r'{\*\bkmkstart '
    ret += self.name
    ret += r'}{\*\bkmkend '
    ret += self.name
    ret += '}'
    return ret


def my_rtf_elements(renderer, element):
  if isinstance(element, RTFHyperlink):
    renderer._write(r'{\field{\*\fldinst HYPERLINK \\l "')
    renderer._write(element.target)
    renderer._write(r'" }{\fldrslt \plain \ul ')
    renderer.writeUnicodeElement(element.content)
    renderer._write('}}')
  elif isinstance(element, RTFBookmark):
    renderer._write(element.to_rtf())
  else:
    raise TypeError()