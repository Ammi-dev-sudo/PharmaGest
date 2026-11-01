from django.urls import path
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from . import views

urlpatterns = [
    path('connexion/', auth_views.LoginView.as_view(template_name='utilisateurs/login.html'), name='login'),
    path('inscription/', views.inscription, name='inscription'),
    path('deconnexion/', auth_views.LogoutView.as_view(), name='logout'),
    path('utilisateurs/', views.liste_utilisateurs, name='liste_utilisateurs'),
    path('utilisateurs/ajouter/', views.ajouter_utilisateur, name='ajouter_utilisateur'),
    path('utilisateurs/modifier/<int:pk>/', views.modifier_utilisateur, name='modifier_utilisateur'),
    path('utilisateurs/basculer/<int:pk>/', views.basculer_utilisateur, name='basculer_utilisateur'),
    path('audit/', views.journal_audit, name='journal_audit'),
    path('mot-de-passe/', auth_views.PasswordChangeView.as_view(
        template_name='utilisateurs/password_change.html',
        success_url=reverse_lazy('password_change_done'),
    ), name='password_change'),
    path('mot-de-passe/fait/', auth_views.PasswordChangeDoneView.as_view(
        template_name='utilisateurs/password_change_done.html',
    ), name='password_change_done'),
    path('mot-de-passe-oublie/', auth_views.PasswordResetView.as_view(
        template_name='utilisateurs/password_reset.html',
        email_template_name='utilisateurs/password_reset_email.txt',
        subject_template_name='utilisateurs/password_reset_subject.txt',
        success_url=reverse_lazy('password_reset_done'),
    ), name='password_reset'),
    path('mot-de-passe-oublie/envoye/', auth_views.PasswordResetDoneView.as_view(
        template_name='utilisateurs/password_reset_done.html',
    ), name='password_reset_done'),
    path('reinitialiser/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='utilisateurs/password_reset_confirm.html',
        success_url=reverse_lazy('password_reset_complete'),
    ), name='password_reset_confirm'),
    path('reinitialiser/termine/', auth_views.PasswordResetCompleteView.as_view(
        template_name='utilisateurs/password_reset_complete.html',
    ), name='password_reset_complete'),
]
