from django.contrib import admin
from .models import Medicament, Categorie


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ['nom', 'description']
    search_fields = ['nom']


@admin.register(Medicament)
class MedicamentAdmin(admin.ModelAdmin):
    list_display = ['nom_commercial', 'categorie', 'forme_pharmaceutique', 'dosage', 'prix_vente', 'seuil_alerte', 'statut']
    list_filter = ['categorie', 'forme_pharmaceutique', 'statut']
    search_fields = ['nom_commercial', 'code_barres', 'denomination_generique']
