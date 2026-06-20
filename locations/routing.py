"""
locations/routing.py

WebSocket URL marshrutlari.

config/asgi.py ga qo'shish:
    from locations.routing import websocket_urlpatterns

    application = ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": JWTAuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        ),
    })

WebSocket URL'lar:
    ws://host/ws/driver/location/  -- Haydovchi GPS yuboradi
    ws://host/ws/map/              -- Operator xaritani ko'radi
"""

from django.urls import path

from .consumers import DriverLocationConsumer, MapConsumer

websocket_urlpatterns = [
    path("ws/driver/location/", DriverLocationConsumer.as_asgi()),
    path("ws/map/",             MapConsumer.as_asgi()),
]