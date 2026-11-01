from django.db import models


class Client(models.Model):
    nom_complet = models.CharField(max_length=200)
    telephone = models.CharField(max_length=20, blank=True)
    adresse = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'
        ordering = ['nom_complet']

    def __str__(self):
        return self.nom_complet
