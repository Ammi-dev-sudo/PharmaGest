import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Sauvegarde la base de données SQLite (et éventuellement les médias)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--include-media', action='store_true',
            help="Copie également le dossier des fichiers médias.",
        )
        parser.add_argument(
            '--destination', type=str, default=None,
            help="Dossier de destination (par défaut : backups/ à la racine).",
        )

    def handle(self, *args, **options):
        db_path = Path(settings.DATABASES['default']['NAME'])
        if not db_path.exists():
            self.stderr.write(self.style.ERROR(f"Base introuvable : {db_path}"))
            return

        destination = Path(options['destination']) if options['destination'] else settings.BASE_DIR / 'backups'
        destination.mkdir(parents=True, exist_ok=True)
        horodatage = datetime.now().strftime('%Y%m%d_%H%M%S')

        connection.close()
        db_backup = destination / f"{db_path.stem}_{horodatage}{db_path.suffix}"
        shutil.copy2(db_path, db_backup)
        self.stdout.write(self.style.SUCCESS(f"Base sauvegardée : {db_backup}"))

        if options['include_media']:
            media_root = Path(settings.MEDIA_ROOT)
            if media_root.exists():
                media_backup = destination / f"media_{horodatage}"
                shutil.copytree(media_root, media_backup)
                self.stdout.write(self.style.SUCCESS(f"Médias sauvegardés : {media_backup}"))
            else:
                self.stdout.write(self.style.WARNING("Aucun dossier médias à sauvegarder."))
