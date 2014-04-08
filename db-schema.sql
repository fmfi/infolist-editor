BEGIN;

CREATE TABLE organizacna_jednotka
(
  kod varchar(100) NOT NULL PRIMARY KEY,
  kod_epc varchar(50),
  nadriadena_kod varchar(100) REFERENCES organizacna_jednotka(kod),
  typ varchar(10) NOT NULL,
  nazov varchar(256) NOT NULL,
  UNIQUE (kod_epc)
);

COMMENT ON COLUMN organizacna_jednotka.kod IS 'kod organizacnej jednotky, ako je v AIS-e';
COMMENT ON COLUMN organizacna_jednotka.kod_epc IS 'kod organizacnej jednotky, ako je v EPC';
COMMENT ON COLUMN organizacna_jednotka.nadriadena_kod IS 'kod nadriadenej OJ alebo NULL';
COMMENT ON COLUMN organizacna_jednotka.nazov IS 'nazov OJ ako je v AIS-e';

INSERT INTO organizacna_jednotka (kod, nadriadena_kod, kod_epc, typ, nazov)
VALUES
  ('AK', 'UK', NULL, 'Úč.pr', 'Akademická knižnica UK'),
  ('BZ', 'UK', NULL, 'Iné', 'Botanická záhrada Bratislava'),
  ('BZ.BZB', 'BZ', NULL, 'Iné', 'Botanická záhrada Blatnica'),
  ('CĎV', 'UK', NULL, 'Iné', 'Centrum ďalšieho vzdelávania'),
  ('CĎV.IVKS', 'CĎV', NULL, 'Ústav', 'Inštitút vzdelávania a kariérových služieb'),
  ('CĎV.JC', 'CĎV', NULL, 'Ústav', 'Jazykové centrum'),
  ('CĎV.OP', 'CĎV', NULL, 'Úč.pr', 'Oddelenie prevádzky'),
  ('CĎV.ŠSM', 'CĎV', NULL, 'Iné', 'ŠS Modra'),
  ('CĎV.ÚJOP', 'CĎV', NULL, 'Ústav', 'Ústav jazykovej a odbornej prípravy zahraničných študentov'),
  ('CĎV.Ústr', 'CĎV', NULL, 'Iné', 'Ústredie CĎVUK'),
  ('CĎV.UTV', 'CĎV', NULL, 'Ústav', 'Univerzita tretieho veku'),
  ('CIT', 'UK', NULL, 'Úč.pr', 'Centrum informačných technológií UK'),
  ('EBF', 'UK', 'UKOEB', 'Fakul', 'Evanjelická bohoslovecká fakulta'),
  ('EBF.Dek', 'EBF', NULL, 'Rekto', 'Dekanát'),
  ('EBF.ICH', 'EBF', NULL, 'Inšti', 'Inštitút cirkevnej hudby'),
  ('EBF.IKT', 'EBF', NULL, 'Inšti', 'Inštitút kontextuálnej teológie'),
  ('EBF.KC', 'EBF', NULL, 'Kated', 'Katedra'),
  ('EBF.KCD', 'EBF', 'UKOEBCD', 'Kated', 'Katedra cirkevných dejín'),
  ('EBF.KFR', 'EBF', 'UKOEBFR', 'Kated', 'Katedra filozofie a religionistiky'),
  ('EBF.KNZ', 'EBF', 'UKOEBNZ', 'Kated', 'Katedra Novej zmluvy'),
  ('EBF.KPT', 'EBF', 'EKOEBPT', 'Kated', 'Katedra praktickej teológie'),
  ('EBF.KST', 'EBF', NULL, 'Kated', 'Katedra systematickej teológie'),
  ('EBF.KSTD', 'EBF', 'UKOEBST', 'Kated', 'Katedra systematickej teológie a dejín'),
  ('EBF.KSZ', 'EBF', 'UKOEBSZ', 'Kated', 'Katedra Starej zmluvy'),
  ('EBF.OP', 'EBF', NULL, 'Úč.pr', 'Oddelenie prevádzky'),
  ('EBF.ŠD', 'EBF', NULL, 'Úč.pr', 'Študentský domov EBF UK'),
  ('EO', 'PdF', NULL, 'Refer', 'Ekonomické oddelenie'),
  ('FaF', 'UK', 'UKOFA', 'Fakul', 'Farmaceutická fakulta'),
  ('FaF.CE', 'FaF', NULL, 'Iné', 'Centrum excelentnosti FARMÁCIA'),
  ('FaF.Dek', 'FaF', NULL, 'Rekto', 'Dekanát'),
  ('FaF.FL', 'FaF', NULL, 'Iné', 'Fakultná lekáreň Farmaceutickej fakulty'),
  ('FaF.IIS', 'FaF', NULL, 'Úč.pr', 'Integrovaný informačný systém'),
  ('FaF.KBMBL', 'FaF', NULL, 'Kated', 'Katedra bunkovej a molekulárnej biológie liečiv'),
  ('FaF.KChTL', 'FaF', 'UKOFACH', 'Kated', 'Katedra chemickej teórie liečiv'),
  ('FaF.KFANF', 'FaF', 'UKOFAA', 'Kated', 'Katedra farmaceutickej analýzy a nukleárnej farmácie'),
  ('FaF.KFB', 'FaF', NULL, 'Kated', 'Katedra farmakognózie a botaniky'),
  ('FaF.KFCh', 'FaF', NULL, 'Kated', 'Katedra farmaceutickej chémie'),
  ('FaF.KFChL', 'FaF', 'UKOFAFYZ', 'Kated', 'Katedra fyzikálnej chémie liečiv'),
  ('FaF.KFT', 'FaF', 'UKOFAFT', 'Kated', 'Katedra farmakológie a toxikológie'),
  ('FaF.KGF', 'FaF', NULL, 'Kated', 'Katedra galenickej farmácie'),
  ('FaF.KJ', 'FaF', NULL, 'Kated', 'Katedra jazykov'),
  ('FaF.KORF', 'FaF', NULL, 'Kated', 'Katedra organizácie a riadenia farmácie'),
  ('FaF.KTV', 'FaF', NULL, 'Kated', 'Katedra telesnej výchovy a športu'),
  ('FaF.NMR', 'FaF', NULL, 'Iné', 'Nukleárna magnetická rezonancia'),
  ('FaF.OP', 'FaF', NULL, 'Úč.pr', 'Oddelenie prevádzky'),
  ('FaF.ŠFEÚ', 'FaF', NULL, 'Iné', 'Štrukturálne fondy EÚ'),
  ('FaF.ŠJ', 'FaF', NULL, 'Iné', 'Študentská jedáleň FaF UK'),
  ('FaF.ÚK', 'FaF', NULL, 'Úč.pr', 'Ústredná knižnica FaF UK'),
  ('FaF.UL', 'FaF', NULL, 'Iné', 'Univerzitná lekáreň Farmaceutickej fakulty'),
  ('FaF.ZLR', 'FaF', NULL, 'Úč.pr', 'Záhrada liečivých rastlín'),
  ('FiF', 'UK', 'UKOFI', 'Fakul', 'Filozofická fakulta'),
  ('FiF.CMTŠ', 'FiF', NULL, 'Úč.pr', 'Centrum pre medzinárodné a teritoriálne štúdiá'),
  ('FiF.CRŠ', 'FiF', NULL, 'Úč.pr', 'Centrum rodových štúdií'),
  ('FiF.Dek', 'FiF', NULL, 'Rekto', 'Dekanát'),
  ('FiF.KAA', 'FiF', 'UKOFIAA', 'Kated', 'Katedra anglistiky a amerikanistiky'),
  ('FiF.KAnd', 'FiF', NULL, 'Kated', 'Katedra andragogiky'),
  ('FiF.KAPVH', 'FiF', 'UKOFIAV', 'Kated', 'Katedra archívnictva a pomocných vied historických'),
  ('FiF.KArch', 'FiF', 'UKOFIPV', 'Kated', 'Katedra archeológie'),
  ('FiF.KDVU', 'FiF', 'UKOFIVU', 'Kated', 'Katedra dejín výtvarného umenia'),
  ('FiF.KE', 'FiF', 'UKOFIES', 'Kated', 'Katedra estetiky'),
  ('FiF.KEKA', 'FiF', 'UKOFIET', 'Kated', 'Katedra etnológie a kultúrnej antropológie'),
  ('FiF.KFDF', 'FiF', 'UKOFIDF', 'Kated', 'Katedra filozofie a dejín filozofie'),
  ('FiF.KGNŠ', 'FiF', 'UKOFIGN', 'Kated', 'Katedra germanistiky, nederlandistiky a škandinavistiky'),
  ('FiF.KHV', 'FiF', 'UKOFIHV', 'Kated', 'Katedra hudobnej vedy'),
  ('FiF.KIP', 'FiF', NULL, 'Úč.pr', 'Knižnično-informačné pracovisko'),
  ('FiF.KJ', 'FiF', NULL, 'Kated', 'Katedra jazykov'),
  ('FiF.KK', 'FiF', NULL, 'Kated', 'Katedra kulturológie'),
  ('FiF.KKIV', 'FiF', NULL, 'Kated', 'Katedra knižničnej a informačnej vedy'),
  ('FiF.KKSF', 'FiF', 'UKOFIKF', 'Kated', 'Katedra klasickej a semitskej filológie'),
  ('FiF.KLMV', 'FiF', 'UKOFILG', 'Kated', 'Katedra logiky a metodológie vied'),
  ('FiF.KMJL', 'FiF', 'UKOFIMJ', 'Kated', 'Katedra maďarského jazyka a literatúry'),
  ('FiF.KMK', 'FiF', 'UKOFIPG', 'Kated', 'Katedra marketingovej komunikácie'),
  ('FiF.KPg', 'FiF', 'UKOFIPD', 'Kated', 'Katedra pedagogiky'),
  ('FiF.KPol', 'FiF', NULL, 'Kated', 'Katedra politológie'),
  ('FiF.KPR', 'FiF', 'UKOFIRL', 'Kated', 'Katedra porovnávacej religionistiky'),
  ('FiF.KPs', 'FiF', 'UKOFIPS', 'Kated', 'Katedra psychológie'),
  ('FiF.KRJL', 'FiF', NULL, 'Kated', 'Katedra ruského jazyka a literatúry'),
  ('FiF.KRom', 'FiF', 'UKOFIRO', 'Kated', 'Katedra romanistiky'),
  ('FiF.KS', 'FiF', 'UKOFISC', 'Kated', 'Katedra sociológie'),
  ('FiF.KSD', 'FiF', NULL, 'Kated', 'Katedra slovenských dejín'),
  ('FiF.KSF', 'FiF', 'UKOFISF', 'Kated', 'Katedra slovanských filológií'),
  ('FiF.KSJ', 'FiF', NULL, 'Kated', 'Katedra slovenského jazyka'),
  ('FiF.KSLLV', 'FiF', NULL, 'Kated', 'Katedra slovenskej literatúry a literárnej vedy'),
  ('FiF.KTV', 'FiF', NULL, 'Kated', 'Katedra telesnej výchovy'),
  ('FiF.KVD', 'FiF', 'UKOFIHS', 'Kated', 'Katedra všeobecných dejín'),
  ('FiF.KVŠ', 'FiF', 'UKOFIJP', 'Kated', 'Katedra východoázijských štúdií'),
  ('FiF.KŽ', 'FiF', 'UKOFIZU', 'Kated', 'Katedra žurnalistiky'),
  ('FiF.OP', 'FiF', NULL, 'Úč.pr', 'Oddelenie prevádzky'),
  ('FiF.PVC', 'FiF', NULL, 'Úč.pr', 'Poradenské a vydavateľské centrum STIMUL'),
  ('FiF.SAS', 'FiF', NULL, 'Úč.pr', 'Studia Academica Slovaca'),
  ('FiF.ŠJ', 'FiF', NULL, 'Iné', 'Študentská jedáleň'),
  ('FiF.ŠJZ', 'FiF', NULL, 'Iné', 'Študentská jedáleň - zamestnanci'),
  ('FiF.STVA', 'FiF', NULL, 'Úč.za', 'Stredisko telovýchovných voľnočasových aktivít'),
  ('FM', 'UK', NULL, 'Fakul', 'Fakulta managementu'),
  ('FM.CIT', 'FM', NULL, 'Úč.pr', 'Centrum informačných technológií'),
  ('FM.Dek', 'FM', NULL, 'Rekto', 'Dekanát'),
  ('FM.KEF', 'FM', NULL, 'Kated', 'Katedra ekonómie a financií'),
  ('FM.KIS', 'FM', 'UKOMAKIS', 'Kated', 'Katedra informačných systémov'),
  ('FM.KMk', 'FM', NULL, 'Kated', 'Katedra marketingu'),
  ('FM.KMn', 'FM', NULL, 'Kated', 'Katedra manažmentu'),
  ('FM.Kn', 'FM', NULL, 'Úč.pr', 'Knižnica'),
  ('FM.KSP', 'FM', NULL, 'Kated', 'Katedra stratégie a podnikania'),
  ('FM.OP', 'FM', NULL, 'Úč.pr', 'Oddelenie prevádzky'),
  ('FM.OVVDŠ', 'FM', NULL, 'Refer', 'Oddelenie vedy, výskumu a doktorandského štúdia'),
  ('FM.OZS', 'FM', NULL, 'Refer', 'Oddelenie zahraničných stykov'),
  ('FM.ŠK', 'FM', NULL, 'Iné', 'Športový klub Fakulty managementu'),
  ('FM.SO', 'FM', NULL, 'Refer', 'Študijné oddelenie'),
  ('FM.WEMBA', 'FM', NULL, 'Iné', 'WEMBA'),
  ('FMFI', 'UK', 'UKOMF', 'Fakul', 'Fakulta matematiky, fyziky a informatiky'),
  ('FMFI.CPP', 'FMFI', NULL, 'Iné', 'Centrum projektovej podpory'),
  ('FMFI.Dek', 'FMFI', 'UKOMFDE', 'Rekto', 'Dekanát'),
  ('FMFI.KAFZM', 'FMFI', 'UKOMFKAFZM', 'Kated', 'Katedra astronómie, fyziky Zeme a meteorológie'),
  ('FMFI.KAGDM', 'FMFI', 'UKOMFKAGDM', 'Kated', 'Katedra algebry, geometrie a didaktiky matematiky'),
  ('FMFI.KAI', 'FMFI', 'UKOMFKAI', 'Kated', 'Katedra aplikovanej informatiky'),
  ('FMFI.KAMŠ', 'FMFI', 'UKOMFKAMS', 'Kated', 'Katedra aplikovanej matematiky a štatistiky'),
  ('FMFI.KEC', 'FMFI', 'UKOMFKEC', 'Úč.pr', 'Knižničné a edičné centrum'),
  ('FMFI.KEF', 'FMFI', 'UKOMFKEF', 'Kated', 'Katedra experimentálnej fyziky'),
  ('FMFI.KI', 'FMFI', 'UKOMFKI', 'Kated', 'Katedra informatiky'),
  ('FMFI.KJFB', 'FMFI', 'UKOMFKJFB', 'Kated', 'Katedra jadrovej fyziky a biofyziky'),
  ('FMFI.KJP', 'FMFI', 'UKOMFKJP', 'Kated', 'Katedra jazykovej prípravy'),
  ('FMFI.KMANM', 'FMFI', 'UKOMFKMANM', 'Kated', 'Katedra matematickej analýzy a numerickej matematiky'),
  ('FMFI.KTFDF', 'FMFI', 'UKOMFKTFDF', 'Kated', 'Katedra teoretickej fyziky a didaktiky fyziky'),
  ('FMFI.KTV', 'FMFI', 'UKOMFKTVS', 'Kated', 'Katedra telesnej výchovy a športu'),
  ('FMFI.KZVI', 'FMFI', 'UKOMFKZVI', 'Kated', 'Katedra základov a vyučovania informatiky'),
  ('FMFI.SB', 'FMFI', NULL, 'Iné', 'Správa budov'),
  ('FMFI.SL', 'FMFI', 'UKOMFSL', 'Iné', 'Schola Ludus'),
  ('FMFI.VC', 'FMFI', NULL, 'Úč.pr', 'Výpočtové centrum'),
  ('FMFI.VL', 'FMFI', NULL, 'Úč.pr', 'Vývojové laboratórium'),
  ('FSEV', 'UK', 'UKOFS', 'Fakul', 'Fakulta sociálnych a ekonomických vied'),
  ('FSEV.Dek', 'FSEV', NULL, 'Rekto', 'Dekanát'),
  ('FSEV.OP', 'FSEV', NULL, 'Úč.pr', 'Oddelenie prevádzky'),
  ('FSEV.ÚAP', 'FSEV', NULL, 'Ústav', 'Ústav aplikovanej psychológie'),
  ('FSEV.ÚE', 'FSEV', NULL, 'Ústav', 'Ústav ekonómie'),
  ('FSEV.ÚEŠMV', 'FSEV', NULL, 'Ústav', 'Ústav európskych štúdií a medzinárodných vzťahov'),
  ('FSEV.ÚSA', 'FSEV', NULL, 'Ústav', 'Ústav sociálnej antropológie'),
  ('FSEV.ÚVP', 'FSEV', 'UKOFSVP', 'Ústav', 'Ústav verejnej politiky'),
  ('FSEV.ÚVPE', 'FSEV', NULL, 'Ústav', 'Ústav verejnej politiky a ekonómie'),
  ('FTVŠ', 'UK', 'UKOTV', 'Fakul', 'Fakulta telesnej výchovy a športu'),
  ('FTVŠ.Dek', 'FTVŠ', NULL, 'Rekto', 'Dekanát'),
  ('FTVŠ.KA', 'FTVŠ', NULL, 'Kated', 'Katedra atletiky'),
  ('FTVŠ.KG', 'FTVŠ', 'UKOTVKGF', 'Kated', 'Katedra gymnastiky'),
  ('FTVŠ.KH', 'FTVŠ', NULL, 'Kated', 'Katedra športových hier'),
  ('FTVŠ.Kn', 'FTVŠ', NULL, 'Úč.pr', 'Knižnica'),
  ('FTVŠ.KŠE', 'FTVŠ', NULL, 'Kated', 'Katedra športovej edukológie'),
  ('FTVŠ.KŠEŠH', 'FTVŠ', 'UKOTVKEH', 'Kated', 'Katedra športovej edukológie a športovej humanistiky'),
  ('FTVŠ.KŠH', 'FTVŠ', 'UKOTVKOJ', 'Kated', 'Katedra športovej humanistiky'),
  ('FTVŠ.KŠK', 'FTVŠ', NULL, 'Kated', 'Katedra športovej kinantropológie'),
  ('FTVŠ.KŠPP', 'FTVŠ', 'UKOTVKPP', 'Kated', 'Katedra športov v prírode a plávania'),
  ('FTVŠ.OP', 'FTVŠ', NULL, 'Úč.pr', 'Oddelenie prevádzky'),
  ('FTVŠ.ŠDL', 'FTVŠ', NULL, 'Úč.pr', 'Študentský domov Lafranconi'),
  ('FTVŠ.ŠJ', 'FTVŠ', NULL, 'Iné', 'Študentská jedáleň'),
  ('FTVŠ.ŠJZ', 'FTVŠ', NULL, 'Iné', 'Študentská jedáleň - zamestnanci'),
  ('IH', 'EBF', NULL, 'Kated', 'Inštitút hudby'),
  ('IKT', 'EBF', NULL, 'Kated', 'Inštitút kontextuálnej teológie'),
  ('JLF', 'UK', 'UKOLJ', 'Fakul', 'Jesseniova lekárska fakulta'),
  ('JLF.ChK1', 'JLF', NULL, 'Klin', 'Chirurgická klinika'),
  ('JLF.ChSP', 'JLF', NULL, 'Úč.za', 'Chata Sklabinský Podzámok'),
  ('JLF.CZ', 'JLF', NULL, 'Úč.pr', 'Centrálny zverinec'),
  ('JLF.Dek', 'JLF', NULL, 'Rekto', 'Dekanát'),
  ('JLF.DK', 'JLF', NULL, 'Klin', 'Dermatovenerologická klinika'),
  ('JLF.FSAT', 'JLF', NULL, 'Úč.pr', 'Fotolaboratórium a stredisko audiovizuálnej techniky'),
  ('JLF.GPK', 'JLF', NULL, 'Klin', 'Gynekologicko-pôrodnícka klinika'),
  ('JLF.IK1', 'JLF', NULL, 'Klin', 'I. interná klinika'),
  ('JLF.IKG', 'JLF', NULL, 'Klin', 'Interná klinika - Gastroenterologická'),
  ('JLF.IMV', 'JLF', NULL, 'Úč.pr', 'Inštitút medicínskeho vzdelávania v AJ'),
  ('JLF.KAIM', 'JLF', NULL, 'Klin', 'Klinika anesteziológie a intenzívnej medicíny'),
  ('JLF.KDAIM', 'JLF', NULL, 'Klin', 'Klinika detskej anesteziológie a intenzívnej medicíny'),
  ('JLF.KDCh', 'JLF', NULL, 'Klin', 'Klinika detskej chirurgie'),
  ('JLF.KDD', 'JLF', NULL, 'Klin', 'Klinika detí a dorastu'),
  ('JLF.KDTBC', 'JLF', NULL, 'Klin', 'Klinika detskej TBC'),
  ('JLF.KENP', 'JLF', NULL, 'Úč.pr', 'Kancelária európskych a národných projektov'),
  ('JLF.KHCh', 'JLF', NULL, 'Klin', 'Klinika hrudníkovej chirurgie'),
  ('JLF.KHT', 'JLF', NULL, 'Klin', 'Klinika hematológie a transfuziológie'),
  ('JLF.KICM', 'JLF', NULL, 'Klin', 'Klinika infektológie a cestovnej medicíny'),
  ('JLF.KNM', 'JLF', NULL, 'Klin', 'Klinika nukleárnej medicíny'),
  ('JLF.KORL', 'JLF', NULL, 'Klin', 'Klinika otorinolaryngológie a chirurgie hlavy a krku'),
  ('JLF.KPF', 'JLF', NULL, 'Klin', 'Klinika pneumológie a ftizeológie'),
  ('JLF.KPLT', 'JLF', NULL, 'Klin', 'Klinika pracovného lekárstva a toxikológie'),
  ('JLF.KSH', 'JLF', NULL, 'Úč.za', 'Kultúrno-spoločenská hala'),
  ('JLF.KŠIS', 'JLF', NULL, 'Úč.pr', 'Knižnica a študijno-informačné stredisko'),
  ('JLF.KSMCh', 'JLF', NULL, 'Klin', 'Klinika stomatológie a maxilofaciálnej chirurgie'),
  ('JLF.KTCCh', 'JLF', NULL, 'Klin', 'Klinika transplantačnej a cievnej chirurgie'),
  ('JLF.KTL', 'JLF', NULL, 'Klin', 'Klinika telovýchovného lekárstva'),
  ('JLF.KTPCh', 'JLF', NULL, 'Klin', 'Klinika tuberkulózy a pľúcnych chorôb'),
  ('JLF.NchK', 'JLF', NULL, 'Klin', 'Neurochirurgická klinika'),
  ('JLF.NlK', 'JLF', NULL, 'Klin', 'Neurologická klinika'),
  ('JLF.NnK', 'JLF', NULL, 'Klin', 'Neonatologická klinika'),
  ('JLF.OK', 'JLF', NULL, 'Klin', 'Očná klinika'),
  ('JLF.OP', 'JLF', NULL, 'Úč.pr', 'Oddelenie prevádzky'),
  ('JLF.OTK', 'JLF', NULL, 'Klin', 'Ortopedická klinika'),
  ('JLF.PK', 'JLF', NULL, 'Klin', 'Psychiatrická klinika'),
  ('JLF.RK', 'JLF', NULL, 'Klin', 'Rádiologická klinika'),
  ('JLF.ŠJŠ', 'JLF', NULL, 'Iné', 'Študentská jedáleň - študenti'),
  ('JLF.ŠJZ', 'JLF', NULL, 'Iné', 'Študentská jedáleň - zamestnanci'),
  ('JLF.SNS', 'JLF', NULL, 'Iné', 'Spoločné nákladové stredisko'),
  ('JLF.SVC', 'JLF', NULL, 'Úč.pr', 'Simulačné výučbové centrum'),
  ('JLF.ÚA', 'JLF', NULL, 'Ústav', 'Ústav anatómie'),
  ('JLF.ÚCJ', 'JLF', NULL, 'Ústav', 'Ústav cudzích jazykov'),
  ('JLF.ÚFa', 'JLF', NULL, 'Ústav', 'Ústav farmakológie'),
  ('JLF.ÚFy', 'JLF', NULL, 'Ústav', 'Ústav fyziológie'),
  ('JLF.ÚHE', 'JLF', NULL, 'Ústav', 'Ústav histológie a embryológie'),
  ('JLF.ÚIT', 'JLF', NULL, 'Ústav', 'Ústav informačných technológií'),
  ('JLF.UK', 'JLF', NULL, 'Klin', 'Urologická klinika'),
  ('JLF.ÚKB', 'JLF', NULL, 'Ústav', 'Ústav klinickej biochémie'),
  ('JLF.ÚLBch', 'JLF', NULL, 'Ústav', 'Ústav lekárskej biochémie'),
  ('JLF.ÚLBf', 'JLF', NULL, 'Ústav', 'Ústav lekárskej biofyziky'),
  ('JLF.ÚLBl', 'JLF', NULL, 'Ústav', 'Ústav lekárskej biológie'),
  ('JLF.ÚMBl', 'JLF', NULL, 'Ústav', 'Ústav molekulovej biológie'),
  ('JLF.ÚMI', 'JLF', NULL, 'Ústav', 'Ústav mikrobiológie a imunológie'),
  ('JLF.ÚNŠP', 'JLF', NULL, 'Ústav', 'Ústav nelekárskych študijných programov'),
  ('JLF.ÚO', 'JLF', NULL, 'Ústav', 'Ústav ošetrovateľstva'),
  ('JLF.ÚPA', 'JLF', NULL, 'Ústav', 'Ústav patologickej anatómie'),
  ('JLF.ÚPAs', 'JLF', NULL, 'Ústav', 'Ústav pôrodnej asistencie'),
  ('JLF.ÚPF', 'JLF', NULL, 'Ústav', 'Ústav patologickej fyziológie'),
  ('JLF.ÚSLME', 'JLF', NULL, 'Ústav', 'Ústav súdneho lekárstva a medicínskych expertíz'),
  ('JLF.ÚTV', 'JLF', NULL, 'Ústav', 'Ústav telesnej výchovy'),
  ('JLF.ÚVZ', 'JLF', NULL, 'Ústav', 'Ústav verejného zdravotnictva'),
  ('JLF.ÚVZ.OE', 'JLF.ÚVZ', NULL, 'Ústav', 'Ústav verejného zdravotníctva - oddelenie epidemiológie'),
  ('JLF.ÚVZ.OH', 'JLF.ÚVZ', NULL, 'Ústav', 'Ústav verejného zdravotníctva - oddelenie hygieny'),
  ('JLF.ÚVZ.OSL', 'JLF.ÚVZ', NULL, 'Ústav', 'Ústav verejného zdravotnictva - oddelenie sociálneho lekárstva'),
  ('JLF.VIJ', 'JLF', NULL, 'Úč.za', 'Vysokoškolský internát a jedáleň'),
  ('KŠ', 'UK', NULL, 'Iné', 'Kanadské študia '),
  ('LF', 'UK', 'UKOLF', 'Fakul', 'Lekárska fakulta'),
  ('LF.AK', 'LF', NULL, 'Úč.pr', 'Akademická knižnica LF UK'),
  ('LF.AÚ', 'LF', 'UKOLFAU', 'Ústav', 'Anatomický ústav LF UK'),
  ('LF.ChK1', 'LF', NULL, 'Klin', 'I. chirurgická klinika LF UK a UN Bratislava'),
  ('LF.ChK2', 'LF', NULL, 'Klin', 'II. chirurgická klinika LF UK a UN Bratislava'),
  ('LF.ChK3', 'LF', NULL, 'Klin', 'III. chirurgická klinika LF UK a UN MB'),
  ('LF.ChK4', 'LF', NULL, 'Klin', 'IV. chirurgická klinika LF UK a UN Bratislava'),
  ('LF.DDK', 'LF', NULL, 'Klin', 'Detská dermatovenerologická klinika LF UK a DFNsP'),
  ('LF.Dek', 'LF', NULL, 'Rekto', 'Dekanát'),
  ('LF.DK', 'LF', 'UKOLFDK', 'Klin', 'Dermatovenerologická klinika LF UK a UN Bratislava'),
  ('LF.DK1', 'LF', 'UKOLF1DK', 'Klin', 'I. detská klinika LF UK a DFNsP'),
  ('LF.DK2', 'LF', NULL, 'Klin', 'II. detská klinika LF UK a DFNsP'),
  ('LF.DOnK', 'LF', NULL, 'Klin', 'Klinika detskej hematológie a onkológie LF UK a DFNsP'),
  ('LF.DORLK', 'LF', NULL, 'Klin', 'Detská otorinolaryngologická klinika LF UK a DFNsP'),
  ('LF.DOrtK', 'LF', 'UKOLFDORT', 'Klin', 'Detská ortopedická klinika LF UK a DFNsP'),
  ('LF.FyÚ', 'LF', NULL, 'Ústav', 'Fyziologický ústav LF UK'),
  ('LF.GPK1', 'LF', NULL, 'Klin', 'I. gynekologicko-pôrodnícka klinika LF UK a UN Bratislava'),
  ('LF.GPK2', 'LF', 'UKOLF2GK', 'Klin', 'II. gynekologicko-pôrodnícka klinika LF UK a UN Bratislava'),
  ('LF.GPK3', 'LF', NULL, 'Klin', 'Klinika III. gynekologicko-pôrodnícka'),
  ('LF.IK1', 'LF', 'UKOLF1IK', 'Klin', 'I. interná klinika LF UK a UN Bratislava'),
  ('LF.IK2', 'LF', 'UKOLF2IK', 'Klin', 'II. interná klinika LF UK a UN Bratislava'),
  ('LF.IK3', 'LF', 'UKOLF3IK', 'Klin', 'III. interná klinika LF UK a UN Bratislava'),
  ('LF.IK4', 'LF', 'UKOLF4IK', 'Klin', 'IV. interná klinika LF UK a UN Bratislava'),
  ('LF.IK5', 'LF', 'UKOLF5IK', 'Klin', 'V. interná klinika LF UK a UN Bratislava'),
  ('LF.IÚ', 'LF', NULL, 'Ústav', 'Imunologický ústav LF UK'),
  ('LF.KAIM1', 'LF', NULL, 'Klin', 'I. klinika anestéziológie a intenzívnej medicíny LF UK a UN Bratislava'),
  ('LF.KAIM2', 'LF', NULL, 'Klin', 'II. klinika anestéziológie a intenzívnej medicíny LF UK a OÚSA'),
  ('LF.KDCh', 'LF', NULL, 'Klin', 'Klinika detskej chirurgie LF UK a DFNsP'),
  ('LF.KDK', 'LF', NULL, 'Klin', 'Klinika detskej kardiológie LF UK a DKC'),
  ('LF.KDN', 'LF', NULL, 'Klin', 'Klinika detskej neurológie LF UK a DFNsP'),
  ('LF.KDO', 'LF', NULL, 'Klin', 'Klinika detskej oftalmológie LF UK a DFNsP'),
  ('LF.KDP', 'LF', 'UKOLFKDP', 'Klin', 'Klinika detskej psychiatrie LF UK a DFNsP'),
  ('LF.KG1', 'LF', NULL, 'Klin', 'I. klinika geriatrie LF UK a UN Bratislava'),
  ('LF.KG2', 'LF', NULL, 'Klin', 'II. klinika geriatrie LF UK a UN MB'),
  ('LF.KHT', 'LF', NULL, 'Klin', 'Klinika hematológie a transfuziológie LF UK a UN Bratislava'),
  ('LF.KIGM', 'LF', NULL, 'Klin', 'Klinika infektológie a geografickej medicíny LF UK a UN Bratislava'),
  ('LF.KNM', 'LF', NULL, 'Klin', 'Klinika nukleárnej medicíny LF UK a OÚSA'),
  ('LF.KO', 'LF', 'UKOLFKO', 'Klin', 'Klinika oftalmológie LF UK a UN Bratislava'),
  ('LF.KOCh', 'LF', 'UKOLFKOCH', 'Klin', 'Klinika onkologickej chirurgie LF UK a OÚSA'),
  ('LF.KORL', 'LF', NULL, 'Klin', 'Klinika otol. a chirurgie hlavy a krku'),
  ('LF.KPF', 'LF', NULL, 'Klin', 'Klinika pneumológie a ftizeológie LF UK a UN Bratislava'),
  ('LF.KPLT', 'LF', NULL, 'Klin', 'Klinika pracovného lekárstva a toxikológie LF UK a UN Bratislava'),
  ('LF.KPRCh', 'LF', NULL, 'Klin', 'Klinika popálenín a rekonštrukčnej chirurgie LF UK a UN Bratislava'),
  ('LF.KPRECh', 'LF', NULL, 'Klin', 'Klinika plastickej, rekonštrukčnej a estetickej chirurgie LF UK a UN Bratislava'),
  ('LF.KSMCh', 'LF', NULL, 'Klin', 'Klinika stomatológie a maxilofaciálnej chirurgie LF UK a OÚSA'),
  ('LF.KTLFR', 'LF', NULL, 'Klin', 'Klinika telovýchovného lekárstva, fyziatrie a rehabilitácie LF UK a UN Bratislava'),
  ('LF.KÚČTCh', 'LF', NULL, 'Klin', 'Klinika ústnej, čeľustnej a tvárovej chirurgie LF UK a UN Bratislava'),
  ('LF.KUMMK', 'LF', 'UKOLFKUM', 'Klin', 'Klinika urgentnej medicíny a medicíny katastrof LF UK UN MB'),
  ('LF.MÚ', 'LF', 'UKOLFMIU', 'Ústav', 'Mikrobiologický ústav LF UK a UN Bratislava'),
  ('LF.NchK', 'LF', 'UKOLFNK', 'Klin', 'Neurochirurgická klinika LF UK a UN Bratislava'),
  ('LF.NK1', 'LF', 'UKOLF1NK', 'Klin', 'I. neurologická klinika LF UK a UN Bratislava'),
  ('LF.NK2', 'LF', NULL, 'Klin', 'II. neurologická klinika LF UK a UN Bratislava'),
  ('LF.OnK1', 'LF', NULL, 'Klin', 'I. onkologická klinika LF UK a OÚSA'),
  ('LF.OnK2', 'LF', 'UKOLF2ONK', 'Klin', 'II. onkologická klinika LF UK NOÚ'),
  ('LF.OP', 'LF', NULL, 'Úč.pr', 'Oddelenie prevádzky'),
  ('LF.ORLK1', 'LF', 'UKOLF1OK', 'Klin', 'I. otorinolaryngologická klinika LF UK a UN Bratislava'),
  ('LF.ORLK2', 'LF', NULL, 'Klin', 'II. otorinolaryngologická klinika LF UK a UN Bratislava'),
  ('LF.OTK1', 'LF', 'UKOLF1ORTK', 'Klin', 'I. ortopedicko-traumatologická klinika LF UK a UN Bratislava'),
  ('LF.OTK2', 'LF', NULL, 'Klin', 'II. ortopedicko-traumatologická klinika LF UK a UN Bratislava'),
  ('LF.PK', 'LF', 'UKOLFPK', 'Klin', 'Psychiatrická klinika LF UK a UN Bratislava'),
  ('LF.RedBLL', 'LF', NULL, 'Úč.pr', 'Redakcia časopisu Bratislavské lekárske listy'),
  ('LF.RK1', 'LF', 'UKOLF1RK', 'Klin', 'I. rádiologická klinika LF UK a UN Bratislava'),
  ('LF.RK2', 'LF', 'UKOLF2RK', 'Klin', 'II. rádiologická klinika LF UK a OÚSA'),
  ('LF.ÚCJ', 'LF', NULL, 'Ústav', 'Ústav cudzích jazykov LF UK'),
  ('LF.ÚE', 'LF', 'UKOLFUE', 'Ústav', 'Ústav epidemiológie LF UK'),
  ('LF.ÚFKF', 'LF', NULL, 'Ústav', 'Ústav farmakológie a klinickej farmakológie LF UK'),
  ('LF.ÚH', 'LF', 'UKOLFUH', 'Ústav', 'Ústav hygieny LF UK'),
  ('LF.ÚHE', 'LF', 'UKOLFUHE', 'Ústav', 'Ústav histológie a embryológie LF UK'),
  ('LF.UK', 'LF', NULL, 'Klin', 'Urologická klinika LF UK a UN Bratislava'),
  ('LF.ÚLBG', 'LF', NULL, 'Ústav', 'Ústav lekárskej biológie, genetiky a klinickej genetiky LF UK a UN Bratislava'),
  ('LF.ÚLChB', 'LF', 'UKOLFUL', 'Ústav', 'Ústav lekárskej chémie, biochémie a klinickej biochémie LF UK'),
  ('LF.ÚLF', 'LF', NULL, 'Ústav', 'Ústav lekárskej fotografie'),
  ('LF.ÚLFBIT', 'LF', NULL, 'Ústav', 'Ústav lekárskej fyziky, biofyziky, informatiky a telemedicíny LF UK'),
  ('LF.ÚLVM', 'LF', NULL, 'Ústav', 'Ústav laboratórnych vyšetrovacích metód LF UK a OÚSA'),
  ('LF.ÚMB', 'LF', 'UKOLFUMB', 'Ústav', 'Ústav molekulárnej biomedicíny'),
  ('LF.ÚO', 'LF', 'UKOLFUO', 'Ústav', 'Ústav ošetrovateľstva LF UK'),
  ('LF.ÚP', 'LF', NULL, 'Ústav', 'Ústav parazitologický'),
  ('LF.ÚPA', 'LF', 'UKOLFUPA', 'Ústav', 'Ústav patologickej anatómie LF UK a UN Bratislava'),
  ('LF.ÚPF', 'LF', 'UKOLFUPF', 'Ústav', 'Ústav patologickej fyziológie LF UK'),
  ('LF.ÚSL', 'LF', 'UKOLFUSUL', 'Ústav', 'Ústav súdneho lekárstva LF UK'),
  ('LF.ÚSLLE', 'LF', 'UKOLFUSOL', 'Ústav', 'Ústav sociálneho lekárstva a lekárskej etiky LF UK'),
  ('LF.USVMV', 'LF', NULL, 'Úč.pr', 'Ústav simulačného a virtuálneho medicínskeho vzdelávania'),
  ('LF.ÚTVŠ', 'LF', 'UKOLFUTVS', 'Ústav', 'Ústav telesnej výchovy a športu LF UK'),
  ('LF.VS', 'LF', NULL, 'Úč.pr', 'Výpočtové stredisko LF UK'),
  ('PdF', 'UK', 'UKOPD', 'Fakul', 'Pedagogická fakulta'),
  ('PdF.AK', 'PdF', NULL, 'Úč.pr', 'Akademická knižnica'),
  ('PdF.CPV', 'PdF', NULL, 'Výsku', 'Centr.pedagogického výskumu'),
  ('PdF.CŠPV', 'PdF', NULL, 'Výsku', 'Centrum špeciálnopedagog.výskumu'),
  ('PdF.CVPaPPP', 'PdF', NULL, 'Výsku', 'Centrum výsk.prim. a predprimpedagogiky'),
  ('PdF.CVSPLP', 'PdF', NULL, 'Výsku', 'Centrum výsk. v soc. práci a liečeb.peda'),
  ('PdF.Dek', 'PdF', NULL, 'Rekto', 'Dekanát'),
  ('PdF.EO', 'PdF', NULL, 'Refer', 'Ekonomické oddelenie'),
  ('PdF.IIKS', 'PdF', NULL, 'Úč.pr', 'Integrovaný informačný a komunikačný systém'),
  ('PdF.KAJL', 'PdF', NULL, 'Kated', 'Katedra anglického jazyka a literatúry'),
  ('PdF.KBl', 'PdF', 'UKOPDBIO', 'Kated', 'Katedra biológie'),
  ('PdF.KEOV', 'PdF', 'UKOPDEOV', 'Kated', 'Katedra etickej a občianskej výchovy'),
  ('PdF.KH', 'PdF', NULL, 'Kated', 'Katedra histórie'),
  ('PdF.KHV', 'PdF', NULL, 'Kated', 'Katedra hudobnej výchovy'),
  ('PdF.KL', 'PdF', NULL, 'Kated', 'Katedra logopédie'),
  ('PdF.KLP', 'PdF', NULL, 'Kated', 'Katedra liečebnej pedagogiky'),
  ('PdF.KMI', 'PdF', NULL, 'Kated', 'Katedra matematiky a informatiky'),
  ('PdF.KNJL', 'PdF', 'UKOPDNJL', 'Kated', 'Katedra nemeckého jazyka a literatúry'),
  ('PdF.KPEP', 'PdF', 'UKOPDPEP', 'Kated', 'Katedra predprimárnej a primárnej pedagogiky'),
  ('PdF.KPg', 'PdF', NULL, 'Kated', 'Katedra pedagogiky a sociálnej pedagogiky - oddelenie pedagogiky'),
  ('PdF.KPsPp', 'PdF', NULL, 'Kated', 'Katedra psychológie a patopsychológie'),
  ('PdF.KRoJL', 'PdF', NULL, 'Kated', 'Katedra románskych jazykov a literatúr'),
  ('PdF.KŠE', 'PdF', NULL, 'Kated', 'predmety športovej edukológie'),
  ('PdF.KSJL', 'PdF', 'UKOPDSJL', 'Kated', 'Katedra slovenského jazyka a literatúry'),
  ('PdF.KSP', 'PdF', NULL, 'Kated', 'Katedra sociálnej práce'),
  ('PdF.KŠP', 'PdF', 'UKOPDSPP', 'Kated', 'Katedra špeciálnej pedagogiky'),
  ('PdF.KSPg', 'PdF', NULL, 'Kated', 'Katedra pedagogiky a sociálnej pedagogiky - oddelenie sociálnej pedagogiky'),
  ('PdF.KVV', 'PdF', NULL, 'Kated', 'Katedra výtvarnej výchovy'),
  ('PdF.OP', 'PdF', NULL, 'Úč.pr', 'Oddelenie prevádzky'),
  ('PdF.OVDŠ', 'PdF', NULL, 'Oddel', 'Odd. pre vedu a doktorandské štúdium'),
  ('PdF.RCV', 'PdF', NULL, 'Refer', 'Referát celoživotného vzdelávania'),
  ('PdF.RZS', 'PdF', NULL, 'Refer', 'Referát zahraničných stykov'),
  ('PdF.ŠO', 'PdF', NULL, 'Oddel', 'Študijné oddelenie'),
  ('PdF.TJSP', 'PdF', NULL, 'Iné', 'TJ Slávia Pedagóg'),
  ('PdF.ÚHŠ', 'PdF', NULL, 'Ústav', 'Ústav humanitných štúdií'),
  ('PP', 'UK', NULL, 'Iné', 'Psychologická poradňa'),
  ('PraF', 'UK', 'UKOPA', 'Fakul', 'Právnická fakulta'),
  ('PraF.AK', 'PraF', NULL, 'Úč.pr', 'Akademická knižnica Právnickej fakulty'),
  ('PraF.Dek', 'PraF', NULL, 'Rekto', 'Dekanát'),
  ('PraF.EO', 'PraF', NULL, 'Refer', 'Ekonomické oddelenie'),
  ('PraF.KEVPIT', 'PraF', NULL, 'Kated', 'Katedra ekonomických vied a práva informačných a komunikačných technológií'),
  ('PraF.KMPEP', 'PraF', NULL, 'Kated', 'Katedra medzinárodného práva a európskeho práva'),
  ('PraF.KOFHP', 'PraF', 'UKOPAHP', 'Kated', 'Katedra obchodného, finančného a hospodárskeho práva'),
  ('PraF.KOP', 'PraF', NULL, 'Kated', 'Katedra občianskeho práva'),
  ('PraF.KPD', 'PraF', 'UKOPADS', 'Kated', 'Katedra právnych dejín'),
  ('PraF.KPKTŠ', 'PraF', NULL, 'Kated', 'Katedra právnej komunikácie, telovýchovy a športu'),
  ('PraF.KPPSZ', 'PraF', NULL, 'Kated', 'Katedra pracovného práva a práva sociálneho zabezpečenia'),
  ('PraF.KSEP', 'PraF', NULL, 'Kated', 'Katedra správneho a environmentálneho práva'),
  ('PraF.KTPKK', 'PraF', NULL, 'Kated', 'Katedra trestného práva, kriminológie a kriminalistiky'),
  ('PraF.KTPSV', 'PraF', NULL, 'Kated', 'Katedra teórie práva a sociálnych vied'),
  ('PraF.KÚP', 'PraF', NULL, 'Kated', 'Katedra ústavného práva'),
  ('PraF.OEVČ', 'PraF', NULL, 'Refer', 'Oddelenie edičnej a vydavateľskej činnosti'),
  ('PraF.OIT', 'PraF', NULL, 'Oddel', 'Oddelenie informačných technológií'),
  ('PraF.OVV', 'PraF', NULL, 'Refer', 'Oddelenie vedy, výskumu, rigorózneho konania, ďalšieho vzdelávania, grantovej politiky a medzinárodných vzťahov'),
  ('PraF.ROČ', 'PraF', NULL, 'Refer', 'Referát obslužných činností'),
  ('PraF.RPP', 'PraF', NULL, 'Refer', 'Referát personálnej práce'),
  ('PraF.SD', 'PraF', NULL, 'Oddel', 'Sekretariát dekana a tajomníka PraF UK'),
  ('PraF.SO', 'PraF', NULL, 'Refer', 'Študijné oddelenie'),
  ('PraF.ÚMVPK', 'PraF', 'UKOPAMV', 'Ústav', 'Ústav medzinárodných vzťahov a právnej komparatistiky'),
  ('PraF.VO', 'PraF', NULL, 'Refer', 'Vydavateľské oddelenie PraF UK'),
  ('PriF', 'UK', 'UKOPR', 'Fakul', 'Prírodovedecká fakulta'),
  ('PriF.BSŠ', 'PriF', NULL, 'Iné', 'Biologická stanica Šúr'),
  ('PriF.ChÚ', 'PriF', 'UKOPRCUS', 'Ústav', 'Chemický ústav'),
  ('PriF.CLEOM', 'PriF', NULL, 'Iné', 'Centr.labor.elektrónovo-optických metód'),
  ('PriF.CPS', 'PriF', NULL, 'Iné', 'Centrum projektovej spolupráce PriFUK'),
  ('PriF.Dek', 'PriF', NULL, 'Rekto', 'Dekanát'),
  ('PriF.GÚ', 'PriF', NULL, 'Ústav', 'Geologický ústav'),
  ('PriF.KAEG', 'PriF', 'UKOPRGGF', 'Kated', 'Katedra aplikovanej a environmentálnej geofyziky'),
  ('PriF.KAgCh', 'PriF', 'UKOPRCAG', 'Kated', 'Katedra anorganickej chémie'),
  ('PriF.KAlCh', 'PriF', NULL, 'Kated', 'Katedra analytickej chémie'),
  ('PriF.KAn', 'PriF', 'UKOPRBAN', 'Kated', 'Katedra antropológie'),
  ('PriF.KBCh', 'PriF', 'UKOPRCBI', 'Kated', 'Katedra biochémie'),
  ('PriF.KBo', 'PriF', NULL, 'Kated', 'Katedra botaniky'),
  ('PriF.KDPP', 'PriF', 'UKOPRDP', 'Kated', 'Katedra didaktiky prírodných vied, pedagogiky a psychológie'),
  ('PriF.KEF', 'PriF', 'UKOPREEF', 'Kated', 'Katedra environmentálnej ekológie'),
  ('PriF.KEk', 'PriF', 'UKOPRBEK', 'Kated', 'Katedra ekológie'),
  ('PriF.KFGG', 'PriF', 'UKOPRZFG', 'Kated', 'Katedra fyzickej geografie a geoekológie'),
  ('PriF.KFR', 'PriF', NULL, 'Kated', 'Katedra fyziológie rastlín'),
  ('PriF.KFTCh', 'PriF', 'UKOPRCFZ', 'Kated', 'Katedra fyzikálnej a teoretickej chémie'),
  ('PriF.KGCh', 'PriF', 'UKOPREGE', 'Kated', 'Katedra geochémie'),
  ('PriF.KGe', 'PriF', NULL, 'Kated', 'Katedra genetiky'),
  ('PriF.KGP', 'PriF', NULL, 'Kated', 'Katedra geológie a paleontológie'),
  ('PriF.KHGD', 'PriF', NULL, 'Kated', 'Katedra humánnej geografie a demografie'),
  ('PriF.KHy', 'PriF', 'UKOPRGHY', 'Kated', 'Katedra hydrogeológie'),
  ('PriF.KIG', 'PriF', NULL, 'Kated', 'Katedra inžinierskej geológie'),
  ('PriF.KJ', 'PriF', NULL, 'Kated', 'Katedra jazykov'),
  ('PriF.KJCh', 'PriF', NULL, 'Kated', 'Katedra jadrovej chémie'),
  ('PriF.KKE', 'PriF', 'UKOPREKE', 'Kated', 'Katedra krajinnej ekológie'),
  ('PriF.KKGDPZ', 'PriF', 'UKOPRZGK', 'Kated', 'Katedra kartografie, geoinformatiky a diaľkového prieskumu zeme'),
  ('PriF.KLG', 'PriF', 'UKOPRGLG', 'Kated', 'Katedra ložiskovej geológie'),
  ('PriF.KMB', 'PriF', NULL, 'Kated', 'Katedra molekulárnej biológie'),
  ('PriF.KMP', 'PriF', 'UKOPRGMP', 'Kated', 'Katedra mineralógie a petrológie'),
  ('PriF.KMV', 'PriF', NULL, 'Kated', 'Katedra mikrobiológie a virológie'),
  ('PriF.KOrCh', 'PriF', NULL, 'Kated', 'Katedra organickej chémie'),
  ('PriF.KPl', 'PriF', NULL, 'Kated', 'Katedra pedológie'),
  ('PriF.KRGOPK', 'PriF', NULL, 'Kated', 'Katedra regionálnej geografie, ochrany a plánovania krajiny'),
  ('PriF.KTV', 'PriF', NULL, 'Kated', 'Katedra telesnej výchovy'),
  ('PriF.KZ', 'PriF', 'UKOPRZO', 'Kated', 'Katedra zoológie'),
  ('PriF.KŽFE', 'PriF', 'UKOPRBZF', 'Kated', 'Katedra živočíšnej fyziológie a etológie'),
  ('PriF.OPA', 'PriF', NULL, 'Úč.pr', 'Oddelenie prevádzky a autodopravy'),
  ('PriF.PVOC', 'PriF', NULL, 'Iné', 'Prírodovedné vzdelávacie a osvetové centrum'),
  ('PriF.ÚBB', 'PriF', 'UKOPRBUB', 'Ústav', 'Ústav bunkovej biológie'),
  ('PriF.ÚK', 'PriF', NULL, 'Úč.pr', 'Ústredná knižnica PriFUK'),
  ('PriF.VECIT', 'PriF', NULL, 'Úč.pr', 'Výskumno-edukačné centrum informačných technológií'),
  ('PriF.VS', 'PriF', NULL, 'Úč.pr', 'Výpočtové stredisko'),
  ('RKCMBF', 'UK', NULL, 'Fakul', 'Rímskokatolícka cyrilometodská bohoslovecká fakulta'),
  ('RKCMBF.AU', 'RKCMBF', NULL, 'Úsek', 'Administratívny úsek'),
  ('RKCMBF.Bi', 'RKCMBF', NULL, 'Kated', 'Katedra biblických vied'),
  ('RKCMBF.Bi.BA', 'RKCMBF.Bi', NULL, 'Oddel', 'Katedra biblických vied, Bratislava'),
  ('RKCMBF.Bi.BB', 'RKCMBF.Bi', NULL, 'Oddel', 'Katedra biblických vied, Badín'),
  ('RKCMBF.Bi.N', 'RKCMBF.Bi', NULL, 'Oddel', 'Katedra biblických vied, Nitra'),
  ('RKCMBF.Bi.Ž', 'RKCMBF.Bi', NULL, 'Oddel', 'Katedra biblických vied, Žilina'),
  ('RKCMBF.CD', 'RKCMBF', NULL, 'Kated', 'Katedra cirkevných dejín'),
  ('RKCMBF.CD.BA', 'RKCMBF.CD', NULL, 'Oddel', 'Katedra cirkevných dejín, Bratislava'),
  ('RKCMBF.CD.BB', 'RKCMBF.CD', NULL, 'Oddel', 'Katedra cirkevných dejín, Badín'),
  ('RKCMBF.CD.N', 'RKCMBF.CD', NULL, 'Oddel', 'Katedra cirkevných dejín, Nitra'),
  ('RKCMBF.CD.Ž', 'RKCMBF.CD', NULL, 'Oddel', 'Katedra cirkevných dejín, Žilina'),
  ('RKCMBF.Dek', 'RKCMBF', NULL, 'Rekto', 'Dekanát'),
  ('RKCMBF.Do', 'RKCMBF', NULL, 'Kated', 'Katedra dogmatickej teológie'),
  ('RKCMBF.Do.BA', 'RKCMBF.Do', NULL, 'Oddel', 'Katedra dogmatickej teológie, Bratislava'),
  ('RKCMBF.Do.BB', 'RKCMBF.Do', NULL, 'Oddel', 'Katedra dogmatickej teológie, Badín'),
  ('RKCMBF.Do.N', 'RKCMBF.Do', NULL, 'Oddel', 'Katedra dogmatickej teológie, Nitra'),
  ('RKCMBF.Do.Ž', 'RKCMBF.Do', NULL, 'Oddel', 'Katedra dogmatickej teológie, Žilina'),
  ('RKCMBF.Fi', 'RKCMBF', NULL, 'Kated', 'Katedra filozofie'),
  ('RKCMBF.Fi.BA', 'RKCMBF.Fi', NULL, 'Oddel', 'Katedra filozofie, Bratislava'),
  ('RKCMBF.Fi.BB', 'RKCMBF.Fi', NULL, 'Oddel', 'Katedra filozofie, Badín'),
  ('RKCMBF.Fi.N', 'RKCMBF.Fi', NULL, 'Oddel', 'Katedra filozofie, Nitra'),
  ('RKCMBF.Fi.Ž', 'RKCMBF.Fi', NULL, 'Oddel', 'Katedra filozofie, Žilina'),
  ('RKCMBF.KaP', 'RKCMBF', NULL, 'Kated', 'Katedra katechetiky a pedagogiky'),
  ('RKCMBF.KaP.BA', 'RKCMBF.KaP', NULL, 'Oddel', 'Katedra katechetiky a pedagogiky, Bratislava'),
  ('RKCMBF.KaP.BB', 'RKCMBF.KaP', NULL, 'Oddel', 'Katedra katechetiky a pedagogiky, Badín'),
  ('RKCMBF.KaP.N', 'RKCMBF.KaP', NULL, 'Oddel', 'Katedra katechetiky a pedagogiky, Nitra'),
  ('RKCMBF.KaP.Ž', 'RKCMBF.KaP', NULL, 'Oddel', 'Katedra katechetiky a pedagogiky, Žilina'),
  ('RKCMBF.Kn', 'RKCMBF', NULL, 'Úč.pr', 'Knižnica RKCMBF UK'),
  ('RKCMBF.KP', 'RKCMBF', NULL, 'Kated', 'Katedra kánonického práva'),
  ('RKCMBF.KP.BA', 'RKCMBF.KP', NULL, 'Oddel', 'Katedra kánonického práva, Bratislava'),
  ('RKCMBF.KP.BB', 'RKCMBF.KP', NULL, 'Oddel', 'Katedra kánonického práva, Badín'),
  ('RKCMBF.KP.N', 'RKCMBF.KP', NULL, 'Oddel', 'Katedra kánonického práva, Nitra'),
  ('RKCMBF.KP.Ž', 'RKCMBF.KP', NULL, 'Oddel', 'Katedra kánonického práva, Žilina'),
  ('RKCMBF.Li', 'RKCMBF', NULL, 'Kated', 'Katedra liturgiky'),
  ('RKCMBF.Li.BA', 'RKCMBF.Li', NULL, 'Oddel', 'Katedra liturgiky, Bratislava'),
  ('RKCMBF.Li.BB', 'RKCMBF.Li', NULL, 'Oddel', 'Katedra liturgiky, Badín'),
  ('RKCMBF.Li.N', 'RKCMBF.Li', NULL, 'Oddel', 'Katedra liturgiky, Nitra'),
  ('RKCMBF.Li.Ž', 'RKCMBF.Li', NULL, 'Oddel', 'Katedra liturgiky, Žilina'),
  ('RKCMBF.Mo', 'RKCMBF', NULL, 'Kated', 'Katedra morálnej teológie'),
  ('RKCMBF.Mo.BA', 'RKCMBF.Mo', NULL, 'Oddel', 'Katedra morálnej teológie, Bratislava'),
  ('RKCMBF.Mo.BB', 'RKCMBF.Mo', NULL, 'Oddel', 'Katedra morálnej teológie, Badín'),
  ('RKCMBF.Mo.N', 'RKCMBF.Mo', NULL, 'Oddel', 'Katedra morálnej teológie, Nitra'),
  ('RKCMBF.Mo.Ž', 'RKCMBF.Mo', NULL, 'Oddel', 'Katedra morálnej teológie, Žilina'),
  ('RKCMBF.OP', 'RKCMBF', NULL, 'Úč.pr', 'Oddelenie prevádzky'),
  ('RKCMBF.Pa', 'RKCMBF', NULL, 'Kated', 'Katedra pastorálnej teológie'),
  ('RKCMBF.Pa.BA', 'RKCMBF.Pa', NULL, 'Oddel', 'Katedra pastorálnej teológie, Bratislava'),
  ('RKCMBF.Pa.BB', 'RKCMBF.Pa', NULL, 'Oddel', 'Katedra pastorálnej teológie, Badín'),
  ('RKCMBF.Pa.N', 'RKCMBF.Pa', NULL, 'Oddel', 'Katedra pastorálnej teológie, Nitra'),
  ('RKCMBF.Pa.Ž', 'RKCMBF.Pa', NULL, 'Oddel', 'Katedra pastorálnej teológie, Žilina'),
  ('RKCMBF.ŠD', 'RKCMBF', NULL, 'Úč.pr', 'Študentský domov RKCMBF UK'),
  ('RKCMBF.ŠDBB', 'RKCMBF', NULL, 'Úč.pr', 'Študentský domov KS Badín'),
  ('RKCMBF.ŠDN', 'RKCMBF', NULL, 'Úč.pr', 'Študentský domov KS Nitra'),
  ('RKCMBF.ŠJ', 'RKCMBF', NULL, 'Iné', 'Študentská jedáleň'),
  ('RKCMBF.ŠJB', 'RKCMBF', NULL, 'Iné', 'Študentská jedáleň Badín'),
  ('RKCMBF.ŠJZ', 'RKCMBF', NULL, 'Iné', 'Študentská jedáleň - zamestnanci'),
  ('RKCMBF.SNS.BB', 'RKCMBF', NULL, 'Úč.pr', 'Spoločné nákladové stredisko za KS Badín'),
  ('RKCMBF.SNS.N', 'RKCMBF', NULL, 'Úč.pr', 'Spoločné nákladové stredisko za KS Nitra'),
  ('RKCMBF.TI', 'RKCMBF', NULL, 'Úč.pr', 'Teologický inštitút'),
  ('RKCMBF.TI.BB', 'RKCMBF', NULL, 'Úč.pr', 'Teologický inštitút v Badíne'),
  ('RKCMBF.TI.N', 'RKCMBF', NULL, 'Úč.pr', 'Teologický inštitút v Nitre'),
  ('RKCMBF.TI.Ž', 'RKCMBF', NULL, 'Úč.pr', 'Inštitút v Žiline'),
  ('RUK', 'UK', NULL, 'Rekto', 'Rektorát'),
  ('STU', NULL, NULL,'Unive', 'Slovenská technická univerzita'),
  ('STU.FChPT', 'STU', NULL, 'Fakul', 'Fakulta chemickej a potravinárskej technológie'),
  ('UK', NULL, 'UKO', 'Unive', 'Univerzita Komenského v Bratislave'),
  ('UKP', 'UK', NULL, 'Iné', 'UNESCO Katedra prekladateľstva'),
  ('UVZM', 'UK', NULL, 'Úč.za', 'Učebno-výcvikové zariadenie Modra-Piesky'),
  ('UVZR', 'UK', NULL, 'Úč.za', 'Učebno-výcvikové zariadenie Richňava'),
  ('VIDr', 'UK', NULL, 'Iné', 'Vysokoškolský internát Družba'),
  ('VIDr.ŠD', 'VIDr', NULL, 'Úč.pr', 'Študentský domov VI Družba'),
  ('VIDr.ŠJ', 'VIDr', NULL, 'Iné', 'Študentská jedáleň VI Družba'),
  ('VIDr.ŠJRUK', 'VIDr', NULL, 'Iné', 'ŠJ RUK VI Družba'),
  ('VIDr.ŠJRUKZ', 'VIDr', NULL, 'Iné', 'ŠJ RUK VI Družba zamestnanci'),
  ('VIDr.ŠJZ', 'VIDr', NULL, 'Iné', 'ŠJ VI Družba zamestnanci'),
  ('VIDr.ŠvD', 'VIDr', NULL, 'Úč.pr', 'Švédske domky'),
  ('VMLS', 'UK', NULL, 'Iné', 'Vysokoškolské mesto Ľ. Štúra - Mlyny'),
  ('VMLS.ŠD', 'VMLS', NULL, 'Úč.pr', 'Študentský domov VMĽŠ - Mlyny UK'),
  ('VMLS.ŠJ', 'VMLS', NULL, 'Iné', 'Študentská jedáleň VMĽŠ - Mlyny UK'),
  ('VMLS.ŠJV9', 'VMLS', NULL, 'Iné', 'ŠJ V9 VMĽ: Štúra'),
  ('VMLS.ŠJV9Š', 'VMLS', NULL, 'Iné', 'ŠJ V9 VMĽ: Štúra -Mlyny Š'),
  ('VMLS.ŠJV9Z', 'VMLS', NULL, 'Iné', 'ŠJ V9 VMĽ: Štúra -Mlyny Z'),
  ('VMLS.ŠJZ', 'VMLS', NULL, 'Iné', 'ŠJ VMĽŠ - Mlyny UK zamestnanci'),
  ('Vyd', 'UK', NULL, 'Iné', 'Vydavateľstvo'),
  ('Vyd.PS', 'Vyd', NULL, 'Iné', 'Polygrafické stredisko UK')
;

CREATE TABLE osoba (
  id serial not null primary key,
  uoc integer,
  login varchar(50),
  ais_id integer,
  meno varchar(250),
  priezvisko varchar(250),
  cele_meno varchar(250),
  rodne_priezvisko varchar(250),
  vyucujuci boolean,
  UNIQUE (uoc),
  UNIQUE (login),
  UNIQUE (ais_id)
);

CREATE TABLE druh_cinnosti (
  kod char(1) not null primary key,
  ais_sposob_vyucby varchar(10),
  popis varchar(50) not null,
  poradie integer not null,
  povolit_vyber boolean,
  UNIQUE (ais_sposob_vyucby)
);

INSERT INTO druh_cinnosti (poradie, kod, ais_sposob_vyucby, popis, povolit_vyber)
VALUES
  ( 1, 'P', 'P',  'prednáška', true),
  ( 2, 'C', 'C',  'cvičenie', true),
  ( 3, 'S', 'S',  'seminár', true),
  ( 4, 'L', 'L',  'laboratórne práce', true),
  ( 5, 'K', 'K',  'kurz', true),
  ( 6, 'X', 'X',  'prax', true),
  ( 7, 'D', 'D',  'samostatná práca', false),
  ( 8, 'T', 'T',  'práca v teréne', false),
  ( 9, 'U', 'Su', 'sústredenie', false),
  (10, 'E', 'E',  'exkurzia', true),
  (11, 'R', 'PS', 'prednáška + seminár', true),
  (99, 'I', 'I',  'iná', false)
;

COMMENT ON TABLE druh_cinnosti IS 'Druhy cinnosti, ktore sa mozu robit na predmetoch';
COMMENT ON COLUMN druh_cinnosti.ais_sposob_vyucby IS 'AISovy sposob vyucby, na ktory sa tento druh cinnosti najblizsie mapuje';
COMMENT ON COLUMN druh_cinnosti.povolit_vyber IS 'Ci sa ma povolit vyber tejto polozky pri editacii';

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
  popis varchar(50) not null,
  povolit_vyber boolean not null,
  poradie int not null
);

INSERT INTO typ_vyucujuceho (kod, popis, povolit_vyber, poradie)
VALUES
  ('P', 'prednášajúci', true, 1),
  ('C', 'cvičiaci', true, 2),
  ('H', 'hodnotiaci', false, 3),
  ('L', 'laborant', false, 4),
  ('S', 'skúšajúci', false, 5),
  ('G', 'garant predmetu', false, 6),
  ('A', 'administrátor', false, 7),
  ('V', 'vedúci seminára', false, 8)
;

COMMENT ON TABLE typ_vyucujuceho IS 'Prebrate z AISoveho ciselniku SCSTTypVyucujuceho';

CREATE TABLE jazyk_vyucby (
  kod varchar(10) not null primary key,
  popis varchar(50) not null
);

INSERT INTO jazyk_vyucby (kod, popis)
VALUES
  ('sk_en', 'slovenský, anglický')
;

CREATE TABLE literatura (
  bib_id integer not null primary key,
  dokument varchar(2000) not null,
  vyd_udaje varchar(2000),
  dostupne boolean not null,
  signatura text
);

CREATE TABLE ilsp_opravnenia (
  osoba integer not null references osoba(id),
  organizacna_jednotka varchar(100) not null references organizacna_jednotka(kod),
  je_admin boolean not null default false,
  je_garant boolean not null default false
  primary key (osoba, organizacna_jednotka)
);

INSERT INTO ilsp_opravnenia (osoba, organizacna_jednotka, je_admin, je_garant)
SELECT o.id, 'FMFI', true, false
FROM osoba o WHERE o.login IN ('sucha14', 'vinar1');

CREATE TABLE infolist_verzia (
  id serial not null primary key,
  podm_absol_percenta_skuska integer,
  podm_absol_percenta_na_a integer,
  podm_absol_percenta_na_b integer,
  podm_absol_percenta_na_c integer,
  podm_absol_percenta_na_d integer,
  podm_absol_percenta_na_e integer,
  nepouzivat_stupnicu boolean not null default false,
  hodnotenia_a_pocet integer,
  hodnotenia_b_pocet integer,
  hodnotenia_c_pocet integer,
  hodnotenia_d_pocet integer,
  hodnotenia_e_pocet integer,
  hodnotenia_fx_pocet integer,
  podmienujuce_predmety text not null,
  odporucane_predmety text not null,
  vylucujuce_predmety text not null,
  modifikovane timestamp not null default now(),
  modifikoval integer references osoba(id),
  hromadna_zmena boolean not null default false,
  pocet_kreditov integer,
  predosla_verzia integer references infolist_verzia(id),
  fakulta varchar(100) not null references organizacna_jednotka(kod),
  potrebny_jazyk varchar(10) not null references jazyk_vyucby(kod),
  treba_zmenit_kod boolean not null,
  predpokladany_semester char(1),
  predpokladany_stupen_studia varchar(10),
  finalna_verzia boolean not null default false,
  bude_v_povinnom boolean not null default false,
  obsahuje_varovania boolean not null default false,
  podm_absol_percenta_zapocet integer
);

COMMENT ON COLUMN infolist_verzia.podm_absol_percenta_skuska IS 'podiel zaverecneho hodnotenia na znamke (priebezne je 100 - tato hodnota)';
COMMENT ON COLUMN infolist_verzia.predpokladany_semester IS 'Z (zimny) alebo L (letny) alebo N (neurceny)';

CREATE TABLE infolist_verzia_preklad (
  infolist_verzia integer not null references infolist_verzia(id),
  jazyk_prekladu varchar(2) not null,
  nazov_predmetu varchar(300) not null,
  podm_absol_priebezne text,
  podm_absol_skuska text,
  podm_absol_nahrada text,
  vysledky_vzdelavania text,
  strucna_osnova text,
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
  pocet_hodin integer not null,
  za_obdobie char(1) not null,
  primary key (infolist_verzia, druh_cinnosti)
);

COMMENT ON COLUMN infolist_verzia_cinnosti.pocet_hodin IS 'Pocet hodin vyucby za obdobie';
COMMENT ON COLUMN infolist_verzia_cinnosti.za_obdobie IS 'Urcuje za ake obdobie je dany pocet hodin (S=semester, T=tyzden)';

CREATE TABLE infolist_verzia_literatura (
  infolist_verzia integer not null references infolist_verzia(id),
  bib_id integer not null references literatura(bib_id),
  poradie integer not null,
  primary key (infolist_verzia, bib_id),
  unique (infolist_verzia, poradie)
);

CREATE TABLE infolist_verzia_nova_literatura (
  infolist_verzia integer not null references infolist_verzia(id),
  popis varchar(2000) not null,
  poradie integer not null,
  primary key (infolist_verzia, popis),
  unique (infolist_verzia, poradie)
);

CREATE TABLE infolist (
  id serial not null primary key,
  posledna_verzia integer not null references infolist_verzia(id),
  import_z_aisu boolean not null default false,
  forknute_z integer references infolist(id),
  zamknute timestamp,
  zamkol integer references osoba(id),
  povodny_kod_predmetu varchar(200),
  vytvorene timestamp not null default now(),
  vytvoril integer references osoba(id),
  zahodeny boolean not null default false
);

CREATE index ON infolist (posledna_verzia);

CREATE TABLE predmet (
  id serial not null primary key,
  kod_predmetu varchar(200) unique,
  skratka varchar(200),
  zmenit_kod boolean default false,
  vytvorene timestamp not null default now(),
  vytvoril integer references osoba(id),
  povodny_kod varchar(200) unique,
  povodna_skratka varchar(200)
);

CREATE TABLE predmet_infolist (
  predmet integer not null references predmet(id),
  infolist integer not null references infolist(id),
  primary key (predmet, infolist)
);
CREATE index ON predmet_infolist (infolist);

CREATE TABLE infolist_verzia_suvisiace_predmety (
  infolist_verzia integer not null references infolist_verzia(id),
  predmet integer not null references predmet(id),
  primary key (infolist_verzia, predmet)
);

CREATE TABLE infolist_verzia_modifikovali (
  infolist_verzia integer not null references infolist_verzia(id),
  osoba integer not null references osoba(id),
  primary key (infolist_verzia, osoba)
);

CREATE SEQUENCE predmet_novy_kod;

CREATE TABLE oblubene_predmety (
  predmet integer not null references predmet(id),
  osoba integer not null references osoba(id),
  primary key (predmet, osoba)
);
CREATE index ON oblubene_predmety(osoba);

CREATE TABLE studprog_verzia (
  id serial primary key,
  aj_konverzny_program boolean not null default false,
  stupen_studia varchar(10) not null,
  garant integer references osoba(id),
  modifikovane timestamp not null default now(),
  modifikoval integer references osoba(id),
  obsahuje_varovania boolean not null default false,
  finalna_verzia boolean not null default false,
  predosla_verzia integer references studprog_verzia(id)
);

CREATE TABLE studprog_verzia_preklad (
  studprog_verzia integer not null references studprog_verzia(id),
  jazyk_prekladu varchar(2) not null,
  nazov varchar(300),
  podmienky_absolvovania text not null,
  poznamka_konverzny text not null,
  primary key (studprog_verzia, jazyk_prekladu)
);

CREATE TABLE studprog_verzia_blok (
  studprog_verzia integer not null references studprog_verzia(id),
  poradie_blok integer not null,
  typ char(1) not null,
  primary key (studprog_verzia, poradie_blok)
);

CREATE TABLE studprog_verzia_blok_preklad (
  studprog_verzia integer not null,
  jazyk_prekladu varchar(2) not null,
  poradie_blok integer not null,
  nazov varchar(300) not null,
  podmienky text not null,
  foreign key (studprog_verzia, poradie_blok) references studprog_verzia_blok(studprog_verzia, poradie_blok)
);

CREATE TABLE studprog_verzia_blok_infolist (
  studprog_verzia integer not null,
  poradie_blok integer not null,
  infolist integer not null references infolist(id),
  semester char(1) not null,
  rocnik integer,
  poznamka text not null,
  predmet_jadra boolean not null,
  primary key (studprog_verzia, poradie_blok, infolist),
  foreign key (studprog_verzia, poradie_blok) references studprog_verzia_blok(studprog_verzia, poradie_blok)
);

CREATE TABLE studprog_verzia_modifikovali (
  studprog_verzia integer not null references studprog_verzia(id),
  osoba integer not null references osoba(id),
  primary key (studprog_verzia, osoba)
);

CREATE TABLE subor (
  id serial not null primary key,
  posledna_verzia integer references subor_verzia(id)
);

CREATE TABLE studprog (
  id serial not null primary key,
  skratka varchar(200) unique,
  posledna_verzia integer not null references studprog_verzia(id),
  zamknute timestamp,
  zamkol integer references osoba(id),
  vytvorene timestamp not null default now(),
  vytvoril integer references osoba(id),
  oblast_vyskumu varchar(20),
  formular integer references subor(id),
  formular_konverzny integer references subor(id)
);

CREATE TABLE subor_verzia (
  id serial not null primary key,
  predosla_verzia integer references subor_verzia(id),
  modifikovane timestamp not null default now(),
  modifikoval integer references osoba(id),
  sha256 char(64) not null,
  nazov varchar(150) not null,
  filename varchar(100) not null,
  mimetype varchar(100)
);

CREATE TABLE studprog_priloha_typ (
  id integer not null primary key,
  nazov text not null,
  kriterium varchar(10),
  moze_vybrat boolean not null default true
);

INSERT INTO studprog_priloha_typ (id, nazov, kriterium, moze_vybrat) VALUES
  ( 0, 'Vyplnený RTF formulár študijného programu', NULL, true),
  ( 1, 'Vedecko-pedagogické alebo umelecko-pedagogické charakteristiky profesorov a docentov pôsobiacich v študijnom programe', 'KSP-A3', false),
  ( 2, 'Vedecko-pedagogické alebo umelecko-pedagogické charakteristiky školiteľov v doktorandskom štúdiu', 'KSP-A4', false),
  ( 3, 'Zoznam vedúcich záverečných prác  a tém záverečných prác za obdobie dvoch rokov', 'KSP-A4', true),
  ( 4, 'Zloženie skúšobných komisií na vykonanie štátnych skúšok v študijnom programe za posledné dva roky', 'KSP-A5', true),
  ( 5, 'Kritériá na obsadzovanie funkcií profesor a docent', 'KSP-A6', true),
  ( 6, 'Odporúčaný študijný plán', 'KSP-B1', true),
  ( 7, 'Dohoda spolupracujúcich vysokých škôl', 'KSP-B1', true),
  ( 8, 'Informačné listy predmetov', 'KSP-B2', true),
  ( 9, 'Požadované schopnosti a predpoklady uchádzača o štúdium študijného programu', 'KSP-B8', true),
  (10, 'Pravidlá na schvaľovanie školiteľov v doktorandskom študijnom programe', 'KSP-B9', true),
  (11, 'Stanovisko alebo súhlas príslušnej autority k študijnému programu', 'KSP-B10', true),
  (12, 'Zoznam dokumentov predložených ako príloha k žiadosti', NULL, false)
;

CREATE TABLE studprog_priloha (
  studprog integer not null references studprog(id),
  typ_prilohy integer not null references studprog_priloha_typ(id),
  subor integer not null references subor(id),
  primary key (studprog, typ_prilohy, subor)
);

CREATE TABLE studprog_skolitel (
  studprog integer not null references studprog(id),
  osoba integer not null references osoba(id),
  primary key (studprog, osoba)
);

CREATE TABLE osoba_uvazok (
  osoba integer not null references osoba(id),
  pracovisko varchar(50),
  funkcia varchar(10),
  kvalifikacia varchar(2),
  uvazok integer,
  PRIMARY KEY (osoba, pracovisko, funkcia)
);

CREATE TABLE osoba_vpchar (
  osoba integer not null references osoba(id),
  token varchar(32),
  uploadnuty_subor integer references subor(id)
);

COMMIT;