from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from archives.models import Document, BordereauVersement, CertificatHorodatageRFC3161, JournalAudit
from django.utils import timezone

class Command(BaseCommand):
    help = "Initialise le compte administrateur FCE et pré-remplit les actes de test (Décision 015 & ARR 042)"

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='admin', help="Nom d'utilisateur administrateur")
        parser.add_argument('--password', type=str, default='admin2026', help="Mot de passe administrateur")
        parser.add_argument('--email', type=str, default='admin@fce.mg', help="Email administrateur")

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        email = options['email']

        # 1. Création / Mise à jour du superutilisateur
        user, created = User.objects.get_or_create(username=username, defaults={'email': email})
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"✓ Superutilisateur '{username}' créé avec succès !"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✓ Mot de passe du superutilisateur '{username}' réinitialisé avec succès !"))

        self.stdout.write(self.style.NOTICE(f"Identifiants de connexion Django Admin :"))
        self.stdout.write(f"  • Nom d'utilisateur : {username}")
        self.stdout.write(f"  • Mot de passe     : {password}")
        self.stdout.write(f"  • URL             : http://localhost:8000/admin/\n")

        # 2. Pré-remplissage des actes réglementaires selon les 5 Catégories Officielles
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
                "tags": "01 Décisions, Direction, PK-54, Limitation 30km/h"
            },
            {
                "classement": "02",
                "chrono": "FCE/DG/NDS/2026/044",
                "cote": "ARC-2026-REG-0016",
                "title": "Note de Service : Consignes d'exploitation par fortes chaleurs et surveillance des joints de dilatation",
                "doc_type": "NDS",
                "status": "scelle",
                "service_emetteur": "Direction Sécurité Ferroviaire",
                "service_destinataire": "Ensemble des services et gares FCE",
                "signataire_nom": "Direction Voies",
                "signataire_role": "Directeur Voies & Bâtiments",
                "sha256_hash": "8b91c0d1e2f3a4b5c6d7e8f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f1a2b3",
                "pages": 1,
                "dua_annees": 10,
                "tags": "02 Notes de service, Sécurité, Rails, Canicule"
            },
            {
                "classement": "03",
                "chrono": "FCE/CHI/2026/112",
                "cote": "ARC-2026-REG-0017",
                "title": "Chrono Interne : Note interne relative à l'affectation du stock de traverses métalliques aux ateliers",
                "doc_type": "CHI",
                "status": "scelle",
                "service_emetteur": "Bureau d'Ordre Central",
                "service_destinataire": "Ateliers de Traction",
                "signataire_nom": "Secrétaire Général",
                "signataire_role": "Secrétaire Général FCE",
                "sha256_hash": "9c0d1e2f3a4b5c6d7e8f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f1a2b3c4d",
                "pages": 2,
                "dua_annees": 10,
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
                "tags": "04 Chrono externe, Madarail, Ministère, Convention, ARR"
            },
            {
                "classement": "05",
                "chrono": "FCE/PV/DVB/2026/088",
                "cote": "ARC-2026-REG-0018",
                "title": "Procès-Verbal : Constat technique d'affaissement partiel de ballast PK-54+300 par la brigade cantonnière",
                "doc_type": "PV",
                "status": "scelle",
                "service_emetteur": "Brigade cantonnière de voie (DVB)",
                "service_destinataire": "Direction Voies & Bâtiments",
                "signataire_nom": "Chef de Brigade",
                "signataire_role": "Contrôleur Voies FCE",
                "sha256_hash": "a7d931bc40e8912d0912cb841289fe42890b215414890c25a189f7823901ba12",
                "pages": 4,
                "dua_annees": 30,
                "tags": "05 Procès-verbaux, PV de constat, Géotechnique, Ballast"
            }
        ]

        for s in samples:
            doc, _ = Document.objects.update_or_create(
                chrono=s["chrono"],
                defaults=s
            )
            self.stdout.write(self.style.SUCCESS(f"✓ Catégorie {s['classement']} : {s['chrono']} initialisé."))
