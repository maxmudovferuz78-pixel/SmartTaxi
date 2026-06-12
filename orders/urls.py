"""
orders/urls.py

Buyurtma URL marshrutlari.

Asosiy urls.py ga qo'shish:
    path("api/orders/", include("orders.urls")),

To'liq URL'lar:
    POST   /api/orders/                        -- Yangi buyurtma
    GET    /api/orders/                        -- Ro'yxat
    GET    /api/orders/{id}/                   -- Batafsil
    PUT    /api/orders/{id}/                   -- To'liq yangilash
    PATCH  /api/orders/{id}/                   -- Qisman yangilash
    DELETE /api/orders/{id}/                   -- O'chirish
    PATCH  /api/orders/{id}/set_status/        -- Status FSM (haydovchi)
    PATCH  /api/orders/{id}/assign_driver/     -- Haydovchi biriktirish (operator)
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import OrderViewSet

app_name = "orders"

router = DefaultRouter()
router.register(r"", OrderViewSet, basename="order")

urlpatterns = [
    path("", include(router.urls)),
]