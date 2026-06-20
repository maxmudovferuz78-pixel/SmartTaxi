"""
drivers/urls.py

Haydovchi URL marshrutlari.

Asosiy urls.py ga qo'shish:
    path("api/drivers/", include("drivers.urls")),

To'liq URL'lar:
    POST   /api/drivers/                    -- Yangi haydovchi (IsOperator)
    GET    /api/drivers/                    -- Ro'yxat (IsOperator)
    GET    /api/drivers/{id}/               -- Batafsil (IsOperator)
    PATCH  /api/drivers/{id}/               -- Yangilash (IsOperator)
    GET    /api/drivers/me/                 -- O'z profili (IsDriver)
    PATCH  /api/drivers/me/status/          -- Onlayn/offline (IsDriver)
    PATCH  /api/drivers/me/profile/         -- Mashina ma'lumotlari (IsDriver)
    PATCH  /api/drivers/{id}/toggle_active/ -- Bloklash (IsOperator)
    GET    /api/drivers/nearby/             -- Yaqin haydovchilar (IsOperator)

Eslatma:
    'me/', 'me/status/', 'nearby/' — detail=False actionlar
    router.urls dan OLDIN qo'yilishi kerak, aks holda Django
    'me' ni {id} deb tushunib xato qaytaradi.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DriverViewSet

app_name = "drivers"

router = DefaultRouter()
router.register(r"", DriverViewSet, basename="driver")

urlpatterns = [
    path("", include(router.urls)),
]