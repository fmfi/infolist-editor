from decimal import Decimal


class Pocitadlo(object):
  def __init__(self):
    self._fyzicky = set()
    self._fyzicky_tyzdenne = set() # ustanoveny tyzdenny prac cas
    self._fyzicky_podskupina = set() # mimoriadny/3st.
    self.prepocitany = Decimal(0)
    self.prepocitany_podskupina = 0 # mimoriadny/3st.

  def pridaj(self, id, vaha, podskupina):
    self._fyzicky.add(id)
    self.prepocitany += vaha
    if podskupina:
      self._fyzicky_podskupina.add(id)
      self.prepocitany_podskupina += vaha
    if vaha == Decimal(1):
      self._fyzicky_tyzdenne.add(id)

  @property
  def fyzicky(self):
    return len(self._fyzicky)

  @property
  def fyzicky_tyzdenne(self):
    return len(self._fyzicky_tyzdenne)

  @property
  def fyzicky_podskupina(self):
    return len(self._fyzicky_podskupina)

  def __str__(self):
    return '{} {} {} {} {}'.format(self.fyzicky, self.fyzicky_podskupina,
      self.prepocitany, self.prepocitany_podskupina, self.fyzicky_tyzdenne)


class PocitadloSucet(object):
  def __init__(self, *pocitadla):
    self.pocitadla = pocitadla

  def sum(self, attr):
    return sum(getattr(x, attr) for x in self.pocitadla)

  @property
  def fyzicky(self):
    return self.sum('fyzicky')

  @property
  def fyzicky_tyzdenne(self):
    return self.sum('fyzicky_tyzdenne')

  @property
  def fyzicky_podskupina(self):
    return self.sum('fyzicky_podskupina')

  @property
  def prepocitany(self):
    return self.sum('prepocitany')

  @property
  def prepocitany_podskupina(self):
    return self.sum('prepocitany_podskupina')


class PocitadloSucetSpecial(PocitadloSucet):
  def __init__(self, prof, doc, *ostat):
    self.profdoc = PocitadloSucet(prof, doc)
    self.ostat = PocitadloSucet(*ostat)

  def sum(self, attr):
    v = self.ostat.sum(attr)
    if attr == 'fyzicky_podskupina':
      v += self.profdoc.fyzicky
    elif attr == 'prepocitany_podskupina':
      v += self.profdoc.prepocitany
    else:
      v += self.profdoc.sum(attr)
    return v


class PocitadloStruktura(object):
  def __init__(self):
    self.profesor = Pocitadlo()
    self.docent = Pocitadlo()
    self.hostujuci_profesor = Pocitadlo()
    self.odborny_asistent = Pocitadlo()
    self.asistent = Pocitadlo()
    self.lektor = Pocitadlo()
    self.ucitelia_spolu = PocitadloSucetSpecial(self.profesor, self.docent, self.hostujuci_profesor, self.odborny_asistent, self.lektor)
    self.vyskumny_pracovnik = Pocitadlo()
    self.zamestnanci_spolu = PocitadloSucet(self.ucitelia_spolu, self.vyskumny_pracovnik)
    self.doktorand = Pocitadlo()
    self.zamestanci_mimo_pomeru = Pocitadlo()
    self.spolu = PocitadloSucet(self.zamestnanci_spolu, self.doktorand, self.zamestanci_mimo_pomeru)
    self.pocitadla = ['profesor', 'docent', 'hostujuci_profesor',
      'odborny_asistent', 'asistent', 'lektor', 'ucitelia_spolu', 'vyskumny_pracovnik',
      'zamestnanci_spolu', 'doktorand', 'zamestnanci_mimo_pomeru', 'spolu']

  def pridaj(self, id, funkcia, kvalifikacia, vaha):
    treti_stupen = ['10', '11', '12', '20', '21', '30', '31']
    if funkcia in ['1P', '1H']:
      self.profesor.pridaj(id, vaha, not kvalifikacia.startswith('1'))
    elif funkcia == '2D':
      self.docent.pridaj(id, vaha, False)
    elif funkcia == '3O':
      self.odborny_asistent.pridaj(id, vaha, kvalifikacia in treti_stupen)
    elif funkcia == '4A':
      self.asistent.pridaj(id, vaha, kvalifikacia in treti_stupen)
    elif funkcia == '5L':
      self.lektor.pridaj(id, vaha, kvalifikacia in treti_stupen)
    elif funkcia in ['6V', '6T', '6P']:
      self.vyskumny_pracovnik.pridaj(id, vaha, kvalifikacia in treti_stupen)
    elif funkcia == '0S':
      self.doktorand.pridaj(id, vaha, kvalifikacia in treti_stupen)
    elif funkcia in ['9U', '9V']:
      self.zamestanci_mimo_pomeru.pridaj(id, vaha, kvalifikacia in treti_stupen)

  def __str__(self):
    return 'fyzicky z_toho prepocitany z_toho fyz_tyzdenny\n'+'\n'.join('{}: {}'.format(x.rjust(20), getattr(self, x)) for x in self.pocitadla)