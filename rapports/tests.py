from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from achats.models import CommandeAchat
from fournisseurs.models import Fournisseur
from medicaments.models import Categorie, Medicament
from stock.models import LotStock
from ventes.models import LigneVente, Vente


class RapportTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='admin', email='admin@test.mg', password='test-pass-123'
        )
        self.client.force_login(self.user)
        self.medicament = Medicament.objects.create(
            nom_commercial='Vitamine C',
            categorie=Categorie.objects.create(nom='Vitamines'),
            forme_pharmaceutique='COMPRIME',
            dosage='1000 mg',
            prix_achat=Decimal('300'),
            prix_vente=Decimal('700'),
        )
        self.lot = LotStock.objects.create(
            medicament=self.medicament, numero_lot='LOT-RAP',
            date_peremption=timezone.localdate() + timedelta(days=300),
            quantite=8, quantite_initiale=8,
        )
        self.vente = Vente.objects.create(
            numero_vente='VTE-RAP-001', utilisateur=self.user,
            mode_paiement='ESPECES', statut='VALIDEE',
            montant_total=Decimal('1400'), montant_paye=Decimal('2000'),
            montant_rendu=Decimal('600'),
        )
        LigneVente.objects.create(
            vente=self.vente, medicament=self.medicament, lot=self.lot,
            quantite=2, prix_unitaire=Decimal('700'), montant_ligne=Decimal('1400'),
        )
        self.fournisseur = Fournisseur.objects.create(
            nom_raison_sociale='Fournisseur Rapport', telephone='0200000000'
        )
        CommandeAchat.objects.create(
            numero_commande='ACH-RAP-001', fournisseur=self.fournisseur,
            utilisateur=self.user, statut='COMMANDEE', montant_total=Decimal('3000'),
        )

    def test_pages_et_exports_pdf(self):
        for name in ('rapports_accueil', 'rapport_ventes', 'rapport_achats', 'rapport_stock'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        for name in ('rapport_ventes_pdf', 'rapport_achats_pdf', 'rapport_stock_pdf'):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200, name)
            self.assertEqual(response['Content-Type'], 'application/pdf')
