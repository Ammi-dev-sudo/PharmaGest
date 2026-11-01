from django.urls import path
from . import views

urlpatterns = [
    path('', views.etat_stock, name='etat_stock'),
    path('mouvements/', views.liste_mouvements, name='liste_mouvements'),
    path('alertes/', views.alertes_stock, name='alertes_stock'),
    path('peremptions/', views.produits_perimes, name='produits_perimes'),
    path('peremptions/pdf/', views.peremptions_pdf, name='peremptions_pdf'),
    path('inventaire/', views.inventaire, name='inventaire'),
]
