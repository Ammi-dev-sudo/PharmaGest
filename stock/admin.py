from django.contrib import admin
from .models import LotStock, MouvementStock


@admin.register(LotStock)
class LotStockAdmin(admin.ModelAdmin):
    list_display = ['medicament', 'numero_lot', 'date_peremption', 'quantite', 'bloque']
    list_filter = ['date_peremption', 'bloque']
    search_fields = ['medicament__nom_commercial', 'numero_lot']


@admin.register(MouvementStock)
class MouvementStockAdmin(admin.ModelAdmin):
    list_display = ['medicament', 'type_mouvement', 'quantite', 'utilisateur', 'date_mouvement', 'reference']
    list_filter = ['type_mouvement', 'date_mouvement']
    search_fields = ['medicament__nom_commercial', 'reference']
    readonly_fields = ['date_mouvement']
