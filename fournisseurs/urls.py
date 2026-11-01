from django.urls import path
from . import views

urlpatterns = [
    path('', views.liste_fournisseurs, name='liste_fournisseurs'),
    path('ajouter/', views.ajouter_fournisseur, name='ajouter_fournisseur'),
    path('modifier/<int:pk>/', views.modifier_fournisseur, name='modifier_fournisseur'),
    path('desactiver/<int:pk>/', views.desactiver_fournisseur, name='desactiver_fournisseur'),
    path('detail/<int:pk>/', views.detail_fournisseur, name='detail_fournisseur'),
]
