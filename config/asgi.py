"""
config/asgi.py

ASGI konfiguratsiyasi — HTTP va WebSocket protokollarini boshqaradi.

Django Channels ProtocolTypeRouter:
    http      -> Django standart HTTP handler
    websocket -> JWTAuthMiddlewareStack + URLRouter
                 (locations.routing.websocket_urlpatterns)

Ishlatilish:
    Daphne: daphne -b 0.0.0.0 -p 8000 config.asgi:application
    Uvicorn: uvicorn config.asgi:application --host 0.0.0.0 --port 8000
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.development",
)

# Django ASGI ilovasini oldindan yuklash (import ordering muhim)
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

from locations.middleware import JWTAuthMiddlewareStack  # noqa: E402
from locations.routing import websocket_urlpatterns       # noqa: E402

application = ProtocolTypeRouter({
    # Oddiy HTTP so'rovlar
    "http": django_asgi_app,

    # WebSocket so'rovlar
    # AllowedHostsOriginValidator: ALLOWED_HOSTS dan tashqaridan kelgan
    # WebSocket ulanishlarini rad etadi (CSRF ekvivalenti)
    "websocket": AllowedHostsOriginValidator(
        JWTAuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})