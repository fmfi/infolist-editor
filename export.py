# -*- coding: utf-8 -*-
from utils import escape_rtf
from StringIO import StringIO
from contextlib import closing
from rtfng.Elements import Document, Section
from rtfng.document.paragraph import Cell, Paragraph, Table
from rtfng.PropertySets import BorderPropertySet, FramePropertySet, ParagraphPropertySet, TabPropertySet
from markupsafe import soft_unicode
from utils import format_datetime
from flask import send_from_directory
from flask import g, url_for, Response
import zipfile
import os.path

class ZipBuffer(object):
    """ A file-like object for zipfile.ZipFile to write into. http://stackoverflow.com/a/9829044"""

    def __init__(self):
        self.data = []
        self.pos = 0

    def write(self, data):
        self.data.append(data)
        self.pos += len(data)

    def tell(self):
        # zipfile calls this so we need it
        return self.pos

    def flush(self):
        # zipfile calls this so we need it
        pass

    def get_and_clear(self):
        result = self.data
        self.data = []
        return result

class Priloha(object):
  def __init__(self, nazov, **kwargs):
    self.nazov = nazov
    self.url_aktualizacie = None
    self.modifikovane = None
  
  def render(self, to_file, **kwargs):
    pass
  
  def send(self, **kwargs):
    with closing(StringIO()) as f:
      self.render(f, **kwargs)
      response = Response(f.getvalue(), mimetype=self.mimetype)
      response.headers['Content-Disposition'] = 'attachment; filename={}'.format(self.nazov)
      return response
  
  @property
  def mimetype(self):
    if self.nazov.endswith('.rtf'):
      return 'application/rtf'
    return 'application/octet-stream'

class PrilohaZoznam(Priloha):
  def render(self, to_file, prilohy, **kwargs):
    doc = Document()
    section = Section()
    doc.Sections.append(section)
    styles = doc.StyleSheet
    
    p = Paragraph(styles.ParagraphStyles.Heading1)
    p.append(u'Zoznam príloh')
    section.append(p)
    
    for typ_prilohy, subory in prilohy:
      if not subory:
        continue
      
      p = Paragraph(styles.ParagraphStyles.Heading2)
      p.append(typ_prilohy.nazov)
      section.append(p)
    
      table = Table(TabPropertySet.DEFAULT_WIDTH * 7, TabPropertySet.DEFAULT_WIDTH * 3)
      table.AddRow(Cell(Paragraph(u'Príloha', styles.ParagraphStyles.Normal)), Cell(Paragraph(u'Dátum modifikácie', styles.ParagraphStyles.Normal)))
      for subor in subory:
        table.AddRow(Cell(Paragraph(subor.nazov, styles.ParagraphStyles.Normal)), Cell(Paragraph(format_datetime(subor.modifikovane, iba_datum=True), styles.ParagraphStyles.Normal)))
      section.append(table)
    
    doc.write(to_file)

class PrilohaSubor(Priloha):
  def __init__(self, id, posledna_verzia, sha256, modifikoval, modifikovane, predosla_verzia, studprog_id, **kwargs):
    super(PrilohaSubor, self).__init__(**kwargs)
    self.id = id
    self.posledna_verzia = posledna_verzia
    self.sha256 = sha256
    self.modifikoval = modifikoval
    self.modifikovane = modifikovane
    self.predosla_verzia = predosla_verzia
    self.url_aktualizacie = url_for('studijny_program_prilohy_upload', studprog_id=studprog_id, subor_id=id)
  
  def render(self, to_file, config, studprog, **kwargs):
    with open(os.path.join(config.files_dir, self.sha256)) as fin:
      buffer_size = 262144 
      data = fin.read(buffer_size)
      while data != '':
        to_file.write(data)
        data = fin.read(buffer_size)
  
  def send(self, config, studprog, **kwargs):
    return send_from_directory(config.files_dir, self.sha256, as_attachment=True,
      attachment_filename=self.nazov)

class TypPrilohySP(object):
  def __init__(self, id, nazov, kriterium):
    self.id = id
    self.nazov = nazov
    self.kriterium = kriterium

class Prilohy(object):
  def __init__(self):
    self.typy = {}
    self.podla_nazvu = {}
    self.podla_typu = {}
    
  def add_typ(self, typ):
    self.typy[typ.id] = typ
    self.podla_typu[typ.id] = []
  
  def add(self, typ, priloha):
    self.podla_typu[typ].append(priloha)
    self.podla_nazvu[priloha.nazov] = priloha
  
  def __iter__(self):
    for typ in self.typy:
      yield self.typy[typ], self.podla_typu[typ]
  
  def send_zip(self, **context):
    def entries():
      output_entries = set()
      for typ, subory in self:
        for subor in subory:
          if subor.nazov in output_entries:
            continue
          output_entries.add(subor.nazov)
          with closing(StringIO()) as f:
            subor.render(f, **context)
            yield subor.nazov, f.getvalue()
    return stream_zip(entries(), 'vsetky.zip')

def stream_zip(entries, filename):
  """inspired by http://stackoverflow.com/a/9829044"""
  def chunks():
    sink = ZipBuffer()
    archive = zipfile.ZipFile(sink, "w")
    for entry, data in entries:
        archive.writestr(entry, data)
        for chunk in sink.get_and_clear():
            yield chunk

    archive.close()
    # close() generates some more data, so we yield that too
    for chunk in sink.get_and_clear():
        yield chunk
  
  response = Response(chunks(), mimetype='application/zip')
  response.headers['Content-Disposition'] = 'attachment; filename={}'.format(filename)
  return response

def prilohy_pre_studijny_program(sp_id):
  prilohy = Prilohy()
  for row in g.db.load_typy_priloh():
    prilohy.add_typ(TypPrilohySP(row.id, row.nazov, row.kriterium))
  
  for typ, subory in g.db.load_studprog_prilohy_subory(sp_id).iteritems():
    for subor in subory:
      prilohy.add(typ, subor)
  
  prilohy.add(12, PrilohaZoznam('zoznam-priloh.rtf'))
  
  return prilohy