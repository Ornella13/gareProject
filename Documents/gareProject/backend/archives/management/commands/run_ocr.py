import os
from django.core.management.base import BaseCommand
from archives.models import Document
from archives.ocr_service import extract_text_from_file_path, get_ocr_engine_status

class Command(BaseCommand):
    help = "Extrait et met à jour automatiquement le texte OCR pour tous les documents scannés enregistrés."

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force la ré-extraction OCR même si le document a déjà un texte OCR enregistré.',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        status = get_ocr_engine_status()
        self.stdout.write(self.style.NOTICE(f"Statut OCR : {status['mode']} — {status['message']}"))

        docs = Document.objects.all()
        total = docs.count()
        processed = 0
        updated = 0

        for doc in docs:
            processed += 1
            if not doc.fichier_original:
                continue

            if doc.ocr_content and not force:
                self.stdout.write(f"[{processed}/{total}] {doc.chrono} : Texte OCR déjà présent (ignorer).")
                continue

            try:
                file_path = doc.fichier_original.path
            except Exception:
                file_path = None

            if not file_path or not os.path.exists(file_path):
                self.stdout.write(self.style.WARNING(f"[{processed}/{total}] {doc.chrono} : Fichier physique introuvable."))
                continue

            self.stdout.write(f"[{processed}/{total}] Analyse OCR de {doc.chrono} ({doc.nom_fichier_original})...")
            text, msg = extract_text_from_file_path(file_path, doc.title)
            
            if text:
                doc.ocr_content = text
                doc.save(update_fields=['ocr_content', 'updated_at'])
                updated += 1
                self.stdout.write(self.style.SUCCESS(f"  -> {msg}"))
            else:
                self.stdout.write(self.style.WARNING(f"  -> {msg}"))

        self.stdout.write(self.style.SUCCESS(f"\nTerminé ! {updated} document(s) mis à jour avec le texte OCR."))
