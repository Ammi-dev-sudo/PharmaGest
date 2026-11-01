from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Administrateur'),
        ('PHARMACIEN', 'Pharmacien responsable'),
        ('GESTIONNAIRE', 'Gestionnaire de stock'),
        ('CAISSIER', 'Caissier'),
        ('RESPONSABLE', 'Responsable de gestion'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='CAISSIER')
    telephone = models.CharField(max_length=20, blank=True)
    actif = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.username} - {self.get_role_display()}"


class JournalAudit(models.Model):
    utilisateur = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='actions'
    )
    action = models.CharField(max_length=100)
    entite = models.CharField(max_length=100, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    details = models.TextField(blank=True)
    adresse_ip = models.GenericIPAddressField(null=True, blank=True)
    date_action = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Journal d'audit"
        verbose_name_plural = "Journal d'audit"
        ordering = ['-date_action']

    def __str__(self):
        return f"{self.date_action:%d/%m/%Y %H:%M} - {self.action}"
