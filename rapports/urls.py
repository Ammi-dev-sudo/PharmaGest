from django.urls import path
from . import views

urlpatterns = [
    path('', views.rapports_accueil, name='rapports_accueil'),
    path('ventes/', views.rapport_ventes, name='rapport_ventes'),
    path('achats/', views.rapport_achats, name='rapport_achats'),
    path('stock/', views.rapport_stock, name='rapport_stock'),
    path('ventes/pdf/', views.rapport_ventes_pdf, name='rapport_ventes_pdf'),
    path('achats/pdf/', views.rapport_achats_pdf, name='rapport_achats_pdf'),
    path('stock/pdf/', views.rapport_stock_pdf, name='rapport_stock_pdf'),
]
