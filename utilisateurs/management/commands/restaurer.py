import shutil
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = "Restaure une sauvegarde SQLite. Opération destructive : utilisez --confirmer."

    def add_arguments(self, parser):
        parser.add_argument('fichier', type=str, help="Chemin du fichier .sqlite3 à restaurer.")
        parser.add_argument(
            '--confirmer', action='store_true',
            help="Confirme le remplacement de la base actuelle.",
        )

    def handle(self, *args, **options):
        if not options['confirmer']:
            raise CommandError(
                "Restauration annulée. Relancez avec --confirmer après avoir sauvegardé la base actuelle."
            )
        source = Path(options['fichier']).expanduser().resolve()
        if not source.exists() or not source.is_file():
            raise CommandError(f"Fichier de sauvegarde introuvable : {source}")

        db_path = Path(settings.DATABASES['default']['NAME']).resolve()
        if source == db_path:
            raise CommandError("Le fichier source est déjà la base de données active.")

        connection.close()
        shutil.copy2(source, db_path)
        self.stdout.write(self.style.SUCCESS(f"Base restaurée depuis : {source}"))
        self.stdout.write(self.style.WARNING("Redémarrez le serveur Django pour recharger les connexions."))
