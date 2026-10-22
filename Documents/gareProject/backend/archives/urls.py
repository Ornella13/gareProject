from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DocumentViewSet, 
    BordereauVersementViewSet, 
    ExportZipBundleView,
    dynamic_seal_image_view,
    dynamic_arrival_stamp_image_view
)

router = DefaultRouter()
router.register(r'documents', DocumentViewSet, basename='document')
router.register(r'bordereaux', BordereauVersementViewSet, basename='bordereau')

urlpatterns = [
    # Bundle download endpoint (Écran 1)
    path('export/bundle/<str:chrono>/', ExportZipBundleView.as_view(), name='export-zip-bundle'),
    
    # Liens dynamiques vers des images à partir de HTML / SVG
    path('images/seal.svg', dynamic_seal_image_view, name='dynamic-seal-image'),
    path('images/stamp.svg', dynamic_arrival_stamp_image_view, name='dynamic-stamp-image'),
] + router.urls
