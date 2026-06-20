"""
config/settings/production.py

Production muhit sozlamalari.

Ishlatilish:
    export DJANGO_SETTINGS_MODULE=config.settings.production
"""

from .base import *  # noqa: F401, F403

DEBUG = False

# ------------------------------------------------------------------
# Xavfsizlik sozlamalari
# ------------------------------------------------------------------

SECURE_HSTS_SECONDS         = 31_536_000   # 1 yil
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD         = True
SECURE_SSL_REDIRECT         = True
SESSION_COOKIE_SECURE       = True
CSRF_COOKIE_SECURE          = True
SECURE_BROWSER_XSS_FILTER   = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS             = "DENY"

# ------------------------------------------------------------------
# Static fayllar (WhiteNoise)
# ------------------------------------------------------------------

MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ------------------------------------------------------------------
# Logging: prod da faylga ham yoziladi
# ------------------------------------------------------------------

LOGGING["handlers"]["file"] = {  # noqa: F405
    "class":     "logging.handlers.RotatingFileHandler",
    "filename":  "/var/log/smarttaxi/app.log",
    "maxBytes":  10 * 1024 * 1024,   # 10 MB
    "backupCount": 5,
    "formatter": "verbose",
}
LOGGING["root"]["handlers"] = ["console", "file"]  # noqa: F405