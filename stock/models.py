from django.db import models
from medicaments.models import Medicament


class LotStock(models.Model):
    medicament = models.ForeignKey(Medicament, on_delete=models.PROTECT, related_name='lots')
    numero_lot = models.CharField(max_length=100)
    date_peremption = models.DateField()
    quantite = models.IntegerField()
    quantite_initiale = models.IntegerField()
    bloque = models.BooleanField(default=False)
    date_reception = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Lot de stock'
        verbose_name_plural = 'Lots de stock'
        ordering = ['date_peremption']

    def __str__(self):
        return f"{self.medicament.nom_commercial} - Lot {self.numero_lot} - Exp {self.date_peremption}"

    def est_perime(self):
        from django.utils import timezone
        return self.date_peremption < timezone.now().date()


class MouvementStock(models.Model):
    TYPE_CHOICES = (
        ('ENTREE', 'Entrée'),
        ('SORTIE', 'Sortie'),
        ('CORRECTION', 'Correction'),
        ('RETOUR', 'Retour'),
    )
    medicament = models.ForeignKey(Medicament, on_delete=models.PROTECT)
    lot = models.ForeignKey(LotStock, on_delete=models.PROTECT, null=True, blank=True)
    type_mouvement = models.CharField(max_length=10, choices=TYPE_CHOICES)
    quantite = models.IntegerField()
    motif = models.TextField()
    utilisateur = models.ForeignKey('utilisateurs.CustomUser', on_delete=models.PROTECT)
    date_mouvement = models.DateTimeField(auto_now_add=True)
    reference = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = 'Mouvement de stock'
        verbose_name_plural = 'Mouvements de stock'
        ordering = ['-date_mouvement']

    def __str__(self):
        return f"{self.type_mouvement} - {self.medicament.nom_commercial} - {self.quantite}"
