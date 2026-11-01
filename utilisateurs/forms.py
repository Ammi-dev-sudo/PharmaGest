from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'role', 'telephone', 'actif')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class PublicUserCreationForm(UserCreationForm):
    first_name = forms.CharField(label='Prénom', max_length=30, required=True)
    last_name = forms.CharField(label='Nom', max_length=30, required=True)
    email = forms.EmailField(label='Adresse e-mail', required=True)
    telephone = forms.CharField(label='Téléphone', max_length=20, required=False)

    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'telephone', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        self.fields['username'].help_text = "Lettres, chiffres et @/./+/-/_ uniquement."
        self.fields['password1'].help_text = "Minimum 8 caractères."

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'CAISSIER'
        user.actif = True
        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'email', 'role', 'telephone', 'actif', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
