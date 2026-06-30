"""
config/urls.py

SmartTaxi asosiy URL yo'naltiruvchi.

API hujjatlari:
    Swagger UI:  /api/docs/
    ReDoc:       /api/redoc/
    OpenAPI JSON:/api/schema/
"""

from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    # Django admin
    path('', include('smarttaxi.urls')),
    path("admin/", admin.site.urls),

    # ------------------------------------------------------------------
    # API hujjatlari (Swagger / ReDoc)
    # ------------------------------------------------------------------
    # OpenAPI 3.0 schema (JSON)
    path("api/schema/",  SpectacularAPIView.as_view(),                             name="schema"),
    # Swagger UI:  http://localhost:8000/api/docs/
    path("api/docs/",    SpectacularSwaggerView.as_view(url_name="schema"),        name="swagger-ui"),
    # ReDoc:       http://localhost:8000/api/redoc/
    path("api/redoc/",   SpectacularRedocView.as_view(url_name="schema"),          name="redoc"),

    # ------------------------------------------------------------------
    # App URL lari
    # ------------------------------------------------------------------
    path("api/auth/",          include("accounts.urls",      namespace="accounts")),
    path("api/drivers/",       include("drivers.urls",       namespace="drivers")),
    path("api/orders/",        include("orders.urls",        namespace="orders")),
    path("api/tariffs/",       include("tariffs.urls",       namespace="tariffs")),
    path("api/wallet/",        include("wallet.urls",        namespace="wallet")),
    path("api/payments/",      include("payments.urls",      namespace="payments")),
    path("api/locations/",     include("locations.urls",     namespace="locations")),
    path("api/notifications/", include("notifications.urls", namespace="notifications")),
]

# Dev muhitda media va static fayllarni serve qilish
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,  document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)