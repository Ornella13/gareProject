#!/usr/bin/env python
"""
Script rapide pour ajouter immédiatement les colonnes de documents scannés
dans PostgreSQL sans toucher aux migrations.
Usage : python fix_columns.py
"""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gare_backend.settings')

try:
    import django
    django.setup()
    from django.db import connection

    print("Ajout des colonnes de documents scannés dans PostgreSQL...")
    with connection.cursor() as cursor:
        cursor.execute("""
            ALTER TABLE archives_document 
            ADD COLUMN IF NOT EXISTS fichier_original varchar(100);

            ALTER TABLE archives_document 
            ADD COLUMN IF NOT EXISTS nom_fichier_original varchar(255) DEFAULT '';

            ALTER TABLE archives_document 
            ADD COLUMN IF NOT EXISTS ocr_content text DEFAULT '';
        """)

    print("✓ SUCCÈS : Les colonnes 'fichier_original' et 'ocr_content' sont maintenant actives dans PostgreSQL !")
    print("Vous pouvez rafraîchir http://localhost:8000/registre/")

except Exception as e:
    print(f"Erreur : {e}")
    sys.exit(1)
