from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from clients.models import Client
from medicaments.models import Categorie, Medicament
from stock.models import LotStock, MouvementStock
from ventes.models import LigneVente, Paiement, RetourVente, Vente


class VenteTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='caissier', password='test-pass-123', role='CAISSIER'
        )
        self.client.force_login(self.user)
        self.categorie = Categorie.objects.create(nom='Antalgiques')
        self.medicament = Medicament.objects.create(
            nom_commercial='Paracétamol',
            categorie=self.categorie,
            forme_pharmaceutique='COMPRIME',
            dosage='500 mg',
            prix_achat=Decimal('500'),
            prix_vente=Decimal('1000'),
            seuil_alerte=5,
        )
        self.lot = LotStock.objects.create(
            medicament=self.medicament,
            numero_lot='LOT-TEST',
            date_peremption=timezone.localdate() + timedelta(days=365),
            quantite=20,
            quantite_initiale=20,
        )
        self.patient = Client.objects.create(nom_complet='Patient Test', telephone='0340000000')

    def _token(self):
        self.client.get(reverse('caisse'))
        return self.client.session['vente_token']

    def _vendre(self, quantite=2):
        self.client.post(reverse('ajouter_au_panier', args=[self.medicament.id]), {'quantite': quantite})
        return self.client.post(reverse('valider_vente'), {
            'client': self.patient.id,
            'mode_paiement': 'ESPECES',
            'montant_paye': '5000',
            'vente_token': self._token(),
        })

    def test_validation_vente_met_a_jour_stock_et_paiement(self):
        response = self._vendre(2)
        self.assertEqual(response.status_code, 302)
        vente = Vente.objects.get()
        self.assertEqual(vente.statut, 'VALIDEE')
        self.assertEqual(vente.montant_total, Decimal('2000'))
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantite, 18)
        self.assertTrue(Paiement.objects.filter(vente=vente, statut='CONFIRME').exists())
        self.assertTrue(MouvementStock.objects.filter(reference=vente.numero_vente, type_mouvement='SORTIE').exists())

    def test_recu_html_et_pdf(self):
        self._vendre(1)
        vente = Vente.objects.get()
        self.assertEqual(self.client.get(reverse('recu_vente', args=[vente.id])).status_code, 200)
        pdf = self.client.get(reverse('recu_vente_pdf', args=[vente.id]))
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf['Content-Type'], 'application/pdf')
        facture = self.client.get(reverse('facture_vente_pdf', args=[vente.id]))
        self.assertEqual(facture.status_code, 200)
        self.assertEqual(facture['Content-Type'], 'application/pdf')

    def test_stock_insuffisant_refuse_la_vente(self):
        self.client.post(reverse('ajouter_au_panier', args=[self.medicament.id]), {'quantite': 2})
        token = self._token()
        self.lot.quantite = 1
        self.lot.save(update_fields=['quantite'])
        response = self.client.post(reverse('valider_vente'), {
            'mode_paiement': 'ESPECES', 'montant_paye': '5000', 'vente_token': token,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Vente.objects.count(), 0)
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantite, 1)

    def test_retour_reintegre_le_stock(self):
        self._vendre(3)
        vente = Vente.objects.get()
        ligne = vente.lignes.first()
        response = self.client.post(reverse('creer_retour', args=[vente.id]), {
            'motif': 'Produit défectueux',
            'remettre_en_stock': 'on',
            f'quantite_{ligne.id}': 2,
        })
        self.assertEqual(response.status_code, 302)
        retour = RetourVente.objects.get()
        self.assertEqual(retour.montant_rembourse, Decimal('2000'))
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantite, 19)

    def test_annulation_vente_reintegre_tout(self):
        self._vendre(4)
        vente = Vente.objects.get()
        response = self.client.post(reverse('annuler_vente', args=[vente.id]))
        self.assertEqual(response.status_code, 302)
        vente.refresh_from_db()
        self.assertEqual(vente.statut, 'ANNULEE')
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantite, 20)
