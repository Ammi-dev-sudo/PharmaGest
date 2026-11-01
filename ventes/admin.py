from django.contrib import admin
from .models import Vente, LigneVente, RetourVente, LigneRetourVente, Paiement


class LigneVenteInline(admin.TabularInline):
    model = LigneVente
    extra = 0
    readonly_fields = ['medicament', 'lot', 'quantite', 'prix_unitaire', 'montant_ligne']


@admin.register(Vente)
class VenteAdmin(admin.ModelAdmin):
    list_display = ['numero_vente', 'client', 'utilisateur', 'montant_total', 'mode_paiement', 'statut', 'date_vente']
    list_filter = ['statut', 'mode_paiement', 'date_vente']
    search_fields = ['numero_vente']
    inlines = [LigneVenteInline]
    readonly_fields = ['date_vente', 'montant_total', 'montant_rendu']


class LigneRetourInline(admin.TabularInline):
    model = LigneRetourVente
    extra = 0


@admin.register(RetourVente)
class RetourVenteAdmin(admin.ModelAdmin):
    list_display = ['vente', 'type_operation', 'utilisateur', 'montant_rembourse', 'remis_en_stock', 'date_retour']
    list_filter = ['type_operation', 'remis_en_stock', 'date_retour']
    readonly_fields = ['date_retour']
    inlines = [LigneRetourInline]


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ['vente', 'mode', 'montant', 'statut', 'date_paiement']
    list_filter = ['mode', 'statut', 'date_paiement']
    search_fields = ['vente__numero_vente', 'reference']
