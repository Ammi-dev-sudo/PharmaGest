# PharmaGest — Application de gestion de pharmacie

Application web Django complète pour gérer une pharmacie : médicaments, lots, stocks, achats, ventes, paiements, retours, clients, fournisseurs, utilisateurs et rapports PDF.

## Installation

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

La base SQLite `db.sqlite3` est créée automatiquement. Les migrations sont fournies dans chaque application.

## Jeu de données de démonstration

```bash
python3 manage.py donnees_demo --reset
```

Cette commande génère 65 médicaments, 200 lots, 45 commandes, 15 réceptions, 220 ventes, 18 retours, 640 mouvements de stock et 320 entrées d'audit. Les comptes créés sont :

- `admin` / `admin123` (administrateur)
- `pharmacien` / `demo12345`
- `gestionnaire` / `demo12345`
- `caissier` / `demo12345`
- `caissier2` / `demo12345`

## Fonctionnalités

- Connexion, inscription, changement et réinitialisation sécurisée du mot de passe.
- Rôles utilisateurs (administrateur, pharmacien, gestionnaire, caissier, responsable) et permissions Django.
- Journal d'audit horodaté des opérations sensibles.
- Catalogue des médicaments : recherche, filtres, tri, pagination, photos validées (type et taille), archivage, catégories protégées.
- Fiches clients et fournisseurs avec historique des ventes et des achats.
- Commandes d'achat : brouillon, validation, réception partielle ou totale, lots et péremptions, bons PDF.
- Stock FEFO par lots, mouvements traçables, alertes de rupture/stock faible, lots périmés ou proches de la péremption, inventaire physique.
- Caisse rapide : panier, lots FEFO, contrôle du stock, paiement, validation atomique et anti-double validation.
- Reçus et factures PDF, retours avec remboursement et remise en stock conditionnelle, annulation traçable.
- Tableau de bord animé avec statistiques et graphiques.
- Rapports ventes, achats et stock avec filtres par période et exports PDF.
- Sauvegarde et restauration de la base de données.

## Sauvegarde et restauration

```bash
python manage.py sauvegarde
python manage.py sauvegarde --include-media
python manage.py restaurer backups/db_AAAAMMJJ_HHMMSS.sqlite3 --confirmer
```

Les sauvegardes sont écrites dans `backups/`. Testez régulièrement une restauration avant toute mise en production.

## Tests

```bash
python manage.py test
```

Les tests couvrent la vente, le stock, les retours, les annulations, les réceptions partielles, l'inventaire, les PDF et les alertes.

## Technologies

Django 6.1.2, SQLite, Bootstrap 5, Bootstrap Icons, Chart.js, ReportLab, Pillow.
