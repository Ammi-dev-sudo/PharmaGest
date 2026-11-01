from django.contrib import admin
from .models import Fournisseur


@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ['nom_raison_sociale', 'telephone', 'email', 'actif']
    list_filter = ['actif']
    search_fields = ['nom_raison_sociale', 'telephone']
