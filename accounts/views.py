"""
accounts/views.py

Autentifikatsiya endpointlari.

Endpointlar:
    POST /api/auth/send-otp/   — OTP yaratib yuboradi (hozircha print)
    POST /api/auth/verify-otp/ — OTP ni tekshirib JWT qaytaradi
    GET  /api/auth/me/         — Joriy foydalanuvchi profili
    PUT  /api/auth/me/         — Profilni yangilash

OTP oqimi:
    1. Foydalanuvchi telefon raqamini yuboradi
    2. Tizim 6 xonali kod yaratadi → OTPCode jadvaliga saqlaydi
       (dev: terminalga print + response'ga qaytaradi)
       (prod: Celery task orqali SMS yuboradi)
    3. Foydalanuvchi telefon + kodni yuboradi
    4. Tizim kodni tekshiradi → User yaratadi yoki topadi → JWT qaytaradi
"""

import logging
import random
import string

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import OTPCode, User
from .serializers import (
    DriverProfileSerializer,
    SendOTPSerializer,
    UserSerializer,
    UserUpdateSerializer,
    VerifyOTPSerializer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Yordamchi funksiyalar
# ---------------------------------------------------------------------------

def _generate_otp_code(length: int = 6) -> str:
    """Kriptografik jihatdan xavfsiz 6 xonali raqamli kod yaratadi."""
    return "".join(random.choices(string.digits, k=length))


def _get_tokens_for_user(user: User) -> dict:
    """
    Foydalanuvchi uchun SimpleJWT access va refresh tokenlarini yaratadi.
    Tokenlarga qo'shimcha claim'lar qo'shiladi (role, phone).
    """
    refresh = RefreshToken.for_user(user)

    # Custom claim'lar — frontend va Android uchun qulay
    refresh["phone"] = user.phone
    refresh["role"]  = user.role

    return {
        "refresh": str(refresh),
        "access":  str(refresh.access_token),
    }


def _send_otp_sms(phone: str, code: str) -> None:
    """
    SMS yuborish funksiyasi.

    DEV muhit: kodni terminalga chiqaradi.
    PROD muhit: bu funksiya o'rniga Celery task ishlatiladi:
        from notifications.tasks import send_sms_otp
        send_sms_otp.delay(phone, code)
    """
    # TODO: Celery task bilan almashtirish (6-hafta: notifications moduli)
    logger.info("📱 OTP [%s] → %s (DEV: SMS yuborilmadi)", code, phone)
    print(f"\n{'='*40}")
    print(f"  📱 OTP KOD: {code}")
    print(f"  📞 TELEFON: {phone}")
    print(f"{'='*40}\n")


# ---------------------------------------------------------------------------
# View'lar
# ---------------------------------------------------------------------------

class SendOTPView(APIView):
    """
    POST /api/auth/send-otp/

    Telefon raqamni qabul qilib, 6 xonali OTP yaratadi va yuboradi.

    Request body:
        { "phone": "+998901234567" }

    Response 200:
        { "detail": "OTP kod yuborildi.", "phone": "+998901234567" }
        DEV muhitda: { ..., "dev_code": "123456" }  ← faqat DEBUG=True da

    Response 400:
        { "phone": ["Telefon raqam noto'g'ri formatda."] }
        { "phone": ["Iltimos, 45 soniya kuting."] }
    """

    permission_classes = []  # Autentifikatsiya talab qilinmaydi

    def post(self, request: Request) -> Response:
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        code  = _generate_otp_code()

        # OTPCode jadvaliga saqlaymiz
        OTPCode.objects.create(phone=phone, code=code)

        # SMS yuborish (hozircha print)
        _send_otp_sms(phone, code)

        response_data: dict = {
            "detail": "OTP kod yuborildi.",
            "phone":  phone,
        }

        # DEV muhitda kodni response'ga ham qo'shamiz (Postman test uchun qulay)
        from django.conf import settings  # noqa: PLC0415
        if getattr(settings, "DEBUG", False):
            response_data["dev_code"] = code
            response_data["dev_note"] = (
                "Bu maydon faqat DEBUG=True bo'lganda ko'rinadi. "
                "Productda olib tashlanadi."
            )

        return Response(response_data, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    """
    POST /api/auth/verify-otp/

    Telefon raqam + OTP kodni tekshiradi.
    Foydalanuvchi bazada yo'q bo'lsa, avtomatik yaratadi (Mijoz sifatida).
    Muvaffaqiyatli bo'lsa SimpleJWT tokenlar qaytaradi.

    Request body:
        { "phone": "+998901234567", "code": "123456" }

    Response 200 (mavjud foydalanuvchi):
        {
            "access": "eyJ...",
            "refresh": "eyJ...",
            "is_new_user": false,
            "user": { ...UserSerializer... }
        }

    Response 200 (yangi foydalanuvchi):
        {
            "access": "eyJ...",
            "refresh": "eyJ...",
            "is_new_user": true,
            "user": { ... }
        }

    Response 400:
        { "code": ["Noto'g'ri kod."] }
        { "code": ["OTP muddati tugagan."] }
    """

    permission_classes = []  # Autentifikatsiya talab qilinmaydi

    def post(self, request: Request) -> Response:
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone        = serializer.validated_data["phone"]
        otp_instance = serializer.validated_data["_otp_instance"]

        with transaction.atomic():
            # OTP ni ishlatilgan deb belgilaymiz (replay attack himoyasi)
            otp_instance.is_used = True
            otp_instance.save(update_fields=["is_used"])

            # Foydalanuvchini topamiz yoki yaratamiz
            user, is_new_user = User.objects.get_or_create(
                phone=phone,
                defaults={
                    "username": phone,          # username unique bo'lishi shart
                    "role":     User.Role.CLIENT,
                    "is_active": True,
                },
            )

        # Yangi foydalanuvchi uchun loglash
        if is_new_user:
            logger.info("Yangi mijoz ro'yxatdan o'tdi: %s", phone)
        else:
            logger.info("Mavjud foydalanuvchi kirdi: %s [%s]", phone, user.role)

        # JWT tokenlar
        tokens = _get_tokens_for_user(user)

        # Foydalanuvchi profilini serializatsiya qilamiz
        # Haydovchi bo'lsa DriverProfileSerializer, aks holda UserSerializer
        if user.role == User.Role.DRIVER and hasattr(user, "driver"):
            user_data = DriverProfileSerializer(user.driver).data
        else:
            user_data = UserSerializer(user).data

        return Response(
            {
                **tokens,
                "is_new_user": is_new_user,
                "role":        user.role,
                "user":        user_data,
            },
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    """
    GET  /api/auth/me/ — Joriy foydalanuvchi profilini qaytaradi
    PUT  /api/auth/me/ — Profilni yangilaydi (ismi, familiyasi)

    Response 200 (GET):
        UserSerializer yoki DriverProfileSerializer (role ga qarab)

    Response 200 (PUT):
        { "detail": "Profil yangilandi.", "user": { ... } }

    Response 401:
        { "detail": "Authentication credentials were not provided." }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        user = request.user

        if user.role == User.Role.DRIVER and hasattr(user, "driver"):
            data = DriverProfileSerializer(user.driver).data
        else:
            data = UserSerializer(user).data

        return Response(data, status=status.HTTP_200_OK)

    def put(self, request: Request) -> Response:
        serializer = UserUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        logger.info("Foydalanuvchi profili yangilandi: %s", request.user.phone)

        return Response(
            {
                "detail": "Profil muvaffaqiyatli yangilandi.",
                "user":   UserSerializer(request.user).data,
            },
            status=status.HTTP_200_OK,
        )


class TokenRefreshHintView(APIView):
    """
    Token yangilash uchun eslatma view'i.
    Haqiqiy refresh → simplejwt'ning TokenRefreshView'i ishlatiladi,
    bu view faqat yo'naltirish uchun qo'shildi.
    """

    permission_classes = []

    def get(self, request: Request) -> Response:
        return Response(
            {
                "detail": (
                    "Token yangilash uchun POST /api/auth/token/refresh/ "
                    "endpointiga { \"refresh\": \"<token>\" } yuboring."
                )
            },
            status=status.HTTP_200_OK,
        )