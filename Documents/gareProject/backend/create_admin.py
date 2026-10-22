#!/usr/bin/env python
"""
Script autonome pour créer instantanément l'administrateur Django FCE
et pré-remplir les 5 catégories documentaires officielles.
Usage : python create_admin.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gare_backend.settings')
django.setup()

from django.contrib.auth.models import User
from archives.models import Document, CertificatHorodatageRFC3161

# 1. Superutilisateur
username = "admin"
password = "admin2026"
email = "admin@fce.mg"

user, created = User.objects.get_or_create(username=username, defaults={'email': email})
user.set_password(password)
user.is_staff = True
user.is_superuser = True
user.save()

print("=" * 65)
if created:
    print(f"✓ SUPERUTILISATEUR CRÉÉ AVEC SUCCÈS !")
else:
    print(f"✓ MOT DE PASSE DU SUPERUTILISATEUR '{username}' RÉINITIALISÉ !")
print("=" * 65)
print(f"  • Nom d'utilisateur : {username}")
print(f"  • Mot de passe      : {password}")
print(f"  • URL de connexion  : http://localhost:8000/admin/")
print("=" * 65)

# 2. Pré-remplissage des 5 catégories
samples = [
    {
        "classement": "01",
        "chrono": "FCE/DG/DEC/2026/015",
        "cote": "ARC-2026-REG-0015",
        "title": "Décision de la Direction : Organisation maintenance urgente voie PK-54 et limitation 30 km/h",
        "doc_type": "DEC",
        "status": "scelle",
        "service_emetteur": "Direction Générale — Archives et Actes Officiels",
        "service_destinataire": "Districts d'exploitation & Magasin WORM",
        "signataire_nom": "Direction Générale",
        "signataire_role": "Directeur Général FCE",
        "sha256_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "pages": 2,
        "dua_annees": 30,
        "nom_fichier_original": "SCAN_DEC_2026_015_SIGNE_ORIGINAL.pdf",
        "ocr_content": "DIRECTION GÉNÉRALE FCE DÉCISION N° 015 Année : 2026 Objet : Organisation maintenance voie PK-54 limitation vitesse 30 km/h. Fait le 24 mars 2026.",
        "tags": "01 Décisions, Direction, PK-54, Limitation 30km/h"
    },
    {
        "classement": "02",
        "chrono": "FCE/DG/NDS/2026/044",
        "cote": "ARC-2026-REG-0016",
        "title": "Note de Service : Consignes d'exploitation par fortes chaleurs et surveillance des rails",
        "doc_type": "NDS",
        "status": "scelle",
        "service_emetteur": "Direction Sécurité Ferroviaire",
        "service_destinataire": "Ensemble des gares et chefs de canton FCE",
        "signataire_nom": "Ing. Hery R.",
        "signataire_role": "Directeur Voies & Bâtiments",
        "sha256_hash": "8b91c0d1e2f3a4b5c6d7e8f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f1a2b3",
        "pages": 1,
        "dua_annees": 10,
        "nom_fichier_original": "SCAN_NDS_044_CANICULE_CONSIGNES.png",
        "ocr_content": "FCE DIRECTION SÉCURITÉ FERROVIAIRE NOTE DE SERVICE 044/2026 Canicule surveillance des rails dilatation joints Ingénieur Hery R. Matricule : 44109 Année : 2026.",
        "tags": "02 Notes de service, Sécurité, Rails, Canicule"
    },
    {
        "classement": "03",
        "chrono": "FCE/CHI/2026/112",
        "cote": "ARC-2026-REG-0017",
        "title": "Chrono Interne : Note relative à l'affectation du stock de traverses métalliques aux ateliers",
        "doc_type": "CHI",
        "status": "scelle",
        "service_emetteur": "Bureau d'Ordre Central",
        "service_destinataire": "Ateliers de Traction de Fianarantsoa",
        "signataire_nom": "Jean-Paul R.",
        "signataire_role": "Secrétaire Général FCE",
        "sha256_hash": "9c0d1e2f3a4b5c6d7e8f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f1a2b3c4d",
        "pages": 2,
        "dua_annees": 10,
        "nom_fichier_original": "SCAN_CHI_112_STOCK_TRAVERSES.jpg",
        "ocr_content": "FCE BUREAU D'ORDRE CHRONO INTERNE 112/2026 Affectation traverses métalliques Jean Rakoto Matricule : 55210 Année : 2026 Ateliers traction.",
        "tags": "03 Chrono interne, Correspondance interne, Ateliers, Traverses"
    },
    {
        "classement": "04",
        "chrono": "FCE/DIR/ARR/2026/042",
        "cote": "ENR-2026-0891",
        "title": "Chrono Externe : Remplacement traverse métallique PK-54 — Convention tripartite Madarail",
        "doc_type": "CHE",
        "status": "en_cours_validation",
        "service_emetteur": "Direction Régionale des Travaux Publics",
        "service_destinataire": "M. le Directeur Général FCE",
        "signataire_nom": "Ing. Direction TP",
        "signataire_role": "Ingénieur en Chef Régional TP",
        "sha256_hash": "7f8a9e4b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f",
        "pages": 3,
        "dua_annees": 30,
        "nom_fichier_original": "COURRIER_ARR_042_CONVENTION_MADARAIL.pdf",
        "ocr_content": "MINISTÈRE DES TRANSPORTS DIRECTION RÉGIONALE TP Réf : ARR/2026/042 Destinataire : FCE Partenaire : Madarail Année : 2026 Travaux de réfection section PK-54.",
        "tags": "04 Chrono externe, Madarail, Ministère, Convention, ARR"
    },
    {
        "classement": "05",
        "chrono": "FCE/PV/DVB/2026/088",
        "cote": "ARC-2026-REG-0018",
        "title": "Procès-Verbal : Constat technique affaissement plate-forme ferroviaire PK-54+300",
        "doc_type": "PV",
        "status": "scelle",
        "service_emetteur": "Brigade cantonnière de voie (DVB)",
        "service_destinataire": "Direction Voies & Bâtiments",
        "signataire_nom": "Chef de Brigade",
        "signataire_role": "Contrôleur Voies FCE",
        "sha256_hash": "a7d931bc40e8912d0912cb841289fe42890b215414890c25a189f7823901ba12",
        "pages": 4,
        "dua_annees": 30,
        "nom_fichier_original": "SCAN_PV_088_CONSTAT_AFFAISSEMENT.pdf",
        "ocr_content": "PROCÈS-VERBAL DE CONSTAT BRIGADE CANTONNIÈRE SAHASINAKA Affaissement remblai PK 54+300 Chef de canton Rivo Rakotoarisoa Matricule : 33091 Année : 2026 FCE Voies et Bâtiments.",
        "tags": "05 Procès-verbaux, PV de constat, Géotechnique, Ballast"
    }
]

for s in samples:
    doc, _ = Document.objects.update_or_create(
        chrono=s["chrono"],
        defaults=s
    )
    print(f"✓ Catégorie {s['classement']} : {s['chrono']} initialisé.")

print("=" * 65)
print("Tous les actes des 5 catégories sont prêts !")
