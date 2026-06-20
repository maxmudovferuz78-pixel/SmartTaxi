"""
config/wsgi.py

WSGI konfiguratsiyasi (Gunicorn uchun, HTTP only).
WebSocket uchun asgi.py ishlatiladi.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.development",
)

application = get_wsgi_application()