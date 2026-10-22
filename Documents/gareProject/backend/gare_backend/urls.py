from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.utils import staticfiles_urlpatterns
from archives.views import (
    dashboard_view,
    document_list_view,
    document_create_view,
    document_detail_view,
    document_update_view,
    document_delete_view,
    export_bordereau_view,
    decision_viewer_view,
    incoming_detail_view,
    register_view,
    document_download_original_view,
    document_preview_file_view,
    audit_trail_view,
    ocr_search_view,
    favicon_view,
    fce_logo_view,
    save_document_ocr_view,
    reprocess_document_ocr_view
)

# Personnalisation de l'interface d'administration Django FCE
admin.site.site_header = "GARE — Système d'Archivage FCE"
admin.site.site_title = "GARE FCE Admin"
admin.site.index_title = "Gestion des Actes, Décisions et Liasses Scellées WORM"

urlpatterns = [
    # Icône et Logo FCE (résout immédiatement les 404 du navigateur et terminal)
    path('favicon.ico', favicon_view, name='favicon'),
    path('logo-fce/', fce_logo_view, name='fce_logo'),
    path('fce-logo.jpg', fce_logo_view, name='fce_logo_root'),
    path('static/fce-logo.jpg', fce_logo_view, name='fce_logo_jpg'),
    path('static/fce-logo.png', fce_logo_view, name='fce_logo_png'),
    # Pages HTML Django + Tailwind CSS
    path('', dashboard_view, name='dashboard'),
    path('registre/', document_list_view, name='document_list'),
    path('register/', document_list_view, name='register'),
    path('recherche-ocr/', ocr_search_view, name='ocr_search'),
    path('tracabilite/', audit_trail_view, name='audit_trail'),
    path('audit/', audit_trail_view, name='audit'),
    path('documents/nouveau/', document_create_view, name='document_create'),
    path('documents/<int:pk>/', document_detail_view, name='document_detail'),
    path('documents/<int:pk>/apercu/', document_preview_file_view, name='document_preview_file'),
    path('documents/<int:pk>/telecharger-original/', document_download_original_view, name='document_download_original'),
    path('documents/<int:pk>/modifier/', document_update_view, name='document_update'),
    path('documents/<int:pk>/sauvegarder-ocr/', save_document_ocr_view, name='save_document_ocr'),
    path('documents/<int:pk>/relancer-ocr/', reprocess_document_ocr_view, name='reprocess_document_ocr'),
    path('documents/<int:pk>/supprimer/', document_delete_view, name='document_delete'),

    # Les 3 Écrans Clés
    path('bordereau/', export_bordereau_view, name='export_bordereau'),
    path('decision/015/', decision_viewer_view, name='decision_viewer'),
    path('document/042/', incoming_detail_view, name='incoming_detail'),

    # Django Admin
    path('admin/', admin.site.urls),

    # API REST & Images Dynamiques
    path('api/', include('archives.urls')),
]
    urlpatterns += staticfiles_urlpatterns()
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / 'static')

