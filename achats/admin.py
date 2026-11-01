from django.contrib import admin
from .models import CommandeAchat, LigneAchat, ReceptionAchat, LigneReception


class LigneAchatInline(admin.TabularInline):
    model = LigneAchat
    extra = 1


@admin.register(CommandeAchat)
class CommandeAchatAdmin(admin.ModelAdmin):
    list_display = ['numero_commande', 'fournisseur', 'statut', 'montant_total', 'date_commande', 'utilisateur']
    list_filter = ['statut', 'date_commande']
    search_fields = ['numero_commande']
    inlines = [LigneAchatInline]
    readonly_fields = ['date_commande', 'montant_total']


@admin.register(ReceptionAchat)
class ReceptionAchatAdmin(admin.ModelAdmin):
    list_display = ['commande', 'utilisateur', 'date_reception']
    readonly_fields = ['date_reception']
