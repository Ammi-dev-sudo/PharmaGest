from decimal import Decimal, InvalidOperation
from datetime import timedelta
import random
import uuid

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.db.models.functions import Coalesce
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from django.urls import reverse
from django.core.paginator import Paginator

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from medicaments.models import Medicament, Categorie
from stock.models import LotStock, MouvementStock
from .models import Vente, LigneVente, RetourVente, LigneRetourVente, Paiement
from clients.models import Client
from fournisseurs.models import Fournisseur
from achats.models import CommandeAchat
from utilisateurs.utils import journaliser

PHARMACIE = {
    'nom': 'PharmaGest',
    'adresse': 'Lot 12, Analakely — Antananarivo, Madagascar',
    'telephone': '+261 34 00 000 00',
    'email': 'contact@pharmagest.mg',
    'nif': 'NIF : 000 000 000',
    'stat': 'STAT : 46100 11 2026 0 00000',
}


def _mois_actuel():
    today = timezone.localdate()
    return today.replace(day=1)


@login_required
def dashboard(request):
    aujourd_hui = timezone.localdate()
    ventes_jour = Vente.objects.filter(date_vente__date=aujourd_hui, statut='VALIDEE')
    nb_ventes = ventes_jour.count()
    montant_jour = ventes_jour.aggregate(total=Sum('montant_total'))['total'] or Decimal('0')

    medicaments = Medicament.objects.filter(statut='ACTIF')
    nb_medicaments = medicaments.count()

    stocks_faibles = [med for med in medicaments if med.stock_total() <= med.seuil_alerte]
    nb_epuises = sum(1 for med in medicaments if med.stock_total() <= 0)

    dans_30_jours = aujourd_hui + timedelta(days=30)
    lots_proches = LotStock.objects.filter(
        date_peremption__lte=dans_30_jours, date_peremption__gte=aujourd_hui, quantite__gt=0
    ).select_related('medicament')
    lots_perimes = LotStock.objects.filter(
        date_peremption__lt=aujourd_hui, quantite__gt=0
    ).select_related('medicament')

    ventes_mois = Vente.objects.filter(
        date_vente__date__gte=_mois_actuel(), statut='VALIDEE'
    )
    ca_mois = ventes_mois.aggregate(total=Sum('montant_total'))['total'] or Decimal('0')
    panier_moyen = (ca_mois / ventes_mois.count()) if ventes_mois.count() else Decimal('0')

    # Ventes des 7 derniers jours
    labels, serie_ventes, serie_ca = [], [], []
    jours_fr = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
    for i in range(6, -1, -1):
        jour = aujourd_hui - timedelta(days=i)
        qs = Vente.objects.filter(date_vente__date=jour, statut='VALIDEE')
        labels.append(f"{jours_fr[jour.weekday()]} {jour.strftime('%d/%m')}")
        serie_ventes.append(qs.count())
        serie_ca.append(float(qs.aggregate(total=Sum('montant_total'))['total'] or 0))

    top_produits = list(
        LigneVente.objects.filter(vente__statut='VALIDEE')
        .values('medicament__nom_commercial')
        .annotate(quantite=Sum('quantite'), total=Sum('montant_ligne'))
        .order_by('-quantite')[:6]
    )

    categories = list(
        Categorie.objects.annotate(nb=Count('medicaments')).order_by('-nb')
    )

    repartition_stock = {
        'ok': max(nb_medicaments - len(stocks_faibles), 0),
        'faible': len([m for m in stocks_faibles if m.stock_total() > 0]),
        'epuise': nb_epuises,
    }

    recentes = Vente.objects.filter(statut='VALIDEE').select_related(
        'client', 'utilisateur'
    )[:6]

    achats_mois = CommandeAchat.objects.filter(date_commande__date__gte=_mois_actuel())
    montant_achats = achats_mois.aggregate(total=Sum('montant_total'))['total'] or Decimal('0')

    vedettes = (
        Medicament.objects.filter(statut='ACTIF')
        .annotate(nb_vendus=Sum('lignevente__quantite'))
        .order_by('-nb_vendus')[:4]
    )

    context = {
        'aujourd_hui': aujourd_hui,
        'nb_ventes': nb_ventes,
        'montant_jour': montant_jour,
        'nb_medicaments': nb_medicaments,
        'stocks_faibles': len(stocks_faibles),
        'lots_proches': lots_proches.count(),
        'lots_perimes': lots_perimes.count(),
        'nb_clients': Client.objects.count(),
        'nb_fournisseurs': Fournisseur.objects.filter(actif=True).count(),
        'ca_mois': ca_mois,
        'panier_moyen': panier_moyen,
        'ventes_mois': ventes_mois.count(),
        'montant_achats': montant_achats,
        'nb_commandes': achats_mois.count(),
        'alertes': stocks_faibles[:6],
        'lots_proches_liste': lots_proches[:6],
        'lots_perimes_liste': lots_perimes[:4],
        'recentes': recentes,
        'top_produits': top_produits,
        'categories': categories,
        'repartition_stock': repartition_stock,
        'vedettes': vedettes,
        'chart_labels': labels,
        'chart_ventes': serie_ventes,
        'chart_ca': serie_ca,
        'chart_categories_labels': [c.nom for c in categories],
        'chart_categories_data': [c.nb for c in categories],
    }
    return render(request, 'ventes/dashboard.html', context)


@login_required
def caisse(request):
    query = request.GET.get('q', '').strip()
    medicaments = (
        Medicament.objects.filter(statut='ACTIF')
        .select_related('categorie')
        .annotate(
            stock_disponible=Coalesce(
                Sum(
                    'lots__quantite',
                    filter=Q(
                        lots__quantite__gt=0,
                        lots__bloque=False,
                        lots__date_peremption__gte=timezone.localdate(),
                    ),
                ),
                0,
            )
        )
    )
    if query:
        medicaments = medicaments.filter(
            Q(nom_commercial__icontains=query)
            | Q(denomination_generique__icontains=query)
            | Q(code_barres__icontains=query)
        )
    medicaments = list(medicaments)
    panier = request.session.get('panier', [])
    total = sum(Decimal(str(item['montant_ligne'])) for item in panier)
    clients = Client.objects.filter(actif=True)
    vente_token = request.session.get('vente_token') or uuid.uuid4().hex
    request.session['vente_token'] = vente_token
    context = {
        'medicaments': medicaments,
        'panier': panier,
        'total': total,
        'nb_articles': sum(item['quantite'] for item in panier),
        'clients': clients,
        'query': query,
        'vente_token': vente_token,
    }
    return render(request, 'ventes/caisse.html', context)


def _ajouter_medicament_au_panier(request, medicament):
    lots = LotStock.objects.filter(
        medicament=medicament,
        quantite__gt=0,
        bloque=False,
        date_peremption__gte=timezone.localdate(),
    ).order_by('date_peremption')
    if not lots.exists():
        messages.error(request, 'Aucun lot valide disponible pour ce médicament.')
        return redirect('caisse')
    lot = lots.first()

    try:
        quantite = int(request.POST.get('quantite', 1))
    except (TypeError, ValueError):
        quantite = 0
    if quantite <= 0:
        messages.error(request, 'La quantité doit être supérieure à zéro.')
        return redirect('caisse')

    panier = request.session.get('panier', [])
    deja = sum(item['quantite'] for item in panier if item['lot_id'] == lot.id)
    if quantite + deja > lot.quantite:
        messages.error(request, 'Quantité supérieure au stock disponible du lot.')
        return redirect('caisse')

    existant = next((item for item in panier if item['lot_id'] == lot.id), None)
    if existant:
        existant['quantite'] += quantite
        existant['montant_ligne'] = float(medicament.prix_vente) * existant['quantite']
    else:
        panier.append({
            'medicament_id': medicament.id,
            'medicament_nom': medicament.nom_commercial,
            'image_url': medicament.image_url,
            'lot_id': lot.id,
            'lot_numero': lot.numero_lot,
            'lot_stock': lot.quantite,
            'quantite': quantite,
            'prix_unitaire': float(medicament.prix_vente),
            'montant_ligne': float(medicament.prix_vente) * quantite,
        })
    request.session['panier'] = panier
    messages.success(request, f'{medicament.nom_commercial} ajouté au panier.')
    return redirect('caisse')


@login_required
@require_POST
def ajouter_au_panier(request, medicament_id):
    medicament = get_object_or_404(Medicament, pk=medicament_id, statut='ACTIF')
    return _ajouter_medicament_au_panier(request, medicament)


@login_required
@require_POST
def ajouter_selection(request):
    medicament = get_object_or_404(
        Medicament, pk=request.POST.get('medicament'), statut='ACTIF'
    )
    return _ajouter_medicament_au_panier(request, medicament)


@login_required
@require_POST
def modifier_quantite(request, index):
    panier = request.session.get('panier', [])
    if not (0 <= index < len(panier)):
        messages.error(request, 'Article introuvable dans le panier.')
        return redirect('caisse')
    item = panier[index]
    try:
        quantite = int(request.POST.get('quantite', item['quantite']))
    except (TypeError, ValueError):
        quantite = 0
    if quantite <= 0:
        messages.error(request, 'La quantité doit être supérieure à zéro.')
        return redirect('caisse')
    lot = LotStock.objects.filter(pk=item.get('lot_id')).first()
    if not lot or quantite > lot.quantite:
        messages.error(request, 'Quantité supérieure au stock disponible du lot.')
        return redirect('caisse')
    item['quantite'] = quantite
    item['montant_ligne'] = float(item['prix_unitaire']) * quantite
    item['lot_stock'] = lot.quantite
    request.session['panier'] = panier
    messages.success(request, f'Quantité de {item["medicament_nom"]} mise à jour.')
    return redirect('caisse')


@login_required
@require_POST
def retirer_du_panier(request, index):
    panier = request.session.get('panier', [])
    if 0 <= index < len(panier):
        nom = panier[index].get('medicament_nom', 'Article')
        panier.pop(index)
        request.session['panier'] = panier
        messages.info(request, f'{nom} retiré du panier.')
    return redirect('caisse')


@login_required
@require_POST
def vider_panier(request):
    request.session['panier'] = []
    messages.info(request, 'Panier vidé.')
    return redirect('caisse')


@login_required
@require_POST
@transaction.atomic
def valider_vente(request):
    token = request.POST.get('vente_token', '')
    if not token or token != request.session.get('vente_token'):
        messages.error(request, 'Cette vente a déjà été traitée. Merci de recommencer.')
        return redirect('caisse')
    request.session.pop('vente_token', None)

    panier = request.session.get('panier', [])
    if not panier:
        messages.error(request, 'Le panier est vide.')
        return redirect('caisse')

    client_id = request.POST.get('client') or None
    mode_paiement = 'ESPECES'

    total = sum(Decimal(str(item['montant_ligne'])) for item in panier)
    try:
        montant_paye = Decimal(request.POST.get('montant_paye', '0') or '0')
    except InvalidOperation:
        messages.error(request, 'Montant payé invalide.')
        return redirect('caisse')

    if montant_paye < total:
        messages.error(request, 'Le montant payé est inférieur au total à régler.')
        return redirect('caisse')

    try:
        vente = Vente.objects.create(
            numero_vente=f"VTE-{timezone.now().strftime('%Y%m%d%H%M%S')}-{random.randint(100, 999)}",
            client_id=client_id,
            utilisateur=request.user,
            mode_paiement=mode_paiement,
            statut='VALIDEE',
            montant_total=total,
            montant_paye=montant_paye,
            montant_rendu=montant_paye - total,
        )
        for item in panier:
            medicament = Medicament.objects.get(pk=item['medicament_id'])
            lot = LotStock.objects.select_for_update().get(pk=item['lot_id'])
            quantite = int(item['quantite'])
            if (
                quantite <= 0
                or lot.quantite < quantite
                or lot.bloque
                or lot.date_peremption < timezone.localdate()
            ):
                raise ValueError(f"Stock insuffisant ou lot invalide pour {medicament.nom_commercial}.")
            LigneVente.objects.create(
                vente=vente,
                medicament=medicament,
                lot=lot,
                quantite=quantite,
                prix_unitaire=Decimal(str(item['prix_unitaire'])),
                montant_ligne=Decimal(str(item['montant_ligne'])),
            )
            lot.quantite -= quantite
            lot.save(update_fields=['quantite'])
            MouvementStock.objects.create(
                medicament=medicament,
                lot=lot,
                type_mouvement='SORTIE',
                quantite=quantite,
                motif=f'Vente {vente.numero_vente}',
                utilisateur=request.user,
                reference=vente.numero_vente,
            )
        Paiement.objects.create(
            vente=vente,
            mode=mode_paiement,
            montant=montant_paye,
            statut='CONFIRME',
            reference=vente.numero_vente,
        )
        journaliser(
            request, 'VALIDATION_VENTE', 'Vente', vente.numero_vente,
            f'{len(panier)} ligne(s) — {total} Ar — {mode_paiement}'
        )
    except Exception as exc:  # rollback automatique
        transaction.set_rollback(True)
        messages.error(request, f'Vente non enregistrée : {exc}')
        return redirect('caisse')

    request.session['panier'] = []
    messages.success(request, 'Vente validée. Le reçu PDF est généré automatiquement.')
    return redirect(reverse('recu_vente', args=[vente.pk]) + '?auto_pdf=1')


@login_required
def liste_ventes(request):
    query = request.GET.get('q', '').strip()
    mode = request.GET.get('mode', '')
    ventes = Vente.objects.filter(statut='VALIDEE').select_related('client', 'utilisateur')
    if query:
        ventes = ventes.filter(
            Q(numero_vente__icontains=query)
            | Q(client__nom_complet__icontains=query)
            | Q(utilisateur__username__icontains=query)
        )
    if mode:
        ventes = ventes.filter(mode_paiement=mode)
    totaux = ventes.aggregate(
        total=Sum('montant_total'),
        encaisse=Sum('montant_paye'),
        rendu=Sum('montant_rendu'),
        nb=Count('id'),
    )
    paginator = Paginator(ventes, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'ventes/liste.html', {
        'ventes': page_obj,
        'page_obj': page_obj,
        'query': query,
        'mode': mode,
        'modes_paiement': Vente.MODE_PAIEMENT_CHOICES,
        'stats': {
            'total': totaux['total'] or 0,
            'encaisse': totaux['encaisse'] or 0,
            'rendu': totaux['rendu'] or 0,
            'nb': totaux['nb'] or 0,
            'panier': (totaux['total'] or 0) / totaux['nb'] if totaux['nb'] else 0,
        },
    })


@login_required
def detail_vente(request, pk):
    vente = get_object_or_404(
        Vente.objects.select_related('client', 'utilisateur').prefetch_related('lignes__medicament', 'paiements'),
        pk=pk,
    )
    return render(request, 'ventes/detail.html', {'vente': vente, 'pharmacie': PHARMACIE})


@login_required
def recu_vente(request, pk):
    vente = get_object_or_404(
        Vente.objects.select_related('client', 'utilisateur').prefetch_related(
            'lignes__medicament', 'lignes__lot', 'paiements'
        ),
        pk=pk,
    )
    return render(request, 'ventes/recu.html', {'vente': vente, 'pharmacie': PHARMACIE})


@login_required
def recu_vente_pdf(request, pk):
    vente = get_object_or_404(
        Vente.objects.select_related('client', 'utilisateur').prefetch_related(
            'lignes__medicament', 'lignes__lot', 'paiements'
        ),
        pk=pk,
    )
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="recu_{vente.numero_vente}.pdf"'
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    teal = (0.05, 0.58, 0.56)

    p.setFillColorRGB(*teal)
    p.rect(0, height - 110, width, 110, fill=1, stroke=0)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 20)
    p.drawString(45, height - 52, "PHARMAGEST")
    p.setFont("Helvetica", 9)
    p.drawString(45, height - 70, "Gestion de pharmacie — Reçu de vente")
    p.drawString(45, height - 84, f"{PHARMACIE['adresse']} — {PHARMACIE['telephone']}")
    p.drawRightString(width - 45, height - 52, f"REÇU N° {vente.numero_vente}")
    p.drawRightString(width - 45, height - 68, f"Date : {vente.date_vente.strftime('%d/%m/%Y à %H:%M')}")
    p.drawRightString(width - 45, height - 84, f"Caissier : {vente.utilisateur.get_full_name() or vente.utilisateur.username}")

    p.setFillColorRGB(0.1, 0.1, 0.15)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(45, height - 140, "CLIENT")
    p.setFont("Helvetica", 9)
    p.drawString(45, height - 155, vente.client.nom_complet if vente.client else 'Client non identifié')

    y = height - 190
    p.setFillColorRGB(0.94, 0.97, 0.98)
    p.rect(40, y - 6, width - 80, 22, fill=1, stroke=0)
    p.setFillColorRGB(0.2, 0.28, 0.35)
    p.setFont("Helvetica-Bold", 8)
    p.drawString(48, y, "DÉSIGNATION")
    p.drawRightString(330, y, "QTÉ")
    p.drawRightString(425, y, "PRIX UNIT.")
    p.drawRightString(width - 48, y, "MONTANT")
    y -= 26

    p.setFont("Helvetica", 8.5)
    for ligne in vente.lignes.all():
        p.setFillColorRGB(0.12, 0.16, 0.22)
        p.drawString(48, y, f"{ligne.medicament.nom_commercial[:38]}")
        p.setFillColorRGB(0.45, 0.5, 0.56)
        p.setFont("Helvetica", 7)
        p.drawString(48, y - 10, f"Lot {ligne.lot.numero_lot} — {ligne.medicament.dosage}")
        p.setFont("Helvetica", 8.5)
        p.setFillColorRGB(0.12, 0.16, 0.22)
        p.drawRightString(330, y, str(ligne.quantite))
        p.drawRightString(425, y, f"{ligne.prix_unitaire:.0f} Ar")
        p.drawRightString(width - 48, y, f"{ligne.montant_ligne:.0f} Ar")
        y -= 28
        p.setStrokeColorRGB(0.88, 0.91, 0.94)
        p.line(45, y + 8, width - 45, y + 8)

    y -= 12
    p.setFont("Helvetica", 10)
    p.setFillColorRGB(0.3, 0.36, 0.42)
    p.drawRightString(425, y, "Total à payer :")
    p.setFont("Helvetica-Bold", 10)
    p.setFillColorRGB(0.12, 0.16, 0.22)
    p.drawRightString(width - 48, y, f"{vente.montant_total:.0f} Ar")
    y -= 18
    p.setFont("Helvetica", 9)
    p.drawRightString(425, y, f"Payé ({vente.get_mode_paiement_display()}) :")
    p.drawRightString(width - 48, y, f"{vente.montant_paye:.0f} Ar")
    y -= 16
    p.drawRightString(425, y, "Monnaie rendue :")
    p.drawRightString(width - 48, y, f"{vente.montant_rendu:.0f} Ar")

    p.setFont("Helvetica-Oblique", 8)
    p.setFillColorRGB(0.45, 0.5, 0.56)
    p.drawCentredString(width / 2, 90, "Merci de votre confiance — Les médicaments ne sont ni repris ni échangés sans ordonnance.")
    p.drawCentredString(width / 2, 76, "PharmaGest — Application de gestion de pharmacie")
    p.showPage()
    p.save()
    return response


def _quantite_deja_retournee(ligne):
    total = LigneRetourVente.objects.filter(ligne_vente=ligne).aggregate(total=Sum('quantite'))['total']
    return total or 0


@login_required
def liste_retours(request):
    retours = RetourVente.objects.select_related('vente', 'utilisateur').prefetch_related('lignes')
    return render(request, 'ventes/retours.html', {'retours': retours})


@login_required
def creer_retour(request, pk):
    vente = get_object_or_404(
        Vente.objects.select_related('client').prefetch_related('lignes__medicament', 'lignes__lot'),
        pk=pk,
    )
    if vente.statut != 'VALIDEE':
        messages.error(request, 'Seule une vente validée peut faire l\'objet d\'un retour.')
        return redirect('detail_vente', pk=pk)

    lignes = []
    for ligne in vente.lignes.all():
        lignes.append({
            'ligne': ligne,
            'deja_retournee': _quantite_deja_retournee(ligne),
            'restante': ligne.quantite - _quantite_deja_retournee(ligne),
        })

    if request.method == 'POST':
        motif = request.POST.get('motif', '').strip()
        remettre = request.POST.get('remettre_en_stock') == 'on'
        if not motif:
            messages.error(request, 'Le motif du retour est obligatoire.')
            return render(request, 'ventes/retour_formulaire.html', {'vente': vente, 'lignes': lignes})

        with transaction.atomic():
            retour = RetourVente.objects.create(
                vente=vente,
                utilisateur=request.user,
                motif=motif,
                montant_rembourse=0,
                type_operation='RETOUR',
                remis_en_stock=remettre,
            )
            montant_total = Decimal('0')
            for item in lignes:
                ligne = item['ligne']
                try:
                    quantite = int(request.POST.get(f'quantite_{ligne.id}', 0))
                except (TypeError, ValueError):
                    quantite = 0
                if quantite <= 0:
                    continue
                if quantite > item['restante']:
                    messages.error(request, f'Quantité trop élevée pour {ligne.medicament.nom_commercial}.')
                    transaction.set_rollback(True)
                    return redirect('creer_retour', pk=pk)
                montant = ligne.prix_unitaire * quantite
                montant_total += montant
                LigneRetourVente.objects.create(
                    retour=retour,
                    ligne_vente=ligne,
                    medicament=ligne.medicament,
                    lot=ligne.lot,
                    quantite=quantite,
                    montant_rembourse=montant,
                )
                if remettre and ligne.lot and ligne.lot.date_peremption >= timezone.localdate():
                    lot = LotStock.objects.select_for_update().get(pk=ligne.lot.pk)
                    lot.quantite += quantite
                    lot.save(update_fields=['quantite'])
                    MouvementStock.objects.create(
                        medicament=ligne.medicament,
                        lot=lot,
                        type_mouvement='RETOUR',
                        quantite=quantite,
                        motif=f'Retour vente {vente.numero_vente} — {motif}',
                        utilisateur=request.user,
                        reference=f'RET-{retour.id}',
                    )
            if montant_total == 0:
                transaction.set_rollback(True)
                messages.error(request, 'Veuillez sélectionner au moins un produit à retourner.')
                return redirect('creer_retour', pk=pk)
            retour.montant_rembourse = montant_total
            retour.save(update_fields=['montant_rembourse'])
            Paiement.objects.create(
                vente=vente,
                mode=vente.mode_paiement,
                montant=montant_total,
                statut='REMBOURSE',
                reference=f'RET-{retour.id}',
            )
            journaliser(request, 'RETOUR_VENTE', 'RetourVente', retour.id,
                        f'{montant_total} Ar — {motif}')
        messages.success(request, 'Retour enregistré et remboursement calculé.')
        return redirect('liste_retours')

    return render(request, 'ventes/retour_formulaire.html', {'vente': vente, 'lignes': lignes})


@login_required
@require_POST
@transaction.atomic
def annuler_vente(request, pk):
    vente = get_object_or_404(Vente, pk=pk)
    if vente.statut != 'VALIDEE':
        messages.error(request, 'Cette vente ne peut plus être annulée.')
        return redirect('detail_vente', pk=pk)

    retour = RetourVente.objects.create(
        vente=vente,
        utilisateur=request.user,
        motif='Annulation de la vente',
        montant_rembourse=vente.montant_total,
        type_operation='ANNULATION',
        remis_en_stock=True,
    )
    for ligne in vente.lignes.all():
        restante = ligne.quantite - _quantite_deja_retournee(ligne)
        if restante <= 0:
            continue
        LigneRetourVente.objects.create(
            retour=retour,
            ligne_vente=ligne,
            medicament=ligne.medicament,
            lot=ligne.lot,
            quantite=restante,
            montant_rembourse=ligne.prix_unitaire * restante,
        )
        if ligne.lot and ligne.lot.date_peremption >= timezone.localdate():
            lot = LotStock.objects.select_for_update().get(pk=ligne.lot.pk)
            lot.quantite += restante
            lot.save(update_fields=['quantite'])
            MouvementStock.objects.create(
                medicament=ligne.medicament,
                lot=lot,
                type_mouvement='RETOUR',
                quantite=restante,
                motif=f'Annulation vente {vente.numero_vente}',
                utilisateur=request.user,
                reference=f'RET-{retour.id}',
            )
    vente.statut = 'ANNULEE'
    vente.save(update_fields=['statut'])
    Paiement.objects.create(
        vente=vente,
        mode=vente.mode_paiement,
        montant=vente.montant_total,
        statut='REMBOURSE',
        reference=f'RET-{retour.id}',
    )
    journaliser(request, 'ANNULATION_VENTE', 'Vente', vente.numero_vente,
                f'Montant remboursé : {vente.montant_total} Ar')
    messages.success(request, 'Vente annulée, stock réintégré et remboursement enregistré.')
    return redirect('detail_vente', pk=pk)


@login_required
def facture_vente_pdf(request, pk):
    vente = get_object_or_404(
        Vente.objects.select_related('client', 'utilisateur').prefetch_related(
            'lignes__medicament', 'lignes__lot', 'paiements'
        ),
        pk=pk,
    )
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="facture_{vente.numero_vente}.pdf"'
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    p.setFillColorRGB(0.05, 0.58, 0.56)
    p.rect(0, height - 110, width, 110, fill=1, stroke=0)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 20)
    p.drawString(45, height - 52, "PHARMAGEST — FACTURE")
    p.setFont("Helvetica", 9)
    p.drawString(45, height - 70, f"{PHARMACIE['adresse']} — {PHARMACIE['telephone']}")
    p.drawString(45, height - 84, f"{PHARMACIE['email']} — {PHARMACIE['nif']} — {PHARMACIE['stat']}")
    p.drawRightString(width - 45, height - 52, f"FACTURE N° {vente.numero_vente}")
    p.drawRightString(width - 45, height - 68, f"Date : {vente.date_vente.strftime('%d/%m/%Y à %H:%M')}")
    p.drawRightString(width - 45, height - 84, f"Caissier : {vente.utilisateur.get_full_name() or vente.utilisateur.username}")

    p.setFillColorRGB(0.1, 0.1, 0.15)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(45, height - 140, "FACTURÉ À")
    p.setFont("Helvetica", 9)
    p.drawString(45, height - 155, vente.client.nom_complet if vente.client else 'Client non identifié')
    if vente.client:
        p.drawString(45, height - 169, f"{vente.client.telephone or ''} {vente.client.email or ''}")
        p.drawString(45, height - 183, vente.client.adresse or '')

    y = height - 215
    p.setFillColorRGB(0.94, 0.97, 0.98)
    p.rect(40, y - 6, width - 80, 22, fill=1, stroke=0)
    p.setFillColorRGB(0.2, 0.28, 0.35)
    p.setFont("Helvetica-Bold", 8)
    p.drawString(48, y, "DÉSIGNATION")
    p.drawRightString(330, y, "QTÉ")
    p.drawRightString(425, y, "PRIX UNIT.")
    p.drawRightString(width - 48, y, "MONTANT")
    y -= 26
    p.setFont("Helvetica", 8.5)
    for ligne in vente.lignes.all():
        p.setFillColorRGB(0.12, 0.16, 0.22)
        p.drawString(48, y, f"{ligne.medicament.nom_commercial[:38]}")
        p.setFillColorRGB(0.45, 0.5, 0.56)
        p.setFont("Helvetica", 7)
        p.drawString(48, y - 10, f"Lot {ligne.lot.numero_lot} — {ligne.medicament.dosage}")
        p.setFont("Helvetica", 8.5)
        p.setFillColorRGB(0.12, 0.16, 0.22)
        p.drawRightString(330, y, str(ligne.quantite))
        p.drawRightString(425, y, f"{ligne.prix_unitaire:.0f} Ar")
        p.drawRightString(width - 48, y, f"{ligne.montant_ligne:.0f} Ar")
        y -= 28
        p.setStrokeColorRGB(0.88, 0.91, 0.94)
        p.line(45, y + 8, width - 45, y + 8)

    y -= 12
    p.setFont("Helvetica", 10)
    p.setFillColorRGB(0.3, 0.36, 0.42)
    p.drawRightString(425, y, "Total à payer :")
    p.setFont("Helvetica-Bold", 10)
    p.setFillColorRGB(0.12, 0.16, 0.22)
    p.drawRightString(width - 48, y, f"{vente.montant_total:.0f} Ar")
    y -= 18
    p.setFont("Helvetica", 9)
    p.drawRightString(425, y, f"Payé ({vente.get_mode_paiement_display()}) :")
    p.drawRightString(width - 48, y, f"{vente.montant_paye:.0f} Ar")
    y -= 16
    p.drawRightString(425, y, "Monnaie rendue :")
    p.drawRightString(width - 48, y, f"{vente.montant_rendu:.0f} Ar")

    p.setFont("Helvetica-Oblique", 8)
    p.setFillColorRGB(0.45, 0.5, 0.56)
    p.drawCentredString(width / 2, 90, "Facture émise par PharmaGest — TVA non applicable, article 06 du CGI malgache.")
    p.drawCentredString(width / 2, 76, f"{PHARMACIE['nif']} — {PHARMACIE['stat']}")
    p.showPage()
    p.save()
    return response
