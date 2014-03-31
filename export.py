# -*- coding: utf-8 -*-
from decimal import ROUND_HALF_EVEN, Decimal
from itertools import groupby
from utils import escape_rtf, filter_fakulta, filter_druh_cinnosti, filter_obdobie, filter_metoda_vyucby, \
  filter_literatura, filter_jazyk_vyucby, filter_typ_vyucujuceho, render_rtf, stupen_studia_titul, filter_typ_bloku
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

class PrilohaContext(object):
  def __init__(self, config):
    self.config = config
    self._studprog_cache = {}
    self._infolist_cache = {}
    self._typy_priloh = {}
    for row in g.db.load_typy_priloh():
      self._typy_priloh[row.id] = row

  def studprog(self, id):
    if id not in self._studprog_cache:
      self._studprog_cache['id'] = g.db.load_studprog(id)
    return self._studprog_cache['id']

  def infolist(self, id):
    if id not in self._infolist_cache:
      self._infolist_cache['id'] = g.db.load_infolist(id)
    return self._infolist_cache['id']

  def typ_prilohy(self, id):
    return self._typy_priloh[id]

class Priloha(object):
  def __init__(self, context, nazov=None, filename=None, **kwargs):
    self.context = context
    self.nazov = nazov
    self.url_aktualizacie = None
    self._filename = secure_filename(filename)
  
  def render(self, to_file):
    pass
  
  def send(self):
    with closing(StringIO()) as f:
      self.render(f)
      response = Response(f.getvalue(), mimetype=self.mimetype)
      response.headers['Content-Disposition'] = 'attachment; filename={}'.format(self.filename)
      return response
  
  @property
  def mimetype(self):
    if self.filename and self.filename.endswith('.rtf'):
      return 'application/rtf'
    return 'application/octet-stream'

  @property
  def filename(self):
    return self._filename

  @property
  def modifikovane(self):
    return None

class PrilohaZoznam(Priloha):
  def __init__(self, prilohy, **kwargs):
    super(PrilohaZoznam, self).__init__(**kwargs)
    self.prilohy = prilohy

  def render(self, to_file):
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
    
    for typ_prilohy_id, entries in groupby(self.prilohy,key=lambda x: x[1]):
      if not entries or typ_prilohy_id == 0:
        continue

      typ_prilohy = self.context.typ_prilohy(typ_prilohy_id)
      
      p = Paragraph(styles.ParagraphStyles.Heading2)
      p.append(typ_prilohy.nazov)
      section.append(p)
    
      table = Table(TabPropertySet.DEFAULT_WIDTH * 7, TabPropertySet.DEFAULT_WIDTH * 3)
      table.AddRow(th(u'Príloha'), th(u'Dátum modifikácie'))
      for filename, _, priloha in entries:
        table.AddRow(td(filename), td(format_datetime(priloha.modifikovane, iba_datum=True)))
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
    self._modifikovane = modifikovane
    self.predosla_verzia = predosla_verzia
    self.url_aktualizacie = url_for('studijny_program_prilohy_upload', studprog_id=studprog_id, subor_id=id)
    self._mimetype = mimetype
  
  def render(self, to_file):
    with open(os.path.join(self.context.config.files_dir, self.sha256)) as fin:
      buffer_size = 262144 
      data = fin.read(buffer_size)
      while data != '':
        to_file.write(data)
        data = fin.read(buffer_size)
  
  def send(self):
    return send_from_directory(self.context.config.files_dir, self.sha256, as_attachment=True,
      attachment_filename=secure_filename(self.filename))

  @property
  def mimetype(self):
    if self._mimetype:
      return self._mimetype
    return super(PrilohaSubor, self).mimetype

  @property
  def modifikovane(self):
    return self._modifikovane

class PrilohaInfolist(Priloha):
  def __init__(self, infolist_id, **kwargs):
    super(PrilohaInfolist, self).__init__(**kwargs)
    self.infolist_id = infolist_id

  def render(self, to_file):
    infolist = self.context.infolist(self.infolist_id)

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

class PrilohaStudPlan(Priloha):
  def __init__(self, studprog_id, **kwargs):
    super(PrilohaStudPlan, self).__init__(**kwargs)
    self.studprog_id = studprog_id

  def render(self, to_file):
    studprog = self.context.studprog(self.studprog_id)

    doc = Document()
    section = Section()
    doc.Sections.append(section)
    styles = doc.StyleSheet

    def th(content):
      return Cell(Paragraph(content, styles.ParagraphStyles.Normal))

    def td(content):
      return Cell(Paragraph(content, styles.ParagraphStyles.Normal))

    nadpis_sp = u''
    if studprog['skratka']:
      nadpis_sp += studprog['skratka']
      nadpis_sp += u' '
    nadpis_sp += studprog['nazov']
    p = Paragraph(styles.ParagraphStyles.Heading1)
    p.append(nadpis_sp)
    section.append(p)

    if studprog['aj_konverzny_program']:
      nadpis_sp += u' (konverzný program)'
      p = Paragraph(styles.ParagraphStyles.Heading1)
      p.append(nadpis_sp)
      section.append(p)

    p = Paragraph(styles.ParagraphStyles.Normal)
    p.append(u'Podmienky absolvovania študijného programu:\n' + studprog['podmienky_absolvovania'])
    section.append(p)

    for blok in studprog['bloky']:
      p = Paragraph(styles.ParagraphStyles.Heading2)
      p.append(blok['nazov'])
      section.append(p)
      p = Paragraph(styles.ParagraphStyles.Normal)
      p.append(u'({})'.format(filter_typ_bloku(blok['typ'])))
      section.append(p)

      if blok['podmienky']:
        p = Paragraph(styles.ParagraphStyles.Normal)
        p.append(blok['podmienky'])
        section.append(p)

      table = Table(3350, 2880, 1200, 1000, 1000)
      table.AddRow(th(u'Predmet'), th(u'Vyučujúci'), th(u'Roč./Sem.'), th(u'Rozsah'), th(u'Kredity'))
      for infolist in blok['infolisty']:
        predmet = u'{} {}'.format(infolist['skratka_predmetu'], infolist['nazov_predmetu'])
        if infolist['poznamka_cislo']:
          predmet = u'{} *{}'.format(predmet, infolist['poznamka_cislo'])
        vyucujuci = u', '.join(x['kratke_meno'] for x in infolist['vyucujuci'])
        semester = u'{}{}'.format(infolist['rocnik'] or '', '.' if infolist['semester'] == 'N' else infolist['semester'])
        rozsah = u' + '.join(infolist['rozsah'])
        kredity = u'{}'.format(infolist['pocet_kreditov'])
        table.AddRow(td(predmet), td(vyucujuci), td(semester), td(rozsah), td(kredity))

      section.append(table)

      for cislo, poznamka in enumerate(blok['poznamky'], start=1):
        p = Paragraph(styles.ParagraphStyles.Normal)
        p.append(u'*{} {}'.format(cislo, poznamka))
        section.append(p)

    if studprog['aj_konverzny_program']:
      p = Paragraph(styles.ParagraphStyles.Normal)
      p.append(u'Poznámka ku konverznému programu: {}'.format(studprog['poznamka_konverzny']))
      section.append(p)

    doc.write(to_file)

  @property
  def modifikovane(self):
    studprog = self.context.studprog(self.studprog_id)
    return studprog['modifikovane']

class TypPrilohySP(object):
  def __init__(self, id, nazov, kriterium):
    self.id = id
    self.nazov = nazov
    self.kriterium = kriterium

class Prilohy(object):
  def __init__(self, context):
    self.podla_nazvu_suboru = {}
    self.entries = []
    self.context = context
  
  def add(self, typ, priloha, adresar=None):
    filename = ''
    if typ > 0:
      filename += 'III_{}_'.format(typ)
    if adresar is not None:
      filename = adresar + '/'
    filename += priloha.filename

    self.podla_nazvu_suboru[filename] = priloha
    self.entries.append((filename, typ, priloha))

  def add_adresar(self, adresar, prilohy):
    for filename, typ, priloha in prilohy.entries:
      self.add(typ, priloha, adresar=adresar)

  def __iter__(self):
    for entry in self.entries:
      yield entry
  
  def send_zip(self, attachment_filename='vsetky.zip'):
    def entries():
      output_entries = set()
      for filename, typ, subor in self.entries:
        if filename in output_entries:
          continue
        output_entries.add(filename)
        with closing(StringIO()) as f:
          subor.render(f)
          yield filename, f.getvalue()
    return stream_zip(entries(), attachment_filename)

def stream_zip(entries, filename):
  """inspired by http://stackoverflow.com/a/9829044"""
  def chunks():
    sink = ZipBuffer()
    archive = zipfile.ZipFile(sink, "w", compression=zipfile.ZIP_DEFLATED)
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

def prilohy_pre_studijny_program(context, sp_id):
  prilohy = Prilohy(context)
  
  for typ, subory in g.db.load_studprog_prilohy_subory(context, sp_id).iteritems():
    for subor in subory:
      prilohy.add(typ, subor)

  for infolist in g.db.load_studprog_infolisty(sp_id):
    prilohy.add(8, PrilohaInfolist(infolist.infolist, context=context, nazov=infolist.nazov_predmetu,
                                   filename=u'{}_{}.rtf'.format(infolist.skratka, infolist.nazov_predmetu)))


  prilohy.add(6, PrilohaStudPlan(sp_id, context=context, nazov=u'Odporúčaný študijný plán', filename='studijny_plan.rtf'))
  prilohy.add(12, PrilohaZoznam(prilohy, context=context, nazov=u'Zoznam dokumentov priložených k žiadosti', filename='zoznam_priloh.rtf'))
  
  return prilohy

def prilohy_vsetky(context):
  root = Prilohy(context)
  for studprog in g.db.fetch_studijne_programy():
    adresar = secure_filename(u'SP_{}_{}_{}'.format(studprog['oblast_vyskumu'],stupen_studia_titul.get(studprog['stupen_studia']),
      studprog['nazov']))
    subory = prilohy_pre_studijny_program(context, studprog['id'])
    root.add_adresar(adresar, subory)
  return root