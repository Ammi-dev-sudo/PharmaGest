import os
import django
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from medicaments.models import Categorie, Medicament
from fournisseurs.models import Fournisseur
from clients.models import Client
from stock.models import LotStock
from utilisateurs.models import CustomUser

User = get_user_model()

# Utilisateurs
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@pharmagest.mg', 'admin123', role='ADMIN')
    print('Superuser créé')
else:
    print('Superuser existe déjà')

# Catégories
categories_data = [
    ('Antalgiques', 'Médicaments contre la douleur'),
    ('Antibiotiques', 'Médicaments antibactériens'),
    ('Anti-inflammatoires', 'Réduction inflammation'),
    ('Vitamines & Compléments', 'Compléments alimentaires'),
    ('Cardiologie', 'Médicaments cardiovasculaires'),
    ('Dermatologie', 'Soins cutanés'),
]
for nom, desc in categories_data:
    Categorie.objects.get_or_create(nom=nom, defaults={'description': desc})

cats = list(Categorie.objects.all())

# Médicaments
medicaments_data = [
    ('Paracétamol 500mg', 'PARACETAMOL', cats[0], 'COMPRIME', '500mg', 'PHARMA', '3400930001111', 150, 350, 50),
    ('Amoxicilline 500mg', 'AMOXICILLINE', cats[1], 'GELULE', '500mg', 'BIOFARMA', '3400930002222', 450, 850, 30),
    ('Ibuprofène 400mg', 'IBUPROFENE', cats[2], 'COMPRIME', '400mg', 'MEDIPHA', '3400930003333', 200, 450, 40),
    ('Vitamine C 1000mg', 'ACIDE ASCORBIQUE', cats[3], 'COMPRIME_EFFERVESCENT', '1000mg', 'VITAPHAR', '3400930004444', 300, 650, 60),
    ('Amlodipine 5mg', 'AMLODIPINE', cats[4], 'COMPRIME', '5mg', 'CARDIOPHAR', '3400930005555', 800, 1450, 25),
    ('Diclofénac gel 1%', 'DICLOFENAC', cats[2], 'CREME', '1%', 'DERMAPHAR', '3400930006666', 650, 1200, 20),
    ('Azithromycine 250mg', 'AZITHROMYCINE', cats[1], 'COMPRIME', '250mg', 'BIOFARMA', '3400930007777', 1200, 2100, 15),
    ('Bêta-carotène', 'BETA_CAROTENE', cats[3], 'COMPRIME', '15mg', 'VITAPHAR', '3400930008888', 400, 750, 40),
    ('Enalapril 10mg', 'ENALAPRIL', cats[4], 'COMPRIME', '10mg', 'CARDIOPHAR', '3400930009999', 600, 1100, 30),
    ('Hydrocortisone crème 1%', 'HYDROCORTISONE', cats[5], 'CREME', '1%', 'DERMAPHAR', '3400930010000', 550, 950, 25),
    ('Doliprane 1000mg', 'PARACETAMOL', cats[0], 'COMPRIME', '1000mg', 'PHARMA', '3400930011000', 200, 450, 40),
    ('Ciprofloxacine 500mg', 'CIPROFLOXACINE', cats[1], 'COMPRIME', '500mg', 'BIOFARMA', '3400930012000', 900, 1650, 20),
]

for data in medicaments_data:
    nom_c, nom_g, cat, forme, dos, labo, cb, pa, pv, seuil = data
    med, created = Medicament.objects.get_or_create(
        nom_commercial=nom_c,
        defaults={
            'denomination_generique': nom_g,
            'categorie': cat,
            'forme_pharmaceutique': forme,
            'dosage': dos,
            'laboratoire': labo,
            'code_barres': cb,
            'prix_achat': pa,
            'prix_vente': pv,
            'seuil_alerte': seuil,
            'statut': 'ACTIF'
        }
    )
    if created:
        print(f'Créé: {nom_c}')

# Fournisseurs
fournisseurs_data = [
    ('PharmImport Madagascar', 'contact@pharmimport.mg', '+261 34 00 000 01', 'Antananarivo, Analakely'),
    ('MediSupply SA', 'ventes@medisupply.mg', '+261 34 00 000 02', 'Antsirabe'),
    ('BioPharma Distribution', 'info@biopharma.mg', '+261 34 00 000 03', 'Toamasina'),
    ('Labomedica', 'commande@labomedica.mg', '+261 34 00 000 04', 'Fianarantsoa'),
]
for nom, email, tel, adr in fournisseurs_data:
    Fournisseur.objects.get_or_create(nom_raison_sociale=nom, defaults={'email': email, 'telephone': tel, 'adresse': adr})

fourns = list(Fournisseur.objects.all())

# Clients
clients_data = [
    ('Rakoto Jean', '+261 32 11 222 33'),
    ('Rasoamanana Marie', '+261 32 11 222 44'),
    ('Andriamanana Paul', '+261 32 11 222 55'),
    ('Razafy Hery', '+261 32 11 222 66'),
    ('Randrianarisoa Lala', '+261 32 11 222 77'),
]
for nom_complet, tel in clients_data:
    Client.objects.get_or_create(nom_complet=nom_complet, defaults={'telephone': tel})

# Lots de stock
meds = list(Medicament.objects.all())
for i, med in enumerate(meds):
    lot_num = f'LOT-2025-{1000 + i}'
    if not LotStock.objects.filter(numero_lot=lot_num).exists():
        qte = 80 + i*15
        LotStock.objects.create(
            medicament=med,
            numero_lot=lot_num,
            quantite=qte,
            quantite_initiale=qte,
            date_peremption=date.today() + timedelta(days=400 + i*20),
            bloque=False
        )
        print(f'Lot créé pour {med.nom_commercial}: {qte} unités')

print(f'\nTotal: {Categorie.objects.count()} catégories, {Medicament.objects.count()} médicaments, {Fournisseur.objects.count()} fournisseurs, {Client.objects.count()} clients, {LotStock.objects.count()} lots')
print('Données peuplées avec succès!')
