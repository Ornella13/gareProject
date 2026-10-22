#!/usr/bin/env python
"""
Script direct pour forcer la création des tables dans PostgreSQL
Nettoie les conflits de migrations et initialise la base.
Usage : python create_tables.py
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# 1. Nettoyage préventif des anciens fichiers de migration en conflit
migrations_dir = BASE_DIR / 'archives' / 'migrations'
if migrations_dir.exists():
    for file_path in migrations_dir.glob('*.py'):
        if file_path.name != '__init__.py':
            try:
                file_path.unlink()
                print(f"✓ Nettoyage ancien fichier : {file_path.name}")
            except Exception as e:
                print(f"Notice nettoyage : {e}")

# Assurer la présence de __init__.py dans migrations
init_file = migrations_dir / '__init__.py'
if not init_file.exists():
    init_file.touch()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gare_backend.settings')

try:
    import django
    django.setup()
    from django.core.management import call_command
    from django.db import connection

    print("=" * 65)
    print("1. Génération des fichiers de migrations propres pour 'archives'...")
    call_command('makemigrations', 'archives', interactive=False)

    print("\n2. Application de TOUTES les migrations vers PostgreSQL...")
    call_command('migrate', interactive=False)

    print("\n3. Vérification de l'existence de la table 'archives_document'...")
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'archives_document'
            );
        """)
        table_exists = cursor.fetchone()[0]

    if table_exists:
        print("✓ SUCCÈS : La table 'archives_document' existe dans PostgreSQL.")
        print("  Vérification et ajout des colonnes pour les documents scannés...")
        with connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE archives_document 
                ADD COLUMN IF NOT EXISTS fichier_original varchar(100);

                ALTER TABLE archives_document 
                ADD COLUMN IF NOT EXISTS nom_fichier_original varchar(255) DEFAULT '';

                ALTER TABLE archives_document 
                ADD COLUMN IF NOT EXISTS ocr_content text DEFAULT '';
            """)
        print("✓ Colonnes 'fichier_original' et 'ocr_content' confirmées dans PostgreSQL !")

        print("\n4. Insertion/Mise à jour des données des 5 catégories et administrateur...")
        import create_admin
        print("\n" + "=" * 65)
        print("✓ INITIALISATION & MIGRATION RÉUSSIES À 100% !")
        print("Toutes les colonnes sont créées dans PostgreSQL.")
        print("Vous pouvez recharger votre page :")
        print("  👉 http://localhost:8000/registre/")
        print("=" * 65)
    else:
        print("❌ La table n'a pas pu être créée. Vérifiez les erreurs ci-dessus.")

except Exception as err:
    print(f"\n❌ Erreur : {err}")
    sys.exit(1)
