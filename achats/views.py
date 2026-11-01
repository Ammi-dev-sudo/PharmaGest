from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from .models import CommandeAchat, LigneAchat, ReceptionAchat, LigneReception
from .forms import CommandeAchatForm
from fournisseurs.models import Fournisseur
from medicaments.models import Medicament
from stock.models import LotStock, MouvementStock
from utilisateurs.utils import journaliser
import random

PHARMACIE = {
    'nom': 'PharmaGest',
    'adresse': 'Lot 12, Analakely — Antananarivo, Madagascar',
    'telephone': '+261 34 00 000 00',
    'email': 'contact@pharmagest.mg',
    'nif': 'NIF : 000 000 000',
    'stat': 'STAT : 46100 11 2026 0 00000',
}


@login_required
def liste_commandes(request):
    query = request.GET.get('q', '').strip()
    statut = request.GET.get('statut', '')
    commandes = CommandeAchat.objects.select_related('fournisseur', 'utilisateur')
    if query:
        commandes = commandes.filter(
            Q(numero_commande__icontains=query)
            | Q(fournisseur__nom_raison_sociale__icontains=query)
        )
    if statut:
        commandes = commandes.filter(statut=statut)
    paginator = Paginator(commandes, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'achats/liste.html', {
        'commandes': page_obj,
        'page_obj': page_obj,
        'query': query,
        'statut': statut,
        'statuts': CommandeAchat.STATUT_CHOICES,
    })


@login_required
def creer_commande(request):
    if request.method == 'POST':
        form = CommandeAchatForm(request.POST)
        if form.is_valid():
            commande = form.save(commit=False)
            commande.utilisateur = request.user
            commande.numero_commande = f"ACH-{timezone.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
            commande.save()
            journaliser(request, 'CREATION_COMMANDE', 'CommandeAchat', commande.numero_commande)
            messages.success(request, 'Commande créée avec succès.')
            return redirect('detail_commande', pk=commande.pk)
    else:
        form = CommandeAchatForm()
    return render(request, 'achats/creer.html', {'form': form})


@login_required
def detail_commande(request, pk):
    commande = get_object_or_404(
        CommandeAchat.objects.select_related('fournisseur', 'utilisateur').prefetch_related('lignes__medicament'),
        pk=pk,
    )
    medicaments = Medicament.objects.filter(statut='ACTIF')
    if request.method == 'POST' and commande.statut == 'BROUILLON':
        medicament_id = request.POST.get('medicament')
        try:
            quantite = int(request.POST.get('quantite', 0))
            prix_unitaire = Decimal(request.POST.get('prix_unitaire', '0'))
        except (TypeError, ValueError, InvalidOperation):
            quantite, prix_unitaire = 0, Decimal('0')
        if medicament_id and quantite > 0 and prix_unitaire >= 0:
            medicament = get_object_or_404(Medicament, pk=medicament_id)
            montant_ligne = quantite * prix_unitaire
            LigneAchat.objects.create(
                commande=commande,
                medicament=medicament,
                quantite=quantite,
                prix_unitaire=prix_unitaire,
                montant_ligne=montant_ligne,
            )
            commande.montant_total = sum(l.montant_ligne for l in commande.lignes.all())
            commande.save(update_fields=['montant_total'])
            messages.success(request, 'Ligne ajoutée avec succès.')
            return redirect('detail_commande', pk=pk)
        messages.error(request, 'Quantité ou prix invalide.')
    return render(request, 'achats/detail.html', {'commande': commande, 'medicaments': medicaments})


@login_required
def supprimer_ligne(request, pk, ligne_pk):
    commande = get_object_or_404(CommandeAchat, pk=pk)
    if commande.statut != 'BROUILLON':
        messages.error(request, 'Impossible de modifier une commande validée.')
        return redirect('detail_commande', pk=pk)
    ligne = get_object_or_404(LigneAchat, pk=ligne_pk, commande=commande)
    ligne.delete()
    commande.montant_total = sum(l.montant_ligne for l in commande.lignes.all())
    commande.save(update_fields=['montant_total'])
    messages.success(request, 'Ligne supprimée.')
    return redirect('detail_commande', pk=pk)


@login_required
def valider_commande(request, pk):
    commande = get_object_or_404(CommandeAchat, pk=pk)
    if commande.statut == 'BROUILLON':
        if not commande.lignes.exists():
            messages.error(request, 'Ajoutez au moins une ligne avant de valider.')
            return redirect('detail_commande', pk=pk)
        commande.statut = 'COMMANDEE'
        commande.save(update_fields=['statut'])
        journaliser(request, 'VALIDATION_COMMANDE', 'CommandeAchat', commande.numero_commande)
        messages.success(request, 'Commande validée.')
    return redirect('detail_commande', pk=pk)


@login_required
@transaction.atomic
def recevoir_commande(request, pk):
    commande = get_object_or_404(CommandeAchat, pk=pk)
    if commande.statut not in ('COMMANDEE', 'PARTIELLEMENT_RECEPTIONNEE'):
        messages.error(request, 'Cette commande ne peut pas être réceptionnée.')
        return redirect('detail_commande', pk=pk)

    if request.method == 'POST':
        reception = ReceptionAchat.objects.create(
            commande=commande, utilisateur=request.user,
            notes=request.POST.get('notes', ''),
        )
        aucune = True
        for ligne in commande.lignes.all():
            try:
                quantite_recue = int(request.POST.get(f'quantite_{ligne.id}', 0))
            except (TypeError, ValueError):
                quantite_recue = 0
            numero_lot = request.POST.get(f'lot_{ligne.id}', '').strip()
            date_peremption = request.POST.get(f'peremption_{ligne.id}')
            if quantite_recue <= 0 or not numero_lot or not date_peremption:
                continue
            if quantite_recue > ligne.quantite_restante:
                messages.error(request, f'Quantité trop élevée pour {ligne.medicament.nom_commercial}.')
                transaction.set_rollback(True)
                return redirect('recevoir_commande', pk=pk)
            LigneReception.objects.create(
                reception=reception,
                ligne_achat=ligne,
                medicament=ligne.medicament,
                numero_lot=numero_lot,
                date_peremption=date_peremption,
                quantite_recue=quantite_recue,
                prix_unitaire=ligne.prix_unitaire,
            )
            lot = LotStock.objects.create(
                medicament=ligne.medicament,
                numero_lot=numero_lot,
                date_peremption=date_peremption,
                quantite=quantite_recue,
                quantite_initiale=quantite_recue,
            )
            MouvementStock.objects.create(
                medicament=ligne.medicament,
                lot=lot,
                type_mouvement='ENTREE',
                quantite=quantite_recue,
                motif=f'Réception commande {commande.numero_commande}',
                utilisateur=request.user,
                reference=f'REC-{reception.id}',
            )
            aucune = False
        if aucune:
            transaction.set_rollback(True)
            messages.error(request, 'Aucune quantité valide saisie.')
            return redirect('recevoir_commande', pk=pk)

        restantes = [l for l in commande.lignes.all() if l.quantite_restante > 0]
        commande.statut = 'PARTIELLEMENT_RECEPTIONNEE' if restantes else 'ENTIEREMENT_RECEPTIONNEE'
        commande.save(update_fields=['statut'])
        journaliser(request, 'RECEPTION_COMMANDE', 'CommandeAchat', commande.numero_commande,
                    f'Réception REC-{reception.id}')
        messages.success(request, 'Réception enregistrée. Le stock a été mis à jour.')
        return redirect('bon_reception_pdf', pk=reception.pk)
    return render(request, 'achats/recevoir.html', {'commande': commande})


@login_required
def bon_commande_pdf(request, pk):
    commande = get_object_or_404(CommandeAchat.objects.select_related('fournisseur'), pk=pk)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="bon_commande_{commande.numero_commande}.pdf"'
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    p.setFillColorRGB(0.05, 0.58, 0.56)
    p.rect(0, height - 100, width, 100, fill=1, stroke=0)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 19)
    p.drawString(45, height - 50, "PHARMAGEST — BON DE COMMANDE")
    p.setFont("Helvetica", 9)
    p.drawString(45, height - 68, PHARMACIE['adresse'])
    p.drawString(45, height - 82, f"{PHARMACIE['telephone']} — {PHARMACIE['email']}")
    p.drawRightString(width - 45, height - 50, f"N° {commande.numero_commande}")
    p.drawRightString(width - 45, height - 68, f"Date : {commande.date_commande.strftime('%d/%m/%Y')}")
    p.setFillColorRGB(0.1, 0.1, 0.15)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(45, height - 130, "FOURNISSEUR")
    p.setFont("Helvetica", 9)
    p.drawString(45, height - 146, commande.fournisseur.nom_raison_sociale)
    p.drawString(45, height - 160, commande.fournisseur.telephone)
    p.drawString(45, height - 174, commande.fournisseur.email or '')

    y = height - 210
    p.setFillColorRGB(0.94, 0.97, 0.98)
    p.rect(40, y - 6, width - 80, 22, fill=1, stroke=0)
    p.setFillColorRGB(0.2, 0.28, 0.35)
    p.setFont("Helvetica-Bold", 8)
    p.drawString(48, y, "DÉSIGNATION")
    p.drawRightString(330, y, "QTÉ")
    p.drawRightString(430, y, "PRIX UNIT.")
    p.drawRightString(width - 48, y, "MONTANT")
    y -= 26
    p.setFont("Helvetica", 8.5)
    for ligne in commande.lignes.all():
        p.setFillColorRGB(0.12, 0.16, 0.22)
        p.drawString(48, y, ligne.medicament.nom_commercial[:40])
        p.drawRightString(330, y, str(ligne.quantite))
        p.drawRightString(430, y, f"{ligne.prix_unitaire:.0f} Ar")
        p.drawRightString(width - 48, y, f"{ligne.montant_ligne:.0f} Ar")
        y -= 20
    p.setStrokeColorRGB(0.88, 0.91, 0.94)
    p.line(45, y + 8, width - 45, y + 8)
    p.setFont("Helvetica-Bold", 11)
    p.drawRightString(430, y - 8, "TOTAL :")
    p.drawRightString(width - 48, y - 8, f"{commande.montant_total:.0f} Ar")
    p.setFont("Helvetica", 8)
    p.setFillColorRGB(0.45, 0.5, 0.56)
    p.drawString(45, 70, "Document généré par PharmaGest — À conserver.")
    p.showPage()
    p.save()
    return response


@login_required
def bon_reception_pdf(request, pk):
    reception = get_object_or_404(
        ReceptionAchat.objects.select_related('commande__fournisseur').prefetch_related('lignes__medicament'),
        pk=pk,
    )
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="bon_reception_REC-{reception.id}.pdf"'
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    p.setFillColorRGB(0.05, 0.58, 0.56)
    p.rect(0, height - 100, width, 100, fill=1, stroke=0)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 19)
    p.drawString(45, height - 50, "PHARMAGEST — BON DE RÉCEPTION")
    p.setFont("Helvetica", 9)
    p.drawString(45, height - 68, PHARMACIE['adresse'])
    p.drawString(45, height - 82, f"{PHARMACIE['telephone']} — {PHARMACIE['email']}")
    p.drawRightString(width - 45, height - 50, f"RÉCEPTION REC-{reception.id}")
    p.drawRightString(width - 45, height - 68, f"Date : {reception.date_reception.strftime('%d/%m/%Y')}")
    p.setFillColorRGB(0.1, 0.1, 0.15)
    p.setFont("Helvetica", 9)
    p.drawString(45, height - 130, f"Commande : {reception.commande.numero_commande}")
    p.drawString(45, height - 146, f"Fournisseur : {reception.commande.fournisseur.nom_raison_sociale}")

    y = height - 185
    p.setFillColorRGB(0.94, 0.97, 0.98)
    p.rect(40, y - 6, width - 80, 22, fill=1, stroke=0)
    p.setFillColorRGB(0.2, 0.28, 0.35)
    p.setFont("Helvetica-Bold", 8)
    p.drawString(48, y, "MÉDICAMENT")
    p.drawString(250, y, "LOT")
    p.drawString(330, y, "EXPIRATION")
    p.drawRightString(430, y, "QTÉ REÇUE")
    p.drawRightString(width - 48, y, "PRIX")
    y -= 26
    p.setFont("Helvetica", 8.5)
    for ligne in reception.lignes.all():
        p.setFillColorRGB(0.12, 0.16, 0.22)
        p.drawString(48, y, ligne.medicament.nom_commercial[:34])
        p.drawString(250, y, ligne.numero_lot)
        p.drawString(330, y, ligne.date_peremption.strftime('%d/%m/%Y'))
        p.drawRightString(430, y, str(ligne.quantite_recue))
        p.drawRightString(width - 48, y, f"{ligne.prix_unitaire:.0f} Ar")
        y -= 20
    p.setFont("Helvetica-Oblique", 8)
    p.setFillColorRGB(0.45, 0.5, 0.56)
    p.drawString(45, 70, f"Réceptionné par : {reception.utilisateur.username}")
    p.showPage()
    p.save()
    return response


@login_required
@require_POST
def annuler_commande(request, pk):
    commande = get_object_or_404(CommandeAchat, pk=pk)
    if commande.statut in ('BROUILLON', 'COMMANDEE'):
        commande.statut = 'ANNULEE'
        commande.save(update_fields=['statut'])
        journaliser(request, 'ANNULATION_COMMANDE', 'CommandeAchat', commande.numero_commande)
        messages.success(request, 'Commande annulée.')
    else:
        messages.error(request, 'Cette commande ne peut plus être annulée.')
    return redirect('detail_commande', pk=pk)
