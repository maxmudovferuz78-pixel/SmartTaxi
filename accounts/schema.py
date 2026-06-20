"""
accounts/schema.py

accounts app view'lari uchun drf-spectacular @extend_schema dekoratorlari.

Ishlatilish (accounts/views.py):
    from accounts.schema import (
        send_otp_schema,
        verify_otp_schema,
        me_get_schema,
        me_put_schema,
    )

    @send_otp_schema
    def post(self, request): ...
"""

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers


send_otp_schema = extend_schema(
    tags=["auth"],
    summary="OTP kod yuborish",
    description=(
        "Telefon raqamga 6 xonali SMS kod yuboradi.\n\n"
        "**DEV muhit:** `dev_code` response'da qaytariladi.\n\n"
        "**Spam himoyasi:** Bir raqamdan 60 soniyada bir marta so'rov yuborsa bo'ladi."
    ),
    request=inline_serializer(
        name="SendOTPRequest",
        fields={"phone": serializers.CharField(help_text="+998901234567")},
    ),
    responses={
        200: OpenApiResponse(
            description="OTP yuborildi",
            examples=[
                OpenApiExample(
                    "Muvaffaqiyat (DEV)",
                    value={
                        "detail":   "OTP kod yuborildi.",
                        "phone":    "+998901234567",
                        "dev_code": "123456",
                        "dev_note": "Bu maydon faqat DEBUG=True bo'lganda ko'rinadi.",
                    },
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Validatsiya xatosi yoki spam limiti",
            examples=[
                OpenApiExample(
                    "Noto'g'ri format",
                    value={"phone": ["Telefon raqam noto'g'ri formatda. Namuna: +998901234567"]},
                    response_only=True,
                ),
                OpenApiExample(
                    "Spam limiti",
                    value={"phone": ["Iltimos, 45 soniya kuting. Spam himoyasi faol."]},
                    response_only=True,
                ),
            ],
        ),
    },
)


verify_otp_schema = extend_schema(
    tags=["auth"],
    summary="OTP kodni tasdiqlash va token olish",
    description=(
        "Telefon raqam + OTP kodini tekshiradi.\n\n"
        "- Foydalanuvchi bazada yo'q bo'lsa **avtomatik yaratiladi** (Mijoz sifatida).\n"
        "- Javobda `access` va `refresh` JWT tokenlar qaytariladi.\n"
        "- Keyingi so'rovlarda: `Authorization: Bearer <access_token>` header."
    ),
    request=inline_serializer(
        name="VerifyOTPRequest",
        fields={
            "phone": serializers.CharField(help_text="+998901234567"),
            "code":  serializers.CharField(help_text="123456"),
        },
    ),
    responses={
        200: OpenApiResponse(
            description="Muvaffaqiyat — tokenlar qaytarildi",
            examples=[
                OpenApiExample(
                    "Muvaffaqiyat",
                    value={
                        "access":       "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "refresh":      "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "is_new_user":  False,
                        "role":         "driver",
                        "user": {
                            "id":       1,
                            "phone":    "+998901234567",
                            "role":     "driver",
                            "balance":  45000,
                            "is_active": True,
                        },
                    },
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(
            description="Noto'g'ri yoki muddati tugagan kod",
            examples=[
                OpenApiExample(
                    "Noto'g'ri kod",
                    value={"code": ["Noto'g'ri kod. Iltimos, qayta tekshiring."]},
                    response_only=True,
                ),
                OpenApiExample(
                    "Muddati tugagan",
                    value={"code": ["OTP kod topilmadi yoki muddati tugagan. Qayta so'rang."]},
                    response_only=True,
                ),
            ],
        ),
    },
)


me_get_schema = extend_schema(
    tags=["auth"],
    summary="Joriy foydalanuvchi profili",
    description="JWT token orqali autentifikatsiya qilingan foydalanuvchi profilini qaytaradi.",
    responses={
        200: OpenApiResponse(description="Foydalanuvchi profili"),
        401: OpenApiResponse(description="Token yo'q yoki yaroqsiz"),
    },
)


me_put_schema = extend_schema(
    tags=["auth"],
    summary="Profilni yangilash",
    description="Ismi, familiyasi yoki Telegram ID sini yangilaydi.",
    request=inline_serializer(
        name="UserUpdateRequest",
        fields={
            "first_name":  serializers.CharField(required=False),
            "last_name":   serializers.CharField(required=False),
            "telegram_id": serializers.IntegerField(required=False),
        },
    ),
    responses={
        200: OpenApiResponse(description="Yangilangan profil"),
        400: OpenApiResponse(description="Validatsiya xatosi"),
    },
)