from django.urls import path
from . import views

urlpatterns = [
    path('', views.liste_medicaments, name='liste_medicaments'),
    path('ajouter/', views.ajouter_medicament, name='ajouter_medicament'),
    path('modifier/<int:pk>/', views.modifier_medicament, name='modifier_medicament'),
    path('archiver/<int:pk>/', views.archiver_medicament, name='archiver_medicament'),
    path('categories/', views.liste_categories, name='liste_categories'),
    path('categories/ajouter/', views.ajouter_categorie, name='ajouter_categorie'),
    path('categories/modifier/<int:pk>/', views.modifier_categorie, name='modifier_categorie'),
]
