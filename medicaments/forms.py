from django import forms
from .models import Medicament, Categorie


class CategorieForm(forms.ModelForm):
    class Meta:
        model = Categorie
        fields = ['nom', 'description']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


MAX_IMAGE_SIZE = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = ('image/jpeg', 'image/png', 'image/webp', 'image/gif')


class MedicamentForm(forms.ModelForm):
    class Meta:
        model = Medicament
        fields = ['nom_commercial', 'denomination_generique', 'categorie', 'forme_pharmaceutique',
                  'dosage', 'laboratoire', 'code_barres', 'photo', 'prix_achat', 'prix_vente',
                  'seuil_alerte', 'statut']
        widgets = {
            'nom_commercial': forms.TextInput(attrs={'class': 'form-control'}),
            'denomination_generique': forms.TextInput(attrs={'class': 'form-control'}),
            'categorie': forms.Select(attrs={'class': 'form-control'}),
            'forme_pharmaceutique': forms.Select(attrs={'class': 'form-control'}),
            'dosage': forms.TextInput(attrs={'class': 'form-control'}),
            'laboratoire': forms.TextInput(attrs={'class': 'form-control'}),
            'code_barres': forms.TextInput(attrs={'class': 'form-control'}),
            'prix_achat': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'prix_vente': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'seuil_alerte': forms.NumberInput(attrs={'class': 'form-control'}),
            'statut': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if not photo:
            return photo
        contenu = getattr(photo, 'content_type', '')
        if contenu and contenu not in ALLOWED_IMAGE_TYPES:
            raise forms.ValidationError('Format d\'image non autorisé (JPEG, PNG, WEBP ou GIF).')
        if photo.size > MAX_IMAGE_SIZE:
            raise forms.ValidationError('L\'image ne doit pas dépasser 5 Mo.')
        return photo

    def clean_prix_achat(self):
        prix = self.cleaned_data.get('prix_achat')
        if prix is not None and prix < 0:
            raise forms.ValidationError('Le prix d\'achat doit être positif.')
        return prix

    def clean_prix_vente(self):
        prix = self.cleaned_data.get('prix_vente')
        if prix is not None and prix < 0:
            raise forms.ValidationError('Le prix de vente doit être positif.')
        return prix

    def clean_seuil_alerte(self):
        seuil = self.cleaned_data.get('seuil_alerte')
        if seuil is not None and seuil < 0:
            raise forms.ValidationError('Le seuil d\'alerte doit être positif.')
        return seuil
