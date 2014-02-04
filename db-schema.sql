BEGIN;

CREATE TABLE osoba (
  id serial not null primary key,
  uoc integer,
  login varchar(50),
  ais_id integer,
  meno varchar(250),
  priezvisko varchar(250),
  cele_meno varchar(250),
  rodne_priezvisko varchar(250)
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

CREATE TABLE infolist_verzia (
  id serial not null primary key,
  kod_predmetu varchar(200),
  skratka varchar(200),
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
  hodnotenia_fx_pocet integer
);

-- COMMENT ON TABLE infolist_verzia.percenta_skuska IS 'podiel zaverecneho hodnotenia na znamke (priebezne je 100 - tato hodnota)';

CREATE TABLE infolist_verzia_preklad (
  infolist_verzia integer not null references infolist_verzia(id),
  jazyk varchar(2) not null,
  podm_absol_priebezne text,
  podm_absol_skuska text,
  podm_absol_nahrada text,
  vysledky_vzdelavania text,
  strucna_osnova text,
  potrebny_jazyk varchar(200),
  modifikovane timestamp not null default 'now',
  primary key (infolist_verzia, jazyk)
);

CREATE TABLE infolist_verzia_vyucujuci (
  infolist_verzia integer not null references infolist_verzia(id),
  osoba_id integer not null references osoba(id),
  druh_cinnosti char(1) not null references druh_cinnosti(kod),
  PRIMARY KEY (infolist_verzia, osoba_id, druh_cinnosti)
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

COMMIT;
