from django import forms
from .models import CommandeAchat
from fournisseurs.models import Fournisseur


class CommandeAchatForm(forms.ModelForm):
    class Meta:
        model = CommandeAchat
        fields = ['fournisseur', 'notes']
        widgets = {
            'fournisseur': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
