Editor informačných listov
--------------------------

Táto aplikácia umožňuje editovať informačné listy a študijné programy.

## Minimálne požiadavky

* Python >=2.7, <3.0
* virtualenv
* postgresql databáza s unaccent extension (postgresql-contrib)
* webserver s CoSign-om

## Inštalácia

V tejto sekcii je popísaná inštalácia na Ubuntu 14.04 LTS, na iných systémoch sa aplikácia
inštaluje obdobne.

### Zdrojové kódy aplikácie

Aplikáciu naklonujeme do `/var/www-apps/ilsp` pod používateľom `ka`.
Najprv vytvorme systémového používateľa, ak neexistuje:

```bash
sudo adduser --system --group ka
```

Potom vytvorme adresár pre aplikáciu a nahrajme doň zdrojové kódy:

```
sudo mkdir -p /var/www-apps/ilsp
sudo chown ka:ka /var/www-apps/ilsp
cd /var/www-apps/ilsp
```

Ak zatiaľ nemáme nainštalovaný git, nainštalujme ho príkazom:

```
sudo apt-get install git
```

A stiahnime zdrojové kódy (všimnite si bodku na konci príkazu):

```
sudo -u ka -H git clone https://github.com/fmfi/infolist-editor.git .
```

### Príprava databázy

Ak ešte nemáme v systéme nainštalovaný PostgreSQL server, spravme tak teraz:

```bash
sudo apt-get install postgresql postgresql-contrib
```

Prihlásme sa ako DBA do postgresu:

```bash
sudo -u postgres psql
```

Vytvorme databázového používateľa a databázu pre aplikáciu
(namiesto hesla `changeit` chceme vygenerovať nejaké náhodné napríklad
pomocou `pwgen -s 64`):

```sql
CREATE USER ka WITH PASSWORD 'changeit';
CREATE DATABASE akreditacia WITH OWNER ka;
```

Vytvorme databázovú extension `unaccent`, to musíme spraviť v správnej databáze,
prepnime sa a vytvorme extension:

```sql
\connect akreditacia
CREATE EXTENSION unaccent;
```

Teraz sa odhlásme z psql (napríklad stlačením `Ctrl+D` alebo príkazom `\q`).

Dáta aplikácie musíme nahrať pod vlastníkom databázy:

```bash
cd /var/www-apps/ilsp
sudo -u ka psql akreditacia <db-schema.sql
```

### Inštalácia závislostí aplikácie

Aplikácia má nejaké systémové a nejaké python závislosti, nainštalujme najprv
tie systémové:

```bash
sudo apt-get install build-essential python-dev libpq-dev python-virtualenv libxml2-dev libxslt-dev zlib1g-dev
```

Prihlásme sa do shellu ako používateľ `ka`:

```bash
sudo -u ka -H -s
```

A ako tento používateľ vytvorme virtualenv a nainštalujme doň python závislosti:

```bash
cd /var/www-apps/ilsp
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```

Opustime shell použivateľa `ka`:

```bash
exit
```

### Konfigurácia aplikácie

Vytvorme adresár pre upload súborov

```bash
sudo -u ka -H mkdir /home/ka/ilsp-files
sudo chmod go= /home/ka/ilsp-files
```

Skopírujme príklad konfiguračného súboru na správne miesto:

```bash
cd /var/www-apps/ilsp
sudo -u ka -H mkdir instance
sudo -u ka -H cp local_settings.py.example instance/local_settings.py
sudo -u ka -H chmod go= instance/local_settings.py
sudoedit -u ka instance/local_settings.py
```

Konfiguračný súbor je spustiteľný python kód skladá sa z nasledovných častí:

#### Tajný kľúč

```python
SECRET_KEY = 'change this!' # tajny sifrovaci kluc
```

`SECRET_KEY` musí byť náhodný tajný reťazec, najlepšie je vygenerovať ho automaticky:

```bash
python -c 'import os; print repr(os.urandom(32))'
```

toto vypíše pythonový string literál, ktorý sa dá použiť ako tajný kľúč.

#### Databáza

```python
DATABASE = 'host=localhost dbname=akreditacia user=ka password=changeit'
```

`DATABASE` je spojenie na postgresql databázu, tak ako ho používa psycopg2
databázový modul

#### Adresár pre uploady

```python
FILES_DIR = '/home/ka/ilsp-files'
```

Sem bude aplikácia nahrávať súbory uploadnuté používateľmi.

#### Adresár s vedecko-pedagogickými charakteristikami

```python
VPCHAR_DIR = '/home/ka/vpchar-files'
```

Editor infolistov načítava vedecko-predagogické charakteristiky vytvorené samostatnou
aplikáciou na vytváranie charakteristík - https://github.com/fmfi/akreditacia-charakteristika

Charakteristiky sú načítavané z JSON a RTF súborov (oba musia byť prítomné).

#### E-mailové posielanie hlásení o chybách

```python
ADMIN_EMAILS = ['email@example.com']
SMTP_SERVER = 'smtp.example.com'
EMAIL_FROM = 'ilsp@example.com'
```

- `ADMIN_EMAILS` je zoznam adries na ktoré sa hlásenia majú posielať
- `SMTP_SERVER` je adresa SMTP servera, cez ktorý sa posiela (bez autentifikácie)
- `EMAIL_FROM` je adresa odosielateľa e-mailov

#### Nastavenie jazykov obsahu

```python
LANGUAGES = ['sk', 'en']
DEFAULT_LANG = 'sk'
```

Nastavenie pre aké jazyky sa v databáze editujú údaje. Je možné uviesť zoznam viacerých
jazykov, pričom `sk` je v aktuálnej verzii potrebné ponechať.

### Spúšťanie príkazov

Aplikácia obsahuje príkazy spúštané z príkazového riadka, no tieto musia byť
spúšťané ako vlastník aplikácie (v našom príklade používateľ `ka`) a s aktívnym
virtuálnym prostredím pythonu. Prostredie teda aktivujeme príkazmi:

```bash
sudo -u ka -H -s
# Zmení sa shell na používateľa ka
cd /var/www-apps/ilsp
source venv/bin/activate
```

Potom už môžeme spúšťať príkazy aplikácie, napríklad:

```bash
./ilsp_app.py --help
```

### Import dát

#### Osoby

Treba naplniť tabuľku `osoba` zoznamom osôb, s ktorými má aplikácia pracovať (tí čo sa prihlasujú + tí čo sú uvedení v infolistoch).

Je možné naimportovať csv súbor v kódovaní UTF-8, ktorý je nasledovného tvaru:

```csv
Plné meno,ID,Meno,Priezvisko,Rodné,Karty,Login,UOČ
"doc. Ing. Jana Hrašková, CSc.",1234567,Jana,Hrašková,Mrkvičková,"UOC - 12345678, PIK - 13245678901234567",hraskova47,12345678
```

* Na poradí stĺpcov nezáleží.
* Stĺpce navyše nevadia.
* Stĺpce `Plné meno`, `Rodné`, `Login`, `UOČ` a `Karty` sú nepovinné.
* Výrazne odporúčam naimportovať okrem AIS ID aj UOČ.
* Ak sa UOČ nenájde v stĺpci UOČ (alebo stĺpec neexistuje, berie sa zo stĺpca s kartami).
* PIK-y sa nepoužívajú, iba UOC.
* Stĺpec `Rodné` sa môže volať aj `Pôvodné`.
* `ID` je z AIS-u.
* položky s AISovým ID, ktoré už existuje v cieľovej databáze sa ignorujú.
* id v databáze ILSP sa vyrobí automaticky.
* import ako celok sa nevykoná (resp. spadne a necommitne sa transakcia) ak by sa vkladalo duplicitné UOČ alebo login.

```bash
./ilsp_app.py import-osoby </cesta/k/suboru.csv
```

> Poznámka: Naimportované osoby sa budú dať vybrať pri výbere
> vyučujúceho predmetu a pod. Ak ich nechceme označiť ako vyučujúcich,
> môžeme použiť prepínač `--nie-su-vyucujuci`

#### Úväzky

Treba naplniť tabuľku `osoba_uvazok` informáciami o pracovných úväzkoch osôb.

Je možné naimportovať csv súbor v kódovaní UTF-8, ktorý je nasledovného tvaru:

```csv
Pracovisko,Priezvisko,Meno,Funkcia,Kvalifikácia,Prac .úv.,UOČ,ID osoby AIS
KJFBF,Hraško,Janko,1H,21,100,123456,12345678
```

* Na poradí stĺpcov nezáleží.
* Stĺpce navyše nevadia.
* Stĺpce Meno a Priezvisko sú nepovinné a používajú sa len pri výpise chýb
* Osoby sa identifikujú podľa UOČ alebo ID osoby z AISu (stačí vyplniť len jednu položku, UOČ má prednosť)

```bash
./ilsp_app.py import-osoby-uvazky </cesta/k/suboru.csv
```

#### Literatúra

Treba naplniť tabuľku `literatura` položkami z knižnice.

Je možné naimportovať csv súbor v kódovaní UTF-8, ktorý je nasledovného tvaru:

```csv
BIBID,Signatúra,Dokument,Vyd. údaje
22110,1856,"Europe's environment : The Dobříš assessment : The report on the state of the pan-European environment requested by the environment ministers for the whole of Europe at the ministerial conference held at Dobříš Castle, Czechoslovakia, June 1991 / Edited by:  David Stanners and Philippe Bourdeau"," Copenhagen : EUR OP, 1955"
```

* Poradie stĺpcov môže byť hocijaké (vyžaduje sa hlavička na začiatku so správnymi popismi).
* Stĺpce navyše nevadia.
* Súbor môže obsahovať viac položiek s rovnakým bib_id, ale `Dokument` a `Vyd. údaje` musia byť zhodné.
* Signatúry z rôznych riadkov sa pri importe spoja do čiarkami oddeleného zoznamu.

```bash
./ilsp_app.py import-literatura-kniznica </cesta/k/suboru.csv
```

### Konfigurácia Apache2

Prepokladáme, že máme nainštalovaný [Apache2 spolu s mod_cosign a rozbehaným SSL-kom](https://cit.uniba.sk/wiki/public/jas/cosign).
Návod na skompilovanie cosign modulu je v [repozitári cosignu](https://github.com/cosignweblogin/cosign/).

> Poznámka: Cosign s Apachom 2.4 som netestoval, ale
> [podľa všetkého](https://www.mail-archive.com/cosign-discuss@lists.sourceforge.net/msg01083.html)
> [by mal fungovať OK](https://github.com/cosignweblogin/cosign/commit/aaea103f93c9364fa07a424218ec18cb715a2a20).

Pre beh aplikácie pod Apache2 použijeme [mod_wsgi](http://www.modwsgi.org/):

```bash
sudo apt-get install libapache2-mod-wsgi
sudo a2enmod wsgi
```

Do správneho virtualhostu (pravdepodobne `/etc/apache2/sites-available/default-ssl`) vložíme nasledovnú Apache2 konfiguráciu:

```ApacheConf
WSGIScriptAlias /ka/ilsp /var/www-apps/ilsp/ilsp_app.py
Alias /ka/ilsp/static /var/www-apps/ilsp/ilsp/static
WSGIDaemonProcess kailsp user=ka group=ka processes=2 threads=15 display-name={%GROUP} python-path=/var/www-apps/ilsp:/var/www-apps/ilsp/venv/lib/python2.7/site-packages home=/var/www-apps/ilsp
<Directory /var/www-apps/ilsp/>
    WSGIProcessGroup kailsp
    WSGICallableObject app
    Require all granted
</Directory>
<Location /ka/ilsp/login>
    CosignAllowPublicAccess Off
    AuthType Cosign
</Location>
```

> Poznámka: Uvedená Apache konfigurácia je pre verziu 2.4, pre Apache 2.2 je namiesto
> 
> ```ApacheConf
> Require all granted
> ```
>
> Treba napísať:
>
> ```ApacheConf
> Order deny,allow
> Allow from all
> ```

A nezabudnime reštartovať web server:

```bash
sudo service apache2 restart
```

## Vývoj aplikácie

### Vývojové dáta

Na lokálny vývoj a testovanie sa dá použiť `db-fixtures.sql`:

```bash
cd /var/www-apps/ilsp
sudo -u ka psql akreditacia <db-fixtures.sql
```

### Štruktúra projektu

Aplikácia používa Flask mikroframework ako základ a je rozdelená do viacerých modulov (blueprintov).

Štruktúra projektu sa delí nasledovne:

    /
      ilsp_app.py - spustiteľný súbor, zároveň exporuje WSGI aplikáciu
      db-schema.sql - skript na vytvorenie schémy DB v PostgreSQL
      db-fixtures.sql - skript na vloženie dát pre vývoj
      drop.sql - skript na zmazanie tabuliek z PostgreSQL
      local_settings.py.example - príklad nastavení
      requirements.txt - súbor obsahujúci zoznam Python závislostí a ich verzií (pre pip)
      tests.py - súbor obsahujúci unit testy
      instance/ - adresár lokálny pre inštanciu
        local_settings.py - konfiguračný súbor
      venv/ - python virtual environment
      ilsp/ - adresár s balíkmi aplikácie
        commands.py - konzolové príkazy aplikácie
        export.py - kód starajúci sa o generovanie exportu a manažment príloh
        storage.py - ostatné funkcie na prácu s databázou
        utils.py - pomocné funkcie
        common/
          auth.py - prihlasovanie a odhlasovanie
          filters.py - filtre v jinja2 templatoch (zväčša preložia ID na názov)
          podmienka.py - parsovanie logických formúl obsahujúcich ID predmetov
          proxies.py - inicializácia databázy
          rtf.py - pomocné funkcie na prácu s RTF
          schema.py - pomocné funkcie na prácu s colander formulárovými schémamy
          storage.py - definícia používateľa a funkcie na prácu s SQL
          upload.py - funkcie na spracovávanie uploadnutých súborov
          widgets.py - dodatočné formulárové widgety pre deform
        infolist/
          literatura.py - REST API pre vyhľadávanie literatúry
          schema.py - deform schéma formuláru pre infolist
          storage.py - storage mixin s funkciami na prácu s infolistami v databáze
          views.py - flaskove routy + API pre JS na prácu s infolistami
          templates/ - jinja2/ZPT/text šablóny
            infolist.html - read-only infolist (view)
            infolist.pt - template select2 deform widgetu na výber infolistu
            infolist.rtf - textový template na generovanie RTF infolistu
                           (nahradzujú sa v ňom placeholdery začínajúce na IL_)
            infolist-core.rtf - ako infolist.rtf, len bez RTF hlavičky a pätičky
                                (aby sa dalo opakovať pre spojené RTF s infolistami)
            infolist-form.html - template pre formulár na editáciu infolistu
            infolist-skin.html - začiatok a koniec RTF infolistu, oddelený textom
                                 INFOLIST_CORE (viď tiež infolist-core.rtf)
            literatura.pt - template select2 deform widgetu na výber literatúry
        osoba/
          views.py - flaskove routy na upload VPCHAR + API pre JS na hľadanie osôb
          templates/
            charakteristika-skin.rtf - začiatok a koniec RTF charakteristiky,
                                       oddelený textom CHARAKTERISTIKA_CORE
                                       (používa sa na spájanie RTF charakteristík)
            osoba.pt - template select2 deform widgetu na výber osoby
            osoba-vpchar-upload.html - template view-u na upload VP charakteristiky
        predmet/
          storage.py - mixin s databázovými funkciami na prácu s predmetmi
          views.py - flaskove routy + API pre JS na prácu s predmetmi
          templates/
            predmet.html - template stránky so zobrazením jedného predmetu
            predmet-index.html - template stránky so zoznamom predmetov
            predmet-item.html - template jedného predmetu (v predmet.html a predmet-index.html)
        static/ - statické súbory pre prehliadač
          css/ - bootstrap css
          fonts/ - bootstrap fonts
          select2/ - knižnica select2 (combo boxy s vyhľadávaním)
          beautify.css - css pre bootstrap deform štýl
          bootstrap.min.js - bootstrap js knižnica
          deform.js - deform js knižnica (upravená)
          form.css - CSS používané vo formulároch
          infolist.css - CSS pre zobrazovanie infolistu
          infolist.js - javascript pre infolisty
          infolist-form.js - javascript pre infolisty
          jquery* - jquery knižnice
          selectize*.css - knižnica selectize - CSS
          selectize.js - knižnica selectize (upravená)
          studprog-form.js - javascript pre formuláre ŠP
          typeahead.* - knižnica na autocomplete
        studprog/
          schema.py - deform schéma formuláru pre ŠP
          statistiky.py - počítanie štatistík ŠP
          storage.py - mixin na prácu so ŠP v databáze
          views.py - flask routes pre študijné programy
        templates/ - ostatné šablóny
          exporty.html - stránka na export dát
          layout.html - štuktúra stránky (hlavička, menu, trackovací kód piwiku)
          login.html - prihlasovacia stránka
          macros.html - pomocné funkcie používané v šablónach
          mapping.pt - deform template pre mapping (dictionary/objekt)
          mapping_item.pt - deform template pre položku mappingu
          ping.js - jinja2 template na generovanie pingovacieho javascriptu
                    (aby nás cosign neodhlásil)
          podmienka.pt - deform2 widget na editovanie logickej formuly obsahujúcej ID predmetov
          pouzivatelia.html - stránka so zoznamom používateľov
          select2.pt - generický select2 deform widget
          sequence.pt - deform widget pre editovanie zoznamov
          sequence_item.pt - položka deform zoznamu
          stav-vyplnania.html - template stránky so zoznamom zistených varovaní
          unauthorized.html - stránka zobrazená ak človek nemá povolený prístup do aplikácie
