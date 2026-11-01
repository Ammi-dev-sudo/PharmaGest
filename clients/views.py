from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Client
from .forms import ClientForm


@login_required
def liste_clients(request):
    query = request.GET.get('q', '').strip()
    clients = Client.objects.all()
    if query:
        clients = clients.filter(
            Q(nom_complet__icontains=query)
            | Q(telephone__icontains=query)
            | Q(email__icontains=query)
        )
    paginator = Paginator(clients, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'clients/liste.html', {
        'clients': page_obj,
        'page_obj': page_obj,
        'query': query,
    })


@login_required
def ajouter_client(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Client ajouté avec succès.')
            return redirect('liste_clients')
    else:
        form = ClientForm()
    return render(request, 'clients/formulaire.html', {'form': form, 'titre': 'Ajouter un client'})


@login_required
def modifier_client(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, 'Client modifié avec succès.')
            return redirect('liste_clients')
    else:
        form = ClientForm(instance=client)
    return render(request, 'clients/formulaire.html', {'form': form, 'titre': 'Modifier un client'})


@login_required
def detail_client(request, pk):
    from ventes.models import Vente
    client = get_object_or_404(Client, pk=pk)
    ventes = Vente.objects.filter(client=client, statut='VALIDEE').order_by('-date_vente')
    total = ventes.aggregate(t=Sum('montant_total'))['t'] or 0
    return render(request, 'clients/detail.html', {
        'client': client,
        'ventes': ventes[:100],
        'total_achats': total,
        'nb_ventes': ventes.count(),
    })


@login_required
def basculer_client(request, pk):
    client = get_object_or_404(Client, pk=pk)
    client.actif = not client.actif
    client.save(update_fields=['actif'])
    messages.success(request, 'Statut du client mis à jour.')
    return redirect('liste_clients')
