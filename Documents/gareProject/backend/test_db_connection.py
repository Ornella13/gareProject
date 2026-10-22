#!/usr/bin/env python
"""
Script de test de connexion PostgreSQL pour GARE FCE
Usage : python test_db_connection.py
"""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gare_backend.settings')

try:
    import django
    django.setup()
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute("SELECT version();")
    db_version = cursor.fetchone()
    print("=" * 65)
    print("✓ SUCCÈS : CONNEXION À POSTGRESQL ÉTABLIE AVEC SUCCÈS !")
    print("=" * 65)
    print(f"Version de la base : {db_version[0]}")
    print("Moteur configuré   : django.db.backends.postgresql")
    print("=" * 65)
    print("\nVous pouvez maintenant exécuter les migrations :")
    print("  python manage.py migrate")
    print("  python create_admin.py")
except Exception as e:
    print("=" * 65)
    print("❌ ERREUR DE CONNEXION À POSTGRESQL")
    print("=" * 65)
    print(f"Détail : {e}\n")
    print("Vérifications à effectuer :")
    print("1. Le service PostgreSQL est-il bien démarré sur votre machine ?")
    print("2. Avez-vous créé la base de données 'gare_fce_db' dans pgAdmin ou psql ?")
    print("   Commande SQL : CREATE DATABASE gare_fce_db;")
    print("3. Vos identifiants dans gare_backend/settings.py correspondent-ils ?")
    print("   (Par défaut : USER='postgres', PASSWORD='votre_mot_de_passe')")
    print("=" * 65)
    sys.exit(1)
