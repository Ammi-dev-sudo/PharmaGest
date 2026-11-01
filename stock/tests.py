from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from medicaments.models import Categorie, Medicament
from stock.models import LotStock


class StockTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='admin', email='admin@test.mg', password='test-pass-123'
        )
        self.client.force_login(self.user)
        self.medicament = Medicament.objects.create(
            nom_commercial='Ibuprofène',
            categorie=Categorie.objects.create(nom='Anti-inflammatoires'),
            forme_pharmaceutique='COMPRIME',
            dosage='400 mg',
            prix_achat=Decimal('600'),
            prix_vente=Decimal('1200'),
            seuil_alerte=10,
        )

    def test_alertes_et_peremptions(self):
        LotStock.objects.create(
            medicament=self.medicament, numero_lot='LOT-FAIBLE',
            date_peremption=timezone.localdate() + timedelta(days=200),
            quantite=3, quantite_initiale=3,
        )
        expire = LotStock.objects.create(
            medicament=self.medicament, numero_lot='LOT-EXPIRE',
            date_peremption=timezone.localdate() - timedelta(days=2),
            quantite=5, quantite_initiale=5,
        )
        self.assertTrue(self.medicament.est_en_alerte)
        self.assertEqual(self.client.get(reverse('alertes_stock')).status_code, 200)
        self.assertEqual(self.client.get(reverse('produits_perimes')).status_code, 200)
        self.assertTrue(expire.est_perime())
        self.assertEqual(self.client.get(reverse('inventaire')).status_code, 200)
        pdf = self.client.get(reverse('peremptions_pdf'))
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf['Content-Type'], 'application/pdf')

    def test_correction_inventaire(self):
        lot = LotStock.objects.create(
            medicament=self.medicament, numero_lot='LOT-INV',
            date_peremption=timezone.localdate() + timedelta(days=200),
            quantite=10, quantite_initiale=10,
        )
        response = self.client.post(reverse('inventaire'), {
            f'qte_{lot.id}': 7,
            'motif': 'Écart de comptage',
        })
        self.assertEqual(response.status_code, 302)
        lot.refresh_from_db()
        self.assertEqual(lot.quantite, 7)
