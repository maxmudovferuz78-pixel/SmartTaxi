"""
tariffs/urls.py

Tarif URL marshrutlari.

Asosiy urls.py ga qo'shish:
    path("api/tariffs/", include("tariffs.urls")),

To'liq URL'lar:
    GET    /api/tariffs/              -- Ro'yxat (IsAuthenticated)
    POST   /api/tariffs/              -- Yaratish (IsAdminUser)
    GET    /api/tariffs/{id}/         -- Batafsil (IsAuthenticated)
    PATCH  /api/tariffs/{id}/         -- Yangilash (IsAdminUser)
    DELETE /api/tariffs/{id}/         -- Faolsizlashtirish (IsAdminUser)
    POST   /api/tariffs/calculate/    -- Narx hisoblash (IsAuthenticated)
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TariffViewSet

app_name = "tariffs"

router = DefaultRouter()
router.register(r"", TariffViewSet, basename="tariff")

urlpatterns = [
    path("", include(router.urls)),
]