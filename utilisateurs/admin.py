from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, JournalAudit
from .forms import CustomUserCreationForm, CustomUserChangeForm


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    list_display = ['username', 'email', 'first_name', 'last_name', 'role', 'actif', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('Informations supplémentaires', {'fields': ('role', 'telephone', 'actif')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informations supplémentaires', {'fields': ('role', 'telephone', 'actif')}),
    )


@admin.register(JournalAudit)
class JournalAuditAdmin(admin.ModelAdmin):
    list_display = ['date_action', 'utilisateur', 'action', 'entite', 'reference']
    list_filter = ['action', 'entite', 'date_action']
    search_fields = ['action', 'reference', 'details']
    readonly_fields = ['date_action']
