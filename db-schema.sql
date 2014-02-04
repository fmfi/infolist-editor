BEGIN;

CREATE TABLE osoba (
  id serial not null primary key,
  uoc integer,
  login varchar(50),
  ais_id integer,
  meno varchar(250),
  priezvisko varchar(250),
  cele_meno varchar(250),
  rodne_priezvisko varchar(250),
  vyucujuci boolean
);

CREATE TABLE druh_cinnosti
(
  kod char(1) NOT NULL primary key,
  popis varchar(100) NOT NULL
);

INSERT INTO druh_cinnosti (kod, popis)
VALUES
  ('P', 'prednáška'),
  ('C', 'cvičenie'),
  ('S', 'seminár'),
  ('L', 'laboratórne práce'),
  ('X', 'projektová práca'),
  ('E', 'exkurzia'),
  ('Z', 'stáž'),
  ('O', 'odborná stáž'),
  ('N', 'iný typ vzdelávacej činnosti'),
  ('A', 'prax'),
  ('K', 'kurz')
;

CREATE TABLE metoda_vyucby (
  kod char(1) not null primary key,
  popis varchar(50) not null
);

INSERT INTO metoda_vyucby (kod, popis)
VALUES
  ('P', 'prezenčná'),
  ('D', 'dištančná'),
  ('K', 'kombinovaná')
;

CREATE TABLE typ_vyucujuceho (
  kod char(1) not null primary key,
  popis varchar(50) not null
);

INSERT INTO typ_vyucujuceho (kod, popis)
VALUES
  ('H', 'hodnotiaci'),
  ('P', 'prednášajúci'),
  ('C', 'cvičiaci'),
  ('L', 'laborant'),
  ('S', 'skúšajúci'),
  ('G', 'garant predmetu'),
  ('A', 'administrátor'),
  ('V', 'vedúci seminára')
;

COMMENT ON TABLE typ_vyucujuceho IS 'Prebrate z AISoveho ciselniku SCSTTypVyucujuceho';

CREATE TABLE infolist_verzia (
  id serial not null primary key,
  nazov_predmetu varchar(300) not null,
  podm_absol_percenta_skuska integer,
  podm_absol_percenta_na_a integer,
  podm_absol_percenta_na_b integer,
  podm_absol_percenta_na_c integer,
  podm_absol_percenta_na_d integer,
  podm_absol_percenta_na_e integer,
  hodnotenia_a_pocet integer,
  hodnotenia_b_pocet integer,
  hodnotenia_c_pocet integer,
  hodnotenia_d_pocet integer,
  hodnotenia_e_pocet integer,
  hodnotenia_fx_pocet integer,
  podmienujuce_predmety text,
  vylucujuce_predmety text,
  modifikovane timestamp not null default 'now'
);

-- COMMENT ON TABLE infolist_verzia.percenta_skuska IS 'podiel zaverecneho hodnotenia na znamke (priebezne je 100 - tato hodnota)';

CREATE TABLE infolist_verzia_preklad (
  infolist_verzia integer not null references infolist_verzia(id),
  jazyk_prekladu varchar(2) not null,
  podm_absol_priebezne text,
  podm_absol_skuska text,
  podm_absol_nahrada text,
  vysledky_vzdelavania text,
  strucna_osnova text,
  potrebny_jazyk varchar(200),
  primary key (infolist_verzia, jazyk_prekladu)
);

CREATE TABLE infolist_verzia_vyucujuci (
  infolist_verzia integer not null references infolist_verzia(id),
  poradie integer not null,
  osoba integer not null references osoba(id),
  PRIMARY KEY (infolist_verzia, osoba),
  UNIQUE (infolist_verzia, poradie)
);

CREATE TABLE infolist_verzia_vyucujuci_typ (
  infolist_verzia integer not null references infolist_verzia(id),
  osoba integer not null references osoba(id),
  typ_vyucujuceho char(1) not null references typ_vyucujuceho(kod),
  PRIMARY KEY (infolist_verzia, osoba, typ_vyucujuceho)
);

CREATE TABLE infolist_verzia_cinnosti (
  infolist_verzia integer not null references infolist_verzia(id),
  druh_cinnosti char(1) not null references druh_cinnosti(kod),
  metoda_vyucby char(1) not null references metoda_vyucby(kod),
  pocet_hodin_tyzdenne integer not null,
  primary key (infolist_verzia, druh_cinnosti)
);

CREATE TABLE infolist (
  id serial not null primary key,
  posledna_verzia integer not null references infolist_verzia(id),
  import_z_aisu boolean not null default false,
  forknute_z integer references infolist(id),
  zamknute boolean not null default false,
  finalna_verzia boolean not null default false
);

CREATE TABLE predmet (
  id serial not null primary key,
  kod_predmetu varchar(200) unique,
  skratka varchar(200),
  zmenit_kod boolean default false
);

CREATE TABLE predmet_infolist (
  predmet integer not null references predmet(id),
  infolist integer not null references infolist(id),
  primary key (predmet, infolist)
);

CREATE TABLE infolist_verzia_suvisiace_predmety (
  infolist_verzia integer not null references infolist_verzia(id),
  predmet integer not null references predmet(id),
  primary key (infolist_verzia, predmet)
);

COMMIT;