from rest_framework import serializers
from .models import Document, BordereauVersement, CertificatHorodatageRFC3161, VisaValidation, JournalAudit

class CertificatHorodatageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CertificatHorodatageRFC3161
        fields = '__all__'


class VisaValidationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisaValidation
        fields = '__all__'


class JournalAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalAudit
        fields = '__all__'


class DocumentSerializer(serializers.ModelSerializer):
    certificat_rfc3161 = CertificatHorodatageSerializer(read_only=True)
    visas = VisaValidationSerializer(many=True, read_only=True)
    audits = JournalAuditSerializer(many=True, read_only=True)

    class Meta:
        model = Document
        fields = '__all__'


class BordereauVersementSerializer(serializers.ModelSerializer):
    documents = DocumentSerializer(many=True, read_only=True)

    class Meta:
        model = BordereauVersement
        fields = '__all__'
