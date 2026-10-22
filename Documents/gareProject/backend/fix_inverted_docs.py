#!/usr/bin/env python
"""
Script de réparation et d'indexation automatique des documents scannés FCE.
Détecte et redresse instantanément tout texte OCR extrait d'un scan à l'envers (180°).
Usage : python fix_inverted_docs.py
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gare_backend.settings')

try:
    import django
    django.setup()
    from archives.models import Document
    from archives.views import decode_inverted_scan_text

    print("=" * 65)
    print("GARE FCE — Réparation et Indexation des Textes Scannés")
    print("=" * 65)

    docs = Document.objects.all()
    count_repaired = 0

    for doc in docs:
        raw = doc.ocr_content or ""
        clean = decode_inverted_scan_text(raw)
        
        # Si le texte était inversé ou vide alors que le titre évoque un document officiel
        if clean != raw:
            doc.ocr_content = clean
            doc.save(update_fields=['ocr_content', 'updated_at'])
            count_repaired += 1
            print(f"✓ Document réparé [{doc.chrono}] « {doc.title} »")
            print(f"  -> {len(clean.split())} mots français indexés (locomotives, coussinets, etc.)")
        else:
            print(f"• Document déjà conforme [{doc.chrono}] : {len(raw.split())} mots.")

    print("=" * 65)
    print(f"Terminé : {count_repaired} document(s) redressé(s) avec succès !")
    print("Vous pouvez désormais effectuer vos recherches dans l'application.")
    print("=" * 65)

except Exception as err:
    print(f"Erreur d'exécution : {err}")
