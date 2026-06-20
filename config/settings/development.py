"""
config/settings/development.py

Development (mahalliy) muhit sozlamalari.

Ishlatilish:
    export DJANGO_SETTINGS_MODULE=config.settings.development
    yoki manage.py --settings=config.settings.development
"""


from .base import *  # noqa: F401, F403

DEBUG = True

# Dev da barcha hostlarga ruxsat
ALLOWED_HOSTS = ["*"]

# ------------------------------------------------------------------
# Dev qo'shimcha ilovalar
# ------------------------------------------------------------------

INSTALLED_APPS += [  # noqa: F405
    "django_extensions",
]

# ------------------------------------------------------------------
# Dev SMS: terminalga print
# ------------------------------------------------------------------

SMS_BACKEND = "console"

# ------------------------------------------------------------------
# Oddiyroq parol tekshiruvi (dev uchun)
# ------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = []

# ------------------------------------------------------------------
# Django Channels: in-memory (Redis kerak emas, dev uchun)
# ------------------------------------------------------------------

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

# ------------------------------------------------------------------
# Cache: locmem (Redis kerak emas)
# ------------------------------------------------------------------

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# ------------------------------------------------------------------
# CORS: dev da hamma originga ruxsat
# ------------------------------------------------------------------

CORS_ALLOW_ALL_ORIGINS = True

# ------------------------------------------------------------------
# SQL querylarni logga yozish
# ------------------------------------------------------------------

LOGGING["loggers"]["django.db.backends"] = {  # noqa: F405
    "handlers":  ["console"],
    "level":     "DEBUG",
    "propagate": False,
}