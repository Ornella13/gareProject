from django.contrib import admin
from .models import Document, BordereauVersement, CertificatHorodatageRFC3161, VisaValidation, JournalAudit

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('classement', 'chrono', 'cote', 'title', 'doc_type', 'status', 'service_destinataire', 'dua_annees', 'created_at')
    list_filter = ('classement', 'doc_type', 'status', 'format_standard', 'dua_annees')
    search_fields = ('chrono', 'cote', 'title', 'sha256_hash', 'ocr_content')
    readonly_fields = ('sha256_hash', 'created_at', 'updated_at')


@admin.register(BordereauVersement)
class BordereauVersementAdmin(admin.ModelAdmin):
    list_display = ('numero_bordereau', 'service_versant', 'service_destinataire', 'date_versement', 'visa_dg_approuve')
    filter_horizontal = ('documents',)


@admin.register(CertificatHorodatageRFC3161)
class CertificatHorodatageAdmin(admin.ModelAdmin):
    list_display = ('document', 'tsa_authority', 'gen_time_utc', 'signature_algorithm', 'is_valid')


@admin.register(VisaValidation)
class VisaValidationAdmin(admin.ModelAdmin):
    list_display = ('document', 'signataire_nom', 'decision', 'timestamp')


@admin.register(JournalAudit)
class JournalAuditAdmin(admin.ModelAdmin):
    list_display = ('action', 'document', 'actor', 'timestamp', 'status')
    list_filter = ('action', 'status')
