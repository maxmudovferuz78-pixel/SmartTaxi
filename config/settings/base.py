"""
config/settings/base.py

Barcha muhitlar uchun umumiy sozlamalar.
dev.py va prod.py shu fayldan voris oladi.

Muhim o'zgaruvchilar .env faylidan o'qiladi (python-decouple).
"""

from pathlib import Path
from decouple import config, Csv
from datetime import timedelta

# Loyiha ildizi: 1177_smarttaxi/
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ------------------------------------------------------------------
# Xavfsizlik
# ------------------------------------------------------------------

SECRET_KEY = config("SECRET_KEY")
ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv(), default="127.0.0.1,localhost")

# ------------------------------------------------------------------
# Ilovalar
# ------------------------------------------------------------------

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "channels",
    "django_celery_beat",
    "django_celery_results",
    "corsheaders",
    "drf_spectacular",
]

LOCAL_APPS = [
    "accounts",
    "drivers",
    "orders",
    "tariffs",
    "wallet",
    "payments",
    "locations",
    "notifications",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ------------------------------------------------------------------
# Middleware
# ------------------------------------------------------------------

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION  = "config.asgi.application"

# ------------------------------------------------------------------
# Templates
# ------------------------------------------------------------------

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ------------------------------------------------------------------
# Ma'lumotlar bazasi
# ------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE":   "django.db.backends.postgresql",
        "NAME":     config("DB_NAME",     default="smarttaxi_db"),
        "USER":     config("DB_USER",     default="smarttaxi_user"),
        "PASSWORD": config("DB_PASSWORD", default=""),
        "HOST":     config("DB_HOST",     default="localhost"),
        "PORT":     config("DB_PORT",     default="5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {
            "connect_timeout": 10,
        },
    }
}

# ------------------------------------------------------------------
# Foydalanuvchi modeli
# ------------------------------------------------------------------

AUTH_USER_MODEL = "accounts.User"

# ------------------------------------------------------------------
# Password validators
# ------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ------------------------------------------------------------------
# Internatsionalizatsiya
# ------------------------------------------------------------------

LANGUAGE_CODE = "uz-uz"
TIME_ZONE     = "Asia/Tashkent"
USE_I18N      = True
USE_TZ        = True

# ------------------------------------------------------------------
# Statik va media fayllar
# ------------------------------------------------------------------

STATIC_URL  = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL   = "/media/"
MEDIA_ROOT  = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------------------------------------------
# Django REST Framework
# ------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/minute",
        "user": "200/minute",
    },
    "EXCEPTION_HANDLER": "rest_framework.views.exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# ------------------------------------------------------------------
# drf-spectacular (Swagger / OpenAPI 3.0)
# ------------------------------------------------------------------

SPECTACULAR_SETTINGS = {
    "TITLE":       "SmartTaxi API",
    "DESCRIPTION": (
        "SmartTaxi — O'zbekiston taxi xizmati uchun backend API.\n\n"
        "## Autentifikatsiya\n"
        "1. `POST /api/auth/send-otp/` — telefon raqam yuboring\n"
        "2. `POST /api/auth/verify-otp/` — kodni tasdiqlang → `access` token oling\n"
        "3. Har so'rovda header qo'shing: `Authorization: Bearer <access_token>`\n\n"
        "## Rollar\n"
        "- **admin** — barcha endpointlarga kirish\n"
        "- **operator** — buyurtma va haydovchi boshqaruvi\n"
        "- **driver** — o'z profili, GPS, hamyon\n"
        "- **client** — buyurtma berish (keyinchalik)\n"
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_SETTINGS": {
        "deepLinking":              True,
        "persistAuthorization":     True,
        "displayOperationId":       False,
        "defaultModelsExpandDepth": 2,
        "defaultModelExpandDepth":  2,
        "docExpansion":             "none",   # Collapsed holda ochiladi
        "filter":                   True,     # Endpointlarni qidirish
    },
    "COMPONENT_SPLIT_REQUEST": True,
    "SORT_OPERATIONS": False,
    "TAGS": [
        {"name": "auth",          "description": "Autentifikatsiya (OTP + JWT)"},
        {"name": "drivers",       "description": "Haydovchi boshqaruvi"},
        {"name": "orders",        "description": "Buyurtmalar va billing"},
        {"name": "tariffs",       "description": "Tarif jadvali va narx hisoblash"},
        {"name": "wallet",        "description": "Virtual hamyon"},
        {"name": "payments",      "description": "To'lov tizimlari (Payme, Click)"},
        {"name": "locations",     "description": "GPS joylashuv (HTTP REST)"},
        {"name": "notifications", "description": "SMS, Push, Telegram xabarlari"},
    ],
}

# ------------------------------------------------------------------
# SimpleJWT
# ------------------------------------------------------------------

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":  timedelta(minutes=config("JWT_ACCESS_MINUTES",  cast=int, default=60)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=config("JWT_REFRESH_DAYS",       cast=int, default=30)),
    "ROTATE_REFRESH_TOKENS":  True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "UPDATE_LAST_LOGIN": True,
}

# ------------------------------------------------------------------
# Redis
# ------------------------------------------------------------------

REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")

# ------------------------------------------------------------------
# Celery
# ------------------------------------------------------------------

CELERY_BROKER_URL            = REDIS_URL
CELERY_RESULT_BACKEND        = config("CELERY_RESULT_BACKEND", default="django-db")
CELERY_ACCEPT_CONTENT        = ["json"]
CELERY_TASK_SERIALIZER       = "json"
CELERY_RESULT_SERIALIZER     = "json"
CELERY_TIMEZONE              = TIME_ZONE
CELERY_TASK_TRACK_STARTED    = True
CELERY_TASK_TIME_LIMIT       = 300        # 5 daqiqa maksimal
CELERY_TASK_SOFT_TIME_LIMIT  = 240

# Celery Beat jadvali
from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    # LocationHistory: har kecha soat 3:00 da 7 kundan eskisini o'chirish
    "clean_location_history": {
        "task":     "locations.tasks.clean_location_history",
        "schedule": crontab(hour=3, minute=0),
    },
}

# ------------------------------------------------------------------
# Django Channels (WebSocket)
# ------------------------------------------------------------------

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG":  {"hosts": [REDIS_URL]},
    }
}

# ------------------------------------------------------------------
# Cache
# ------------------------------------------------------------------

CACHES = {
    "default": {
        "BACKEND":  "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "TIMEOUT":  300,
        "KEY_PREFIX": "smarttaxi",
    }
}

# ------------------------------------------------------------------
# CORS
# ------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    cast=Csv(),
    default="http://localhost:3000,http://127.0.0.1:3000",
)
CORS_ALLOW_CREDENTIALS = True

# ------------------------------------------------------------------
# To'lov tizimlari
# ------------------------------------------------------------------

# Payme
PAYME_MERCHANT_ID = config("PAYME_MERCHANT_ID", default="")
PAYME_KEY         = config("PAYME_KEY",         default="")

# Click
CLICK_SERVICE_ID  = config("CLICK_SERVICE_ID",  default="")
CLICK_MERCHANT_ID = config("CLICK_MERCHANT_ID", default="")
CLICK_SECRET_KEY  = config("CLICK_SECRET_KEY",  default="")

# Uzum
UZUM_MERCHANT_ID  = config("UZUM_MERCHANT_ID",  default="")

# ------------------------------------------------------------------
# Xabar yuborish
# ------------------------------------------------------------------

SMS_BACKEND          = config("SMS_BACKEND", default="console")
ESKIZ_TOKEN          = config("ESKIZ_TOKEN", default="")
ESKIZ_FROM           = config("ESKIZ_FROM",  default="4546")
PLAYMOBILE_LOGIN     = config("PLAYMOBILE_LOGIN",    default="")
PLAYMOBILE_PASSWORD  = config("PLAYMOBILE_PASSWORD", default="")

FCM_SERVER_KEY       = config("FCM_SERVER_KEY",      default="")
TELEGRAM_BOT_TOKEN   = config("TELEGRAM_BOT_TOKEN",  default="")

# ------------------------------------------------------------------
# Yandex Maps (keyinchalik)
# ------------------------------------------------------------------

YANDEX_MAPS_API_KEY  = config("YANDEX_MAPS_API_KEY", default="")

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {message}",
            "style":  "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style":  "{",
        },
    },
    "handlers": {
        "console": {
            "class":     "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level":    "INFO",
    },
    "loggers": {
        "django": {
            "handlers":  ["console"],
            "level":     "WARNING",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers":  ["console"],
            "level":     "WARNING",
            "propagate": False,
        },
    },
}