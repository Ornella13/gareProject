from django import forms
from django.db.models import Q
from .models import Document
from django.utils import timezone

class SimpleSecretaryUploadForm(forms.ModelForm):
    """
    Formulaire ultra-simple spécialement conçu pour les secrétaires.
    Demande uniquement : Catégorie, Document scanné, Objet/Titre, Date et Émetteur/Destinataire.
    Objet et destinataire restent vides par défaut.
    """
    service_destinataire = forms.CharField(
        required=False, 
        initial="", 
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-white border border-[#c4c6ce] rounded-lg px-3.5 py-2.5 text-sm text-[#001229] focus:ring-2 focus:ring-[#0051d5] focus:outline-none',
            'placeholder': 'Destinataire (laisser vide ou renseigner)'
        })
    )

    class Meta:
        model = Document
        fields = [
            'classement',
            'fichier_original',
            'title',
            'date_acte',
            'chrono',
            'service_emetteur',
            'service_destinataire',
            'ocr_content'
        ]
        widgets = {
            'classement': forms.Select(attrs={
                'class': 'w-full bg-[#f8f9ff] border border-[#c4c6ce] rounded-lg px-3.5 py-2.5 text-sm font-bold text-[#001229] focus:ring-2 focus:ring-[#0051d5] focus:outline-none'
            }),
            'fichier_original': forms.ClearableFileInput(attrs={
                'class': 'hidden',
                'id': 'file_upload_input',
                'accept': '.pdf,image/png,image/jpeg,image/jpg'
            }),
            'title': forms.TextInput(attrs={
                'class': 'w-full bg-white border border-[#c4c6ce] rounded-lg px-3.5 py-2.5 text-sm text-[#001229] focus:ring-2 focus:ring-[#0051d5] focus:outline-none placeholder:text-gray-400',
                'placeholder': 'Objet / Intitulé du document (laisser vide par défaut)'
            }),
            'date_acte': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full bg-white border border-[#c4c6ce] rounded-lg px-3.5 py-2.5 text-sm text-[#001229] focus:ring-2 focus:ring-[#0051d5] focus:outline-none'
            }),
            'chrono': forms.TextInput(attrs={
                'class': 'w-full bg-white border border-[#c4c6ce] rounded-lg px-3.5 py-2.5 text-sm font-mono font-bold text-[#0051d5] focus:ring-2 focus:ring-[#0051d5] focus:outline-none',
                'placeholder': 'Laisser vide pour génération automatique du numéro de l\'année'
            }),
            'service_emetteur': forms.TextInput(attrs={
                'class': 'w-full bg-white border border-[#c4c6ce] rounded-lg px-3.5 py-2.5 text-sm text-[#001229] focus:ring-2 focus:ring-[#0051d5] focus:outline-none',
                'placeholder': 'Ex : Direction Générale'
            }),
            'ocr_content': forms.Textarea(attrs={
                'class': 'w-full bg-white border border-[#c4c6ce] rounded-lg px-3.5 py-2.5 text-xs text-[#001229] focus:ring-2 focus:ring-[#0051d5] focus:outline-none font-sans h-28 placeholder:text-gray-400 leading-relaxed',
                'placeholder': 'Texte extrait pour la recherche'
            }),
        }

    def clean_chrono(self):
        chrono = self.cleaned_data.get('chrono')
        classement = self.cleaned_data.get('classement', '01')
        date_acte = self.cleaned_data.get('date_acte') or timezone.now().date()
        doc_year = date_acte.year
        prefix_map = {
            '01': 'FCE/DG/DEC',
            '02': 'FCE/DG/NDS',
            '03': 'FCE/CHI',
            '04': 'FCE/CHE',
            '05': 'FCE/PV/DVB'
        }
        prefix = prefix_map.get(classement, 'FCE/DOC')
        if not chrono:
            try:
                # Le numéro séquentiel se réinitialise à 001 à chaque nouvelle année pour chaque catégorie
                year_count = Document.objects.filter(
                    classement=classement
                ).filter(
                    Q(chrono__icontains=f"/{doc_year}/") | Q(date_acte__year=doc_year)
                ).count() + 1
                chrono = f"{prefix}/{doc_year}/{year_count:03d}"
                while Document.objects.filter(chrono=chrono).exists():
                    year_count += 1
                    chrono = f"{prefix}/{doc_year}/{year_count:03d}"
            except Exception:
                chrono = f"{prefix}/{doc_year}/001"
        else:
            if not self.instance.pk and Document.objects.filter(chrono=chrono).exists():
                raise forms.ValidationError(f"Le numéro chrono « {chrono} » est déjà utilisé. Veuillez en choisir un autre ou laisser vide pour attribution automatique.")
        return chrono


class DocumentForm(forms.ModelForm):
    """Formulaire complet d'archivage (avec options avancées)."""
    class Meta:
        model = Document
        fields = [
            'classement',
            'fichier_original',
            'chrono',
            'cote',
            'title',
            'doc_type',
            'status',
            'date_acte',
            'service_emetteur',
            'service_destinataire',
            'format_standard',
            'pages',
            'dua_annees',
            'magasin_worm',
            'confidentialite',
            'priorite',
            'ocr_content',
        ]
        widgets = {
            'classement': forms.Select(attrs={
                'class': 'w-full bg-white border border-[#c4c6ce] rounded px-3 py-2 text-xs font-semibold text-[#001229] focus:ring-1 focus:ring-[#0051d5] focus:outline-none'
            }),
            'fichier_original': forms.ClearableFileInput(attrs={
                'class': 'w-full text-xs text-[#001229]'
            }),
            'chrono': forms.TextInput(attrs={
                'class': 'w-full bg-white border border-[#c4c6ce] rounded px-3 py-2 text-xs font-mono font-bold text-[#0051d5] focus:ring-1 focus:ring-[#0051d5] focus:outline-none',
                'placeholder': 'Ex: FCE/DG/DEC/2026/001'
            }),
            'cote': forms.TextInput(attrs={
                'class': 'w-full bg-white border border-[#c4c6ce] rounded px-3 py-2 text-xs font-mono text-[#001229] focus:ring-1 focus:ring-[#0051d5] focus:outline-none',
                'placeholder': 'Ex: ARC-2026-REG-0019'
            }),
            'title': forms.TextInput(attrs={
                'class': 'w-full bg-white border border-[#c4c6ce] rounded px-3 py-2 text-xs text-[#001229] focus:ring-1 focus:ring-[#0051d5] focus:outline-none',
                'placeholder': 'Objet ou intitulé officiel de l\'acte'
            }),
            'doc_type': forms.Select(attrs={
                'class': 'w-full bg-white border border-[#c4c6ce] rounded px-3 py-2 text-xs text-[#001229] focus:ring-1 focus:ring-[#0051d5] focus:outline-none'
            }),
            'status': forms.Select(attrs={
                'class': 'w-full bg-white border border-[#c4c6ce] rounded px-3 py-2 text-xs text-[#001229] focus:ring-1 focus:ring-[#0051d5] focus:outline-none'
            }),
            'date_acte': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full bg-white border border-[#c4c6ce] rounded px-3 py-2 text-xs text-[#001229] focus:ring-1 focus:ring-[#0051d5] focus:outline-none'
            }),
            'service_emetteur': forms.TextInput(attrs={
                'class': 'w-full bg-white border border-[#c4c6ce] rounded px-3 py-2 text-xs text-[#001229] focus:ring-1 focus:ring-[#0051d5] focus:outline-none',
                'placeholder': 'Direction Générale, Direction Voies & Bâtiments...'
            }),
            'service_destinataire': forms.TextInput(attrs={
                'class': 'w-full bg-white border border-[#c4c6ce] rounded px-3 py-2 text-xs text-[#001229] focus:ring-1 focus:ring-[#0051d5] focus:outline-none',
                'placeholder': 'Ex : Direction Générale, Service Technique, Archives...'
            }),
            'format_standard': forms.Select(attrs={
                'class': 'w-full bg-white border border-[#c4c6ce] rounded px-3 py-2 text-xs text-[#001229] focus:ring-1 focus:ring-[#0051d5] focus:outline-none'
            }),
            'pages': forms.NumberInput(attrs={
                'class': 'w-full bg-white border border-[#c4c6ce] rounded px-3 py-2 text-xs text-[#001229] focus:ring-1 focus:ring-[#0051d5] focus:outline-none',
                'min': 1
            }),
            'dua_annees': forms.NumberInput(attrs={
                'class': 'w-full bg-white border border-[#c4c6ce] rounded px-3 py-2 text-xs text-[#001229] focus:ring-1 focus:ring-[#0051d5] focus:outline-none',
                'min': 1
            }),
            'magasin_worm': forms.TextInput(attrs={
                'class': 'w-full bg-white border border-[#c4c6ce] rounded px-3 py-2 text-xs text-[#001229] focus:ring-1 focus:ring-[#0051d5] focus:outline-none'
            }),
            'confidentialite': forms.TextInput(attrs={
                'class': 'w-full bg-white border border-[#c4c6ce] rounded px-3 py-2 text-xs text-[#001229] focus:ring-1 focus:ring-[#0051d5] focus:outline-none'
            }),
            'priorite': forms.TextInput(attrs={
                'class': 'w-full bg-white border border-[#c4c6ce] rounded px-3 py-2 text-xs text-[#001229] focus:ring-1 focus:ring-[#0051d5] focus:outline-none'
            }),
            'ocr_content': forms.Textarea(attrs={
                'class': 'w-full bg-white border border-[#c4c6ce] rounded px-3 py-2 text-xs text-[#001229] focus:ring-1 focus:ring-[#0051d5] focus:outline-none h-24 font-mono',
                'placeholder': 'Texte intégral extrait pour la recherche...'
            }),
        }
