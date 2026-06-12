"""
accounts/urls.py

Autentifikatsiya va profil URL marshrutlari.

Asosiy urls.py ga qo'shish:
    path("api/auth/", include("accounts.urls")),

To'liq URL'lar:
    POST /api/auth/send-otp/           — OTP yuborish
    POST /api/auth/verify-otp/         — OTP tekshirish → JWT qaytaradi
    POST /api/auth/token/refresh/      — Access tokenni yangilash (SimpleJWT)
    POST /api/auth/token/blacklist/    — Refresh tokenni bekor qilish (logout)
    GET  /api/auth/me/                 — Joriy profil
    PUT  /api/auth/me/                 — Profilni yangilash
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenBlacklistView, TokenRefreshView

from .views import MeView, SendOTPView, VerifyOTPView

app_name = "accounts"

urlpatterns = [
    # --- OTP autentifikatsiya ---
    path(
        "send-otp/",
        SendOTPView.as_view(),
        name="send-otp",
    ),
    path(
        "verify-otp/",
        VerifyOTPView.as_view(),
        name="verify-otp",
    ),

    # --- SimpleJWT token boshqaruvi ---
    path(
        "token/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh",
    ),
    path(
        "token/blacklist/",          # Logout (refresh tokenni o'chiradi)
        TokenBlacklistView.as_view(),
        name="token-blacklist",
    ),

    # --- Foydalanuvchi profili ---
    path(
        "me/",
        MeView.as_view(),
        name="me",
    ),
]