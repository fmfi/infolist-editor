ALTER TABLE druh_cinnosti ADD COLUMN popis_en varchar(50);
UPDATE druh_cinnosti SET popis_en = CONCAT(popis, ' [en]');
ALTER TABLE druh_cinnosti ALTER COLUMN popis_en SET NOT NULL;

ALTER TABLE jazyk_vyucby ADD COLUMN popis_en varchar(50);
UPDATE jazyk_vyucby SET popis_en = CONCAT(popis, ' [en]');
UPDATE jazyk_vyucby SET popis_en = 'slovak, english' WHERE kod = 'sk_en';
ALTER TABLE jazyk_vyucby ALTER COLUMN popis_en SET NOT NULL;

ALTER TABLE jazyk_vyucby ADD COLUMN popis_en varchar(50);
UPDATE jazyk_vyucby SET popis_en = CONCAT(popis, ' [en]');
UPDATE jazyk_vyucby SET popis_en = 'slovak, english' WHERE kod = 'sk_en';
ALTER TABLE jazyk_vyucby ALTER COLUMN popis_en SET NOT NULL;

ALTER TABLE typ_vyucujuceho ADD COLUMN popis_en varchar(50);
UPDATE typ_vyucujuceho SET popis_en = CONCAT(popis, ' [en]');
ALTER TABLE typ_vyucujuceho ALTER COLUMN popis_en SET NOT NULL;