"""
notifications/urls.py

Bildirishnoma URL marshrutlari.

Asosiy urls.py ga qo'shish:
    path("api/notifications/", include("notifications.urls")),

To'liq URL'lar:
    GET  /api/notifications/       -- O'z xabarlari (IsAuthenticated)
    POST /api/notifications/test/  -- Test xabar (IsAdminUser)
"""

from django.urls import path

from .views import NotificationListView, TestNotificationView

app_name = "notifications"

urlpatterns = [
    path("",      NotificationListView.as_view(),   name="list"),
    path("test/", TestNotificationView.as_view(),   name="test"),
]