# Backend Django — Système d'Archivage FCE (GARE)

Ce dossier contient l'architecture backend complète **Django 5.x & Django REST Framework** pour le système d'archivage probant de la **Compagnie du Chemin de Fer Fianarantsoa-Côte Est (FCE)**.

---

## 1. Démarrage rapide

### Prérequis
- Python 3.10+
- `pip` et `virtualenv`

### Installation
```bash
cd backend
python -m venv venv
# Linux / macOS
source venv/bin/activate
# Windows
.\venv\Scripts\activate

pip install -r requirements.txt
```

### Migrations et Base de Données
```bash
python manage.py makemigrations archives
python manage.py migrate
python manage.py createsuperuser
```

### Lancement du serveur Django
```bash
python manage.py runserver 8000
```
Le serveur sera disponible sur `http://localhost:8000/`.
- **API REST** : `http://localhost:8000/api/`
- **Django Admin** : `http://localhost:8000/admin/`

---

## 2. Endpoints de l'API REST FCE

| Méthode | Endpoint | Description | Écran Correspondant |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/documents/` | Liste de tous les actes FCE | Registre |
| `GET` | `/api/documents/decisions/` | Actes exécutoires scellés (ex: 015) | **Écran 2** (Visualiseur PDF/A) |
| `GET` | `/api/documents/incoming/` | Courriers arrivés ARR (ex: 042) | **Écran 3** (Document Entrant) |
| `POST` | `/api/documents/{id}/add_visa/` | Apposition de visa électronique & PIN | Modal Visa / Validation |
| `GET` | `/api/bordereaux/` | Bordereaux DAF-04/B & magasins WORM | **Écran 1** (Bordereau RFC 3161) |
| `GET` | `/api/export/bundle/{chrono}/` | Téléchargement du bundle scellé `.zip` | Écran 1 & Toast Bundle |
| `GET` | `/api/images/seal.svg` | **Lien dynamique vers image SVG** du Sceau | Sceau réglementaire FCE |
| `GET` | `/api/images/stamp.svg` | **Lien dynamique vers image SVG** du Tampon | Tampon officiel ARR |

---

## 3. Intégration Frontend (Tailwind CSS + React)
Le frontend React / Tailwind CSS est configuré pour communiquer nativement avec ce backend Django via la variable d'environnement :
```bash
VITE_DJANGO_API_URL=http://localhost:8000/api
```
En l'absence du serveur Django actif, le frontend utilise automatiquement le stockage réactif local de secours tout en permettant de tester les appels Django.
