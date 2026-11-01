from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from utilisateurs.utils import journaliser
from .models import Medicament, Categorie
from .forms import MedicamentForm, CategorieForm


@login_required
def liste_medicaments(request):
    query = request.GET.get('q', '').strip()
    categorie_id = request.GET.get('categorie', '')
    statut = request.GET.get('statut', '')
    tri = request.GET.get('tri', 'nom')

    medicaments = Medicament.objects.select_related('categorie')
    if query:
        medicaments = medicaments.filter(
            Q(nom_commercial__icontains=query)
            | Q(denomination_generique__icontains=query)
            | Q(code_barres__icontains=query)
            | Q(laboratoire__icontains=query)
        )
    if categorie_id:
        medicaments = medicaments.filter(categorie_id=categorie_id)
    if statut:
        medicaments = medicaments.filter(statut=statut)

    tris = {
        'nom': 'nom_commercial',
        'prix_asc': 'prix_vente',
        'prix_desc': '-prix_vente',
        'recents': '-date_creation',
        'categorie': 'categorie__nom',
    }
    medicaments = medicaments.order_by(tris.get(tri, 'nom_commercial'))

    total = Medicament.objects.count()
    actifs = Medicament.objects.filter(statut='ACTIF').count()
    en_alerte = sum(1 for m in Medicament.objects.filter(statut='ACTIF') if m.stock_total() <= m.seuil_alerte)

    paginator = Paginator(medicaments, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'medicaments': page_obj,
        'page_obj': page_obj,
        'categories': Categorie.objects.all(),
        'query': query,
        'categorie_id': categorie_id,
        'statut': statut,
        'tri': tri,
        'total': total,
        'actifs': actifs,
        'en_alerte': en_alerte,
    }
    return render(request, 'medicaments/liste.html', context)


@login_required
def ajouter_medicament(request):
    if request.method == 'POST':
        form = MedicamentForm(request.POST, request.FILES)
        if form.is_valid():
            med = form.save()
            journaliser(request, 'AJOUT_MEDICAMENT', 'Medicament', med.id, med.nom_commercial)
            messages.success(request, 'Médicament ajouté avec succès.')
            return redirect('liste_medicaments')
    else:
        form = MedicamentForm()
    return render(request, 'medicaments/formulaire.html', {'form': form, 'titre': 'Ajouter un médicament'})


@login_required
def modifier_medicament(request, pk):
    medicament = get_object_or_404(Medicament, pk=pk)
    if request.method == 'POST':
        form = MedicamentForm(request.POST, request.FILES, instance=medicament)
        if form.is_valid():
            form.save()
            journaliser(request, 'MODIFICATION_MEDICAMENT', 'Medicament', medicament.id, medicament.nom_commercial)
            messages.success(request, 'Médicament modifié avec succès.')
            return redirect('liste_medicaments')
    else:
        form = MedicamentForm(instance=medicament)
    return render(request, 'medicaments/formulaire.html', {'form': form, 'titre': 'Modifier un médicament'})


@login_required
def archiver_medicament(request, pk):
    medicament = get_object_or_404(Medicament, pk=pk)
    medicament.statut = 'ARCHIVE'
    medicament.save()
    journaliser(request, 'ARCHIVAGE_MEDICAMENT', 'Medicament', medicament.id, medicament.nom_commercial)
    messages.success(request, 'Médicament archivé avec succès.')
    return redirect('liste_medicaments')


@login_required
def liste_categories(request):
    categories = Categorie.objects.all()
    return render(request, 'medicaments/categories_liste.html', {'categories': categories})


@login_required
def ajouter_categorie(request):
    if request.method == 'POST':
        form = CategorieForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Catégorie ajoutée avec succès.')
            return redirect('liste_categories')
    else:
        form = CategorieForm()
    return render(request, 'medicaments/categories_formulaire.html', {'form': form, 'titre': 'Ajouter une catégorie'})


@login_required
def modifier_categorie(request, pk):
    categorie = get_object_or_404(Categorie, pk=pk)
    if request.method == 'POST':
        form = CategorieForm(request.POST, instance=categorie)
        if form.is_valid():
            form.save()
            messages.success(request, 'Catégorie modifiée avec succès.')
            return redirect('liste_categories')
    else:
        form = CategorieForm(instance=categorie)
    return render(request, 'medicaments/categories_formulaire.html', {'form': form, 'titre': 'Modifier une catégorie'})
