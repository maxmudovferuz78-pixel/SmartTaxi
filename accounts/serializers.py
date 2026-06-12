"""
accounts/serializers.py

OTP autentifikatsiya va foydalanuvchi ma'lumotlari uchun serializerlar.

Oqim:
    1. POST /api/auth/send-otp/   →  SendOTPSerializer
    2. POST /api/auth/verify-otp/ →  VerifyOTPSerializer → JWT qaytaradi
"""

import re
from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import OTPCode, SavedAddress, User

# OTP muddati: 3 daqiqa
OTP_LIFETIME_MINUTES = 3

# Bir raqamdan ketma-ket so'rov orasidagi minimal vaqt (spam himoyasi)
OTP_RESEND_COOLDOWN_SECONDS = 60

# O'zbekiston telefon raqami pattern: +998XXXXXXXXX
_UZ_PHONE_RE = re.compile(r"^\+998[0-9]{9}$")


def validate_uzbek_phone(phone: str) -> str:
    """
    Qayta ishlatiladigan telefon validatsiya funksiyasi.
    +998901234567 formatini tekshiradi.
    """
    if not _UZ_PHONE_RE.match(phone):
        raise serializers.ValidationError(
            "Telefon raqam noto'g'ri formatda. Namuna: +998901234567"
        )
    return phone


# ---------------------------------------------------------------------------
# OTP serializerlari
# ---------------------------------------------------------------------------

class SendOTPSerializer(serializers.Serializer):
    """
    OTP yuborish uchun.
    Faqat telefon raqamni qabul qiladi va validatsiya qiladi.
    """

    phone = serializers.CharField(max_length=13)

    def validate_phone(self, value: str) -> str:
        return validate_uzbek_phone(value)

    def validate(self, attrs: dict) -> dict:
        phone = attrs["phone"]
        cooldown_threshold = timezone.now() - timedelta(
            seconds=OTP_RESEND_COOLDOWN_SECONDS
        )

        # Spam himoyasi: oxirgi OTP dan 60 soniya o'tmagan bo'lsa bloklash
        recent_otp = (
            OTPCode.objects.filter(phone=phone, created_at__gte=cooldown_threshold)
            .order_by("-created_at")
            .first()
        )
        if recent_otp:
            remaining = OTP_RESEND_COOLDOWN_SECONDS - int(
                (timezone.now() - recent_otp.created_at).total_seconds()
            )
            raise serializers.ValidationError(
                {
                    "phone": (
                        f"Iltimos, {remaining} soniya kuting. "
                        "Spam himoyasi faol."
                    )
                }
            )

        return attrs


class VerifyOTPSerializer(serializers.Serializer):
    """
    OTP kodni tekshirish uchun.
    Muvaffaqiyatli bo'lsa JWT tokenlar va foydalanuvchi ma'lumotlari qaytariladi.
    """

    phone = serializers.CharField(max_length=13)
    code  = serializers.CharField(min_length=6, max_length=6)

    def validate_phone(self, value: str) -> str:
        return validate_uzbek_phone(value)

    def validate_code(self, value: str) -> str:
        if not value.isdigit():
            raise serializers.ValidationError("Kod faqat raqamlardan iborat bo'lishi kerak.")
        return value

    def validate(self, attrs: dict) -> dict:
        phone = attrs["phone"]
        code  = attrs["code"]

        expiry_threshold = timezone.now() - timedelta(minutes=OTP_LIFETIME_MINUTES)

        # Eng so'nggi, ishlatilmagan, muddati o'tmagan OTPni olamiz
        otp = (
            OTPCode.objects.filter(
                phone=phone,
                is_used=False,
                created_at__gte=expiry_threshold,
            )
            .order_by("-created_at")
            .first()
        )

        if otp is None:
            raise serializers.ValidationError(
                {"code": "OTP kod topilmadi yoki muddati tugagan. Qayta so'rang."}
            )

        if otp.code != code:
            raise serializers.ValidationError(
                {"code": "Noto'g'ri kod. Iltimos, qayta tekshiring."}
            )

        # Validatsiyadan o'tgan OTP ni contextga saqlaymiz
        # (view'da is_used=True qilish uchun)
        attrs["_otp_instance"] = otp
        return attrs


# ---------------------------------------------------------------------------
# Foydalanuvchi serializerlari
# ---------------------------------------------------------------------------

class SavedAddressSerializer(serializers.ModelSerializer):
    """Saqlangan manzillarni ko'rsatish uchun (ichki serializer)."""

    class Meta:
        model  = SavedAddress
        fields = ["id", "label", "address", "lat", "lng", "is_default"]
        read_only_fields = ["id"]


class UserSerializer(serializers.ModelSerializer):
    """
    Foydalanuvchi profilini qaytarish uchun (read-only).
    JWT verify-otp response'da va /api/auth/me/ da ishlatiladi.
    """

    saved_addresses = SavedAddressSerializer(many=True, read_only=True)
    role_display    = serializers.CharField(source="get_role_display", read_only=True)

    class Meta:
        model  = User
        fields = [
            "id",
            "phone",
            "first_name",
            "last_name",
            "role",
            "role_display",
            "is_elderly",
            "cashback_balance",
            "telegram_id",
            "saved_addresses",
            "date_joined",
        ]
        read_only_fields = fields  # To'liq read-only


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Foydalanuvchi o'z profilini yangilashi uchun (ismi, familiyasi).
    Telefon va rol o'zgartirib bo'lmaydi.
    """

    class Meta:
        model  = User
        fields = ["first_name", "last_name", "telegram_id"]


class DriverProfileSerializer(serializers.ModelSerializer):
    """
    Haydovchi profilini qaytarish uchun.
    Driver modeli + User ma'lumotlari + Wallet balansi birlashtirilgan.
    """

    phone      = serializers.CharField(source="user.phone",       read_only=True)
    first_name = serializers.CharField(source="user.first_name",  read_only=True)
    last_name  = serializers.CharField(source="user.last_name",   read_only=True)
    balance    = serializers.IntegerField(source="wallet.balance", read_only=True, default=0)

    class Meta:
        # Import ichkarida — circular import'dan saqlanish uchun
        from drivers.models import Driver  # noqa: PLC0415

        model  = Driver
        fields = [
            "id",
            "phone",
            "first_name",
            "last_name",
            "car_type",
            "car_model",
            "car_number",
            "is_active",
            "is_online",
            "balance",
            "joined_at",
        ]
        read_only_fields = fields