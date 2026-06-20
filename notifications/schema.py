"""
notifications/schema.py

notifications app view'lari uchun drf-spectacular @extend_schema dekoratorlari.
"""

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from drf_spectacular.types import OpenApiTypes


notification_list_schema = extend_schema(
    tags=["notifications"],
    summary="Bildirishnomalar tarixi",
    description="Foydalanuvchiga yuborilgan barcha SMS, Push va Telegram xabarlarini qaytaradi.",
    parameters=[
        OpenApiParameter("channel", OpenApiTypes.STR, description="sms|push|tg"),
        OpenApiParameter("status",  OpenApiTypes.STR, description="sent|failed"),
        OpenApiParameter("limit",   OpenApiTypes.INT, description="Yozuvlar soni (max: 50, sukut: 20)"),
    ],
    responses={
        200: OpenApiResponse(
            description="Xabarlar ro'yxati",
            examples=[
                OpenApiExample(
                    "Natija",
                    value={
                        "count": 2,
                        "results": [
                            {
                                "id":              1,
                                "channel":         "sms",
                                "channel_display": "SMS",
                                "message":         "SmartTaxi: Tasdiqlash kodingiz 123456.",
                                "status":          "sent",
                                "created_at":      "2024-01-15T10:30:00+05:00",
                            }
                        ],
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)


test_notification_schema = extend_schema(
    tags=["notifications"],
    summary="Test xabar yuborish (admin)",
    description=(
        "Admin istalgan foydalanuvchiga test xabar yuboradi.\n\n"
        "**Kanallar:** `sms`, `push`, `tg` (Telegram)\n\n"
        "Faqat admin huquqi bilan ishlaydi."
    ),
    examples=[
        OpenApiExample(
            "SMS test",
            value={"user_id": 5, "channel": "sms", "message": "SmartTaxi test xabari"},
            request_only=True,
        ),
        OpenApiExample(
            "Telegram test",
            value={"user_id": 5, "channel": "tg", "message": "Test xabar Telegram orqali"},
            request_only=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            description="Yuborildi",
            examples=[
                OpenApiExample(
                    "Muvaffaqiyat",
                    value={"sent": True, "channel": "sms"},
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(description="user_id yoki channel yo'q"),
        404: OpenApiResponse(description="Foydalanuvchi topilmadi"),
    },
)