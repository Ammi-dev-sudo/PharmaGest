from datetime import datetime, timedelta
from decimal import Decimal

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from django.http import HttpResponse

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from ventes.models import Vente, LigneVente
from achats.models import CommandeAchat
from medicaments.models import Medicament
from stock.models import LotStock

PHARMACIE = {
    'nom': 'PharmaGest',
    'adresse': 'Lot 12, Analakely — Antananarivo, Madagascar',
    'telephone': '+261 34 00 000 00',
    'email': 'contact@pharmagest.mg',
}


def _parse_date(value, default):
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (TypeError, ValueError):
        return default


def _periode(request, days=30):
    today = timezone.now().date()
    debut = _parse_date(request.GET.get('debut'), today - timedelta(days=days))
    fin = _parse_date(request.GET.get('fin'), today)
    return debut, fin


def _base_pdf(titre, sous_titre):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{titre.lower().replace(" ", "_")}.pdf"'
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    p.setFillColorRGB(0.05, 0.58, 0.56)
    p.rect(0, height - 100, width, 100, fill=1, stroke=0)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 18)
    p.drawString(45, height - 50, f"PHARMAGEST — {titre.upper()}")
    p.setFont("Helvetica", 9)
    p.drawString(45, height - 68, PHARMACIE['adresse'])
    p.drawString(45, height - 82, f"{PHARMACIE['telephone']} — {PHARMACIE['email']}")
    p.setFillColorRGB(0.1, 0.1, 0.15)
    p.setFont("Helvetica-Oblique", 9)
    p.drawString(45, height - 120, sous_titre)
    return response, p, width, height


def _tableau(p, width, height, colonnes, lignes, y=None):
    if y is None:
        y = height - 150
    p.setFillColorRGB(0.94, 0.97, 0.98)
    p.rect(40, y - 6, width - 80, 20, fill=1, stroke=0)
    p.setFillColorRGB(0.2, 0.28, 0.35)
    p.setFont("Helvetica-Bold", 8)
    for label, x, align in colonnes:
        if align == 'right':
            p.drawRightString(x, y, label)
        elif align == 'center':
            p.drawCentredString(x, y, label)
        else:
            p.drawString(x, y, label)
    y -= 22
    p.setFont("Helvetica", 8)
    for ligne in lignes:
        if y < 70:
            p.showPage()
            y = height - 70
        p.setFillColorRGB(0.12, 0.16, 0.22)
        for valeur, x, align in ligne:
            if align == 'right':
                p.drawRightString(x, y, str(valeur))
            elif align == 'center':
                p.drawCentredString(x, y, str(valeur))
            else:
                p.drawString(x, y, str(valeur))
        y -= 16
    return y


@login_required
def rapports_accueil(request):
    today = timezone.now().date()
    debut_mois = today.replace(day=1)
    ventes_mois = Vente.objects.filter(statut='VALIDEE', date_vente__date__gte=debut_mois)
    ca = ventes_mois.aggregate(t=Sum('montant_total'))['t'] or 0
    nb_ventes = ventes_mois.count()
    achats_mois = CommandeAchat.objects.filter(date_commande__date__gte=debut_mois)
    stock_value = sum((m.prix_achat * m.stock_total() for m in Medicament.objects.filter(statut='ACTIF')), Decimal('0'))
    contexte = {
        'ca_mois': ca,
        'nb_ventes': nb_ventes,
        'panier_moyen': (ca / nb_ventes) if nb_ventes else 0,
        'achats_mois': achats_mois.aggregate(t=Sum('montant_total'))['t'] or 0,
        'stock_value': stock_value,
        'nb_medicaments': Medicament.objects.filter(statut='ACTIF').count(),
        'alertes': sum(1 for m in Medicament.objects.filter(statut='ACTIF') if m.est_en_alerte or m.est_epuise),
        'perimes': LotStock.objects.filter(quantite__gt=0, date_peremption__lt=today).count(),
    }
    return render(request, 'rapports/accueil.html', contexte)


def _donnees_ventes(request):
    debut, fin = _periode(request)
    ventes = Vente.objects.filter(statut='VALIDEE', date_vente__date__range=(debut, fin)).select_related('client', 'utilisateur')
    total = ventes.aggregate(t=Sum('montant_total'))['t'] or 0
    nb = ventes.count()
    par_mode = ventes.values('mode_paiement').annotate(total=Sum('montant_total'), nombre=Count('id')).order_by('-total')
    top = (LigneVente.objects.filter(vente__in=ventes)
           .values('medicament__nom_commercial')
           .annotate(quantite=Sum('quantite'), total=Sum('montant_ligne'))
           .order_by('-quantite')[:10])
    return {
        'ventes': ventes,
        'debut': debut,
        'fin': fin,
        'total': total,
        'nb': nb,
        'panier_moyen': (total / nb) if nb else 0,
        'par_mode': par_mode,
        'top': top,
    }


@login_required
def rapport_ventes(request):
    return render(request, 'rapports/ventes.html', _donnees_ventes(request))


@login_required
def rapport_ventes_pdf(request):
    data = _donnees_ventes(request)
    response, p, width, height = _base_pdf(
        "Rapport des ventes", f"Période : {data['debut']:%d/%m/%Y} au {data['fin']:%d/%m/%Y}"
    )
    p.setFont("Helvetica-Bold", 10)
    p.drawString(45, height - 145, f"Chiffre d'affaires : {data['total']:.0f} Ar    |    Ventes : {data['nb']}    |    Panier moyen : {data['panier_moyen']:.0f} Ar")
    lignes = [
        ((v.date_vente.strftime('%d/%m/%Y %H:%M'), 48, 'left'),
         (v.numero_vente, 170, 'left'),
         ((v.client.nom_complet if v.client else 'Client de passage')[:24], 280, 'left'),
         (v.get_mode_paiement_display(), 420, 'left'),
         (f"{v.montant_total:.0f} Ar", width - 48, 'right'))
        for v in data['ventes']
    ]
    _tableau(p, width, height, [
        ('Date', 48, 'left'), ('N° vente', 170, 'left'), ('Client', 280, 'left'),
        ('Paiement', 420, 'left'), ('Montant', width - 48, 'right'),
    ], lignes, y=height - 175)
    p.showPage()
    p.save()
    return response


def _donnees_achats(request):
    debut, fin = _periode(request, days=90)
    achats = CommandeAchat.objects.filter(date_commande__date__range=(debut, fin)).select_related('fournisseur')
    total = achats.aggregate(t=Sum('montant_total'))['t'] or 0
    par_statut = achats.values('statut').annotate(total=Sum('montant_total'), nombre=Count('id'))
    par_fournisseur = achats.values('fournisseur__nom_raison_sociale').annotate(total=Sum('montant_total')).order_by('-total')
    return {
        'achats': achats,
        'debut': debut,
        'fin': fin,
        'total': total,
        'nb': achats.count(),
        'par_statut': par_statut,
        'par_fournisseur': par_fournisseur,
    }


@login_required
def rapport_achats(request):
    return render(request, 'rapports/achats.html', _donnees_achats(request))


@login_required
def rapport_achats_pdf(request):
    data = _donnees_achats(request)
    response, p, width, height = _base_pdf(
        "Rapport des achats", f"Période : {data['debut']:%d/%m/%Y} au {data['fin']:%d/%m/%Y}"
    )
    p.setFont("Helvetica-Bold", 10)
    p.drawString(45, height - 145, f"Total achats : {data['total']:.0f} Ar    |    Commandes : {data['nb']}")
    lignes = [
        ((a.date_commande.strftime('%d/%m/%Y'), 48, 'left'),
         (a.numero_commande, 150, 'left'),
         (a.fournisseur.nom_raison_sociale[:30], 280, 'left'),
         (a.get_statut_display(), 430, 'left'),
         (f"{a.montant_total:.0f} Ar", width - 48, 'right'))
        for a in data['achats']
    ]
    _tableau(p, width, height, [
        ('Date', 48, 'left'), ('N° commande', 150, 'left'), ('Fournisseur', 280, 'left'),
        ('Statut', 430, 'left'), ('Montant', width - 48, 'right'),
    ], lignes, y=height - 175)
    p.showPage()
    p.save()
    return response


def _donnees_stock():
    medicaments = Medicament.objects.filter(statut='ACTIF').select_related('categorie')
    lignes = []
    valeur_totale = Decimal('0')
    for m in medicaments:
        stock = m.stock_total()
        valeur = m.prix_achat * stock
        valeur_totale += valeur
        lignes.append({'medicament': m, 'stock': stock, 'valeur': valeur})
    alertes = [l for l in lignes if l['medicament'].est_en_alerte or l['medicament'].est_epuise]
    return {
        'lignes': lignes,
        'valeur_totale': valeur_totale,
        'alertes': alertes,
        'nb': len(lignes),
    }


@login_required
def rapport_stock(request):
    return render(request, 'rapports/stock.html', _donnees_stock())


@login_required
def rapport_stock_pdf(request):
    data = _donnees_stock()
    response, p, width, height = _base_pdf(
        "Rapport de stock", f"Édité le {timezone.now():%d/%m/%Y à %H:%M}"
    )
    p.setFont("Helvetica-Bold", 10)
    p.drawString(45, height - 145, f"Valeur du stock : {data['valeur_totale']:.0f} Ar    |    Références : {data['nb']}    |    En alerte : {len(data['alertes'])}")
    lignes = [
        ((l['medicament'].nom_commercial[:34], 48, 'left'),
         (l['medicament'].dosage, 270, 'left'),
         (str(l['stock']), 400, 'center'),
         (f"{l['medicament'].prix_achat:.0f} Ar", 480, 'right'),
         (f"{l['valeur']:.0f} Ar", width - 48, 'right'))
        for l in data['lignes']
    ]
    _tableau(p, width, height, [
        ('Médicament', 48, 'left'), ('Dosage', 270, 'left'), ('Stock', 400, 'center'),
        ('Prix achat', 480, 'right'), ('Valeur', width - 48, 'right'),
    ], lignes, y=height - 175)
    p.showPage()
    p.save()
    return response
