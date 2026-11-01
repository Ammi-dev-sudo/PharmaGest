import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from achats.models import CommandeAchat, LigneAchat, LigneReception, ReceptionAchat
from clients.models import Client
from fournisseurs.models import Fournisseur
from medicaments.models import Categorie, Medicament
from stock.models import LotStock, MouvementStock
from ventes.models import LigneRetourVente, LigneVente, Paiement, RetourVente, Vente
from utilisateurs.models import JournalAudit

User = get_user_model()

CATEGORIES = [
    ('Antalgiques', 'Traitement de la douleur légère à modérée.'),
    ('Antibiotiques', 'Traitement des infections bactériennes.'),
    ('Anti-inflammatoires', 'Réduction des inflammations et douleurs.'),
    ('Vitamines & Compléments', 'Compléments alimentaires et vitamines.'),
    ('Cardiologie', 'Médicaments cardiovasculaires.'),
    ('Dermatologie', 'Soins et traitements de la peau.'),
    ('Gastro-entérologie', 'Traitement digestif et gastrique.'),
    ('Ophtalmologie', 'Soins et traitements oculaires.'),
    ('Pédiatrie', 'Formes adaptées aux enfants.'),
    ('Diabétologie', 'Suivi et traitement du diabète.'),
]

# (nom, générique, catégorie, forme, dosage, laboratoire, prix achat, prix vente, seuil)
MEDICAMENTS = [
    ('Paracétamol', 'PARACETAMOL', 'Antalgiques', 'COMPRIME', '500 mg', 'PharmaPlus', 150, 350, 40),
    ('Doliprane', 'PARACETAMOL', 'Antalgiques', 'COMPRIME', '1000 mg', 'Sanofi', 220, 480, 40),
    ('Efferalgan', 'PARACETAMOL', 'Antalgiques', 'COMPRIME', '500 mg', 'UPSA', 180, 400, 30),
    ('Ibuprofène', 'IBUPROFENE', 'Anti-inflammatoires', 'COMPRIME', '400 mg', 'Medipha', 200, 450, 35),
    ('Diclofénac', 'DICLOFENAC', 'Anti-inflammatoires', 'COMPRIME', '50 mg', 'Novartis', 260, 550, 25),
    ('Diclofénac gel', 'DICLOFENAC', 'Anti-inflammatoires', 'CREME', '1 %', 'Dermaphar', 650, 1200, 15),
    ('Amoxicilline', 'AMOXICILLINE', 'Antibiotiques', 'GELULE', '500 mg', 'Biofarma', 450, 850, 30),
    ('Amoxicilline acide', 'AMOXICILLINE', 'Antibiotiques', 'COMPRIME', '1 g', 'Biofarma', 700, 1300, 20),
    ('Azithromycine', 'AZITHROMYCINE', 'Antibiotiques', 'COMPRIME', '250 mg', 'Pfizer', 1200, 2100, 15),
    ('Ciprofloxacine', 'CIPROFLOXACINE', 'Antibiotiques', 'COMPRIME', '500 mg', 'Bayer', 900, 1650, 20),
    ('Ceftriaxone', 'CEFTRIAXONE', 'Antibiotiques', 'INJECTION', '1 g', 'Roche', 1800, 3200, 12),
    ('Vitamine C', 'ACIDE ASCORBIQUE', 'Vitamines & Compléments', 'COMPRIME', '1000 mg', 'Vitaphar', 300, 650, 50),
    ('Vitamine D3', 'COLECALCIFEROL', 'Vitamines & Compléments', 'SOLUTION', '10000 UI', 'Vitaphar', 420, 800, 30),
    ('Bêta-carotène', 'BETA-CAROTENE', 'Vitamines & Compléments', 'GELULE', '15 mg', 'Vitaphar', 400, 750, 25),
    ('Magnésium', 'MAGNESIUM', 'Vitamines & Compléments', 'COMPRIME', '300 mg', 'Nutriphar', 350, 700, 30),
    ('Fer + Acide folique', 'FER', 'Vitamines & Compléments', 'COMPRIME', '100 mg', 'Nutriphar', 280, 600, 25),
    ('Amlodipine', 'AMLODIPINE', 'Cardiologie', 'COMPRIME', '5 mg', 'Cardiophar', 800, 1450, 20),
    ('Enalapril', 'ENALAPRIL', 'Cardiologie', 'COMPRIME', '10 mg', 'Cardiophar', 600, 1100, 20),
    ('Valsartan', 'VALSARTAN', 'Cardiologie', 'COMPRIME', '80 mg', 'Novartis', 950, 1750, 15),
    ('Aténolol', 'ATENOLOL', 'Cardiologie', 'COMPRIME', '50 mg', 'Medipha', 520, 980, 18),
    ('Furosémide', 'FUROSEMIDE', 'Cardiologie', 'COMPRIME', '40 mg', 'Sanofi', 380, 720, 20),
    ('Hydrocortisone crème', 'HYDROCORTISONE', 'Dermatologie', 'CREME', '1 %', 'Dermaphar', 550, 950, 18),
    ('Bétaméthasone', 'BETAMETHASONE', 'Dermatologie', 'CREME', '0,05 %', 'Dermaphar', 620, 1100, 15),
    ('Pommade cicatrisante', 'OXYDE DE ZINC', 'Dermatologie', 'POMMADE', '10 %', 'Dermaphar', 450, 850, 20),
    ('Fluconazole', 'FLUCONAZOLE', 'Dermatologie', 'GELULE', '150 mg', 'Pfizer', 780, 1400, 12),
    ('Oméprazole', 'OMEPRAZOLE', 'Gastro-entérologie', 'GELULE', '20 mg', 'AstraZeneca', 600, 1150, 25),
    ('Oméprazole 40', 'OMEPRAZOLE', 'Gastro-entérologie', 'COMPRIME', '40 mg', 'AstraZeneca', 900, 1650, 15),
    ('Métoclopramide', 'METOCLOPRAMIDE', 'Gastro-entérologie', 'COMPRIME', '10 mg', 'Sanofi', 320, 650, 20),
    ('Smecta', 'DIOSMECTITE', 'Gastro-entérologie', 'SOLUTION', '3 g', 'Ipsen', 500, 950, 20),
    ('Collyre antiseptique', 'POVIDONE IODEE', 'Ophtalmologie', 'SOLUTION', '5 %', 'VisioPharm', 700, 1300, 12),
    ('Collyre lubrifiant', 'HYALURONATE', 'Ophtalmologie', 'SOLUTION', '0,2 %', 'VisioPharm', 850, 1500, 10),
    ('Paracétamol pédiatrique', 'PARACETAMOL', 'Pédiatrie', 'SIROP', '120 mg/5 ml', 'UPSA', 380, 750, 25),
    ('Ibuprofène pédiatrique', 'IBUPROFENE', 'Pédiatrie', 'SIROP', '100 mg/5 ml', 'Medipha', 420, 820, 25),
    ('Amoxicilline pédiatrique', 'AMOXICILLINE', 'Pédiatrie', 'SIROP', '250 mg/5 ml', 'Biofarma', 650, 1200, 18),
    ('Sérum physiologique', 'CHLORURE DE SODIUM', 'Pédiatrie', 'SOLUTION', '0,9 %', 'Nutriphar', 180, 400, 40),
    ('Metformine', 'METFORMINE', 'Diabétologie', 'COMPRIME', '500 mg', 'Merck', 450, 850, 25),
    ('Metformine 1000', 'METFORMINE', 'Diabétologie', 'COMPRIME', '1000 mg', 'Merck', 620, 1150, 20),
    ('Gliclazide', 'GLICLAZIDE', 'Diabétologie', 'COMPRIME', '30 mg', 'Servier', 780, 1450, 15),
    ('Insuline rapide', 'INSULINE', 'Diabétologie', 'INJECTION', '100 UI/ml', 'Novo', 6500, 9800, 8),
    ('Bandelettes glycémie', 'BANDELETTES', 'Diabétologie', 'AUTRE', '50 unités', 'Roche', 2200, 3600, 10),
    ('Seringue 5 ml', 'SERINGUE', 'Pédiatrie', 'AUTRE', '5 ml', 'Medisupply', 120, 300, 50),
    ('Compresses stériles', 'COMPRESSE', 'Dermatologie', 'AUTRE', '10 x 10', 'Medisupply', 200, 450, 40),
    ('Sparadrap', 'BANDE ADHESIVE', 'Dermatologie', 'AUTRE', '2,5 cm', 'Medisupply', 300, 600, 25),
    ('Gants latex', 'GANTS', 'Dermatologie', 'AUTRE', 'M', 'Medisupply', 350, 700, 30),
    ('Masques chirurgicaux', 'MASQUE', 'Dermatologie', 'AUTRE', '50 unités', 'Medisupply', 500, 950, 20),
    ('Gel hydroalcoolique', 'ALCOOL', 'Dermatologie', 'SOLUTION', '500 ml', 'Dermaphar', 650, 1200, 20),
    ('Cotrimoxazole', 'COTRIMOXAZOLE', 'Antibiotiques', 'COMPRIME', '480 mg', 'Biofarma', 380, 750, 20),
    ('Doxycycline', 'DOXYCYCLINE', 'Antibiotiques', 'GELULE', '100 mg', 'Medipha', 500, 950, 18),
    ('Métronidazole', 'METRONIDAZOLE', 'Antibiotiques', 'COMPRIME', '500 mg', 'Sanofi', 420, 800, 20),
    ('Artéméther-Luméfantrine', 'ARTEMETHER', 'Antalgiques', 'COMPRIME', '20/120 mg', 'Novartis', 850, 1500, 18),
    ('Quinine', 'QUININE', 'Antalgiques', 'COMPRIME', '300 mg', 'Sanofi', 600, 1100, 15),
    ('Salbutamol', 'SALBUTAMOL', 'Cardiologie', 'SOLUTION', '100 µg', 'GSK', 1200, 2100, 12),
    ('Prednisolone', 'PREDNISOLONE', 'Anti-inflammatoires', 'COMPRIME', '20 mg', 'Medipha', 380, 750, 20),
    ('Dexaméthasone', 'DEXAMETHASONE', 'Anti-inflammatoires', 'INJECTION', '4 mg', 'Roche', 700, 1300, 12),
    ('Loratadine', 'LORATADINE', 'Anti-inflammatoires', 'COMPRIME', '10 mg', 'Bayer', 300, 600, 25),
    ('Cétirizine', 'CETIRIZINE', 'Anti-inflammatoires', 'COMPRIME', '10 mg', 'Medipha', 320, 650, 25),
    ('Ondansétron', 'ONDANSETRON', 'Gastro-entérologie', 'INJECTION', '4 mg', 'GSK', 900, 1650, 10),
    ('Lopéramide', 'LOPERAMIDE', 'Gastro-entérologie', 'GELULE', '2 mg', 'Janssen', 350, 700, 20),
    ('Lactulose', 'LACTULOSE', 'Gastro-entérologie', 'SIROP', '66 %', 'Medipha', 650, 1200, 15),
    ('Héparine', 'HEPARINE', 'Cardiologie', 'INJECTION', '5000 UI', 'Sanofi', 1500, 2700, 10),
    ('Amlodipine 10', 'AMLODIPINE', 'Cardiologie', 'COMPRIME', '10 mg', 'Cardiophar', 950, 1700, 15),
    ('Latanoprost', 'LATANOPROST', 'Ophtalmologie', 'SOLUTION', '0,005 %', 'VisioPharm', 1800, 3200, 8),
    ('Dexaméthasone collyre', 'DEXAMETHASONE', 'Ophtalmologie', 'SOLUTION', '0,1 %', 'VisioPharm', 900, 1650, 10),
    ('Sérum glucose', 'GLUCOSE', 'Diabétologie', 'SOLUTION', '5 %', 'Medisupply', 350, 700, 20),
    ('Bétadine', 'POVIDONE IODEE', 'Dermatologie', 'SOLUTION', '10 %', 'Meda', 550, 1050, 20),
]

FOURNISSEURS = [
    ('PharmImport Madagascar', 'contact@pharmimport.mg', '+261 34 00 000 01', 'Antananarivo, Analakely', 'M. Rakoto'),
    ('MediSupply SA', 'ventes@medisupply.mg', '+261 34 00 000 02', 'Antsirabe', 'Mme Rasoa'),
    ('BioPharma Distribution', 'info@biopharma.mg', '+261 34 00 000 03', 'Toamasina', 'M. Andry'),
    ('Labomedica', 'commande@labomedica.mg', '+261 34 00 000 04', 'Fianarantsoa', 'Mme Hanta'),
    ('Océan Médical', 'contact@oceanmedical.mg', '+261 34 00 000 05', 'Mahajanga', 'M. Tiana'),
    ('Central Pharma', 'achats@centralpharma.mg', '+261 34 00 000 06', 'Antananarivo, Isoraka', 'M. Fanja'),
    ('Santal Distribution', 'info@santal.mg', '+261 34 00 000 07', 'Antsiranana', 'Mme Voahangy'),
    ('VitaHealth Import', 'ventes@vitahealth.mg', '+261 34 00 000 08', 'Toliara', 'M. Rivo'),
]

CLIENTS = [
    ('Rakoto Jean', '+261 32 11 222 33', 'jean.rakoto@mail.mg', 'Analakely, Antananarivo'),
    ('Rasoamanana Marie', '+261 32 11 222 44', 'marie.rasoa@mail.mg', 'Ambohipo, Antananarivo'),
    ('Andriamanana Paul', '+261 32 11 222 55', 'paul.andria@mail.mg', 'Isoraka, Antananarivo'),
    ('Razafy Hery', '+261 32 11 222 66', 'hery.razafy@mail.mg', 'Itaosy, Antananarivo'),
    ('Randrianarisoa Lala', '+261 32 11 222 77', 'lala.randria@mail.mg', 'Ivato, Antananarivo'),
    ('Ramanantsoa Soa', '+261 33 22 333 11', 'soa.rama@mail.mg', 'Antsirabe'),
    ('Rakotondrabe Mamy', '+261 33 22 333 22', 'mamy.rakoto@mail.mg', 'Ambohidratrimo'),
    ('Raveloarison Nirina', '+261 33 22 333 33', 'nirina.ravelo@mail.mg', 'Toamasina'),
    ('Rajaonarivelo Fara', '+261 33 22 333 44', 'fara.rajao@mail.mg', 'Fianarantsoa'),
    ('Andrianjaka Lova', '+261 34 44 555 11', 'lova.andria@mail.mg', 'Mahajanga'),
    ('Rasendrasoa Miora', '+261 34 44 555 22', 'miora.rasen@mail.mg', 'Antananarivo, Ankadifotsy'),
    ('Rakotomalala Tojo', '+261 34 44 555 33', 'tojo.rakoto@mail.mg', 'Antananarivo, Ambatoroka'),
    ('Rafanomezantsoa Aina', '+261 34 44 555 44', 'aina.rafano@mail.mg', 'Antsirabe'),
    ('Randriamahazo Zo', '+261 32 55 666 11', 'zo.randria@mail.mg', 'Toliara'),
    ('Rakotoarisoa Faly', '+261 32 55 666 22', 'faly.rakoto@mail.mg', 'Antananarivo, 67 Ha'),
    ('Rasoarimalala Tiana', '+261 32 55 666 33', 'tiana.rasoa@mail.mg', 'Antsiranana'),
    ('Andriamihaja Rado', '+261 33 66 777 11', 'rado.andria@mail.mg', 'Antananarivo, Andravoahangy'),
    ('Razanamalala Hoby', '+261 33 66 777 22', 'hoby.raza@mail.mg', 'Moramanga'),
    ('Rakotonirina Voary', '+261 34 77 888 11', 'voary.rakoto@mail.mg', 'Antananarivo, Ampasampito'),
    ('Rasolofonirina Nat', '+261 34 77 888 22', 'nat.rasolo@mail.mg', 'Antsirabe'),
    ('Ramanandraibe Feno', '+261 32 88 999 11', 'feno.rama@mail.mg', 'Antananarivo, Analamahitsy'),
    ('Rakotobe Sitraka', '+261 32 88 999 22', 'sitraka.rakoto@mail.mg', 'Ambohimanga'),
    ('Razafindrakoto Manda', '+261 33 99 000 11', 'manda.raza@mail.mg', 'Toamasina'),
    ('Rasarimanana Elia', '+261 33 99 000 22', 'elia.rasa@mail.mg', 'Fianarantsoa'),
    ('Rakotoarivony Tovo', '+261 34 00 111 22', 'tovo.rakoto@mail.mg', 'Antananarivo, Mahamasina'),
    ('Randrianasolo Voahirana', '+261 34 00 111 33', 'voah.ran@mail.mg', 'Antananarivo, Anosy'),
    ('Rakotonandrasana Haja', '+261 32 12 345 67', 'haja.rakoto@mail.mg', 'Antananarivo, Analakely'),
    ('Razanadrakoto Lova', '+261 32 23 456 78', 'lova.raza@mail.mg', 'Antsirabe'),
    ('Rafidison Miora', '+261 33 34 567 89', 'miora.rafi@mail.mg', 'Mahajanga'),
    ('Rakotonjanahary Rado', '+261 34 45 678 90', 'rado.rakoto@mail.mg', 'Antananarivo, Ivandry'),
]


class Command(BaseCommand):
    help = "Génère un jeu de données de démonstration riche pour tester PharmaGest."

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help="Supprime les données métier existantes avant de générer (les comptes utilisateurs sont conservés).",
        )
        parser.add_argument('--ventes', type=int, default=220, help="Nombre de ventes à générer (défaut : 220).")
        parser.add_argument('--commandes', type=int, default=45, help="Nombre de commandes d'achat (défaut : 45).")

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(2026)
        if options['reset']:
            self._reset()

        self.stdout.write("Création des utilisateurs…")
        users = self._utilisateurs()

        self.stdout.write("Création des catégories, médicaments, fournisseurs et clients…")
        categories = {}
        for nom, description in CATEGORIES:
            categories[nom], _ = Categorie.objects.get_or_create(nom=nom, defaults={'description': description})

        medicaments = self._medicaments(categories)
        fournisseurs = self._fournisseurs()
        clients = self._clients()

        self.stdout.write("Création des lots et du stock initial…")
        lots_par_medicament = self._lots(medicaments)

        self.stdout.write("Création des commandes d'achat et réceptions…")
        self._achats(fournisseurs, medicaments, options['commandes'], users)

        self.stdout.write(f"Création de {options['ventes']} ventes, paiements et retours…")
        self._ventes(clients, medicaments, lots_par_medicament, options['ventes'], users)

        self.stdout.write("Création du journal d'audit…")
        self._audit(users)

        self._resume()

    def _reset(self):
        self.stdout.write(self.style.WARNING("Suppression des données métier existantes…"))
        JournalAudit.objects.all().delete()
        Paiement.objects.all().delete()
        LigneRetourVente.objects.all().delete()
        RetourVente.objects.all().delete()
        LigneVente.objects.all().delete()
        Vente.objects.all().delete()
        LigneReception.objects.all().delete()
        ReceptionAchat.objects.all().delete()
        LigneAchat.objects.all().delete()
        CommandeAchat.objects.all().delete()
        MouvementStock.objects.all().delete()
        LotStock.objects.all().delete()
        Medicament.objects.all().delete()
        Categorie.objects.all().delete()
        Client.objects.all().delete()
        Fournisseur.objects.all().delete()

    def _utilisateurs(self):
        comptes = [
            ('admin', 'admin123', 'ADMIN', 'Administrateur', 'PharmaGest', True),
            ('pharmacien', 'demo12345', 'PHARMACIEN', 'Responsable', 'Pharmacie', False),
            ('gestionnaire', 'demo12345', 'GESTIONNAIRE', 'Gestion', 'Stock', False),
            ('caissier', 'demo12345', 'CAISSIER', 'Caisse', 'Comptoir', False),
            ('caissier2', 'demo12345', 'CAISSIER', 'Caisse', 'Deux', False),
        ]
        users = {}
        for username, password, role, first, last, is_super in comptes:
            user, created = User.objects.get_or_create(username=username, defaults={
                'email': f'{username}@pharmagest.mg',
                'first_name': first,
                'last_name': last,
                'role': role,
                'telephone': f'+261 34 00 000 {random.randint(10, 99)}',
                'actif': True,
                'is_staff': is_super,
                'is_superuser': is_super,
            })
            user.role = role
            user.actif = True
            user.is_active = True
            user.set_password(password)
            user.save()
            users[username] = user
        return users

    def _medicaments(self, categories):
        medicaments = []
        for index, (nom, generique, cat, forme, dosage, labo, prix_achat, prix_vente, seuil) in enumerate(MEDICAMENTS, start=1):
            med, _ = Medicament.objects.get_or_create(
                nom_commercial=nom,
                dosage=dosage,
                defaults={
                    'denomination_generique': generique,
                    'categorie': categories[cat],
                    'forme_pharmaceutique': forme,
                    'laboratoire': labo,
                    'code_barres': f'340093{index:07d}',
                    'prix_achat': prix_achat,
                    'prix_vente': prix_vente,
                    'seuil_alerte': seuil,
                    'statut': 'ACTIF',
                },
            )
            medicaments.append(med)
        return medicaments

    def _fournisseurs(self):
        resultat = []
        for nom, email, tel, adresse, contact in FOURNISSEURS:
            fournisseur, _ = Fournisseur.objects.get_or_create(
                nom_raison_sociale=nom,
                defaults={
                    'email': email,
                    'telephone': tel,
                    'adresse': adresse,
                    'contact_principal': contact,
                    'numero_fiscal': f'NIF-{random.randint(100000, 999999)}',
                    'actif': True,
                },
            )
            resultat.append(fournisseur)
        return resultat

    def _clients(self):
        resultat = []
        for nom, tel, email, adresse in CLIENTS:
            client, _ = Client.objects.get_or_create(
                nom_complet=nom,
                defaults={'telephone': tel, 'email': email, 'adresse': adresse, 'actif': True},
            )
            resultat.append(client)
        return resultat

    def _lots(self, medicaments):
        today = timezone.localdate()
        lots_par_medicament = {}
        for index, med in enumerate(medicaments):
            existing = list(med.lots.filter(quantite__gt=0))
            if existing:
                lots_par_medicament[med.id] = existing
                continue
            lots = []
            nombre_lots = random.choice([2, 2, 3])
            for position in range(nombre_lots):
                # Mélange de lots valides, proches de la péremption, périmés et en rupture.
                tirage = random.random()
                if tirage < 0.07:
                    peremption = today - timedelta(days=random.randint(1, 45))
                    quantite = random.randint(5, 25)
                elif tirage < 0.22:
                    peremption = today + timedelta(days=random.randint(1, 30))
                    quantite = random.randint(10, 45)
                elif tirage < 0.30:
                    peremption = today + timedelta(days=random.randint(60, 400))
                    quantite = 0
                else:
                    peremption = today + timedelta(days=random.randint(120, 900))
                    quantite = random.randint(30, 180)
                lot = LotStock.objects.create(
                    medicament=med,
                    numero_lot=f'LOT-{today.year}-{index + 1:03d}-{position + 1}',
                    date_peremption=peremption,
                    quantite=quantite,
                    quantite_initiale=max(quantite, random.randint(quantite, quantite + 60)),
                    bloque=random.random() < 0.02,
                )
                if quantite > 0:
                    lots.append(lot)
            lots_par_medicament[med.id] = lots
        return lots_par_medicament

    def _achats(self, fournisseurs, medicaments, nombre, users):
        utilisateurs = [users['gestionnaire'], users['pharmacien'], users['admin']]
        today = timezone.now()
        statuts = ['BROUILLON', 'COMMANDEE', 'COMMANDEE', 'PARTIELLEMENT_RECEPTIONNEE',
                   'ENTIEREMENT_RECEPTIONNEE', 'ENTIEREMENT_RECEPTIONNEE', 'ANNULEE']
        for index in range(nombre):
            date_commande = today - timedelta(days=random.randint(0, 120), hours=random.randint(0, 8))
            fournisseur = random.choice(fournisseurs)
            commande = CommandeAchat.objects.create(
                numero_commande=f'ACH-{date_commande.strftime("%Y%m%d")}-{index + 1:04d}',
                fournisseur=fournisseur,
                utilisateur=random.choice(utilisateurs),
                statut=random.choice(statuts),
                notes=random.choice(['', '', 'Commande urgente', 'Réapprovisionnement mensuel', 'Promotion fournisseur']),
            )
            CommandeAchat.objects.filter(pk=commande.pk).update(date_commande=date_commande)
            lignes = []
            for med in random.sample(medicaments, random.randint(1, 6)):
                quantite = random.randint(5, 60)
                prix = med.prix_achat
                lignes.append(LigneAchat.objects.create(
                    commande=commande,
                    medicament=med,
                    quantite=quantite,
                    prix_unitaire=prix,
                    montant_ligne=prix * quantite,
                ))
            total = sum(ligne.montant_ligne for ligne in lignes)
            CommandeAchat.objects.filter(pk=commande.pk).update(montant_total=total)

            if commande.statut in ('ENTIEREMENT_RECEPTIONNEE', 'PARTIELLEMENT_RECEPTIONNEE'):
                reception = ReceptionAchat.objects.create(
                    commande=commande,
                    utilisateur=random.choice(utilisateurs),
                    notes='Réception conforme' if commande.statut == 'ENTIEREMENT_RECEPTIONNEE' else 'Livraison partielle',
                )
                ReceptionAchat.objects.filter(pk=reception.pk).update(
                    date_reception=date_commande + timedelta(days=random.randint(1, 7))
                )
                for ligne in lignes:
                    quantite = ligne.quantite if commande.statut == 'ENTIEREMENT_RECEPTIONNEE' else max(1, ligne.quantite // 2)
                    lot = LotStock.objects.create(
                        medicament=ligne.medicament,
                        numero_lot=f'LOT-ACH-{commande.id:04d}-{ligne.id:04d}',
                        date_peremption=timezone.localdate() + timedelta(days=random.randint(180, 900)),
                        quantite=quantite,
                        quantite_initiale=quantite,
                    )
                    LigneReception.objects.create(
                        reception=reception,
                        ligne_achat=ligne,
                        medicament=ligne.medicament,
                        numero_lot=lot.numero_lot,
                        date_peremption=lot.date_peremption,
                        quantite_recue=quantite,
                        prix_unitaire=ligne.prix_unitaire,
                    )
                    mouvement = MouvementStock.objects.create(
                        medicament=ligne.medicament,
                        lot=lot,
                        type_mouvement='ENTREE',
                        quantite=quantite,
                        motif=f'Réception commande {commande.numero_commande}',
                        utilisateur=reception.utilisateur,
                        reference=f'REC-{reception.id}',
                    )
                    MouvementStock.objects.filter(pk=mouvement.pk).update(
                        date_mouvement=reception.date_reception
                    )

    def _ventes(self, clients, medicaments, lots_par_medicament, nombre, users):
        caissiers = [users['caissier'], users['caissier2'], users['pharmacien']]
        today = timezone.now()
        modes = ['ESPECES', 'ESPECES', 'ESPECES', 'MOBILE_MONEY', 'MOBILE_MONEY', 'CARTE']
        ventes_creees = []
        for index in range(nombre):
            date_vente = today - timedelta(
                days=random.randint(0, 89),
                hours=random.randint(0, 10),
                minutes=random.randint(0, 59),
            )
            caissier = random.choice(caissiers)
            client = random.choice(clients) if random.random() < 0.72 else None
            mode = random.choice(modes)
            vente = Vente.objects.create(
                numero_vente=f'VTE-{date_vente.strftime("%Y%m%d")}-{index + 1:05d}',
                client=client,
                utilisateur=caissier,
                mode_paiement=mode,
                statut='VALIDEE',
                montant_total=0,
                montant_paye=0,
                montant_rendu=0,
            )
            Vente.objects.filter(pk=vente.pk).update(date_vente=date_vente)

            total = Decimal('0')
            lignes = []
            for med in random.sample(medicaments, random.randint(1, 4)):
                candidats = [lot for lot in lots_par_medicament.get(med.id, []) if lot.quantite > 0 and not lot.bloque]
                if not candidats:
                    continue
                lot = random.choice(candidats)
                max_qte = min(lot.quantite, 10)
                if max_qte <= 0:
                    continue
                quantite = random.randint(1, max_qte)
                prix = med.prix_vente
                montant = prix * quantite
                LigneVente.objects.create(
                    vente=vente,
                    medicament=med,
                    lot=lot,
                    quantite=quantite,
                    prix_unitaire=prix,
                    montant_ligne=montant,
                )
                lot.quantite -= quantite
                lot.save(update_fields=['quantite'])
                if lot.quantite == 0:
                    lots_par_medicament[med.id].remove(lot)
                total += montant
                lignes.append((med, lot, quantite, prix))
                mouvement = MouvementStock.objects.create(
                    medicament=med,
                    lot=lot,
                    type_mouvement='SORTIE',
                    quantite=quantite,
                    motif=f'Vente {vente.numero_vente}',
                    utilisateur=caissier,
                    reference=vente.numero_vente,
                )
                MouvementStock.objects.filter(pk=mouvement.pk).update(date_mouvement=date_vente)

            if not lignes:
                vente.delete()
                continue

            if mode == 'ESPECES':
                paye = total + Decimal(random.choice([0, 0, 500, 1000, 2000]))
            else:
                paye = total
            Vente.objects.filter(pk=vente.pk).update(
                montant_total=total,
                montant_paye=paye,
                montant_rendu=paye - total,
            )
            paiement = Paiement.objects.create(
                vente=vente,
                mode=mode,
                montant=paye,
                statut='CONFIRME',
                reference=vente.numero_vente,
            )
            Paiement.objects.filter(pk=paiement.pk).update(date_paiement=date_vente)
            vente.refresh_from_db()
            ventes_creees.append((vente, lignes))

        # Retours et annulations sur une minorité de ventes.
        for vente, lignes in random.sample(ventes_creees, min(18, len(ventes_creees))):
            if not lignes:
                continue
            med, lot, quantite, prix = random.choice(lignes)
            quantite_retour = max(1, quantite // 2)
            remettre = random.random() < 0.75
            retour = RetourVente.objects.create(
                vente=vente,
                utilisateur=random.choice([users['pharmacien'], users['admin']]),
                motif=random.choice([
                    'Produit non conforme',
                    'Erreur de délivrance',
                    'Effet indésirable signalé',
                    'Client s\'est trompé de dosage',
                ]),
                montant_rembourse=prix * quantite_retour,
                type_operation='RETOUR',
                remis_en_stock=remettre,
            )
            LigneRetourVente.objects.create(
                retour=retour,
                ligne_vente=LigneVente.objects.filter(vente=vente, medicament=med).first(),
                medicament=med,
                lot=lot,
                quantite=quantite_retour,
                montant_rembourse=prix * quantite_retour,
            )
            if remettre and lot.date_peremption >= timezone.localdate():
                lot.quantite += quantite_retour
                lot.save(update_fields=['quantite'])
                mouvement = MouvementStock.objects.create(
                    medicament=med,
                    lot=lot,
                    type_mouvement='RETOUR',
                    quantite=quantite_retour,
                    motif=f'Retour vente {vente.numero_vente}',
                    utilisateur=retour.utilisateur,
                    reference=f'RET-{retour.id}',
                )
                MouvementStock.objects.filter(pk=mouvement.pk).update(date_mouvement=vente.date_vente + timedelta(days=1))
            Paiement.objects.create(
                vente=vente,
                mode=vente.mode_paiement,
                montant=retour.montant_rembourse,
                statut='REMBOURSE',
                reference=f'RET-{retour.id}',
            )

    def _audit(self, users):
        actions = [
            ('CONNEXION', 'Utilisateur', 'Connexion réussie'),
            ('VALIDATION_VENTE', 'Vente', 'Vente encaissée'),
            ('RECEPTION_COMMANDE', 'CommandeAchat', 'Réception de marchandises'),
            ('INVENTAIRE', 'Stock', 'Correction après inventaire'),
            ('CREATION_MEDICAMENT', 'Medicament', 'Ajout au catalogue'),
            ('MODIFICATION_PRIX', 'Medicament', 'Mise à jour du prix de vente'),
            ('RETOUR_VENTE', 'RetourVente', 'Retour enregistré'),
            ('ANNULATION_VENTE', 'Vente', 'Annulation avec remboursement'),
        ]
        utilisateurs = list(users.values())
        maintenant = timezone.now()
        for index in range(320):
            action, entite, details = random.choice(actions)
            journal = JournalAudit.objects.create(
                utilisateur=random.choice(utilisateurs),
                action=action,
                entite=entite,
                reference=f'REF-{random.randint(10000, 99999)}',
                details=details,
                adresse_ip=f'192.168.1.{random.randint(2, 250)}',
            )
            JournalAudit.objects.filter(pk=journal.pk).update(
                date_action=maintenant - timedelta(days=random.randint(0, 90), minutes=random.randint(0, 1440))
            )

    def _resume(self):
        self.stdout.write(self.style.SUCCESS("\nJeu de données de démonstration prêt :"))
        self.stdout.write(f"  Utilisateurs .......... {User.objects.count()}")
        self.stdout.write(f"  Catégories ............ {Categorie.objects.count()}")
        self.stdout.write(f"  Médicaments ........... {Medicament.objects.count()}")
        self.stdout.write(f"  Fournisseurs .......... {Fournisseur.objects.count()}")
        self.stdout.write(f"  Clients ............... {Client.objects.count()}")
        self.stdout.write(f"  Lots de stock ......... {LotStock.objects.count()}")
        self.stdout.write(f"  Commandes d'achat ..... {CommandeAchat.objects.count()}")
        self.stdout.write(f"  Réceptions ............ {ReceptionAchat.objects.count()}")
        self.stdout.write(f"  Ventes ................ {Vente.objects.count()}")
        self.stdout.write(f"  Retours ............... {RetourVente.objects.count()}")
        self.stdout.write(f"  Mouvements de stock ... {MouvementStock.objects.count()}")
        self.stdout.write(f"  Entrées d'audit ....... {JournalAudit.objects.count()}")
        self.stdout.write("\nComptes : admin / admin123 — caissier / demo12345 — pharmacien / demo12345")
