# -*- coding: utf-8 -*-
from decimal import ROUND_HALF_EVEN, Decimal
from itertools import groupby
import json
from rtfng.Renderer import Renderer
from utils import filter_fakulta, filter_druh_cinnosti, filter_obdobie, filter_metoda_vyucby, \
  filter_literatura, filter_jazyk_vyucby, filter_typ_vyucujuceho, render_rtf, stupen_studia_titul, filter_typ_bloku, \
  prilohy_podla_typu
from StringIO import StringIO
from contextlib import closing
from rtfng.Elements import Document, Section
from rtfng.document.paragraph import Cell, Paragraph, Table
from rtfng.PropertySets import TabPropertySet
from utils import format_datetime
from flask import send_from_directory, stream_with_context, safe_join
from flask import g, url_for, Response
import zipfile
import os.path
from werkzeug.utils import secure_filename
from pkg_resources import resource_string
from datetime import datetime
import re


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
    self._warning_by_typ = {}
    for row in g.db.load_typy_priloh():
      self._typy_priloh[row.id] = row
      self._warning_by_typ[row.id] = []

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

  def add_warning_by_typ(self, typ, message):
    self._warning_by_typ[typ].append(message)

  def warnings_by_typ(self, typ):
    return self._warning_by_typ[typ]

class Priloha(object):
  def __init__(self, context, nazov=None, filename=None, **kwargs):
    self.context = context
    self._nazov = nazov
    if filename is not None:
      self._filename = secure_filename(filename)
    else:
      self._filename = None
  
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

  @property
  def nazov(self):
    return self._nazov

  @property
  def url_aktualizacie(self):
    return None

  @property
  def url_zmazania(self):
    return None

  def check_if_exists(self):
    return True

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

    for typ_prilohy, entries in prilohy_podla_typu(self.prilohy):
      if not entries or typ_prilohy.id == 0:
        continue

      p = Paragraph(styles.ParagraphStyles.Heading2)
      p.append(u'III.{} {}'.format(typ_prilohy.id, typ_prilohy.nazov))
      section.append(p)
    
      table = Table(4075, 4075, 1450)
      table.AddRow(th(u'Príloha'), th(u'Súbor'), th(u'Dátum modifikácie'))
      for filename, priloha in entries:
        table.AddRow(td(priloha.nazov), td(filename), td(format_datetime(priloha.modifikovane, iba_datum=True)))
      section.append(table)
    
    doc.write(to_file)

  @property
  def modifikovane(self):
    return datetime.now()

class PrilohaSuborBase(Priloha):
  def __init__(self, mimetype=None, **kwargs):
    super(PrilohaSuborBase, self).__init__(**kwargs)
    self._mimetype = mimetype

  def render(self, to_file):
    with open(self.real_filename) as fin:
      buffer_size = 262144
      data = fin.read(buffer_size)
      while data != '':
        to_file.write(data)
        data = fin.read(buffer_size)

  def send(self):
    l_dir, l_file = self.location
    return send_from_directory(l_dir, l_file, as_attachment=True,
      attachment_filename=secure_filename(self.filename))

  @property
  def mimetype(self):
    if self._mimetype:
      return self._mimetype
    return super(PrilohaSubor, self).mimetype

  @property
  def real_filename(self):
    return safe_join(*self.location)

class PrilohaUploadnutySubor(PrilohaSuborBase):
  def __init__(self, id, posledna_verzia, sha256, modifikoval, modifikovane, predosla_verzia, studprog_id,
               **kwargs):
    super(PrilohaUploadnutySubor, self).__init__(**kwargs)
    self.id = id
    self.posledna_verzia = posledna_verzia
    self.sha256 = sha256
    self.modifikoval = modifikoval
    self._modifikovane = modifikovane
    self.predosla_verzia = predosla_verzia
    self.studprog_id = studprog_id

  @property
  def modifikovane(self):
    return self._modifikovane

  @property
  def location(self):
    return self.context.config.files_dir, self.sha256

class PrilohaSubor(PrilohaUploadnutySubor):
  def __init__(self, typ_prilohy, **kwargs):
    super(PrilohaSubor, self).__init__(**kwargs)
    self.typ_prilohy = typ_prilohy

  @property
  def url_zmazania(self):
    return url_for('studijny_program_priloha_zmaz', id=self.studprog_id, typ_prilohy=self.typ_prilohy, subor=self.id)

  @property
  def url_aktualizacie(self):
    return url_for('studijny_program_prilohy_upload', studprog_id=self.studprog_id, subor_id=self.id)

def formular_nazov(studprog, konverzny=False):
  nazov_dokumentu = u'Formulár pre študijný program '
  if studprog['skratka']:
    nazov_dokumentu += u'{} '.format(studprog['skratka'])
  nazov_dokumentu += studprog['nazov']
  if konverzny:
    nazov_dokumentu += u' (konverzný program)'
  return nazov_dokumentu

def formular_filename(studprog, konverzny=False):
  return u'2a_SP_{}_{}_{}{}_formular.rtf'.format(studprog['oblast_vyskumu'], stupen_studia_titul.get(studprog['stupen_studia']),
    secure_filename(studprog['nazov']), (u'_konverzny_program' if konverzny else u''))

class PrilohaFormularSP(PrilohaUploadnutySubor):
  def __init__(self, konverzny, **kwargs):
    super(PrilohaFormularSP, self).__init__(**kwargs)
    self.konverzny = konverzny

  @property
  def url_aktualizacie(self):
    return url_for('studijny_program_upload_formular', studprog_id=self.studprog_id, konverzny=self.konverzny)

  @property
  def url_zmazania(self):
    return url_for('studijny_program_zmaz_formular', studprog_id=self.studprog_id, konverzny=self.konverzny)

  @property
  def filename(self):
    studprog = self.context.studprog(self.studprog_id)
    return formular_filename(studprog, self.konverzny)

  @property
  def nazov(self):
    studprog = self.context.studprog(self.studprog_id)
    return formular_nazov(studprog, self.konverzny)

class VPCharMixin(object):
  def __init__(self, osoba, **kwargs):
    self.osoba = osoba
    super(VPCharMixin, self).__init__(**kwargs)

  @property
  def filename(self):
    return secure_filename(u'VPCH_{}_{}_{}.rtf'.format(self.osoba.priezvisko, self.osoba.meno, self.osoba.osoba))

  @property
  def nazov(self):
    return self.osoba.cele_meno

class DiskVPCharMixin(VPCharMixin):
  def __init__(self, *args, **kwargs):
    super(DiskVPCharMixin, self).__init__(*args, **kwargs)
    if self.osoba.token:
      self._vpchar_name = 'token-{}'.format(self.osoba.token)
    elif self.osoba.login:
      self._vpchar_name = 'user-{}'.format(self.osoba.login)
    else:
      self._vpchar_name = None
    self._json_data = None

  @staticmethod
  def _json_object_hook(obj):
    if '__colander' in obj and obj['__colander'] == 'null':
      return None
    return obj

  @property
  def json_data(self):
    if self._json_data is not None:
      return self._json_data
    json_filename = safe_join(self.context.config.vpchar_dir, self.jsonname)
    try:
      with open(json_filename, 'r') as f:
        self._json_data = json.load(f, object_hook=DiskVPCharMixin._json_object_hook)
        return self._json_data
    except IOError:
      return None
    except ValueError:
      return None

  @property
  def modifikovane(self):
    if self.json_data is None:
      return None

    timestamp = self.json_data.get('metadata', {}).get('updated') or self.json_data.get('metadata', {}).get('created')
    if timestamp is None:
      return None

    return datetime.fromtimestamp(timestamp)

  @property
  def jsonname(self):
    return '{}.json'.format(self._vpchar_name)

  @property
  def rtfname(self):
    return '{}.rtf'.format(self._vpchar_name)

  def check_if_exists(self):
    if self._vpchar_name is None:
      return False
    return os.path.exists(safe_join(self.context.config.vpchar_dir, self.rtfname))

class PrilohaVPChar(DiskVPCharMixin, PrilohaSuborBase):
  def __init__(self, **kwargs):
    super(PrilohaVPChar, self).__init__(mimetype='application/rtf', **kwargs)

  @property
  def location(self):
    return self.context.config.vpchar_dir, self.rtfname

class PrilohaUploadnutaVPChar(VPCharMixin, PrilohaUploadnutySubor):
  pass

def infolist_tdata(infolist):
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
  tdata['IL_SCHVALIL'] = u', '.join(x['cele_meno'] for x in infolist['garanti'])

  return tdata

class PrilohaInfolist(Priloha):
  def __init__(self, infolist_id, modifikovane=None, **kwargs):
    super(PrilohaInfolist, self).__init__(**kwargs)
    self.infolist_id = infolist_id
    self._modifikovane = modifikovane

  def render(self, to_file):
    infolist = self.context.infolist(self.infolist_id)
    tdata = infolist_tdata(infolist)
    rtf_template = resource_string(__name__, 'templates/infolist.rtf')
    to_file.write(render_rtf(rtf_template, tdata))

  @property
  def mimetype(self):
    return 'application/rtf'

  @property
  def modifikovane(self):
    return self._modifikovane

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

class PrilohaInfolisty(Priloha):
  def __init__(self, infolisty, **kwargs):
    super(PrilohaInfolisty, self).__init__(**kwargs)
    self.infolisty = infolisty

  def render(self, to_file):
    rtf_skin = resource_string(__name__, 'templates/infolist-skin.rtf').split('INFOLIST_CORE')
    rtf_core = resource_string(__name__, 'templates/infolist-core.rtf')
    to_file.write(rtf_skin[0])

    def th(content):
      return Cell(Paragraph(content))

    def td(content):
      return Cell(Paragraph(content))

    table = Table(3000, 6450)
    table.AddRow(th(u'Kód'), th(u'Názov predmetu'))
    for infolist_id in self.infolisty:
      infolist = self.context.infolist(infolist_id)
      target = 'infolist{}'.format(infolist_id)
      table.AddRow(
        td(infolist['skratka']),
        td(RTFHyperlink(target, infolist['nazov_predmetu']))
      )

    with closing(StringIO()) as table_rtf:
      r = Renderer(write_custom_element_callback=my_rtf_elements)
      r._fout = table_rtf
      r._CurrentStyle = r'\infolistemptystyle'
      r.paragraph_style_map = {'' :''}
      r.WriteTableElement(table)
      to_file.write(table_rtf.getvalue())

    for infolist_id in self.infolisty:
      to_file.write('\n\page\n')
      to_file.write(RTFBookmark('infolist{}'.format(infolist_id)).to_rtf())
      infolist = self.context.infolist(infolist_id)
      tdata = infolist_tdata(infolist)
      to_file.write(render_rtf(rtf_core, tdata))
    to_file.write(rtf_skin[1])

  @property
  def mimetype(self):
    return 'application/rtf'

class PrilohaVPCharakteristiky(Priloha):
  def __init__(self, charakteristiky=None, **kwargs):
    super(PrilohaVPCharakteristiky, self).__init__(**kwargs)
    if charakteristiky is None:
      self.charakteristiky = []
    else:
      self.charakteristiky = charakteristiky

  def render(self, to_file):
    rtf_skin = resource_string(__name__, 'templates/charakteristika-skin.rtf').split('CHARAKTERISTIKA_CORE')
    to_file.write(rtf_skin[0])

    def th(content):
      return Cell(Paragraph(content))

    def td(content):
      return Cell(Paragraph(content))

    table = Table(3000 + 6450)
    table.AddRow(th(u'VP charakteristika'))
    for priloha in self.charakteristiky:
      target = 'osoba{}'.format(priloha.osoba.osoba)
      table.AddRow(
        td(RTFHyperlink(target, priloha.osoba.cele_meno))
      )

    with closing(StringIO()) as table_rtf:
      r = Renderer(write_custom_element_callback=my_rtf_elements)
      r._fout = table_rtf
      r._CurrentStyle = r'\infolistemptystyle'
      r.paragraph_style_map = {'' :''}
      r.WriteTableElement(table)
      to_file.write(table_rtf.getvalue())

    for priloha in self.charakteristiky:
      to_file.write('\n\page\n')
      to_file.write(RTFBookmark('osoba{}'.format(priloha.osoba.osoba)).to_rtf())
      to_file.write(PrilohaVPCharakteristiky.get_core(priloha))

    to_file.write(rtf_skin[1])

  @property
  def mimetype(self):
    return 'application/rtf'

  @staticmethod
  def get_core(priloha):
    def strip_last_space(s):
      if re.match(r'.*\\[a-zA-Z]+(?:-?[0-9]+)? $', s):
        return s[:-1]
      return s
    def normalize_crlf(text):
      return '\r\n'.join(strip_last_space(x) for x in text.strip().splitlines())
    rtf_skin = normalize_crlf(resource_string(__name__, 'templates/charakteristika-skin.rtf')).split('CHARAKTERISTIKA_CORE')
    with closing(StringIO()) as f:
        priloha.render(f)
        s = f.getvalue()
    s = normalize_crlf(s)

    if not s.startswith(rtf_skin[0]):
      raise ValueError('VPChar priloha nezacina skinom')
    if not s.endswith(rtf_skin[1]):
      raise ValueError('VPChar priloha nekonci skinom')
    return s[len(rtf_skin[0]):-len(rtf_skin[1])]

  @staticmethod
  def has_core(priloha):
    try:
      PrilohaVPCharakteristiky.get_core(priloha)
    except ValueError:
      return False
    return True

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


    stupen = {
      '1.': u' - bakalárske štúdium',
      '2.': u' - magisterské štúdium',
      '3.': u' - doktorandské štúdium'
    }
    nadpis = u'Odporúčaný študijný plán' + stupen.get(studprog['stupen_studia'], u'')

    nadpis_sp = u''
    if studprog['skratka']:
      nadpis_sp += studprog['skratka']
      nadpis_sp += u' '
    nadpis_sp += studprog['nazov']
    nadpis += u'\n' + nadpis_sp

    if studprog['aj_konverzny_program']:
      nadpis_sp += u' (konverzný program)'
      nadpis += u'\n' + nadpis_sp

    p = Paragraph(styles.ParagraphStyles.Heading1)
    p.append(nadpis)
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

      table = Table(2850, 2380, 1250, 1100, 950, 900)
      table.AddRow(th(u'Predmet'), th(u'Vyučujúci'), th(u'Roč./Sem.'), th(u'Rozsah'), th(u'Kredity'), th(u'Jadro'))
      for infolist in blok['infolisty']:
        predmet = u'{} {}'.format(infolist['skratka_predmetu'], infolist['nazov_predmetu'])
        if infolist['poznamka_cislo'] is not None:
          predmet = u'{} *{}'.format(predmet, infolist['poznamka_cislo']+1)
        vyucujuci = u', '.join(x['kratke_meno'] for x in infolist['vyucujuci'])
        semester = u'{}{}'.format(infolist['rocnik'] or '', '.' if infolist['semester'] == 'N' else infolist['semester'])
        rozsah = u' + '.join(infolist['rozsah'])
        kredity = u'{}'.format(infolist['pocet_kreditov'])
        jadro = u'áno' if infolist['predmet_jadra'] else u'nie'
        table.AddRow(td(predmet), td(vyucujuci), td(semester), td(rozsah), td(kredity), td(jadro))

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
    if not priloha.check_if_exists():
      return
    filename = ''
    if adresar is not None:
      filename = adresar + '/'
    if typ > 2 and typ != 8:
      filename += 'III_{}_'.format(typ)
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
  
  response = Response(stream_with_context(chunks()), mimetype='application/zip')
  response.headers['Content-Disposition'] = 'attachment; filename={}'.format(filename)
  return response

def prilohy_pre_studijny_program(context, sp_id, spolocne, infolisty_samostatne=True, charakteristiky_samostatne=True):
  prilohy = Prilohy(context)

  formular, formular_konverzny = g.db.load_studprog_formulare(context, sp_id)
  if formular and spolocne in ('normalny', None):
    prilohy.add(0, formular)
  if formular_konverzny and spolocne in ('konverzny', None):
    prilohy.add(0, formular_konverzny)

  for typ, subory in g.db.load_studprog_prilohy_subory(context, sp_id, spolocne=spolocne).iteritems():
    for subor in subory:
      prilohy.add(typ, subor)

  infolisty = g.db.load_studprog_infolisty(sp_id, spolocne=spolocne)
  if infolisty_samostatne:
    for infolist in infolisty:
      prilohy.add(8, PrilohaInfolist(infolist.infolist, modifikovane=infolist.modifikovane,
                                     context=context, nazov=infolist.nazov_predmetu,
                                     filename=u'IL_PREDMETU_{}_{}.rtf'.format(infolist.skratka, infolist.nazov_predmetu)))
  else:
    prilohy.add(8, PrilohaInfolisty([x.infolist for x in infolisty], context=context, nazov='Infolisty', filename=u'IL_PREDMETU_vzor.rtf'))

  spojene_charakteristiky = {
    1: PrilohaVPCharakteristiky(context=context, filename='VPCH_zabezpecujuci.rtf'),
    2: PrilohaVPCharakteristiky(context=context, filename='VPCH_skolitelia.rtf')
  }

  def pridaj_vpchar(typ, osoba):
    if osoba.uploadnuty_subor is not None:
      usubor = g.db.load_subor(osoba.uploadnuty_subor)
      priloha = PrilohaUploadnutaVPChar(osoba=osoba, id=osoba.uploadnuty_subor,
          posledna_verzia=usubor.posledna_verzia, sha256=usubor.sha256, modifikoval=usubor.modifikoval,
          modifikovane=usubor.modifikovane,predosla_verzia=usubor.predosla_verzia, studprog_id=sp_id,
          mimetype=usubor.mimetype, context=context)
    else:
      priloha = PrilohaVPChar(osoba=osoba, context=context)
      if not priloha.check_if_exists():
        context.add_warning_by_typ(typ, u'Chýba VPCHAR pre {}!'.format(osoba.cele_meno))
        return

    if charakteristiky_samostatne or not PrilohaVPCharakteristiky.has_core(priloha):
      prilohy.add(typ, priloha)
    else:
      spojene_charakteristiky[typ].charakteristiky.append(priloha)

  for osoba in g.db.load_studprog_vpchar(sp_id, spolocne=spolocne):
    if not osoba.mame_funkciu and not (u'prof.' in osoba.cele_meno.lower() or u'doc.' in osoba.cele_meno.lower()
                                       or osoba.cele_meno.lower().startswith(u'prof ') or osoba.cele_meno.lower().startswith(u'doc ')):
      context.add_warning_by_typ(1, u'V databáze chýba funkcia pre {}, neviem zistiť, či treba prikladať VPCHAR!'.format(osoba.cele_meno))
      continue
    pridaj_vpchar(1, osoba)

  for osoba in g.db.load_studprog_skolitelia_vpchar(sp_id):
    pridaj_vpchar(2, osoba)

  for typ, priloha in spojene_charakteristiky.iteritems():
    if len(priloha.charakteristiky) > 0:
      prilohy.add(typ, priloha)

  prilohy.add(6, PrilohaStudPlan(sp_id, context=context, nazov=u'Odporúčaný študijný plán', filename='studijny_plan.rtf'))
  incl_spolocne = g.db.resolve_spolocne_bloky(sp_id, spolocne)
  if incl_spolocne:
    prilohy.add(6, PrilohaStudPlan(incl_spolocne, context=context, nazov=u'Odporúčaný študijný plán - spoločný základ', filename='studijny_plan_spolocny.rtf'))

  prilohy.add(12, PrilohaZoznam(prilohy, context=context, nazov=u'Zoznam dokumentov priložených k žiadosti', filename='zoznam_priloh.rtf'))
  
  return prilohy

def prilohy_vsetky(context, **kwargs):
  root = Prilohy(context)

  def pridaj_normalny(studprog):
    adresar = secure_filename(u'SP_{}_{}_{}'.format(studprog['oblast_vyskumu'],stupen_studia_titul.get(studprog['stupen_studia']),
      studprog['nazov']))
    subory = prilohy_pre_studijny_program(context, studprog['id'], spolocne='normalny', **kwargs)
    root.add_adresar(adresar, subory)

  def pridaj_konverzny(studprog):
    adresar = secure_filename(u'SP_{}_{}_{}_konverzny_program'.format(studprog['oblast_vyskumu'],stupen_studia_titul.get(studprog['stupen_studia']),
      studprog['nazov']))
    subory = prilohy_pre_studijny_program(context, studprog['id'], spolocne='konverzny', **kwargs)
    root.add_adresar(adresar, subory)

  for studprog in g.db.fetch_studijne_programy():
    if not studprog['finalna_verzia']:
      continue
    pridaj_normalny(studprog)
    if studprog['aj_konverzny_program']:
      pridaj_konverzny(studprog)

  return root
