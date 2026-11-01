from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth import login
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .models import CustomUser
from .forms import CustomUserCreationForm, CustomUserChangeForm, PublicUserCreationForm


@login_required
@permission_required('utilisateurs.view_customuser', raise_exception=True)
def liste_utilisateurs(request):
    query = request.GET.get('q', '').strip()
    utilisateurs = CustomUser.objects.all().order_by('username')
    if query:
        utilisateurs = utilisateurs.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(role__icontains=query)
        )
    paginator = Paginator(utilisateurs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'utilisateurs/liste.html', {
        'utilisateurs': page_obj,
        'page_obj': page_obj,
        'query': query,
    })


def inscription(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = PublicUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Inscription réussie. Bienvenue sur PharmaGest !')
            return redirect('dashboard')
    else:
        form = PublicUserCreationForm()
    return render(request, 'utilisateurs/inscription.html', {'form': form})


@login_required
@permission_required('utilisateurs.add_customuser', raise_exception=True)
def ajouter_utilisateur(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Utilisateur créé avec succès.')
            return redirect('liste_utilisateurs')
    else:
        form = CustomUserCreationForm()
    return render(request, 'utilisateurs/formulaire.html', {'form': form, 'titre': 'Ajouter un utilisateur'})


@login_required
@permission_required('utilisateurs.change_customuser', raise_exception=True)
def modifier_utilisateur(request, pk):
    utilisateur = get_object_or_404(CustomUser, pk=pk)
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=utilisateur)
        if form.is_valid():
            form.save()
            messages.success(request, 'Utilisateur modifié avec succès.')
            return redirect('liste_utilisateurs')
    else:
        form = CustomUserChangeForm(instance=utilisateur)
    return render(request, 'utilisateurs/formulaire.html', {'form': form, 'titre': 'Modifier un utilisateur'})


@login_required
@permission_required('utilisateurs.view_customuser', raise_exception=True)
def journal_audit(request):
    from .models import JournalAudit
    actions = JournalAudit.objects.select_related('utilisateur')
    query = request.GET.get('q', '').strip()
    if query:
        actions = actions.filter(
            Q(action__icontains=query)
            | Q(reference__icontains=query)
            | Q(entite__icontains=query)
            | Q(utilisateur__username__icontains=query)
        )
    return render(request, 'utilisateurs/audit.html', {'actions': actions[:300], 'query': query})


@login_required
@permission_required('utilisateurs.change_customuser', raise_exception=True)
def basculer_utilisateur(request, pk):
    from django.views.decorators.http import require_POST
    if request.method != 'POST':
        return redirect('liste_utilisateurs')
    utilisateur = get_object_or_404(CustomUser, pk=pk)
    if utilisateur == request.user:
        messages.error(request, 'Vous ne pouvez pas désactiver votre propre compte.')
        return redirect('liste_utilisateurs')
    utilisateur.actif = not utilisateur.actif
    utilisateur.is_active = utilisateur.actif
    utilisateur.save(update_fields=['actif', 'is_active'])
    messages.success(request, 'Statut du compte mis à jour.')
    return redirect('liste_utilisateurs')
