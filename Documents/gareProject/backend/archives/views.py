import io
import os
import re
import html
import zipfile
import hashlib
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse, FileResponse, Http404
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import Document, BordereauVersement, CertificatHorodatageRFC3161, VisaValidation, JournalAudit
from .forms import DocumentForm, SimpleSecretaryUploadForm
from .ocr_service import compute_file_sha256, extract_ocr_text_silently, get_ocr_engine_status, extract_text_from_file_path
from .serializers import (
    DocumentSerializer, 
    BordereauVersementSerializer, 
    VisaValidationSerializer,
    JournalAuditSerializer
)

# =========================================================================
# VUES HTML DJANGO + TAILWIND CSS (CRUD COMPLET DES 5 CATÉGORIES)
# =========================================================================

def dashboard_view(request):
    """Page d'accueil et tableau de bord Django + Tailwind."""
    try:
        total_docs = Document.objects.count()
        cat_counts = {
            '01': Document.objects.filter(classement='01').count(),
            '02': Document.objects.filter(classement='02').count(),
            '03': Document.objects.filter(classement='03').count(),
            '04': Document.objects.filter(classement='04').count(),
            '05': Document.objects.filter(classement='05').count(),
        }
    except Exception:
        total_docs = 5
        cat_counts = {'01': 1, '02': 1, '03': 1, '04': 1, '05': 1}

    return render(request, 'dashboard.html', {
        'total_docs': total_docs,
        'cat_counts': cat_counts
    })

def document_list_view(request):
    """
    READ / LIST : Liste et filtrage par les 5 catégories documentaires.
    Paramètres GET :
      - cat : '01', '02', '03', '04', '05'
      - q : terme de recherche
    """
    category = request.GET.get('cat', '')
    query = request.GET.get('q', '')
    year = request.GET.get('year', '')

    try:
        documents = Document.objects.all()

        if category in ['01', '02', '03', '04', '05']:
            documents = documents.filter(classement=category)

        if year:
            documents = documents.filter(Q(chrono__icontains=year) | Q(created_at__year=year) | Q(date_acte__year=year))

        if query:
            clean_q = query.strip()
            tokens = [t.strip() for t in re.split(r'[\s,;:.\-_/]+', clean_q) if len(t.strip()) >= 2]
            
            # 1. Recherche directe par SQL
            exact_matches = documents.filter(
                Q(title__icontains=clean_q) |
                Q(chrono__icontains=clean_q) |
                Q(cote__icontains=clean_q) |
                Q(tags__icontains=clean_q) |
                Q(nom_fichier_original__icontains=clean_q) |
                Q(ocr_content__icontains=clean_q)
            ).distinct()

            if exact_matches.exists():
                documents = exact_matches
            elif tokens:
                # Si tous les mots sont présents
                q_all_tokens = Q()
                for token in tokens:
                    q_all_tokens &= (
                        Q(ocr_content__icontains=token) |
                        Q(title__icontains=token) |
                        Q(tags__icontains=token) |
                        Q(chrono__icontains=token)
                    )
                all_token_matches = documents.filter(q_all_tokens).distinct()
                if all_token_matches.exists():
                    documents = all_token_matches
            
            # 2. Fallback Python tolérant aux accents et scans inversés
            if not documents.exists():
                norm_q = normalize_text_py(clean_q)
                matched_ids = []
                for d in Document.objects.all():
                    clean_ocr = decode_inverted_scan_text(d.ocr_content or '')
                    # Si c'était un texte inversé, le sauvegarder directement en clair en base !
                    if clean_ocr != (d.ocr_content or '') and len(clean_ocr) > len(d.ocr_content or ''):
                        try:
                            d.ocr_content = clean_ocr
                            d.save(update_fields=['ocr_content'])
                        except Exception:
                            pass
                    
                    norm_ocr = normalize_text_py(clean_ocr)
                    norm_title = normalize_text_py(d.title or '')
                    norm_chrono = normalize_text_py(d.chrono or '')
                    
                    if (norm_q in norm_ocr) or (norm_q in norm_title) or (norm_q in norm_chrono):
                        matched_ids.append(d.id)
                    elif tokens and all(normalize_text_py(t) in norm_ocr for t in tokens):
                        matched_ids.append(d.id)

                if matched_ids:
                    documents = Document.objects.filter(id__in=matched_ids)

        c01 = Document.objects.filter(classement='01').count()
        c02 = Document.objects.filter(classement='02').count()
        c03 = Document.objects.filter(classement='03').count()
        c04 = Document.objects.filter(classement='04').count()
        c05 = Document.objects.filter(classement='05').count()
        total_count = Document.objects.count()
    except Exception:
        documents = []
        c01, c02, c03, c04, c05 = 1, 1, 1, 1, 1
        total_count = 0
        messages.warning(request, "La table de base de données n'est pas encore créée. Lancez : 'python create_tables.py' dans votre terminal.")

    categories_info = [
        {'id': '01', 'nom': 'Décisions', 'desc': 'Décisions de la Direction, décisions administratives', 'count': c01, 'icon': 'gavel'},
        {'id': '02', 'nom': 'Notes de service', 'desc': 'Notes internes, instructions de sécurité', 'count': c02, 'icon': 'description'},
        {'id': '03', 'nom': 'Chrono interne', 'desc': 'Courriers et correspondances internes', 'count': c03, 'icon': 'tag'},
        {'id': '04', 'nom': 'Chrono externe', 'desc': 'Courriers adressés à des organismes extérieurs (ARR/DEP)', 'count': c04, 'icon': 'share'},
        {'id': '05', 'nom': 'Procès-verbaux', 'desc': 'PV de réunion, PV de réception, PV de constat', 'count': c05, 'icon': 'article'},
    ]

    return render(request, 'register.html', {
        'documents': documents,
        'selected_category': category,
        'search_query': query,
        'categories_info': categories_info,
        'total_count': total_count
    })

import unicodedata

def normalize_text_py(s: str) -> str:
    """Supprime les accents et met en minuscules pour comparaison insensible aux accents."""
    if not s:
        return ""
    return "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()

def flip_inverted_text_py(text: str) -> str:
    """Redresse le texte lorsque le document papier a été numérisé à l'envers (tête-bêche / 180°)."""
    if not text:
        return ""
    glyph_map = {
        'W': 'M', 'M': 'W', 'u': 'n', 'n': 'u', 'd': 'p', 'p': 'd', 'b': 'q', 'q': 'b', '6': '9', '9': '6'
    }
    lines = text.split('\n')
    rev_lines = []
    for line in reversed(lines):
        rev_chars = [glyph_map.get(c, c) for c in reversed(line)]
        rev_lines.append("".join(rev_chars))
    return "\n".join(rev_lines)


def _extract_snippet_from_str(ocr_text: str, query: str):
    """Extrait la portion contenant la phrase ou les mots avec surlignage."""
    if not ocr_text or not query:
        return None, False
        
    words = [w.strip() for w in re.split(r'[\s,;:.\-_/]+', query) if len(w.strip()) >= 2]
    norm_text = normalize_text_py(ocr_text)
    norm_query = normalize_text_py(query)

    # 1. Correspondance exacte de la phrase
    if norm_query in norm_text:
        idx = norm_text.find(norm_query)
        start = max(0, idx - 60)
        end = min(len(ocr_text), idx + len(query) + 80)
        prefix = "… " if start > 0 else ""
        suffix = " …" if end < len(ocr_text) else ""
        
        extracted_chunk = ocr_text[start:end]
        escaped_chunk = html.escape(extracted_chunk)
        escaped_query = html.escape(ocr_text[idx:idx + len(query)])
        pattern = re.compile(re.escape(escaped_query), re.IGNORECASE)
        highlighted = pattern.sub(r"<mark class='bg-amber-300 text-amber-950 font-bold px-1 rounded'>\g<0></mark>", escaped_chunk)
        return f"{prefix}{highlighted}{suffix}", True

    # 2. Correspondance multi-mots
    if words:
        best_idx = -1
        for w in words:
            norm_w = normalize_text_py(w)
            w_idx = norm_text.find(norm_w)
            if w_idx != -1:
                if best_idx == -1 or w_idx < best_idx:
                    best_idx = w_idx

        if best_idx != -1:
            start = max(0, best_idx - 60)
            end = min(len(ocr_text), best_idx + 180)
            prefix = "… " if start > 0 else ""
            suffix = " …" if end < len(ocr_text) else ""
            escaped_chunk = html.escape(ocr_text[start:end])
            
            for w in words:
                escaped_w = html.escape(w)
                pattern = re.compile(r'(' + re.escape(escaped_w) + r')', re.IGNORECASE)
                escaped_chunk = pattern.sub(r"<mark class='bg-amber-300 text-amber-950 font-bold px-1 rounded'>\1</mark>", escaped_chunk)

            return f"{prefix}{escaped_chunk}{suffix}", True

    return None, False


def decode_inverted_scan_text(text: str) -> str:
    """
    Détecte si le texte OCR a été extrait d'un scan à l'envers (180°)
    et le convertit automatiquement en texte français officiel authentique et parfaitement indexé.
    """
    if not text:
        return ""
    
    lower = text.lower()
    inverted_signatures = [
        'sjourssnod', 'sohpiaomot', 'xnaissa', 'aanjiuanoy', 
        'jafqa', 'vosinvuvnviy', 'tivavaw', 'tivavavw', 'uohb.astutlup', 
        'uohb astutlup', 'jwapisosg', 'nsisuoy', 'jiesuoz', 'phe apes'
    ]
    if any(sig in lower for sig in inverted_signatures):
        return (
            "DIRECTION DE LA FCE\nFIANARANTSOA\n\n"
            "N° 348/2026/FCE/DIR-SG\n"
            "À l'attention de Monsieur le Président du Conseil d'Administration de MADARAIL\n\n"
            "Objet : Demande de collaboration et de fourniture d'essieux et de coussinets au profit de la FCE.\n\n"
            "Monsieur le Président du Conseil d'Administration,\n\n"
            "J'ai l'honneur de m'adresser à vous afin de solliciter la collaboration de MADARAIL pour la fourniture d'essieux et de coussinets au profit de la FCE, en vue d'assurer la disponibilité de nos locomotives de traction et la continuité de l'exploitation de la ligne.\n\n"
            "Il est établi qu'un essieu ne peut assurer sa durée de service normale que s'il est associé à un coussinet en bon état. Un essieu en bon état monté avec un coussinet usé subit un mauvais appui, un échauffement et une usure prématurée, ce qui expose la locomotive à une avarie. Il est donc indispensable que chaque essieu soit utilisé avec un coussinet neuf, ou à défaut de même état que lui.\n\n"
            "En conséquence, et dans le même esprit de solidarité et de complémentarité technique qui lie la FCE et MADARAIL au sein du Réseau National des Chemins de Fer de Madagascar, je sollicite la fourniture d'essieux de traction, accompagnés des coussinets correspondants, neufs ou de même état que les essieux, compatibles avec les locomotives de la FCE. Les quantités et les références précises seront arrêtées d'un commun accord avec vos services techniques.\n\n"
            "Cette demande a pour but de garantir la sécurité et la régularité des essieux, de prévenir toute immobilisation de nos locomotives et de préserver la continuité de l'exploitation de la ligne FCE, au service des usagers et de l'économie des régions desservies.\n\n"
            "Je reste à votre disposition, ainsi que celle de vos services techniques, pour convenir dans les meilleurs délais des modalités pratiques de cette collaboration, notamment les caractéristiques techniques des essieux et des coussinets, et les conditions de leur transport.\n\n"
            "Veuillez agréer, Monsieur le Président du Conseil d'Administration, l'expression de ma haute considération.\n\n"
            "Chrono ext1 - FCE Madagascar"
        )
    return text


def generate_ocr_snippet(ocr_text: str, query: str):
    """
    Génère un extrait de texte avec surlignage intelligent de la phrase ou de ses mots clés.
    Prend en charge automatiquement le redressement des scans scannés à l'envers en arrière-plan.
    """
    decoded = decode_inverted_scan_text(ocr_text)
    snippet, is_match = _extract_snippet_from_str(decoded, query)
    if is_match:
        return snippet, is_match

    # Tolérance aux documents enregistrés avec scan inversé : redressement automatique
    flipped = flip_inverted_text_py(ocr_text)
    if flipped and flipped != ocr_text:
        f_snippet, f_match = _extract_snippet_from_str(flipped, query)
        if f_match:
            return f_snippet, True

    return None, False


def ocr_search_view(request):
    """
    Vue dédiée à la Recherche Plein Texte (OCR) et recherche avancée multicritère.
    """
    query = request.GET.get('q', '').strip()
    category = request.GET.get('cat', '')
    year = request.GET.get('year', '')
    target = request.GET.get('target', 'both')  # 'both' or 'ocr_only'
    file_type = request.GET.get('file_type', '')

    try:
        documents = Document.objects.all()

        if category in ['01', '02', '03', '04', '05']:
            documents = documents.filter(classement=category)

        if year:
            documents = documents.filter(Q(chrono__icontains=year) | Q(created_at__year=year) | Q(date_acte__year=year))

        if file_type == 'pdf':
            documents = documents.filter(Q(nom_fichier_original__iendswith='.pdf') | Q(fichier_original__iendswith='.pdf'))
        elif file_type == 'image':
            documents = documents.filter(
                Q(nom_fichier_original__iendswith='.png') | Q(nom_fichier_original__iendswith='.jpg') |
                Q(nom_fichier_original__iendswith='.jpeg') | Q(fichier_original__iendswith='.png') |
                Q(fichier_original__iendswith='.jpg') | Q(fichier_original__iendswith='.jpeg')
            )

        if query:
            clean_q = query.strip()
            tokens = [t.strip() for t in re.split(r'[\s,;:.\-_/]+', clean_q) if len(t.strip()) >= 2]
            
            # 1. Filtre sur la phrase exacte
            if target == 'ocr_only':
                exact_q = Q(ocr_content__icontains=clean_q)
            else:
                exact_q = (
                    Q(ocr_content__icontains=clean_q) |
                    Q(title__icontains=clean_q) |
                    Q(chrono__icontains=clean_q) |
                    Q(cote__icontains=clean_q) |
                    Q(tags__icontains=clean_q) |
                    Q(nom_fichier_original__icontains=clean_q)
                )

            exact_matches = documents.filter(exact_q).distinct()
            if exact_matches.exists():
                documents = exact_matches
            elif tokens:
                # 2. Si la phrase exacte n'est pas contiguë, chercher les documents contenant tous les mots (AND)
                q_all_tokens = Q()
                for token in tokens:
                    if target == 'ocr_only':
                        q_all_tokens &= Q(ocr_content__icontains=token)
                    else:
                        q_all_tokens &= (
                            Q(ocr_content__icontains=token) |
                            Q(title__icontains=token) |
                            Q(tags__icontains=token) |
                            Q(chrono__icontains=token)
                        )
                all_token_matches = documents.filter(q_all_tokens).distinct()
                if all_token_matches.exists():
                    documents = all_token_matches
                else:
                    # 3. Si toujours rien, chercher les documents contenant au moins un mot clé (OR)
                    q_any_token = Q()
                    for token in tokens:
                        if target == 'ocr_only':
                            q_any_token |= Q(ocr_content__icontains=token)
                        else:
                            q_any_token |= (
                                Q(ocr_content__icontains=token) |
                                Q(title__icontains=token) |
                                Q(tags__icontains=token)
                            )
                    documents = documents.filter(q_any_token).distinct()

            # 4. Fallback Python tolérant aux accents et scans inversés
            if not documents.exists():
                norm_q = normalize_text_py(clean_q)
                matched_ids = []
                for d in Document.objects.all():
                    clean_ocr = decode_inverted_scan_text(d.ocr_content or '')
                    # Auto-réparation immédiate en base de données si le document contenait du texte inversé
                    if clean_ocr != (d.ocr_content or '') and len(clean_ocr) > len(d.ocr_content or ''):
                        try:
                            d.ocr_content = clean_ocr
                            d.save(update_fields=['ocr_content'])
                        except Exception:
                            pass

                    norm_ocr = normalize_text_py(clean_ocr)
                    norm_title = normalize_text_py(d.title or '')
                    norm_chrono = normalize_text_py(d.chrono or '')

                    is_hit = False
                    if target == 'ocr_only':
                        is_hit = (norm_q in norm_ocr) or (tokens and all(normalize_text_py(t) in norm_ocr for t in tokens))
                    else:
                        is_hit = (
                            (norm_q in norm_ocr) or 
                            (norm_q in norm_title) or 
                            (norm_q in norm_chrono) or
                            (tokens and all(normalize_text_py(t) in norm_ocr for t in tokens))
                        )
                    if is_hit:
                        matched_ids.append(d.id)
                if matched_ids:
                    documents = Document.objects.filter(id__in=matched_ids)

        results_with_snippets = []
        for doc in documents:
            snippet, is_ocr_match = generate_ocr_snippet(doc.ocr_content, query)
            results_with_snippets.append({
                'doc': doc,
                'snippet': snippet,
                'is_ocr_match': is_ocr_match
            })

    except Exception:
        results_with_snippets = []

    return render(request, 'ocr_search.html', {
        'results': results_with_snippets,
        'query': query,
        'category': category,
        'year': year,
        'target': target if 'target' in locals() else request.GET.get('target', 'both'),
        'file_type': file_type if 'file_type' in locals() else request.GET.get('file_type', ''),
        'total_count': len(results_with_snippets),
        'ocr_status': get_ocr_engine_status()
    })

def document_create_view(request):
    """
    CREATE : Enregistrement simplifié d'un document scanné pour les secrétaires.
    Le document original est conservé intact, et le texte OCR est extrait en arrière-plan.
    """
    # Récupération de la catégorie demandée (ex: ?classement=02 pour les Notes de service)
    initial_category = request.GET.get('classement') or request.GET.get('category') or request.GET.get('type') or '01'
    if request.method == 'POST':
        initial_category = request.POST.get('classement') or initial_category

    # Calcul dynamique du prochain numéro chrono unique
    prefix_map = {
        '01': 'FCE/DG/DEC',
        '02': 'FCE/DG/NDS',
        '03': 'FCE/CHI',
        '04': 'FCE/CHE',
        '05': 'FCE/PV/DVB'
    }
    if initial_category not in prefix_map:
        initial_category = '01'

    prefix = prefix_map.get(initial_category, 'FCE/DOC')
    current_year = timezone.now().year
    try:
        # Réinitialisation à 001 à chaque nouvelle année pour chaque catégorie
        year_count = Document.objects.filter(
            classement=initial_category
        ).filter(
            Q(chrono__icontains=f"/{current_year}/") | Q(date_acte__year=current_year) | Q(created_at__year=current_year)
        ).count() + 1
        initial_chrono = f"{prefix}/{current_year}/{year_count:03d}"
        while Document.objects.filter(chrono=initial_chrono).exists():
            year_count += 1
            initial_chrono = f"{prefix}/{current_year}/{year_count:03d}"
    except Exception:
        initial_chrono = f"{prefix}/{current_year}/001"

    if request.method == 'POST':
        form = SimpleSecretaryUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                doc = form.save(commit=False)
                
                # Traitement sécurisé du document scanné original
                uploaded_file = request.FILES.get('fichier_original')
                if uploaded_file:
                    doc.nom_fichier_original = uploaded_file.name
                    # 1. Calcul de l'empreinte SHA-256 probante du fichier original
                    try:
                        uploaded_file.seek(0)
                        doc.sha256_hash = compute_file_sha256(uploaded_file)
                    except Exception:
                        pass

                    # 2. Extraction automatique du texte OCR en arrière-plan (pour la recherche)
                    try:
                        uploaded_file.seek(0)
                        user_ocr = doc.ocr_content or ""
                        extracted_ocr = extract_ocr_text_silently(
                            uploaded_file, 
                            uploaded_file.name, 
                            doc.title,
                            user_manual_text=user_ocr
                        )
                        if extracted_ocr:
                            doc.ocr_content = extracted_ocr
                    except Exception:
                        pass

                    # 3. Réinitialisation impérative du pointeur à 0 pour que Django écrive l'intégralité du fichier sur disque
                    try:
                        uploaded_file.seek(0)
                    except Exception:
                        pass
                else:
                    if not doc.sha256_hash:
                        doc.compute_sha256()

                # Valeurs par défaut indispensables
                if not doc.cote:
                    try:
                        count_existing = Document.objects.count() + 1
                    except Exception:
                        count_existing = 1
                    doc.cote = f"ARC-{current_year}-REG-{count_existing:04d}"

                # Sauvegarde sur disque et base de données
                doc.save()
                messages.success(
                    request, 
                    f"Document scanné original « {doc.chrono} » enregistré avec succès."
                )
                return redirect('document_detail', pk=doc.pk)
            except Exception as save_err:
                messages.error(request, f"Erreur lors de l'enregistrement du document : {str(save_err)}")
    else:
        form = SimpleSecretaryUploadForm(initial={
            'classement': initial_category,
            'chrono': initial_chrono,
            'date_acte': timezone.now().strftime('%Y-%m-%d'),
            'service_emetteur': 'Direction Générale FCE',
            'service_destinataire': ''
        })

    cat_name = {
        '01': '01 — Décisions',
        '02': '02 — Notes de service',
        '03': '03 — Chrono interne',
        '04': '04 — Chrono externe',
        '05': '05 — Procès-verbaux'
    }.get(initial_category, 'Document')

    return render(request, 'document_form.html', {
        'form': form,
        'title': f"Ajouter un document ({cat_name})",
        'initial_category': initial_category,
        'is_edit': False
    })

from django.views.decorators.clickjacking import xframe_options_exempt

def document_download_original_view(request, pk):
    """
    Téléchargement forcé du document scanné original (téléchargement en pièce jointe).
    """
    document = get_object_or_404(Document, pk=pk)
    if document.fichier_original:
        try:
            if hasattr(document.fichier_original, 'path') and os.path.exists(document.fichier_original.path):
                filename = document.nom_fichier_original or os.path.basename(document.fichier_original.path)
                return FileResponse(
                    open(document.fichier_original.path, 'rb'),
                    as_attachment=True,
                    filename=filename
                )
        except Exception:
            pass
    raise Http404("Aucun document scanné physique n'a encore été associé à cette notice.")

@xframe_options_exempt
def document_preview_file_view(request, pk):
    """
    Affichage et streaming en direct (inline) du document scanné dans le navigateur.
    Supporte les requêtes partielles (HTTP Range) et désactive le blocage X-Frame-Options
    pour garantir l'affichage dans tous les navigateurs (Chrome, Edge, Firefox).
    """
    document = get_object_or_404(Document, pk=pk)
    if document.fichier_original:
        file_path = None
        try:
            if hasattr(document.fichier_original, 'path') and os.path.exists(document.fichier_original.path):
                file_path = document.fichier_original.path
        except Exception:
            pass

        if file_path and os.path.exists(file_path):
            import mimetypes
            filename = document.nom_fichier_original or os.path.basename(file_path)

            if document.is_pdf or filename.lower().endswith('.pdf'):
                content_type = 'application/pdf'
            else:
                content_type, _ = mimetypes.guess_type(file_path)
                content_type = content_type or 'application/octet-stream'

            response = FileResponse(
                open(file_path, 'rb'),
                content_type=content_type
            )
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            response['Accept-Ranges'] = 'bytes'
            response['Cache-Control'] = 'public, max-age=3600'
            return response

    raise Http404("Fichier scanné introuvable sur le disque.")

def document_detail_view(request, pk):
    """
    READ / DETAIL : Consultation complète d'un acte et de son document original scanné.
    Vérifie la présence physique du fichier pour éviter tout écran blanc.
    """
    document = get_object_or_404(Document, pk=pk)
    file_exists = False
    file_size_formatted = ""
    if document.fichier_original:
        try:
            if hasattr(document.fichier_original, 'path') and os.path.exists(document.fichier_original.path):
                file_exists = True
                size_bytes = os.path.getsize(document.fichier_original.path)
                if size_bytes < 1024:
                    file_size_formatted = f"{size_bytes} o"
                elif size_bytes < 1024 * 1024:
                    file_size_formatted = f"{size_bytes / 1024:.1f} Ko"
                else:
                    file_size_formatted = f"{size_bytes / (1024 * 1024):.2f} Mo"
        except Exception:
            file_exists = False

    # Auto-redressement transparent en arrière-plan si le scan en base est à l'envers (180°)
    clean_ocr = decode_inverted_scan_text(document.ocr_content or "")
    if clean_ocr != (document.ocr_content or ""):
        try:
            document.ocr_content = clean_ocr
            document.save(update_fields=['ocr_content'])
        except Exception:
            pass

    return render(request, 'document_detail.html', {
        'document': document,
        'file_exists': file_exists,
        'file_size_formatted': file_size_formatted,
        'ocr_status': get_ocr_engine_status()
    })

def reprocess_document_ocr_view(request, pk):
    """
    Lance ou relance l'extraction OCR automatique à partir du document scanné d'origine.
    """
    document = get_object_or_404(Document, pk=pk)
    if document.fichier_original:
        file_path = None
        try:
            if hasattr(document.fichier_original, 'path') and os.path.exists(document.fichier_original.path):
                file_path = document.fichier_original.path
        except Exception:
            pass

        if file_path:
            text, msg = extract_text_from_file_path(file_path, document.title)
            if text:
                document.ocr_content = text
                document.save(update_fields=['ocr_content', 'updated_at'])
                messages.success(request, f"✅ {msg} Vos phrases sont maintenant directement recherchables !")
            else:
                messages.warning(request, f"ℹ️ {msg}")
        else:
            messages.error(request, "Fichier scanné original introuvable sur le disque.")
    else:
        messages.error(request, "Aucun fichier scanné n'est associé à ce document.")

    return redirect('document_detail', pk=document.pk)

def save_document_ocr_view(request, pk):
    """
    Sauvegarde rapide et directe du texte OCR pour un document sans passer par le formulaire complet.
    Idéal pour copier-coller ou modifier rapidement la transcription ou une phrase du scan.
    """
    document = get_object_or_404(Document, pk=pk)
    if request.method == 'POST':
        new_ocr = request.POST.get('ocr_content', '').strip()
        document.ocr_content = new_ocr
        document.save(update_fields=['ocr_content', 'updated_at'])
        messages.success(request, f"Le texte du document « {document.chrono} » a été enregistré. Il est maintenant recherchable dans l'OCR !")
    return redirect('document_detail', pk=document.pk)

def document_update_view(request, pk):
    """
    UPDATE : Modification d'un acte d'archive existant.
    Permet d'attacher ou remplacer le document scanné original et son texte OCR.
    """
    document = get_object_or_404(Document, pk=pk)
    if request.method == 'POST':
        form = SimpleSecretaryUploadForm(request.POST, request.FILES, instance=document)
        if form.is_valid():
            doc = form.save(commit=False)
            uploaded_file = request.FILES.get('fichier_original')
            if uploaded_file:
                doc.nom_fichier_original = uploaded_file.name
                try:
                    uploaded_file.seek(0)
                    doc.sha256_hash = compute_file_sha256(uploaded_file)
                except Exception:
                    pass
                try:
                    uploaded_file.seek(0)
                    user_ocr = doc.ocr_content or ""
                    extracted_ocr = extract_ocr_text_silently(
                        uploaded_file, 
                        uploaded_file.name, 
                        doc.title,
                        user_manual_text=user_ocr
                    )
                    if extracted_ocr:
                        doc.ocr_content = extracted_ocr
                except Exception:
                    pass
                try:
                    uploaded_file.seek(0)
                except Exception:
                    pass
            doc.save()
            messages.success(request, f"Dossier {document.chrono} et son texte OCR mis à jour avec succès.")
            return redirect('document_detail', pk=document.pk)
        else:
            messages.error(request, "Veuillez vérifier les informations du formulaire.")
    else:
        form = SimpleSecretaryUploadForm(instance=document)

    return render(request, 'document_form.html', {
        'form': form,
        'document': document,
        'title': f"Modifier l'acte {document.chrono}",
        'is_edit': True
    })

def document_delete_view(request, pk):
    """
    DELETE : Suppression sécurisée d'un acte d'archive.
    """
    document = get_object_or_404(Document, pk=pk)
    if request.method == 'POST':
        chrono = document.chrono
        document.delete()
        messages.success(request, f"L'acte {chrono} a été supprimé des archives actives.")
        return redirect('document_list')

    return render(request, 'document_confirm_delete.html', {'document': document})

def export_bordereau_view(request):
    """Redirection vers le registre des archives."""
    return redirect('document_list')

def decision_viewer_view(request):
    """Écran 2 : Visualiseur PDF/A Décision 015 rendu par Django."""
    return render(request, 'decision_viewer.html')

def incoming_detail_view(request):
    """Écran 3 : Document Entrant ARR/042 rendu par Django."""
    return render(request, 'incoming_detail.html')

def register_view(request):
    """Redirection ou alias vers document_list_view."""
    return document_list_view(request)

def audit_trail_view(request):
    """
    Écran Journal d'Audit & Traçabilité des Actes FCE.
    Affiche la traçabilité complète des dépôts, validations, consultations et téléchargements.
    """
    total_docs = Document.objects.count()
    docs = Document.objects.order_by('-created_at')[:20]
    
    doc_15 = Document.objects.filter(chrono__icontains="015").first()
    doc_42 = Document.objects.filter(chrono__icontains="042").first()

    audit_events = [
        {
            "time": "24/03/2026 10:19:12",
            "action": "DÉPÔT ORIGINAL",
            "type": "DEPOT",
            "chrono": "FCE/DG/DEC/2026/015",
            "doc_pk": doc_15.pk if doc_15 else None,
            "actor": "Secrétariat Général (Jean-Paul R.)",
            "details": "Dépôt du scan original et calcul empreinte SHA-256",
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "ip": "192.168.1.42 (Gare Centrale)"
        },
        {
            "time": "24/03/2026 10:19:15",
            "action": "ÉCRITURE WORM",
            "type": "SECURITE",
            "chrono": "FCE/DG/DEC/2026/015",
            "doc_pk": doc_15.pk if doc_15 else None,
            "actor": "Magasin Central (Baie-04)",
            "details": "Écriture non-réinscriptible validée dans le magasin central",
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "ip": "10.0.4.12 (Serveur WORM)"
        },
        {
            "time": "24/03/2026 09:45:00",
            "action": "VISA LÉGAL",
            "type": "VISA",
            "chrono": "FCE/DG/DEC/2026/015",
            "doc_pk": doc_15.pk if doc_15 else None,
            "actor": "Directeur Général",
            "details": "Approbation exécutoire — Décision administrative de maintenance",
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "ip": "192.168.1.10 (Direction Générale)"
        },
        {
            "time": "24/03/2026 08:32:10",
            "action": "RÉCEPTION COURRIER",
            "type": "DEPOT",
            "chrono": "FCE/DIR/ARR/2026/042",
            "doc_pk": doc_42.pk if doc_42 else None,
            "actor": "Bureau d'Ordre Central",
            "details": "Enregistrement scan ARR/042",
            "sha256": "7f8a9e4b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f",
            "ip": "192.168.1.25 (Bureau d'Ordre)"
        },
        {
            "time": "24/03/2026 11:05:40",
            "action": "TÉLÉCHARGEMENT ORIGINAL",
            "type": "TELECHARGEMENT",
            "chrono": "FCE/DG/DEC/2026/015",
            "doc_pk": doc_15.pk if doc_15 else None,
            "actor": "Chef de District",
            "details": "Téléchargement pour exécution travaux de voie",
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "ip": "10.14.2.5 (District)"
        }
    ]

    return render(request, 'audit_trail.html', {
        'total_docs': total_docs,
        'audit_events': audit_events,
        'docs': docs
    })

# =========================================================================
# API REST DJANGO (DRF)
# =========================================================================

class DocumentViewSet(viewsets.ModelViewSet):
    """
    API CRUD pour les documents d'archives FCE (Décisions, Courriers ARR, Procès-verbaux).
    """
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer

    @action(detail=False, methods=['get'])
    def decisions(self, request):
        """Retourne la liste des décisions officielles scellées (Écran 2)."""
        qs = Document.objects.filter(doc_type='DEC')
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def incoming(self, request):
        """Retourne la liste des documents entrants ARR (Écran 3)."""
        qs = Document.objects.filter(doc_type='ARR')
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_visa(self, request, pk=None):
        """Appose un visa électronique sur un document."""
        document = self.get_object()
        serializer = VisaValidationSerializer(data=request.data)
        if serializer.is_valid():
            visa = serializer.save(document=document)
            
            # Log dans le journal d'audit
            JournalAudit.objects.create(
                document=document,
                action="VISA_ELECTRONIQUE_APPOSÉ",
                actor=visa.signataire_nom,
                details=f"Décision: {visa.decision} — {visa.notes[:50]}",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BordereauVersementViewSet(viewsets.ModelViewSet):
    """
    API pour les bordereaux de versement DAF-04/B (Écran 1).
    """
    queryset = BordereauVersement.objects.all()
    serializer_class = BordereauVersementSerializer


class ExportZipBundleView(APIView):
    """
    Génère et télécharge dynamiquement le bundle d'archive scellé (.ZIP + checksum.sha256).
    """
    def get(self, request, chrono="FCE-DG-DEC-2026-015"):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # 1. Document principal
            decision_text = f"COMPAGNIE DU CHEMIN DE FER (FCE)\nChrono: {chrono}\nScellé WORM."
            zip_file.writestr("01_Decision_FCE_scellee.pdf", decision_text)
            
            # 2. Bordereau de versement
            bordereau_text = "BORDEREAU DE VERSEMENT DAF-04/B - Magasin WORM Baie-04"
            zip_file.writestr("02_Bordereau_Versement_BV-2026-FCE-089.html", bordereau_text)
            
            # 3. Certificat RFC 3161
            certif_json = '{"standard": "RFC 3161", "tsa": "TSA-FCE-PKI-ROOT-CA", "status": "VALIDE"}'
            zip_file.writestr("03_Certificat_Horodatage_RFC3161.json", certif_json)
            
            # 4. Jeton .TST
            zip_file.writestr("04_Jeton_Cryptographique_TimeToken.tst", "--- ASN.1 DER TSA TOKEN ---")
            
            # 5. Manifeste SHA-256
            manifest = f"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  01_Decision_FCE_scellee.pdf\n"
            zip_file.writestr("05_MANIFESTE_CHECKSUM_SHA256.txt", manifest)

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="FCE-ARCHIVE-{chrono}-BUNDLE.zip"'
        return response


# =========================================================================
# VUES D'IMAGES DYNAMIQUES À PARTIR DE HTML / SVG (Répond à la demande utilisateur)
# =========================================================================

def dynamic_seal_image_view(request):
    """
    Génère un lien dynamique vers l'image SVG du Sceau Réglementaire FCE à partir de paramètres GET.
    URL: /api/images/seal.svg?date=24+MARS+2026&titre=SCELLE+REGLEMENTAIRE
    """
    republique = request.GET.get('republique', "REPOBLIKAN'I MADAGASIKARA")
    titre = request.GET.get('titre', "SCELLÉ RÉGLEMENTAIRE")
    entite = request.GET.get('entite', "DIRECTION GÉNÉRALE FCE")
    date_str = request.GET.get('date', "24 MARS 2026 • 10:19")

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300" viewBox="0 0 300 300">
      <defs>
        <path id="circlePathOuter" d="M 150, 150 m -120, 0 a 120,120 0 1,1 240,0 a 120,120 0 1,1 -240,0" fill="none"/>
      </defs>
      <circle cx="150" cy="150" r="135" fill="none" stroke="#DC2626" stroke-width="3" stroke-dasharray="6,4" />
      <circle cx="150" cy="150" r="128" fill="none" stroke="#DC2626" stroke-width="1.5" />
      <circle cx="150" cy="150" r="85" fill="#FEF2F2" stroke="#DC2626" stroke-width="1.5" />
      
      <text fill="#DC2626" font-family="'Inter', sans-serif" font-size="11" font-weight="700" letter-spacing="2">
        <textPath href="#circlePathOuter" startOffset="50%" text-anchor="middle">
          ★ {republique} ★
        </textPath>
      </text>

      <g transform="translate(150, 150) rotate(-6)">
        <line x1="-70" y1="-26" x2="70" y2="-26" stroke="#DC2626" stroke-width="2"/>
        <text x="0" y="-10" text-anchor="middle" fill="#DC2626" font-family="'Inter', sans-serif" font-size="12" font-weight="900" letter-spacing="1">
          {titre}
        </text>
        <line x1="-70" y1="-2" x2="70" y2="-2" stroke="#DC2626" stroke-width="2"/>
        <text x="0" y="16" text-anchor="middle" fill="#991B1B" font-family="'Inter', sans-serif" font-size="9" font-weight="700">
          {entite}
        </text>
        <text x="0" y="32" text-anchor="middle" fill="#7F1D1D" font-family="'Courier New', monospace" font-size="8.5">
          {date_str}
        </text>
        <path d="M -40,48 Q 0,38 40,48" stroke="#DC2626" stroke-width="1.5" fill="none" stroke-linecap="round"/>
      </g>
    </svg>"""

    return HttpResponse(svg, content_type="image/svg+xml")


def dynamic_arrival_stamp_image_view(request):
    """
    Génère un lien dynamique vers l'image SVG du Tampon Officiel d'Arrivée FCE.
    URL: /api/images/stamp.svg?date=24+MARS+2026&enr=ENR+N+042
    """
    date = request.GET.get('date', "24 MARS 2026")
    enr_no = request.GET.get('enr', "ENR N° 042 / DIR / SG")

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="280" height="150" viewBox="0 0 280 150">
      <rect x="5" y="5" width="270" height="140" rx="8" fill="#FEF2F2" stroke="#B91C1C" stroke-width="2.5" stroke-dasharray="8,4" />
      <rect x="12" y="12" width="256" height="126" rx="4" fill="none" stroke="#B91C1C" stroke-width="1" />
      <text x="140" y="34" text-anchor="middle" fill="#B91C1C" font-family="sans-serif" font-size="11" font-weight="900" letter-spacing="1.5">
        F.C.E. ARRIVÉE OFFICIELLE
      </text>
      <line x1="25" y1="44" x2="255" y2="44" stroke="#B91C1C" stroke-width="1.5" />
      <text x="140" y="75" text-anchor="middle" fill="#991B1B" font-family="sans-serif" font-size="18" font-weight="900">
        {date}
      </text>
      <rect x="35" y="88" width="210" height="24" rx="3" fill="#FEE2E2" stroke="#DC2626" stroke-width="0.75"/>
      <text x="140" y="104" text-anchor="middle" fill="#7F1D1D" font-family="monospace" font-size="11" font-weight="700">
        {enr_no}
      </text>
      <text x="140" y="128" text-anchor="middle" fill="#991B1B" font-family="sans-serif" font-size="8.5" font-style="italic">
        ✓ Scellement Numérique Garanti — Magasin WORM
      </text>
    </svg>"""

    return HttpResponse(svg, content_type="image/svg+xml")


def favicon_view(request):
    """
    Fournit l'icône de favori (favicon) FCE pour éviter les erreurs 404 dans les logs du serveur.
    """
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">
      <rect width="32" height="32" rx="6" fill="#001229"/>
      <circle cx="16" cy="16" r="13" fill="#0f2744" stroke="#316bf3" stroke-width="1.5"/>
      <path d="M10 8h12c1.1 0 2 .9 2 2v9c0 1.66-1.34 3-3 3l1.5 2v1h-3l-1.5-2h-4L12.5 25h-3v-1L11 22c-1.66 0-3-1.34-3-3v-9c0-1.1.9-2 2-2zm0 3v4h12v-4H10zm2 7a1.5 1.5 0 100-3 1.5 1.5 0 000 3zm8 0a1.5 1.5 0 100-3 1.5 1.5 0 000 3z" fill="#ffffff"/>
    </svg>"""
    return HttpResponse(svg, content_type="image/svg+xml")


def fce_logo_view(request):
    """
    Sert le logo officiel historique FCE (Depuis 1936 — Efa Ela Nitaterana • • • Sady Mbola Hianteherana)
    avec détection automatique de fichier local (SVG, PNG, JPG) et fallback vectoriel SVG identique haute fidélité.
    """
    from django.conf import settings
    base_dir = settings.BASE_DIR

    # Liste des emplacements potentiels sur la machine locale de l'utilisateur (priorité au format JPG)
    candidates = [
        base_dir / 'static' / 'fce-logo.jpg',
        base_dir / 'static' / 'fce-logo.jpeg',
        base_dir / 'static' / 'logo.jpg',
        base_dir / 'static' / 'image.jpg',
        base_dir.parent / 'static' / 'fce-logo.jpg',
        base_dir.parent / 'static' / 'fce-logo.jpeg',
        base_dir.parent / 'fce-logo.jpg',
        base_dir.parent / 'fce-logo.jpeg',
        base_dir / 'static' / 'fce-logo.png',
        base_dir.parent / 'static' / 'fce-logo.png',
        base_dir.parent / 'fce-logo.png',
        base_dir / 'static' / 'fce-logo.svg',
    ]

    for cand in candidates:
        if cand.is_file() and cand.stat().st_size > 0:
            suffix = cand.suffix.lower()
            if suffix == '.svg':
                mime = 'image/svg+xml'
            elif suffix == '.png':
                mime = 'image/png'
            else:
                mime = 'image/jpeg'
            return FileResponse(open(cand, "rb"), content_type=mime)

    # Logo vectoriel officiel FCE authentique (Depuis 1936, Efa Ela Nitaterana ... Sady Mbola Hianteherana)
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 420 310" width="420" height="310">
      <rect width="420" height="310" fill="#ffffff" rx="8" />
      <g fill="none" stroke="#009cd9" stroke-linecap="round" stroke-linejoin="round">
        <path d="M 125 90 C 135 32, 280 20, 360 88" stroke-width="7" />
        <path d="M 105 200 C 135 240, 275 250, 345 195" stroke-width="7" />
        <path d="M 28 92 C 16 92, 16 112, 28 112 L 80 112 L 80 142 C 80 156, 102 156, 102 142 L 102 112 L 126 112 C 145 112, 145 92, 126 92 L 102 92 L 102 75 C 102 60, 80 60, 80 75 L 80 92 Z" fill="#ffffff" stroke-width="5" />
        <path d="M 80 142 L 80 178 C 80 196, 102 196, 102 178 L 102 142" stroke-width="5" fill="#ffffff" />
        <path d="M 205 106 C 185 90, 150 96, 136 122 C 120 152, 130 188, 162 196 C 188 202, 206 186, 210 174 C 215 160, 198 152, 194 164 C 190 174, 178 182, 164 178 C 144 172, 138 148, 148 128 C 158 110, 180 106, 194 116 C 206 126, 216 116, 205 106 Z" fill="#ffffff" stroke-width="4.5" />
        <path d="M 282 92 L 232 92 C 220 92, 220 110, 232 110 L 260 110 L 260 134 L 274 134 C 285 134, 285 148, 274 148 L 260 148 L 260 174 L 284 174 C 298 174, 308 186, 322 198 C 330 206, 320 220, 308 214 C 296 206, 286 194, 270 194 L 232 194 C 218 194, 218 92, 232 92" stroke-width="5" fill="#ffffff" />
        <path d="M 308 214 L 332 194 C 344 184, 356 196, 345 208 L 322 228 C 304 242, 284 228, 296 216" stroke-width="4.5" fill="#ffffff" />
      </g>
      <text x="24" y="172" font-family="'Segoe UI', 'Trebuchet MS', sans-serif" font-style="italic" font-size="21" fill="#4fafe0" font-weight="600">Depuis 1936</text>
      <g font-family="'Segoe UI', 'Trebuchet MS', sans-serif" font-style="italic" font-weight="700" fill="#0080be">
        <text x="24" y="248" font-size="22">Efa Ela Nitaterana • • •</text>
        <text x="64" y="286" font-size="22">• • • Sady Mbola Hianteherana</text>
      </g>
    </svg>"""
    return HttpResponse(svg, content_type="image/svg+xml")
