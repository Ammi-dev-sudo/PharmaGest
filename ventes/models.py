from django.db import models
from utilisateurs.models import CustomUser
from clients.models import Client
from medicaments.models import Medicament
from stock.models import LotStock


class Vente(models.Model):
    MODE_PAIEMENT_CHOICES = (
        ('ESPECES', 'Espèces'),
        ('MOBILE_MONEY', 'Mobile Money'),
        ('CARTE', 'Carte bancaire'),
        ('AUTRE', 'Autre'),
    )
    STATUT_CHOICES = (
        ('EN_COURS', 'En cours'),
        ('VALIDEE', 'Validée'),
        ('ANNULEE', 'Annulée'),
    )
    numero_vente = models.CharField(max_length=50, unique=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, null=True, blank=True)
    utilisateur = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    date_vente = models.DateTimeField(auto_now_add=True)
    mode_paiement = models.CharField(max_length=20, choices=MODE_PAIEMENT_CHOICES, default='ESPECES')
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='EN_COURS')
    montant_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_paye = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_rendu = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Vente'
        verbose_name_plural = 'Ventes'
        ordering = ['-date_vente']

    def __str__(self):
        return f"V-{self.numero_vente}"


class LigneVente(models.Model):
    vente = models.ForeignKey(Vente, on_delete=models.CASCADE, related_name='lignes')
    medicament = models.ForeignKey(Medicament, on_delete=models.PROTECT)
    lot = models.ForeignKey(LotStock, on_delete=models.PROTECT)
    quantite = models.IntegerField()
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    montant_ligne = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Ligne de vente'
        verbose_name_plural = 'Lignes de vente'

    def __str__(self):
        return f"{self.vente} - {self.medicament.nom_commercial}"


class Paiement(models.Model):
    MODE_CHOICES = (
        ('ESPECES', 'Espèces'),
        ('MOBILE_MONEY', 'Mobile Money'),
        ('CARTE', 'Carte bancaire'),
        ('AUTRE', 'Autre'),
    )
    STATUT_CHOICES = (
        ('EN_ATTENTE', 'En attente'),
        ('CONFIRME', 'Confirmé'),
        ('ECHOUE', 'Échoué'),
        ('REMBOURSE', 'Remboursé'),
    )
    vente = models.ForeignKey(Vente, on_delete=models.CASCADE, related_name='paiements')
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='ESPECES')
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, blank=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='CONFIRME')
    date_paiement = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Paiement'
        verbose_name_plural = 'Paiements'
        ordering = ['-date_paiement']

    def __str__(self):
        return f"{self.vente.numero_vente} - {self.montant} Ar ({self.get_statut_display()})"


class RetourVente(models.Model):
    TYPE_CHOICES = (
        ('RETOUR', 'Retour de produit'),
        ('ANNULATION', 'Annulation de vente'),
    )
    vente = models.ForeignKey(Vente, on_delete=models.PROTECT, related_name='retours')
    utilisateur = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    date_retour = models.DateTimeField(auto_now_add=True)
    motif = models.TextField()
    montant_rembourse = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    type_operation = models.CharField(max_length=20, choices=TYPE_CHOICES, default='RETOUR')
    remis_en_stock = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Retour de vente'
        verbose_name_plural = 'Retours de vente'
        ordering = ['-date_retour']

    def __str__(self):
        return f"RET-{self.id} - {self.vente.numero_vente}"

    @property
    def quantite_totale(self):
        return sum(ligne.quantite for ligne in self.lignes.all())


class LigneRetourVente(models.Model):
    retour = models.ForeignKey(RetourVente, on_delete=models.CASCADE, related_name='lignes')
    ligne_vente = models.ForeignKey(LigneVente, on_delete=models.PROTECT, null=True, blank=True)
    medicament = models.ForeignKey(Medicament, on_delete=models.PROTECT)
    lot = models.ForeignKey(LotStock, on_delete=models.PROTECT, null=True, blank=True)
    quantite = models.IntegerField()
    montant_rembourse = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Ligne de retour'
        verbose_name_plural = 'Lignes de retour'

    def __str__(self):
        return f"{self.retour} - {self.medicament.nom_commercial}"
