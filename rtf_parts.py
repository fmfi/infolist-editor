# -*- coding: utf-8 -*-
from utils import escape_rtf
from StringIO import StringIO
from contextlib import closing
from rtfng.Elements import Document, Section
from rtfng.document.paragraph import Cell, Paragraph, Table
from rtfng.PropertySets import BorderPropertySet, FramePropertySet, ParagraphPropertySet, TabPropertySet
from markupsafe import soft_unicode
from utils import format_datetime

def rtf_zoznam_priloh(prilohy):
  doc = Document()
  section = Section()
  doc.Sections.append(section)
  styles = doc.StyleSheet
  
  p = Paragraph(styles.ParagraphStyles.Heading1)
  p.append(u'Zoznam príloh')
  section.append(p)
  
  for typ_prilohy in prilohy:
    if not typ_prilohy['subory']:
      continue
    
    p = Paragraph(styles.ParagraphStyles.Heading2)
    p.append(typ_prilohy['nazov'])
    section.append(p)
  
    table = Table(TabPropertySet.DEFAULT_WIDTH * 7, TabPropertySet.DEFAULT_WIDTH * 3)
    table.AddRow(Cell(Paragraph(u'Príloha', styles.ParagraphStyles.Normal)), Cell(Paragraph(u'Dátum modifikácie', styles.ParagraphStyles.Normal)))
    for subor in typ_prilohy['subory']:
      table.AddRow(Cell(Paragraph(subor['nazov'], styles.ParagraphStyles.Normal)), Cell(Paragraph(format_datetime(subor['modifikovane'], iba_datum=True), styles.ParagraphStyles.Normal)))
    section.append(table)
  
  with closing(StringIO()) as f:
    doc.write(f)
    return f.getvalue()