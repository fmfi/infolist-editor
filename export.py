# -*- coding: utf-8 -*-
from decimal import ROUND_HALF_EVEN, Decimal
from itertools import groupby
from utils import escape_rtf, filter_fakulta, filter_druh_cinnosti, filter_obdobie, filter_metoda_vyucby, \
  filter_literatura, filter_jazyk_vyucby, filter_typ_vyucujuceho, render_rtf
from StringIO import StringIO
from contextlib import closing
from rtfng.Elements import Document, Section
from rtfng.document.paragraph import Cell, Paragraph, Table
from rtfng.document.character import B
from rtfng.PropertySets import BorderPropertySet, FramePropertySet, ParagraphPropertySet, TabPropertySet
from markupsafe import soft_unicode
from utils import format_datetime
from flask import send_from_directory
from flask import g, url_for, Response
import zipfile
import os.path
from werkzeug.utils import secure_filename
from pkg_resources import resource_string


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
  def __init__(self, nazov=None, filename=None, **kwargs):
    self.nazov = nazov
    self.url_aktualizacie = None
    self.modifikovane = None
    self._filename = filename
  
  def render(self, to_file, **kwargs):
    pass
  
  def send(self, **kwargs):
    with closing(StringIO()) as f:
      self.render(f, **kwargs)
      response = Response(f.getvalue(), mimetype=self.mimetype)
      response.headers['Content-Disposition'] = 'attachment; filename={}'.format(self.filename)
      return response
  
  @property
  def mimetype(self):
    if self.nazov.endswith('.rtf'):
      return 'application/rtf'
    return 'application/octet-stream'

  @property
  def filename(self):
    print self._filename
    return self._filename

class PrilohaZoznam(Priloha):
  def render(self, to_file, prilohy, **kwargs):
    doc = Document()
    section = Section()
    doc.Sections.append(section)
    styles = doc.StyleSheet
    
    p = Paragraph(styles.ParagraphStyles.Heading1)
    p.append(u'Zoznam príloh')
    section.append(p)
    
    def th(content):
      return Cell(Paragraph(content, styles.ParagraphStyles.Normal))
    
    def td(content):
      return Cell(Paragraph(content, styles.ParagraphStyles.Normal))
    
    for typ_prilohy, subory in prilohy:
      if not subory or typ_prilohy.id == 0:
        continue
      
      p = Paragraph(styles.ParagraphStyles.Heading2)
      p.append(typ_prilohy.nazov)
      section.append(p)
    
      table = Table(TabPropertySet.DEFAULT_WIDTH * 7, TabPropertySet.DEFAULT_WIDTH * 3)
      table.AddRow(th(u'Príloha'), th(u'Dátum modifikácie'))
      for subor in subory:
        table.AddRow(td(subor.nazov), td(format_datetime(subor.modifikovane, iba_datum=True)))
      section.append(table)
    
    doc.write(to_file)

class PrilohaSubor(Priloha):
  def __init__(self, id, posledna_verzia, sha256, modifikoval, modifikovane, predosla_verzia, studprog_id, mimetype,
               **kwargs):
    super(PrilohaSubor, self).__init__(**kwargs)
    self.id = id
    self.posledna_verzia = posledna_verzia
    self.sha256 = sha256
    self.modifikoval = modifikoval
    self.modifikovane = modifikovane
    self.predosla_verzia = predosla_verzia
    self.url_aktualizacie = url_for('studijny_program_prilohy_upload', studprog_id=studprog_id, subor_id=id)
    self._mimetype = mimetype
  
  def render(self, to_file, config, studprog, **kwargs):
    with open(os.path.join(config.files_dir, self.sha256)) as fin:
      buffer_size = 262144 
      data = fin.read(buffer_size)
      while data != '':
        to_file.write(data)
        data = fin.read(buffer_size)
  
  def send(self, config, studprog, **kwargs):
    return send_from_directory(config.files_dir, self.sha256, as_attachment=True,
      attachment_filename=secure_filename(self.filename))

  @property
  def mimetype(self):
    if self._mimetype:
      return self._mimetype
    return super(PrilohaSubor, self).mimetype

class PrilohaInfolist(Priloha):
  def __init__(self, infolist_id, **kwargs):
    super(PrilohaInfolist, self).__init__(**kwargs)
    self.infolist_id = infolist_id
    self._data = None

  def load(self):
    if self._data is None:
      self._data = g.db.load_infolist(self.infolist_id)
    return self._data

  def render(self, to_file, **kwargs):
    infolist = self.load()

    tdata = {}
    tdata['IL_NAZOV_SKOLY'] = u'Univerzita Komenského v Bratislave'
    tdata['IL_NAZOV_FAKULTY'] = filter_fakulta(infolist['fakulta'])
    tdata['IL_KOD_PREDMETU'] = infolist['skratka']
    tdata['IL_NAZOV_PREDMETU'] = infolist['nazov_predmetu']

    cinnosti = u''
    for cinn in infolist['cinnosti']:
      cinnosti += u'\n{}, {}h/{}, {}'.format(
        filter_druh_cinnosti(cinn['druh_cinnosti']),
        cinn['pocet_hodin'],
        filter_obdobie(cinn['za_obdobie']),
        filter_metoda_vyucby(cinn['metoda_vyucby'])
      )
    tdata['IL_CINNOSTI'] = cinnosti

    tdata['IL_POCET_KREDITOV'] = infolist['pocet_kreditov']

    sem2text = {
      'L': u'letný',
      'Z': u'zimný',
    }
    odp_group = []
    for k, grp in groupby(infolist['odporucane_semestre'], lambda x: (x['rocnik'], x['semester'])):
      odp_group.append((k, list(grp)))
    odp_sem = u''
    if len(odp_group) > 1:
      odp_sem += u'\n'
    for i, ((rocnik, semester), odp) in enumerate(odp_group):
      if i > 0:
        odp_sem += u'\n'
      if semester == 'N' and rocnik is None:
        odp_sem += u'neurčený'
      else:
        if rocnik is not None:
          odp_sem += u'{}. ročník'.format(rocnik)
        if rocnik is not None and semester != 'N':
          odp_sem += u', '
        if semester != 'N':
          odp_sem += u'{} semester'.format(
            sem2text[semester] if semester in sem2text else semester or '?')
      if len(odp_group) > 1:
        odp_sem += u' ({})'.format(u', '.join(u'{} {}'.format(x['studprog_skratka'], x['studprog_nazov']) for x in odp))

    tdata['IL_ODPORUCANY_SEMESTER'] = odp_sem


    stup_group = []
    for k, grp in groupby(infolist['odporucane_semestre'], lambda x: x['stupen_studia']):
      stup_group.append((k, list(grp)))
    stup_stud = u''
    if len(stup_group) > 1:
      stup_stud += u'\n'
    for i, (stupen, group) in enumerate(stup_group):
      if i > 0:
        stup_stud += u'\n'
      stup_stud += stupen
      if len(stup_group) > 1:
        stup_stud += u' ({})'.format(u', '.join(u'{} {}'.format(x['studprog_skratka'], x['studprog_nazov']) for x in group))
    tdata['IL_STUPEN_STUDIA'] = stup_stud

    podm_predmety = unicode(infolist['podmienujuce_predmety'])
    if infolist['odporucane_predmety']:
      podm_predmety += u'\n\nOdporúčané predmety (nie je nutné ich absolvovať pred zapísaním predmetu):\n'
      podm_predmety += unicode(infolist['odporucane_predmety'])
    tdata['IL_PODMIENUJUCE_PREDMETY'] = podm_predmety

    podm_absol_text = u'\n'
    podm_absol = infolist['podm_absolvovania']
    if podm_absol['nahrada']:
      podm_absol_text = podm_absol['nahrada']
    else:
      if podm_absol['priebezne']:
        podm_absol_text += u'Priebežné hodnotenie: {}\n'.format(podm_absol['priebezne'])
      if podm_absol['percenta_zapocet'] != None:
        podm_absol_text += u'Na pripustenie ku skúške je potrebných aspoň {}% bodov z priebežného hodnotenia.\n'.format(podm_absol['percenta_zapocet'])
      if podm_absol['skuska']:
        podm_absol_text += u'Skúška: {}\n'.format(podm_absol['skuska'])
      if podm_absol['percenta_skuska'] != None:
        podm_absol_text += u'Váha skúšky v hodnotení: {}%\n'.format(podm_absol['percenta_skuska'])
      if any(podm_absol['percenta_na'].values()) and not podm_absol['nepouzivat_stupnicu']:
        stupnica = podm_absol['percenta_na']
        podm_absol_text += u'Na získanie hodnotenia A je potrebné získať najmenej {}% bodov'.format(stupnica['A'])
        for znamka in ['B', 'C', 'D', 'E']:
          podm_absol_text += u' a ' if znamka == 'E' else u', '
          podm_absol_text += u'na hodnotenie {} najmenej {}% bodov'.format(znamka, stupnica[znamka])
        podm_absol_text += u'.\n'
    podm_absol_text = podm_absol_text.rstrip()

    tdata['IL_PODMIENKY_ABSOLVOVANIA'] = podm_absol_text

    tdata['IL_VYSLEDKY_VZDELAVANIA'] = infolist['vysledky_vzdelavania']
    tdata['IL_STRUCNA_OSNOVA'] = infolist['strucna_osnova']

    literatura = u''
    for bib_id in infolist['odporucana_literatura']['zoznam']:
      lit = filter_literatura(bib_id)
      literatura += u'\n{}. {}'.format(lit.dokument, lit.vyd_udaje)
    for popis in infolist['odporucana_literatura']['nove']:
      literatura += u'\n{}'.format(popis)
    tdata['IL_LITERATURA'] = literatura

    tdata['IL_POTREBNY_JAZYK'] = filter_jazyk_vyucby(infolist['potrebny_jazyk'])
    tdata['IL_POZNAMKY'] = u''

    mame_hodnotenia = True
    hodn = infolist['hodnotenia_pocet']
    for znamka in hodn:
      if hodn[znamka] == None:
        mame_hodnotenia = False
        break
    if mame_hodnotenia:
      celk_pocet = sum(hodn.values())
      mame_hodnotenia = (celk_pocet > 0)
    if mame_hodnotenia:
      tdata['IL_CELKOVY_POCET_STUDENTOV'] = celk_pocet
      for znamka in hodn:
        perc = Decimal(hodn[znamka]) / Decimal(celk_pocet) * Decimal(100)
        perc = perc.quantize(Decimal('.01'), rounding=ROUND_HALF_EVEN)
        tdata['IL_PERC_{}'.format(znamka.upper())] = u'{}%'.format(perc)
    else:
      tdata['IL_CELKOVY_POCET_STUDENTOV'] = ''
      for znamka in ['A', 'B', 'C', 'D', 'E', 'FX']:
        tdata['IL_PERC_{}'.format(znamka)] = ''

    vyuc_str = u''
    for vyucujuci in infolist['vyucujuci']:
      vyuc_str += u'\n{}'.format(vyucujuci['cele_meno'])
      if vyucujuci['typy']:
        vyuc_str += u' - {}'.format(
          u', '.join(filter_typ_vyucujuceho(x) for x in vyucujuci['typy'])
        )
    tdata['IL_VYUCUJUCI'] = vyuc_str
    tdata['IL_POSLEDNA_ZMENA'] = format_datetime(infolist['modifikovane'], iba_datum=True)
    tdata['IL_SCHVALIL'] = ''

    rtf_template = resource_string(__name__, 'templates/infolist.rtf')
    to_file.write(render_rtf(rtf_template, tdata))

  @property
  def mimetype(self):
    return 'application/rtf'

  @property
  def filename(self):
    return 'infolist-{}.rtf'.format(self.infolist_id)

class TypPrilohySP(object):
  def __init__(self, id, nazov, kriterium):
    self.id = id
    self.nazov = nazov
    self.kriterium = kriterium

class Prilohy(object):
  def __init__(self):
    self.typy = {}
    self.podla_nazvu_suboru = {}
    self.podla_typu = {}
    
  def add_typ(self, typ):
    self.typy[typ.id] = typ
    self.podla_typu[typ.id] = []
  
  def add(self, typ, priloha):
    self.podla_typu[typ].append(priloha)
    self.podla_nazvu_suboru[priloha.filename] = priloha
  
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
  
  prilohy.add(12, PrilohaZoznam(u'Zoznam dokumentov priložených k žiadosti', 'zoznam_priloh.rtf'))
  
  return prilohy