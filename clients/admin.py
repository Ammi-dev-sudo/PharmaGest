from django.contrib import admin
from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['nom_complet', 'telephone', 'email']
    search_fields = ['nom_complet', 'telephone']
