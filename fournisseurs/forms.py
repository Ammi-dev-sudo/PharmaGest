from django import forms
from .models import Fournisseur


class FournisseurForm(forms.ModelForm):
    class Meta:
        model = Fournisseur
        fields = ['nom_raison_sociale', 'adresse', 'telephone', 'email', 'numero_fiscal', 'contact_principal', 'actif']
        widgets = {
            'nom_raison_sociale': forms.TextInput(attrs={'class': 'form-control'}),
            'adresse': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'telephone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'numero_fiscal': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_principal': forms.TextInput(attrs={'class': 'form-control'}),
        }
