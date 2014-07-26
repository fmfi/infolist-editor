INSERT INTO osoba (login, meno, priezvisko, cele_meno, vyucujuci) VALUES ('vinar1', 'Tomáš', 'Vinař', 'Mgr. Tomáš Vinař, PhD.', true);

INSERT INTO ilsp_opravnenia (osoba, organizacna_jednotka, je_admin, je_garant)
SELECT o.id, 'FMFI', true, false
FROM osoba o WHERE o.login IN ('vinar1');
