from django.db import models

class SnapshotTextFields(models.Model):
    language = models.CharField(max_length=2) # ISO 639-1 2-letter code
    name = models.CharField(max_length=300)
    # ...

class Snapshot(models.Model):
    # Polozky k verziam
    parent = models.ForeignKey('self')
    # author = 
    time_created = models.DateTimeField(auto_now_add=True)
    # Datove polozky
    # Kod je stredisko/kratkykod/rok
    kod_katedra = models.CharField(max_length=200)
    kod_predmet = models.CharField(max_length=200)
    kod_rok = models.CharField(max_length=10)
    # Odkaz na textove polozky
    text_sk = models.ForeignKey(SnapshotTextFields, related_name='+')
    text_en = models.ForeignKey(SnapshotTextFields, related_name='+')
    # dalsie polia...

class List(models.Model):
    # owner = ...
    snapshot = models.ForeignKey(Snapshot)
    imported = models.BooleanField()