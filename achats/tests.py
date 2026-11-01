from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from fournisseurs.models import Fournisseur
from medicaments.models import Categorie, Medicament
from stock.models import LotStock, MouvementStock
from achats.models import CommandeAchat, LigneAchat, ReceptionAchat


class AchatTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='admin', email='admin@test.mg', password='test-pass-123'
        )
        self.client.force_login(self.user)
        self.fournisseur = Fournisseur.objects.create(
            nom_raison_sociale='Grossiste Test', telephone='0200000000'
        )
        self.medicament = Medicament.objects.create(
            nom_commercial='Amoxicilline',
            categorie=Categorie.objects.create(nom='Antibiotiques'),
            forme_pharmaceutique='GELULE',
            dosage='500 mg',
            prix_achat=Decimal('800'),
            prix_vente=Decimal('1500'),
        )
        self.commande = CommandeAchat.objects.create(
            numero_commande='ACH-TEST-001',
            fournisseur=self.fournisseur,
            utilisateur=self.user,
            statut='COMMANDEE',
        )
        self.ligne = LigneAchat.objects.create(
            commande=self.commande,
            medicament=self.medicament,
            quantite=10,
            prix_unitaire=Decimal('800'),
            montant_ligne=Decimal('8000'),
        )

    def test_reception_partielle_puis_totale(self):
        url = reverse('recevoir_commande', args=[self.commande.id])
        horizon = timezone.localdate() + timedelta(days=400)
        self.client.post(url, {
            f'quantite_{self.ligne.id}': 4,
            f'lot_{self.ligne.id}': 'LOT-A',
            f'peremption_{self.ligne.id}': horizon.isoformat(),
        })
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.statut, 'PARTIELLEMENT_RECEPTIONNEE')
        self.assertTrue(LotStock.objects.filter(numero_lot='LOT-A', quantite=4).exists())
        self.assertTrue(MouvementStock.objects.filter(type_mouvement='ENTREE', quantite=4).exists())

        self.client.post(url, {
            f'quantite_{self.ligne.id}': 6,
            f'lot_{self.ligne.id}': 'LOT-B',
            f'peremption_{self.ligne.id}': horizon.isoformat(),
        })
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.statut, 'ENTIEREMENT_RECEPTIONNEE')
        self.assertEqual(ReceptionAchat.objects.count(), 2)
        self.assertEqual(self.ligne.quantite_recue, 10)

    def test_pdf_bon_commande_et_reception(self):
        bon = self.client.get(reverse('bon_commande_pdf', args=[self.commande.id]))
        self.assertEqual(bon.status_code, 200)
        self.assertEqual(bon['Content-Type'], 'application/pdf')
        url = reverse('recevoir_commande', args=[self.commande.id])
        horizon = timezone.localdate() + timedelta(days=400)
        self.client.post(url, {
            f'quantite_{self.ligne.id}': 10,
            f'lot_{self.ligne.id}': 'LOT-C',
            f'peremption_{self.ligne.id}': horizon.isoformat(),
        })
        reception = ReceptionAchat.objects.get()
        pdf = self.client.get(reverse('bon_reception_pdf', args=[reception.id]))
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf['Content-Type'], 'application/pdf')
