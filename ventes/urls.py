from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('caisse/', views.caisse, name='caisse'),
    path('caisse/ajouter/<int:medicament_id>/', views.ajouter_au_panier, name='ajouter_au_panier'),
    path('caisse/ajouter/', views.ajouter_selection, name='ajouter_selection'),
    path('caisse/modifier/<int:index>/', views.modifier_quantite, name='modifier_quantite'),
    path('caisse/retirer/<int:index>/', views.retirer_du_panier, name='retirer_du_panier'),
    path('caisse/vider/', views.vider_panier, name='vider_panier'),
    path('caisse/valider/', views.valider_vente, name='valider_vente'),
    path('ventes/', views.liste_ventes, name='liste_ventes'),
    path('ventes/detail/<int:pk>/', views.detail_vente, name='detail_vente'),
    path('ventes/recu/<int:pk>/', views.recu_vente, name='recu_vente'),
    path('ventes/recu/<int:pk>/pdf/', views.recu_vente_pdf, name='recu_vente_pdf'),
    path('ventes/facture/<int:pk>/pdf/', views.facture_vente_pdf, name='facture_vente_pdf'),
    path('ventes/retour/<int:pk>/', views.creer_retour, name='creer_retour'),
    path('ventes/annuler/<int:pk>/', views.annuler_vente, name='annuler_vente'),
    path('retours/', views.liste_retours, name='liste_retours'),
]
