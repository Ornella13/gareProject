"""
Service OCR & Traitement d'Arrière-Plan FCE
Extrait automatiquement le texte pour l'indexation de recherche sans jamais
altérer ni modifier le document scanné original.
Prend en charge la détection automatique de Tesseract sous Windows et Linux,
l'extraction de texte natif et d'images de PDF scannés, ainsi que la fusion avec la saisie manuelle.
"""
import os
import hashlib
import re
import shutil

def get_tesseract_cmd():
    """Détecte l'exécutable Tesseract sous Windows et Linux."""
    cmd = shutil.which("tesseract")
    if cmd:
        return cmd

    windows_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
    ]
    for p in windows_paths:
        if os.path.isfile(p):
            return p
    return None

def compute_file_sha256(uploaded_file) -> str:
    """Calcule l'empreinte SHA-256 du fichier scanné d'origine."""
    sha = hashlib.sha256()
    for chunk in uploaded_file.chunks():
        sha.update(chunk)
    uploaded_file.seek(0)
    return sha.hexdigest()

def extract_ocr_text_silently(uploaded_file, file_name: str, document_title: str = "", user_manual_text: str = "") -> str:
    """
    Extrait le texte du document scanné en arrière-plan pour alimenter
    la base de recherche.
    Ne bloque jamais l'enregistrement si les outils OCR locaux ne sont pas installés.
    """
    extracted_text = ""
    lower_name = (file_name or "").lower()
    tesseract_path = get_tesseract_cmd()

    # Configuration de pytesseract si un exécutable a été trouvé
    pytesseract_module = None
    if tesseract_path:
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            pytesseract_module = pytesseract
        except Exception:
            pytesseract_module = None
    else:
        try:
            import pytesseract
            pytesseract_module = pytesseract
        except Exception:
            pytesseract_module = None

    # 1. Tentative d'extraction si c'est un PDF
    if lower_name.endswith('.pdf'):
        try:
            import pypdf
            reader = pypdf.PdfReader(uploaded_file)
            pages_text = []
            for p in reader.pages[:10]:
                text = p.extract_text()
                if text and text.strip():
                    pages_text.append(text.strip())
            
            # Si le PDF contient du texte numérique
            if pages_text:
                extracted_text = "\n".join(pages_text)
            
            # Si le PDF est un scan d'images (aucun texte natif extrait) et que pytesseract est disponible
            elif pytesseract_module:
                try:
                    from PIL import Image, ImageOps
                    import io
                    img_texts = []
                    for p in reader.pages[:4]: # 4 premières pages scannées
                        for img_obj in getattr(p, 'images', []):
                            try:
                                img_data = io.BytesIO(img_obj.data)
                                pil_img = Image.open(img_data)
                                pil_img = ImageOps.exif_transpose(pil_img)
                                ocr_part = pytesseract_module.image_to_string(pil_img, lang='fra+eng')
                                
                                # Si le texte semble inversé (180°), tester la rotation automatique
                                if ocr_part and any(sig in ocr_part.lower() for sig in ['enoy', 'xnaissa', 'sjourssnod', 'tivavaw', 'jafqa', 'uosinvuvnviy']):
                                    rotated = pil_img.rotate(180, expand=True)
                                    ocr_part = pytesseract_module.image_to_string(rotated, lang='fra+eng')

                                if ocr_part and ocr_part.strip():
                                    img_texts.append(ocr_part.strip())
                            except Exception:
                                continue
                    if img_texts:
                        extracted_text = "\n".join(img_texts)
                except Exception:
                    pass

            uploaded_file.seek(0)
        except Exception:
            try:
                uploaded_file.seek(0)
            except Exception:
                pass

    # 2. Tentative d'extraction OCR pour image (PNG, JPG, JPEG, TIFF)
    elif lower_name.endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp')):
        if pytesseract_module:
            try:
                from PIL import Image, ImageOps
                img = Image.open(uploaded_file)
                img = ImageOps.exif_transpose(img)
                extracted_text = pytesseract_module.image_to_string(img, lang='fra+eng')
                
                # Auto-détection et redressement transparent si scan à l'envers
                if extracted_text and any(sig in extracted_text.lower() for sig in ['enoy', 'xnaissa', 'sjourssnod', 'tivavaw', 'jafqa', 'uosinvuvnviy']):
                    rotated = img.rotate(180, expand=True)
                    text_180 = pytesseract_module.image_to_string(rotated, lang='fra+eng')
                    if text_180 and len(text_180.strip()) > 10:
                        extracted_text = text_180

                uploaded_file.seek(0)
            except Exception:
                try:
                    uploaded_file.seek(0)
                except Exception:
                    pass

    # 3. Enrichissement avec la saisie manuelle de l'utilisateur et métadonnées
    cleaned_name = re.sub(r'[_.\-]+', ' ', os.path.splitext(file_name)[0]) if file_name else ""
    tokens = []
    
    if user_manual_text and user_manual_text.strip():
        tokens.append(user_manual_text.strip())
        
    if extracted_text and extracted_text.strip():
        tokens.append(extracted_text.strip())
        
    if document_title and document_title.strip():
        tokens.append(document_title.strip())
        
    if cleaned_name and cleaned_name.strip():
        tokens.append(cleaned_name.strip())

    final_searchable_text = "\n\n".join(tokens).strip()
    return final_searchable_text


def get_ocr_engine_status():
    """
    Vérifie la disponibilité des modules OCR (pypdf, pytesseract, binaire Tesseract).
    Retourne un dictionnaire informatif pour guider l'utilisateur.
    """
    status = {
        'has_pypdf': False,
        'has_pytesseract': False,
        'tesseract_cmd': None,
        'is_fully_ready': False,
        'mode': 'Manuel',
        'message': ''
    }
    try:
        import pypdf
        status['has_pypdf'] = True
    except Exception:
        status['has_pypdf'] = False

    tesseract_path = get_tesseract_cmd()
    status['tesseract_cmd'] = tesseract_path

    try:
        import pytesseract
        status['has_pytesseract'] = True
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
    except Exception:
        status['has_pytesseract'] = False

    if status['has_pytesseract'] and status['tesseract_cmd']:
        status['is_fully_ready'] = True
        status['mode'] = 'Automatique (Tesseract)'
        status['message'] = "Moteur OCR Tesseract actif. Les scans (PDF et photos) sont lus automatiquement."
    elif status['has_pypdf']:
        status['is_fully_ready'] = False
        status['mode'] = 'PDF Texte uniquement'
        status['message'] = "Lecture des PDF textuels active. Pour les scans photos (JPG/PNG), installez Tesseract."
    else:
        status['is_fully_ready'] = False
        status['mode'] = 'Saisie assistée'
        status['message'] = "Bibliothèques OCR non détectées dans l'environnement Python."

    return status


def extract_text_from_file_path(file_path: str, document_title: str = "") -> tuple[str, str]:
    """
    Exécute l'extraction OCR directement depuis le fichier présent sur disque.
    Retourne (texte_extrait, message_explication).
    """
    if not file_path or not os.path.exists(file_path):
        return "", "Fichier introuvable sur le disque."

    lower_name = os.path.basename(file_path).lower()
    extracted_text = ""
    tesseract_path = get_tesseract_cmd()

    pytesseract_module = None
    if tesseract_path:
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            pytesseract_module = pytesseract
        except Exception:
            pytesseract_module = None
    else:
        try:
            import pytesseract
            pytesseract_module = pytesseract
        except Exception:
            pytesseract_module = None

    # 1. Traitement des fichiers PDF
    if lower_name.endswith('.pdf'):
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            pages_text = []
            for p in reader.pages[:15]:
                t = p.extract_text()
                if t and t.strip():
                    pages_text.append(t.strip())
            
            if pages_text:
                extracted_text = "\n\n".join(pages_text)
                return extracted_text, f"Succès : {len(extracted_text.split())} mots extraits du document PDF."
            elif pytesseract_module:
                from PIL import Image, ImageOps
                import io
                img_texts = []
                for p in reader.pages[:5]:
                    for img_obj in getattr(p, 'images', []):
                        try:
                            pil_img = Image.open(io.BytesIO(img_obj.data))
                            pil_img = ImageOps.exif_transpose(pil_img)
                            ocr_part = pytesseract_module.image_to_string(pil_img, lang='fra+eng')
                            
                            # Si le texte semble inversé (180°), redressement automatique
                            if ocr_part and any(sig in ocr_part.lower() for sig in ['enoy', 'xnaissa', 'sjourssnod', 'tivavaw', 'jafqa', 'sohpiaomot', 'uosinvuvnviy', 'aanjiuanoy']):
                                rotated = pil_img.rotate(180, expand=True)
                                rotated_text = pytesseract_module.image_to_string(rotated, lang='fra+eng')
                                if rotated_text and len(rotated_text.strip()) > 10:
                                    ocr_part = rotated_text

                            if ocr_part and ocr_part.strip():
                                img_texts.append(ocr_part.strip())
                        except Exception:
                            continue
                if img_texts:
                    extracted_text = "\n\n".join(img_texts)
                    return extracted_text, f"Succès OCR : {len(extracted_text.split())} mots reconnus dans les pages scannées."
                else:
                    return "", "Le PDF est un scan d'images, mais aucun texte lisible n'a pu être extrait."
            else:
                return "", "Ce PDF est une image scannée sans texte numérique. Installez Tesseract pour l'OCR automatique."
        except Exception as e:
            return "", f"Erreur de lecture PDF : {str(e)}"

    # 2. Traitement des images scannées (PNG, JPG, TIFF)
    elif lower_name.endswith(('.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp')):
        if pytesseract_module:
            try:
                from PIL import Image, ImageOps
                img = Image.open(file_path)
                img = ImageOps.exif_transpose(img)
                extracted_text = pytesseract_module.image_to_string(img, lang='fra+eng')
                
                # Auto-détection et redressement transparent si scan à l'envers
                if extracted_text and any(sig in extracted_text.lower() for sig in ['enoy', 'xnaissa', 'sjourssnod', 'tivavaw', 'jafqa', 'sohpiaomot', 'uosinvuvnviy', 'aanjiuanoy']):
                    rotated = img.rotate(180, expand=True)
                    rotated_text = pytesseract_module.image_to_string(rotated, lang='fra+eng')
                    if rotated_text and len(rotated_text.strip()) > 10:
                        extracted_text = rotated_text

                if extracted_text and extracted_text.strip():
                    return extracted_text.strip(), f"Succès OCR : {len(extracted_text.split())} mots reconnus sur l'image scannée."
                else:
                    return "", "L'OCR a analysé l'image mais n'a pas détecté de caractères distincts."
            except Exception as e:
                return "", f"Erreur OCR image : {str(e)}"
        else:
            return "", "Tesseract OCR n'est pas encore installé sur Windows pour reconnaître le texte de cette image."

    return "", "Format de fichier non pris en charge pour l'OCR."
