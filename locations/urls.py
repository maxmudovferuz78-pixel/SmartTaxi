"""
locations/urls.py

Joylashuv HTTP REST URL marshrutlari.

Asosiy urls.py ga qo'shish:
    path("api/locations/", include("locations.urls")),

WebSocket marshrutlari alohida — config/asgi.py ga qo'shiladi:
    from locations.routing import websocket_urlpatterns

To'liq HTTP URL'lar:
    GET /api/locations/                       -- Barcha aktiv (IsOperator)
    GET /api/locations/me/                    -- O'z joylashuvi (IsDriver)
    GET /api/locations/{driver_id}/           -- Bitta haydovchi (IsOperator)
    GET /api/locations/{driver_id}/history/   -- GPS tarixi (IsOperator)

WebSocket URL'lar:
    ws://host/ws/driver/location/  -- Haydovchi GPS yuboradi
    ws://host/ws/map/              -- Operator xaritani ko'radi
"""

from django.urls import path

from .views import (
    ActiveLocationsView,
    DriverLocationDetailView,
    LocationHistoryView,
    MyLocationView,
)

app_name = "locations"

urlpatterns = [
    path("",                          ActiveLocationsView.as_view(),       name="active-locations"),
    path("me/",                       MyLocationView.as_view(),            name="my-location"),
    path("<int:driver_id>/",          DriverLocationDetailView.as_view(),  name="driver-location"),
    path("<int:driver_id>/history/",  LocationHistoryView.as_view(),       name="location-history"),
]