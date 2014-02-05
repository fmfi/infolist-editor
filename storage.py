# -*- coding: utf-8 -*-

def dict_rec_update(d1, d2):
  for key in d2:
    if isinstance(d2[key], dict):
      d1[key] = dict_rec_update(d1.get(key, {}), d2[key])
    else:
      d1[key] = d2[key]
  return d1

class DataStore(object):
  def __init__(self, conn):
    self.conn = conn
  
  def cursor(self):
    return self.conn.cursor()
  
  def load_infolist(self, id, lang='sk'):
    with self.cursor() as cur:
      cur.execute('''SELECT posledna_verzia, import_z_aisu,
        forknute_z, zamknute, finalna_verzia
        FROM infolist
        WHERE id = %s''',
        (id,))
      data = cur.fetchone()
      if data == None:
        raise KeyError('infolist({})'.format(id))
      posledna_verzia, import_z_aisu, forknute_z, zamknute, finalna_verzia = data
      i = {
        'posledna_verzia': posledna_verzia,
        'import_z_aisu': import_z_aisu,
        'forknute_z': forknute_z,
        'zamknute': zamknute,
        'finalna_verzia': finalna_verzia
      }
    i.update(self.load_infolist_verzia(id, lang))
    return i
  
  def load_infolist_verzia(self, id, lang='sk'):
    with self.cursor() as cur:
      data = self._load_iv_data(cur, id)
      data['vyucujuci'] = self._load_iv_vyucujuci(cur, id)
      data['cinnosti'] = self._load_iv_cinnosti(cur, id)
      dict_rec_update(data, self._load_iv_trans(cur, id, lang))
    return data
  
  def _load_iv_data(self, cur, id):
    cur.execute('''SELECT pocet_kreditov,
      podm_absol_percenta_skuska, podm_absol_percenta_na_a,
      podm_absol_percenta_na_b, podm_absol_percenta_na_c,
      podm_absol_percenta_na_d, podm_absol_percenta_na_e,
      hodnotenia_a_pocet, hodnotenia_b_pocet, hodnotenia_c_pocet,
      hodnotenia_d_pocet, hodnotenia_e_pocet, hodnotenia_fx_pocet,
      podmienujuce_predmety, vylucujuce_predmety,
      modifikovane, predosla_verzia
      FROM infolist_verzia WHERE id = %s''', (id,))
    row = cur.fetchone()
    if row == None:
      raise KeyError('infolist_verzia({})'.format(id))
    
    (pocet_kreditov, percenta_skuska,
    pct_a, pct_b, pct_c, pct_d, pct_e,
    hodn_a, hodn_b, hodn_c, hodn_d, hodn_e, hodn_fx,
    podmienujuce_predmety, vylucujuce_predmety,
    modifikovane, predosla_verzia) = row
    
    iv = {
      'id': id,
      'pocet_kreditov': pocet_kreditov,
      'podm_absolvovania': {
        'percenta_skuska': percenta_skuska,
        'percenta_na': {
          'A': pct_a,
          'B': pct_b,
          'C': pct_c,
          'D': pct_d,
          'E': pct_e
        },
      },
      'hodnotenia_pocet': {
        'A': hodn_a,
        'B': hodn_b,
        'C': hodn_c,
        'D': hodn_d,
        'E': hodn_e,
        'Fx': hodn_fx
      },
      'podmienujuce_predmety': podmienujuce_predmety,
      'vylucujuce_predmety': vylucujuce_predmety,
      'modifikovane': modifikovane,
      'predosla_verzia': predosla_verzia,
    }
    return iv
  
  def _load_iv_vyucujuci(self, cur, id):
    cur.execute('''SELECT ivv.osoba,
      o.cele_meno, ivvt.typ_vyucujuceho
      FROM osoba o, infolist_verzia_vyucujuci ivv
      LEFT JOIN infolist_verzia_vyucujuci_typ ivvt
      ON ivv.infolist_verzia = ivvt.infolist_verzia AND ivv.osoba = ivvt.osoba
      WHERE ivv.osoba = o.id AND ivv.infolist_verzia = %s
      ORDER BY ivv.poradie''',
      (id,))
    ivv = []
    vyucujuci = None
    for osoba, cele_meno, typ_vyucujuceho in cur:
      if vyucujuci == None or vyucujuci['osoba'] != osoba:
        vyucujuci = {'osoba': osoba,
                     'cele_meno': cele_meno,
                     'typy': set()}
        ivv.append(vyucujuci)
      vyucujuci['typy'].add(typ_vyucujuceho)
    return ivv
  
  def _load_iv_cinnosti(self, cur, id):
    cur.execute('''SELECT druh_cinnosti, metoda_vyucby,
      pocet_hodin_tyzdenne
      FROM infolist_verzia_cinnosti
      WHERE infolist_verzia = %s''',
      (id,))
    cinnosti = []
    for druh_cinnosti, metoda_vyucby, pocet_hodin_tyzdenne in cur:
      cinnosti.append({
        'druh_cinnosti': druh_cinnosti,
        'metoda_vyucby': metoda_vyucby,
        'pocet_hodin_tyzdenne': pocet_hodin_tyzdenne
      })
    return cinnosti
  
  def _load_iv_trans(self, cur, id, lang='sk'):
    cur.execute('''SELECT nazov_predmetu, podm_absol_priebezne,
      podm_absol_skuska, podm_absol_nahrada, vysledky_vzdelavania,
      strucna_osnova, potrebny_jazyk
      FROM infolist_verzia_preklad
      WHERE infolist_verzia = %s AND jazyk_prekladu = %s''',
      (id, lang))
    data = cur.fetchone()
    if data == None:
      raise KeyError('infolist_verzia_preklad({}, {})'.format(id, lang))
    
    return {
      'nazov_predmetu': data.nazov_predmetu,
      'podm_absolvovania': {
        'skuska': data.podm_absol_skuska,
        'priebezne': data.podm_absol_priebezne,
        'nahrada': data.podm_absol_nahrada,
      },
      'vysledky_vzdelavania': data.vysledky_vzdelavania,
      'strucna_osnova': data.strucna_osnova,
      'potrebny_jazyk': data.potrebny_jazyk,
      'jazyk_prekladu': lang,
    }
