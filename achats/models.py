from django.db import models
from fournisseurs.models import Fournisseur
from medicaments.models import Medicament
from utilisateurs.models import CustomUser


class CommandeAchat(models.Model):
    STATUT_CHOICES = (
        ('BROUILLON', 'Brouillon'),
        ('COMMANDEE', 'Commandée'),
        ('PARTIELLEMENT_RECEPTIONNEE', 'Partiellement réceptionnée'),
        ('ENTIEREMENT_RECEPTIONNEE', 'Entièrement réceptionnée'),
        ('ANNULEE', 'Annulée'),
    )
    numero_commande = models.CharField(max_length=50, unique=True)
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.PROTECT)
    utilisateur = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    date_commande = models.DateTimeField(auto_now_add=True)
    statut = models.CharField(max_length=30, choices=STATUT_CHOICES, default='BROUILLON')
    montant_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Commande d\'achat'
        verbose_name_plural = 'Commandes d\'achat'
        ordering = ['-date_commande']

    def __str__(self):
        return f"CMD-{self.numero_commande}"


class LigneAchat(models.Model):
    commande = models.ForeignKey(CommandeAchat, on_delete=models.CASCADE, related_name='lignes')
    medicament = models.ForeignKey(Medicament, on_delete=models.PROTECT)
    quantite = models.IntegerField()
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    montant_ligne = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Ligne d\'achat'
        verbose_name_plural = 'Lignes d\'achat'

    def __str__(self):
        return f"{self.commande} - {self.medicament.nom_commercial}"

    @property
    def quantite_recue(self):
        total = self.receptions.aggregate(total=models.Sum('quantite_recue'))['total']
        return total or 0

    @property
    def quantite_restante(self):
        return max(self.quantite - self.quantite_recue, 0)


class ReceptionAchat(models.Model):
    commande = models.ForeignKey(CommandeAchat, on_delete=models.PROTECT, related_name='receptions')
    utilisateur = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    date_reception = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Réception d\'achat'
        verbose_name_plural = 'Réceptions d\'achat'
        ordering = ['-date_reception']

    def __str__(self):
        return f"REC-{self.id} - {self.commande.numero_commande}"


class LigneReception(models.Model):
    reception = models.ForeignKey(ReceptionAchat, on_delete=models.CASCADE, related_name='lignes')
    ligne_achat = models.ForeignKey(LigneAchat, on_delete=models.PROTECT, null=True, blank=True, related_name='receptions')
    medicament = models.ForeignKey(Medicament, on_delete=models.PROTECT)
    numero_lot = models.CharField(max_length=100)
    date_peremption = models.DateField()
    quantite_recue = models.IntegerField()
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Ligne de réception'
        verbose_name_plural = 'Lignes de réception'

    def __str__(self):
        return f"{self.reception} - {self.medicament.nom_commercial}"
