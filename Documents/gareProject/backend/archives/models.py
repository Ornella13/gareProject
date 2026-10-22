from django.db import models
from django.utils import timezone
import hashlib

class Document(models.Model):
    # Classement principal officiel GARE FCE
    CLASSEMENT_CHOICES = [
        ('01', '01 — Décisions (Décisions de la Direction, décisions administratives)'),
        ('02', '02 — Notes de service (Notes internes, instructions)'),
        ('03', '03 — Chrono interne (Courriers et correspondances internes)'),
        ('04', '04 — Chrono externe (Courriers adressés à des organismes extérieurs)'),
        ('05', '05 — Procès-verbaux (PV de réunion, PV de réception, PV de constat)'),
    ]

    DOC_TYPES = [
        ('DEC', 'Décision de la Direction'),
        ('NDS', 'Note de service interne'),
        ('CHI', 'Chrono interne (Courrier interne)'),
        ('CHE', 'Chrono externe (Courrier extérieur / ARR / DEP)'),
        ('PV', 'Procès-verbal (Réunion, Réception, Constat)'),
    ]

    STATUS_CHOICES = [
        ('scelle', 'Acte Exécutoire Scellé'),
        ('en_cours_validation', 'En cours de validation / Visa'),
        ('archive_definitif', 'Archivage Définitif WORM'),
        ('diffuse', 'Diffusé aux Districts'),
    ]

    FORMAT_CHOICES = [
        ('PDF/A-1b', 'PDF/A-1b (ISO 19005-1)'),
        ('PDF/A-2u', 'PDF/A-2u (Unicode natif)'),
        ('SEDA v2.1', 'SEDA v2.1 (XML Métadonnées)'),
    ]

    classement = models.CharField(
        max_length=2, 
        choices=CLASSEMENT_CHOICES, 
        default='01', 
        verbose_name="N° Classement Principal"
    )
    chrono = models.CharField(max_length=60, unique=True, verbose_name="Chrono Officiel FCE")
    cote = models.CharField(max_length=60, verbose_name="Cote du Registre Central")
    title = models.CharField(max_length=255, verbose_name="Objet & Intitulé Officiel")
    doc_type = models.CharField(max_length=10, choices=DOC_TYPES, default='DEC')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='scelle')
    
    date_acte = models.DateField(default=timezone.now, verbose_name="Date de l'acte original")
    date_reception = models.DateTimeField(null=True, blank=True, verbose_name="Date de réception GARE")
    
    service_emetteur = models.CharField(max_length=120, default="Direction Générale")
    service_destinataire = models.CharField(max_length=120, blank=True, default="", verbose_name="Destinataire")
    signataire_nom = models.CharField(max_length=100, blank=True, null=True, default="")
    signataire_role = models.CharField(max_length=100, blank=True, null=True, default="")
    
    sha256_hash = models.CharField(max_length=64, blank=True, verbose_name="Empreinte SHA-256")
    format_standard = models.CharField(max_length=20, choices=FORMAT_CHOICES, default='PDF/A-1b')
    pages = models.PositiveIntegerField(default=1)
    dua_annees = models.PositiveIntegerField(default=30, verbose_name="Durée Utilité Administrative (ans)")
    magasin_worm = models.CharField(max_length=100, default="Magasin Central : Baie-04 / Casier-12")
    
    confidentialite = models.CharField(max_length=50, default="Public / Réglementaire")
    priorite = models.CharField(max_length=50, default="Normale")
    
    # Fichier original scanné (strictement préservé sans altération)
    fichier_original = models.FileField(
        upload_to='scans/%Y/%m/', 
        null=True, 
        blank=True, 
        verbose_name="Document Scanné Original (PDF / Image)"
    )
    nom_fichier_original = models.CharField(
        max_length=255, 
        blank=True, 
        verbose_name="Nom du fichier original"
    )

    tags = models.CharField(max_length=255, blank=True, help_text="Mots-clés séparés par des virgules")
    ocr_content = models.TextField(blank=True, verbose_name="Contenu textuel OCR pour la recherche")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Document d'Archive FCE"
        verbose_name_plural = "Documents d'Archives FCE"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.chrono} — {self.title[:50]}"

    def compute_sha256(self, raw_bytes: bytes = None) -> str:
        """Calcule ou régénère l'empreinte SHA-256 certifiée."""
        if raw_bytes:
            self.sha256_hash = hashlib.sha256(raw_bytes).hexdigest()
        elif not self.sha256_hash:
            sample_content = f"{self.chrono}:{self.cote}:{self.title}".encode('utf-8')
            self.sha256_hash = hashlib.sha256(sample_content).hexdigest()
        return self.sha256_hash

    @property
    def is_pdf(self) -> bool:
        """Indique si le fichier original scanné est un PDF."""
        if bool(self.fichier_original):
            name = (self.nom_fichier_original or self.fichier_original.name or "").lower()
            return name.endswith('.pdf')
        return False

    def save(self, *args, **kwargs):
        if not self.sha256_hash:
            self.compute_sha256()
        super().save(*args, **kwargs)


class BordereauVersement(models.Model):
    numero_bordereau = models.CharField(max_length=50, unique=True, verbose_name="N° de Bordereau (ex: BV-2026-FCE-089)")
    service_versant = models.CharField(max_length=120, default="Direction Générale / Voies & Bâtiments (DVB)")
    responsable_versant = models.CharField(max_length=100, default="Jean-Paul R., Secrétaire Général FCE")
    service_destinataire = models.CharField(max_length=120, default="Dépôt Central des Archives")
    localisation_worm = models.CharField(max_length=100, default="Magasin Optique WORM — Baie 04 / Rayon 12")
    date_versement = models.DateTimeField(default=timezone.now)
    statut_conservation = models.CharField(max_length=80, default="Versement définitif sous scellement probant")
    
    # Visas
    visa_dg_approuve = models.BooleanField(default=True)
    visa_dg_date = models.DateTimeField(default=timezone.now)
    visa_archiviste_date = models.DateTimeField(default=timezone.now)
    visa_magasinier_pris_en_charge = models.BooleanField(default=True)

    documents = models.ManyToManyField(Document, related_name="bordereaux", verbose_name="Articles Versés")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bordereau de Versement DAF-04/B"
        verbose_name_plural = "Bordereaux de Versement DAF-04/B"

    def __str__(self):
        return f"{self.numero_bordereau} ({self.service_versant})"


class CertificatHorodatageRFC3161(models.Model):
    document = models.OneToOneField(Document, on_delete=models.CASCADE, related_name="certificat_rfc3161")
    tsa_authority = models.CharField(max_length=100, default="TSA-FCE-PKI-ROOT-CA")
    policy_oid = models.CharField(max_length=100, default="1.3.6.1.4.1.58923.1.2.1")
    gen_time_utc = models.DateTimeField(default=timezone.now)
    gen_time_local = models.CharField(max_length=60, default="24/03/2026 13:19:14 (UTC+3)")
    signature_algorithm = models.CharField(max_length=50, default="SHA256withRSA")
    key_size = models.PositiveIntegerField(default=4096)
    serial_number_hex = models.CharField(max_length=50, default="0x7F4A-98C2-FCE-0015")
    tst_token_data = models.TextField(verbose_name="Jeton ASN.1 DER (.TST)")
    is_valid = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Certificat d'Horodatage RFC 3161"
        verbose_name_plural = "Certificats d'Horodatage RFC 3161"

    def __str__(self):
        return f"Jeton RFC 3161 — {self.document.chrono}"


class VisaValidation(models.Model):
    DECISION_CHOICES = [
        ('approved', 'Approuvé & Scellé'),
        ('reserved', 'Visé avec réserves'),
        ('rejected', 'Rejeté / Retour émetteur'),
    ]

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="visas")
    signataire_nom = models.CharField(max_length=100)
    signataire_role = models.CharField(max_length=100)
    decision = models.CharField(max_length=20, choices=DECISION_CHOICES, default='approved')
    notes = models.TextField(blank=True)
    pin_verified = models.BooleanField(default=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Visa de Conformité"
        verbose_name_plural = "Visas de Conformité"


class JournalAudit(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, null=True, blank=True, related_name="audits")
    action = models.CharField(max_length=80)
    actor = models.CharField(max_length=100)
    details = models.CharField(max_length=255)
    status = models.CharField(max_length=20, default="success")
    timestamp = models.DateTimeField(default=timezone.now)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = "Journal d'Audit Système"
        verbose_name_plural = "Journaux d'Audit Système"
        ordering = ['-timestamp']
