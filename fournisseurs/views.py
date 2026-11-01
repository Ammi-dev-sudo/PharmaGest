from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Fournisseur
from .forms import FournisseurForm


@login_required
def liste_fournisseurs(request):
    query = request.GET.get('q', '').strip()
    fournisseurs = Fournisseur.objects.all()
    if query:
        fournisseurs = fournisseurs.filter(
            Q(nom_raison_sociale__icontains=query) | Q(telephone__icontains=query)
        )
    paginator = Paginator(fournisseurs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'fournisseurs/liste.html', {
        'fournisseurs': page_obj,
        'page_obj': page_obj,
        'query': query,
    })


@login_required
def ajouter_fournisseur(request):
    if request.method == 'POST':
        form = FournisseurForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fournisseur ajouté avec succès.')
            return redirect('liste_fournisseurs')
    else:
        form = FournisseurForm()
    return render(request, 'fournisseurs/formulaire.html', {'form': form, 'titre': 'Ajouter un fournisseur'})


@login_required
def detail_fournisseur(request, pk):
    from achats.models import CommandeAchat, ReceptionAchat
    fournisseur = get_object_or_404(Fournisseur, pk=pk)
    commandes = CommandeAchat.objects.filter(fournisseur=fournisseur).order_by('-date_commande')
    total = commandes.aggregate(t=Sum('montant_total'))['t'] or 0
    receptions = ReceptionAchat.objects.filter(commande__fournisseur=fournisseur).order_by('-date_reception')
    return render(request, 'fournisseurs/detail.html', {
        'fournisseur': fournisseur,
        'commandes': commandes[:100],
        'receptions': receptions[:50],
        'total_commandes': total,
        'nb_commandes': commandes.count(),
    })


@login_required
def modifier_fournisseur(request, pk):
    fournisseur = get_object_or_404(Fournisseur, pk=pk)
    if request.method == 'POST':
        form = FournisseurForm(request.POST, instance=fournisseur)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fournisseur modifié avec succès.')
            return redirect('liste_fournisseurs')
    else:
        form = FournisseurForm(instance=fournisseur)
    return render(request, 'fournisseurs/formulaire.html', {'form': form, 'titre': 'Modifier un fournisseur'})


@login_required
def desactiver_fournisseur(request, pk):
    fournisseur = get_object_or_404(Fournisseur, pk=pk)
    fournisseur.actif = not fournisseur.actif
    fournisseur.save()
    messages.success(request, 'Statut du fournisseur mis à jour.')
    return redirect('liste_fournisseurs')
