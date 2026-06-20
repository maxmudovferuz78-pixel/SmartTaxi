"""
payments/schema.py

payments app view'lari uchun drf-spectacular @extend_schema dekoratorlari.
"""

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
)


topup_schema = extend_schema(
    tags=["payments"],
    summary="To'ldirish linki olish",
    description=(
        "Haydovchi to'lov tizimini tanlab, hamyonini to'ldirish uchun link oladi.\n\n"
        "Qaytarilgan `payment_url` ga mijoz redirect qilinadi."
    ),
    examples=[
        OpenApiExample(
            "Payme orqali",
            value={"provider": "payme", "amount": 50000},
            request_only=True,
        ),
        OpenApiExample(
            "Click orqali",
            value={"provider": "click", "amount": 30000},
            request_only=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            description="To'lov URL",
            examples=[
                OpenApiExample(
                    "Payme URL",
                    value={
                        "provider":    "payme",
                        "amount":      50000,
                        "wallet_id":   3,
                        "payment_url": "https://checkout.paycom.uz/bT0uLi47YWMud2FsbGV0X2lkPTM7YT01MDAwMDAw",
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)


payme_webhook_schema = extend_schema(
    tags=["payments"],
    summary="Payme JSONRPC webhook",
    description=(
        "Payme to'lov tizimining JSONRPC 2.0 webhook endpointi.\n\n"
        "⚠️ Bu endpoint faqat Payme serveri tomonidan chaqiriladi.\n"
        "Autentifikatsiya: `Authorization: Basic base64(Payme:<PAYME_KEY>)`\n\n"
        "**Metodlar:** CheckPerformTransaction, CreateTransaction, "
        "PerformTransaction, CancelTransaction, CheckTransaction, GetStatement"
    ),
    exclude=True,   # Swagger UI da ko'rsatmaslik (tashqi webhook)
)


click_webhook_schema = extend_schema(
    tags=["payments"],
    summary="Click webhook",
    description="Click to'lov tizimining Prepare/Complete webhook endpointi.",
    exclude=True,
)


history_schema = extend_schema(
    tags=["payments"],
    summary="To'lov tarixi",
    description="Haydovchining oxirgi to'lovlari (Payme, Click, Uzum).",
    responses={
        200: OpenApiResponse(
            description="To'lovlar ro'yxati",
            examples=[
                OpenApiExample(
                    "Natija",
                    value={
                        "count":   2,
                        "results": [
                            {
                                "id":         1,
                                "provider":   "payme",
                                "amount":     50000,
                                "status":     "completed",
                                "created_at": "2024-01-15T10:30:00+05:00",
                            },
                        ],
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)