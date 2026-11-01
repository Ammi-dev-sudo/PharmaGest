from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from medicaments.models import Medicament
from utilisateurs.utils import journaliser
from .models import LotStock, MouvementStock


@login_required
def etat_stock(request):
    query = request.GET.get('q', '').strip()
    medicaments = Medicament.objects.filter(statut='ACTIF').select_related('categorie')
    if query:
        medicaments = medicaments.filter(
            Q(nom_commercial__icontains=query) | Q(code_barres__icontains=query)
        )
    medicaments = list(medicaments)
    total_unites = sum(m.stock_total() for m in medicaments)
    valeur_stock = sum(m.stock_total() * m.prix_achat for m in medicaments)
    en_alerte = [m for m in medicaments if m.stock_total() <= m.seuil_alerte]
    paginator = Paginator(medicaments, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    context = {
        'medicaments': page_obj,
        'page_obj': page_obj,
        'query': query,
        'total_unites': total_unites,
        'valeur_stock': valeur_stock,
        'nb_alertes': len(en_alerte),
        'nb_references': len(medicaments),
    }
    return render(request, 'stock/etat.html', context)


@login_required
def liste_mouvements(request):
    query = request.GET.get('q', '').strip()
    type_mouvement = request.GET.get('type', '')
    mouvements = MouvementStock.objects.select_related('medicament', 'lot', 'utilisateur')
    if query:
        mouvements = mouvements.filter(
            Q(medicament__nom_commercial__icontains=query)
            | Q(reference__icontains=query)
            | Q(motif__icontains=query)
        )
    if type_mouvement:
        mouvements = mouvements.filter(type_mouvement=type_mouvement)
    paginator = Paginator(mouvements, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'stock/mouvements.html', {
        'mouvements': page_obj,
        'page_obj': page_obj,
        'query': query,
        'type_mouvement': type_mouvement,
        'types': MouvementStock.TYPE_CHOICES,
    })


@login_required
def alertes_stock(request):
    medicaments = Medicament.objects.filter(statut='ACTIF').select_related('categorie')
    alertes = [med for med in medicaments if med.stock_total() <= med.seuil_alerte]
    return render(request, 'stock/alertes.html', {'alertes': alertes})


@login_required
def produits_perimes(request):
    aujourd_hui = timezone.localdate()
    dans_30_jours = aujourd_hui + timedelta(days=30)
    lots_proches = LotStock.objects.filter(
        date_peremption__lte=dans_30_jours, date_peremption__gte=aujourd_hui, quantite__gt=0
    ).select_related('medicament')
    lots_perimes = LotStock.objects.filter(
        date_peremption__lt=aujourd_hui, quantite__gt=0
    ).select_related('medicament')
    return render(request, 'stock/peremptions.html', {
        'lots_proches': lots_proches,
        'lots_perimes': lots_perimes,
        'aujourd_hui': aujourd_hui,
    })


@login_required
def inventaire(request):
    query = request.GET.get('q', '').strip()
    lots = LotStock.objects.select_related('medicament').order_by('medicament__nom_commercial')
    if query:
        lots = lots.filter(
            Q(medicament__nom_commercial__icontains=query) | Q(numero_lot__icontains=query)
        )
    if request.method == 'POST':
        with transaction.atomic():
            corrections = 0
            for lot in lots:
                valeur = request.POST.get(f'qte_{lot.id}')
                if valeur is None or valeur == '':
                    continue
                try:
                    nouvelle = int(valeur)
                except ValueError:
                    continue
                if nouvelle < 0:
                    continue
                if nouvelle != lot.quantite:
                    ecart = nouvelle - lot.quantite
                    lot.quantite = nouvelle
                    lot.save(update_fields=['quantite'])
                    MouvementStock.objects.create(
                        medicament=lot.medicament,
                        lot=lot,
                        type_mouvement='CORRECTION',
                        quantite=ecart,
                        motif='Inventaire physique',
                        utilisateur=request.user,
                        reference=f'INV-{lot.numero_lot}',
                    )
                    corrections += 1
            if corrections:
                journaliser(request, 'INVENTAIRE', 'Stock', '', f'{corrections} lot(s) corrigé(s)')
                messages.success(request, f'Inventaire enregistré : {corrections} correction(s).')
            else:
                messages.info(request, 'Aucune différence détectée.')
        return redirect('inventaire')
    return render(request, 'stock/inventaire.html', {'lots': lots, 'query': query})


@login_required
def peremptions_pdf(request):
    from django.http import HttpResponse
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4

    aujourd_hui = timezone.localdate()
    dans_30_jours = aujourd_hui + timedelta(days=30)
    lots_proches = LotStock.objects.filter(
        date_peremption__lte=dans_30_jours, date_peremption__gte=aujourd_hui, quantite__gt=0
    ).select_related('medicament')
    lots_perimes = LotStock.objects.filter(
        date_peremption__lt=aujourd_hui, quantite__gt=0
    ).select_related('medicament')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="produits_peremptions.pdf"'
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    p.setFillColorRGB(0.05, 0.58, 0.56)
    p.rect(0, height - 100, width, 100, fill=1, stroke=0)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 18)
    p.drawString(45, height - 50, "PHARMAGEST — PÉREMPTIONS")
    p.setFont("Helvetica", 9)
    p.drawString(45, height - 68, "Lot 12, Analakely — Antananarivo, Madagascar")
    p.drawRightString(width - 45, height - 68, f"Édité le {timezone.now():%d/%m/%Y à %H:%M}")

    y = height - 130

    def bloc(titre, lots, couleur):
        nonlocal y
        if y < 120:
            p.showPage()
            y = height - 70
        p.setFillColorRGB(*couleur)
        p.setFont("Helvetica-Bold", 11)
        p.drawString(45, y, titre)
        y -= 18
        p.setFillColorRGB(0.94, 0.97, 0.98)
        p.rect(40, y - 5, width - 80, 18, fill=1, stroke=0)
        p.setFillColorRGB(0.2, 0.28, 0.35)
        p.setFont("Helvetica-Bold", 8)
        p.drawString(48, y, "MÉDICAMENT")
        p.drawString(280, y, "LOT")
        p.drawString(400, y, "EXPIRATION")
        p.drawRightString(width - 48, y, "QTÉ")
        y -= 20
        p.setFont("Helvetica", 8)
        for lot in lots:
            if y < 70:
                p.showPage()
                y = height - 70
            p.setFillColorRGB(0.12, 0.16, 0.22)
            p.drawString(48, y, lot.medicament.nom_commercial[:38])
            p.drawString(280, y, lot.numero_lot)
            p.drawString(400, y, lot.date_peremption.strftime('%d/%m/%Y'))
            p.drawRightString(width - 48, y, str(lot.quantite))
            y -= 16
        if not lots:
            p.setFillColorRGB(0.5, 0.55, 0.6)
            p.drawString(48, y, "Aucun lot concerné.")
            y -= 16
        y -= 14

    bloc(f"Lots périmés ({lots_perimes.count()})", lots_perimes, (0.75, 0.07, 0.24))
    bloc(f"Lots expirant sous 30 jours ({lots_proches.count()})", lots_proches, (0.71, 0.33, 0.04))
    p.showPage()
    p.save()
    return response
