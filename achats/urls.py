from django.urls import path
from . import views

urlpatterns = [
    path('', views.liste_commandes, name='liste_commandes'),
    path('creer/', views.creer_commande, name='creer_commande'),
    path('detail/<int:pk>/', views.detail_commande, name='detail_commande'),
    path('valider/<int:pk>/', views.valider_commande, name='valider_commande'),
    path('recevoir/<int:pk>/', views.recevoir_commande, name='recevoir_commande'),
    path('bon-commande/<int:pk>/pdf/', views.bon_commande_pdf, name='bon_commande_pdf'),
    path('bon-reception/<int:pk>/pdf/', views.bon_reception_pdf, name='bon_reception_pdf'),
    path('annuler/<int:pk>/', views.annuler_commande, name='annuler_commande'),
    path('supprimer-ligne/<int:pk>/<int:ligne_pk>/', views.supprimer_ligne, name='supprimer_ligne'),
]
