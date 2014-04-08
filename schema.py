# -*- coding: utf-8 -*-
from colander import MappingSchema, SchemaNode, String, Integer, Bool, Sequence, Set
import colander
import deform
from chameleon.utils import Markup
import widgets
from flask import url_for, g
from utils import je_profesor_alebo_docent, Podmienka

class DuplicitnyValidator(object):
  def __init__(self, idkey, msg):
    self.idkey = idkey
    self.msg = msg
  
  def __call__(self, node, items):
    seen_items = set()
    root_exc = colander.Invalid(node)
    err = False
    for pos, i in enumerate(items):
      if self.idkey:
        val = i[self.idkey]
      else:
        val = i
      if val in seen_items:
        subnode = node.children[0]
        if self.idkey:
          exc = colander.Invalid(subnode)
          exc[self.idkey] = self.msg
        else:
          exc = colander.Invalid(subnode, self.msg)
        root_exc.add(exc, pos)
        err = True
      seen_items.add(val)
    if err:
      raise root_exc

def VzdelavaciaCinnost(**kwargs):
  schema = MappingSchema(**kwargs)
  schema.add(SchemaNode(String(),
    name='druh_cinnosti',
    title=u'Druh činnosti',
    widget=deform.widget.Select2Widget(values=g.db.load_druhy_cinnosti())
  ))
  schema.add(SchemaNode(Integer(),
    name='pocet_hodin',
    title=u'Počet hodín'
  ))
  schema.add(SchemaNode(String(),
    name='za_obdobie',
    title=u'Za obdobie',
    widget=deform.widget.Select2Widget(values=(('T', 'týždeň'), ('S', 'semester'))),
    description=u'Obdobie "za semester" sa používa len výnimočne v prípade, že sa príslušná činnosť vykonáva blokovo (napr. "prax" 30 hodín)'
  ))
  schema.add(SchemaNode(String(),
    name='metoda_vyucby',
    title=u'Metóda výučby',
    widget=deform.widget.Select2Widget(values=(('P', 'prezenčná'), ('D', 'dištančná'), ('K', 'kombinovaná')))
  ))
  return schema

def Vyucujuci(**kwargs):
  schema = MappingSchema(**kwargs)
  schema.add(SchemaNode(Integer(),
    name='osoba',
    title=u'Osoba',
    widget=widgets.RemoteSelect2Widget(
      search_url=url_for('osoba_search', _external=True),
      item_url=url_for('osoba_get', _external=True),
      template="osoba"
    )
  ))
  schema.add(SchemaNode(Set(),
    name='typy',
    title=u'Typy',
    widget=deform.widget.CheckboxChoiceWidget(values=g.db.load_typy_vyucujuceho(iba_povolene=True))
  ))
  return schema

def PodmienkyAbsolvovania(podm_absolvovania, **kwargs):
  schema = MappingSchema(**kwargs)
  nahrada = podm_absolvovania.get('nahrada')
  if g.user.moze_pridat_nahradu_hodnotenia() or not nahrada:
    schema.add(SchemaNode(String(),
      name='priebezne',
      title=u'Spôsob priebežného hodnotenia',
      description=u'Napríklad: domáce úlohy, písomka',
      missing=''
    ))
    schema.add(SchemaNode(Integer(),
      name='percenta_zapocet',
      title=u'Percentá na pripustenie ku skúške',
      description=u'Zobrazí vetu "Na pripustenie ku skúške je potrebných aspoň X% bodov z priebežného hodnotenia." Ak túto vetu nechcete zobraziť, ponechajte pole prázdne.',
      missing=colander.null,
    ))
    schema.add(SchemaNode(String(),
      name='skuska',
      title=u'Forma skúšky',
      description=u'Napríklad: písomná, ústna; nevyplňovať ak predmet nemá skúšku',
      missing=''
    ))
    schema.add(SchemaNode(Integer(),
      name='percenta_skuska',
      title=u'Váha skúšky v hodnotení (%)',
      description=u'''Napríklad ak predmet nemá skúšku, váha skúšky bude 0. 
        Ak predmet nemá priebežné hodnotenie, váha skúšky bude 100.''',
      missing=0
    ))
    percenta_na = MappingSchema(
      name='percenta_na',
      title=u'Stupnica hodnotenia'
    )
    schema.add(percenta_na)
    for i, x in enumerate(['A', 'B', 'C', 'D', 'E']):
      percenta_na.add(SchemaNode(Integer(),
        name=x,
        title=u'Minimálna hranica na {} (%)'.format(x),
        default=(90 - i * 10)
      ))
    schema.add(SchemaNode(Bool(),
      name='nepouzivat_stupnicu',
      title=u'Nepoužívať stupnicu hodnotenia',
      description=u'''Napríklad pri štátnicových predmetoch. Predmety ktoré
        majú vyplnený nejaký druh vzdelávacej činnosti musia používať stupnicu hodnotenia.''',
    ))
  if g.user.moze_pridat_nahradu_hodnotenia() or nahrada:
    kwargs = {}
    if g.user.moze_pridat_nahradu_hodnotenia():
      kwargs['missing'] = colander.null
    schema.add(SchemaNode(String(),
      name='nahrada',
      title=u'Podmienky absolvovania predmetu (náhradný textový obsah)',
      widget=deform.widget.TextAreaWidget(rows=5),
      **kwargs
    ))
  return schema

def OdporucanaLiteratura(**kwargs):
  schema = MappingSchema(**kwargs)
  schema.add(SchemaNode(Sequence(),
    SchemaNode(Integer(),
      name='literatura',
      title=u'Literatúra z knižného fondu',
      widget=widgets.RemoteSelect2Widget(
        search_url=url_for('literatura_search', _external=True),
        item_url=url_for('literatura_get', _external=True),
        template="literatura"
      )
    ),
    name='zoznam',
    title=u'Literatúra z knižného fondu',
    description=u'''Písaním do boxu sa spustí vyhľadávanie knihy v aktuálnom
      knižnom fonde. Ak sa kniha nenájde, musíte ju pridať do položky
      "Nová literatúra"''',
    widget=deform.widget.SequenceWidget(orderable=True),
    validator=DuplicitnyValidator(None,
      u'''Literatúra sa už v zozname nachádza, prosím zadajte ju iba raz''')
  ))
  schema.add(SchemaNode(Sequence(),
    SchemaNode(String(),
      name='bibl',
      title=u'Nová literatúra',
      widget=deform.widget.AutocompleteInputWidget(min_length=1,
        values=url_for('nova_literatura_search', _external=True)
      )
    ),
    name='nove',
    title=u'Nová literatúra',
    description=Markup(u'''<p>Pozor, literatúru musíme byť schopní zabezpečiť!</p>
      <p>Napríklad:</p>
      <ul>
        <li>Propedeutika astrológie / Jozef Mrkvička, František Hruška. Springer, 2012</li>
        <li>Vlastné elektronické texty vyučujúceho predmetu zverejňované
          prostredníctvom web stránky predmetu.</li>
        <li>Výber aktuálnych článkov z oblasti.</li>
      </ul>'''),
    widget=deform.widget.SequenceWidget(orderable=True)
  ))
  return schema

def get_child(node, name):
  for pos, child in enumerate(node.children):
    if child.name == name:
      return pos, child
  raise KeyError(name)

def invalid_add_exc(exc, node, name, subexc):
  pos, child = get_child(node, name)
  exc.add(subexc, pos)

def bude_v_povinnom_validator(form, value):
  if value['bude_v_povinnom']:
    if len(value['vyucujuci']) == 0 or not je_profesor_alebo_docent(value['vyucujuci'][0]['osoba']):
      exc = colander.Invalid(form)
      exc['vyucujuci'] = u'''Ak je predmet zaradený v niektorom
        študijnom programe ako povinný alebo povinne voliteľný, musí prvý z
        uvedených vyučujúcich byť profesor alebo docent.'''
      raise exc
  else:
    if value['podm_absolvovania']['percenta_skuska'] != 0:
      exc = colander.Invalid(form['podm_absolvovania']['percenta_skuska'],
        u'''Ak predmet nie je zaradený v niektorom
        študijnom programe ako povinný alebo povinne voliteľný, váha skúšky musí byť nulová.''')
      exc2 = colander.Invalid(form['podm_absolvovania'])
      invalid_add_exc(exc2, form['podm_absolvovania'], 'percenta_skuska', exc)
      exc3 = colander.Invalid(form)
      invalid_add_exc(exc3, form, 'podm_absolvovania', exc2)
      raise exc3

def Infolist(infolist):
  schema = MappingSchema(warning_validator=bude_v_povinnom_validator)
  schema.add(SchemaNode(String(),
    name='fakulta',
    title=u'Fakulta',
    widget=deform.widget.Select2Widget(values=g.db.load_fakulty()),
    description=u'Uvádza sa názov fakulty, ktorá predmet personálne a materiálne zabezpečuje'
  ))
  schema.add(SchemaNode(String(),
    name='nazov_predmetu',
    title=u'Názov predmetu'
  ))
  schema.add(SchemaNode(String(),
    name='povodny_kod_predmetu',
    title=u'Kód predmetu',
    description=u'Kódy predmetov budu priradené centrálne',
    missing=colander.null
  ))
  schema.add(SchemaNode(Bool(),
    name='treba_zmenit_kod',
    title=u'Ide o výraznú zmenu, žiadame priradiť predmetu nový kód'
  ))
  schema.add(SchemaNode(Bool(),
    name='bude_v_povinnom',
    title=u'Tento predmet bude zaradený ako povinný alebo povinne voliteľný v niektorom študijnom programe'
  ))
  schema.add(SchemaNode(Sequence(),
    VzdelavaciaCinnost(
      name='vzdelavacia_cinnost',
      title=u'Činnosť'
    ),
    name='cinnosti',
    title=u'Druh, rozsah a metóda vzdelávacích činností',
    description=u'''Ak má predmet prednášky a cvičenia, treba vyplniť dva bloky
      s príslušnými rozsahmi'''
  ))
  schema.add(SchemaNode(Integer(),
    name='pocet_kreditov',
    title=u'Počet kreditov',
    description=Markup(u'''<p>Kreditová hodnota predmetu nezávisí na programe,
      v ktorom sa jeho absolvovanie hodnotí. 1 kredit zodpovedá 25-30 hodinám
      práce študenta. Táto hodnota zahŕňa časovú náročnosť priamej výučby
      (počas 13 týždňov), samostatného štúdia, domácich úloh a projektov,
      ako aj prípravy na skúšku.</p><p>Bližšie pokyny k tvorbe študijných programov:</p><ul class="help-block"><li>FMFI: <a href="https://sluzby.fmph.uniba.sk/ka/dokumenty/pravidla/pravidla-tvorby-studijnych-programov.docx">https://sluzby.fmph.uniba.sk/ka/dokumenty/pravidla/pravidla-tvorby-studijnych-programov.docx</a></li></ul>'''),
    missing=colander.null,
    warn_if_missing=True
  ))
  schema.add(SchemaNode(String(),
    name='predpokladany_semester',
    title=u'Predpokladaný semester výučby',
    widget=deform.widget.Select2Widget(values=(('', ''), ('Z', 'zimný'), ('L', 'letný'), ('N', 'neurčený')), placeholder=u'Vyberte semester'),
    missing=colander.null,
    warn_if_missing=True
  ))
  schema.add(SchemaNode(String(),
    name='predpokladany_stupen_studia',
    title=u'Predpokladaný stupeň štúdia',
    widget=deform.widget.Select2Widget(
      values=(('', ''), ('1.', '1.'), ('2.', '2.'), ('3.', '3.')),
      placeholder=u'Vyberte stupeň štúdia'
    ),
    missing=colander.null,
    warn_if_missing=True
  ))
  schema.add(SchemaNode(widgets.PodmienkaTyp(),
    name='podmienujuce_predmety',
    title=u'Podmieňujúce predmety',
    missing=Podmienka(''),
    widget=widgets.PodmienkaWidget(),
    description=Markup(u'''Uvádzajú sa predmety, ktoré študent musí riadne absolvovať,
      aby si mohol zapísať tento predmet. <strong>Podmieňujúce predmety by mali
      byť splniteľné v rámci študijného programu.</strong> Nemali by ísť napr. 
      medzi bakalárskym a magisterským štúdiom alebo medzi rôznymi študijnými
      programami. Ak chcete vyjadriť obsahovú nadväznosť medzi bakalárskym a
      magisterským programom, využite kolonku Odporúčané predmety.
      Napríklad: "(1-INF-123 alebo 1-INF-234) a 1-INF-456".
      Kódy budú automaticky preklopené na nové priradené kódy.''')
  ))
  schema.add(SchemaNode(widgets.PodmienkaTyp(),
    name='odporucane_predmety',
    title=u'Odporúčané predmety',
    missing=Podmienka(''),
    widget=widgets.PodmienkaWidget(),
    description=u'Napríklad: "(1-INF-123 alebo 1-INF-234) a 1-INF-456". Kódy budú automaticky preklopené na nové priradené kódy.'
  ))
  schema.add(SchemaNode(widgets.PodmienkaTyp(),
    name='vylucujuce_predmety',
    title=u'Vylučujúce predmety',
    missing=Podmienka(''),
    widget=widgets.PodmienkaWidget(),
    description=u'Napríklad: "1-INF-123 alebo 1-INF-456". Kódy budú automaticky preklopené na nové priradené kódy.'
  ))
  schema.add(PodmienkyAbsolvovania(
    infolist.get('podm_absolvovania', {}),
    name='podm_absolvovania',
    title=u'Podmienky absolvovania predmetu'
  ))
  schema.add(SchemaNode(String(),
    name='vysledky_vzdelavania',
    title=u'Výsledky vzdelávania',
    description=Markup(u'''Výsledky vzdelávania určujú, <strong>aké znalosti alebo schopnosti študenti
      budú mať po absolvovaní tohto predmetu</strong>. Môžu sa týkať obsahových
      znalostí (po absolvovaní predmetu študenti budú vedieť kategorizovať
      makroekonomické stratégie na základe ekonomických teórií, z ktorých
      tieto stratégie vychádzajú), schopností (po absolvovaní predmetu
      študenti budú schopní počítať jednoduché derivácie), alebo hodnôt a
      všeobecných schopností (po absolvovaní predmetu budú študenti schopní
      spolupracovať v rámci malých tímov). <strong>Formulácia typu "oboznámiť
      študentov s ..." nie je v tomto kontexte vhodná.</strong>'''),
    widget=deform.widget.TextAreaWidget(rows=5),
    missing=colander.null,
    warn_if_missing=True
  ))
  schema.add(SchemaNode(String(),
    name='strucna_osnova',
    title=u'Stručná osnova predmetu',
    description=u'''Osnova predmetu určuje postupnosť obsahových tém,
      ktoré budú v rámci predmetu preberané. Text zbytočne neštrukturujte
      (ideálne vymenujte postupnosť tém v rámci jedného odstavca).''',
    widget=deform.widget.TextAreaWidget(rows=5),
    missing=colander.null,
    warn_if_missing=True
  ))
  schema.add(OdporucanaLiteratura(
    name='odporucana_literatura',
    title=u'Odporúčaná literatúra',
    description=Markup(u'''<p>Akreditačná komisia bude hodnotiť, ako dobre je pokrytá odporúčaná
      študijná literatúra v rámci prezenčného fondu knižnice. Preto v rámci
      odporúčanej literatúry k predmetu:</p>
      <ol style="list-style-type: lower-alpha">
        <li>Uvádzajte knihy, ktoré slúžia ako <strong>hlavný zdroj</strong>
          informácií pre študentov (spravidla 1-3). Ďalšie zdroje možno
          študentom odporučiť napr. pomocou web stránky predmetu.</li>
        <li>Vyberajte pokiaľ možno zo zoznamu literatúry, ktorá je v
          súčasnosti k dispozícii v knižnom fonde.</li>
        <li>V žiadnom prípade <strong>neuvádzajte literatúru, ktorú nie je
          možné zohnať</strong>.</li>
      </ol>''')
  ))
  schema.add(SchemaNode(String(),
    name='potrebny_jazyk',
    title=u'Jazyk, ktorého znalosť je potrebná na absolvovanie predmetu',
    widget=deform.widget.Select2Widget(values=g.db.load_jazyky_vyucby())
  ))
  schema.add(SchemaNode(Sequence(),
    Vyucujuci(name='vyucujuci', title=u'Vyučujúci'),
    name='vyucujuci',
    title=u'Vyučujúci',
    descrption=Markup(u'''<p><strong>Ak je predmet zaradený v niektorom
      študijnom programe ako povinný alebo povinne voliteľný, musí prvý z
      uvedených vyučujúcich byť profesor alebo docent.</strong>
      V prípade, že sa požadovaný vyučujúci nenachádza v
      zozname, prosím kontaktujte nás (potrebujeme meno, priezvisko a tituly
      vyučujúceho).</p>'''),
    widget=deform.widget.SequenceWidget(orderable=True),
    validator=DuplicitnyValidator('osoba',
      u'''Vyučujúci sa už v zozname nachádza, prosím zadajte ho iba raz''')
  ))
  schema.add(SchemaNode(Bool(),
    name='finalna_verzia',
    title=u'Táto verzia je finálna a dá sa použiť do akreditačného spisu'
  ))
  return schema

def warning_schema(node):
  warning_validator = getattr(node, 'warning_validator', None)
  if warning_validator:
    node.validator = warning_validator
  if getattr(node, 'warn_if_missing', False):
    node.missing = colander.required
  for child in node:
    warning_schema(child)
  return node

def infolisty_v_bloku_nie_su_duplicitne_validator(node, infolisty):
  videne = set()
  root_exc = colander.Invalid(node)
  err = False
  for pos, i in enumerate(infolisty):
    if i['infolist'] in videne:
      subnode = node.children[0]
      exc = colander.Invalid(subnode)
      exc['infolist'] = u'''Informačný list sa už v bloku nachádza, prosím zadajte ho iba raz'''
      root_exc.add(exc, pos)
      err = True
    videne.add(i['infolist'])
  if err:
    raise root_exc

def Blok(**kwargs):
  schema = MappingSchema(**kwargs)
  schema.add(SchemaNode(String(),
    name='nazov',
    title=u'Názov bloku',
    description=u'Napr. S1: Astrológia',
  ))
  schema.add(SchemaNode(String(),
    name='typ',
    title=u'Typ bloku',
    widget=deform.widget.Select2Widget(values=[('', '')] + g.db.load_typy_bloku(), placeholder=u'Vyberte typ bloku'),
  ))
  schema.add(SchemaNode(String(),
    name='podmienky',
    title=u'Podmienky absolvovania bloku',
    description=u'Napr. "výber aspoň 27 kreditov", "všetky predmety z bloku", "výber 1 predmetu" a pod.',
    missing=u''
  ))
  infolist_schema = MappingSchema(name='infolist')
  infolist_schema.add(SchemaNode(Integer(),
    name='infolist',
    title=u'Infolist',
    description=u'''Ak nenájdete vami požadovaný predmet v zozname, môže to byť 
    z dôvodu, že predmet nebol označený ako finálna verzia. Vyhľadajte v editore
    infolistov príslušný informačný list, skontrolujte jeho rozpracovanosť a 
    označte ho ako finálna verzia.''',
    widget=widgets.RemoteSelect2Widget(
      search_url=url_for('infolist_search', _external=True),
      item_url=url_for('infolist_get', _external=True),
      template="infolist"
    )
  ))
  infolist_schema.add(SchemaNode(Bool(),
    name='predmet_jadra',
    title=u'Predmet je v jadre študijného programu',
  ))
  infolist_schema.add(SchemaNode(Integer(),
    name='rocnik',
    title=u'Ročník',
    missing=colander.null
  ))
  infolist_schema.add(SchemaNode(String(),
    name='semester',
    title=u'Semester',
    widget=deform.widget.Select2Widget(values=(('', ''), ('Z', 'zimný'), ('L', 'letný'), ('N', 'neurčený')), placeholder=u'Vyberte semester'),
  ))
  infolist_schema.add(SchemaNode(String(),
    name='poznamka',
    title=u'Poznámka',
    missing=''
  ))
  schema.add(SchemaNode(Sequence(),
    infolist_schema,
    name='infolisty',
    title=u'Informačné listy',
    #widget=widgets.BlokInfolistWidget(),
    validator=DuplicitnyValidator('infolist', u'''Informačný list sa už v bloku nachádza, prosím zadajte ho iba raz''')
  ))
  return schema

def Studprog():
  schema = MappingSchema()
  if (g.user.moze_menit_kody_sp()):
    schema.add(SchemaNode(String(),
      name=u'skratka',
      title=u'Kód študijného programu'
    ))
  schema.add(SchemaNode(String(),
    name=u'nazov',
    title=u'Názov študijného programu'
  ))
  schema.add(SchemaNode(Bool(),
    name=u'aj_konverzny_program',
    title=u'Aj konverzný program'
  ))
  schema.add(SchemaNode(Integer(),
    name=u'garant',
    title=u'Garant študijného programu',
    widget=widgets.RemoteSelect2Widget(
      search_url=url_for('osoba_search', _external=True),
      item_url=url_for('osoba_get', _external=True),
      template="osoba"
    ),
    missing=colander.null,
    warn_if_missing=True
  ))
  schema.add(SchemaNode(String(),
    name=u'stupen_studia',
    title=u'Stupeň štúdia',
    widget=deform.widget.Select2Widget(values=(('', ''), ('1.', '1. - bakalárske štúdium'), ('2.', '2. - magisterské štúdium'), ('3.', '3. - doktorandské štúdium')), placeholder=u'Vyberte stupeň štúdia'),
  ))
  schema.add(SchemaNode(String(),
    name=u'podmienky_absolvovania',
    title=u'Podmienky absolvovania študijného programu',
    description=u'''Napr. Pre úspešné absolvovanie študijného programu musí
      študent okrem povinných predmetov absolvovať jeden celý špecializačný blok
      povinne voliteľných predmetov S1-S10 a zo všetkých povinne voliteľných
      predmetov musí z ostatných blokov absolvovať aspoň 15 kreditov.''',
    widget=deform.widget.TextAreaWidget(rows=5),
    missing=u'',
    warn_if_missing=True
  ))
  schema.add(SchemaNode(Sequence(),
    Blok(
      name='blok',
      title=u'Blok',
      widget=deform.widget.MappingWidget(template='blok_mapping')
    ),
    name='bloky',
    title=u'Bloky',
    widget=deform.widget.SequenceWidget(orderable=True),
  ))
  schema.add(SchemaNode(String(),
    name=u'poznamka_konverzny',
    title=u'Poznámka ku konverznému programu',
    description=u'Táto poznámka sa zobrazuje len v prípade, že je zaškrtnuté políčko "aj konverzný program"',
    missing=u'',
    default=u'''Konverzný študijný program je určený pre absolventov bakalárskeho
      štúdia, na ktoré tento program nenadväzuje, resp. rozsah a kvalita ich
      vedomostí nenapĺňa dostatočne predpoklady pre úspešné dvojročné magisterské
      štúdium. Študent navyše oproti uvedenému absolvuje úvodný ročník, v ktorom
      absolvuje predmety z bakalárskeho štúdia, ktoré sú potrebné ako prerekvizita
      k úspešnému absolvovaniu magisterského štúdia. Tieto predmety určuje
      individuálne garant študijného programu na základe dokladov o absolvovanom
      bakalárskom štúdiu a na základe výsledkov prijímacích skúšok.
      Po absolvovaní úvodného ročníka budú študenti pokračovať podľa
      štandardného odporúčaného študijného plánu.'''.replace('\n      ', ' '),
    widget=deform.widget.TextAreaWidget(rows=5),
  ))
  schema.add(SchemaNode(Bool(),
    name='finalna_verzia',
    title=u'Táto verzia je finálna a dá sa použiť do akreditačného spisu'
  ))
  return schema