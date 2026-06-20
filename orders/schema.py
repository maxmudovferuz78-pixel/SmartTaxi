"""
orders/schema.py

orders app view'lari uchun drf-spectacular @extend_schema dekoratorlari.
"""

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from drf_spectacular.types import OpenApiTypes


order_viewset_schema = extend_schema_view(
    list=extend_schema(
        tags=["orders"],
        summary="Buyurtmalar ro'yxati",
        description="Barcha buyurtmalarni qaytaradi. Faqat operator va adminlar uchun.",
        parameters=[
            OpenApiParameter("status",   OpenApiTypes.STR, description="new|accepted|arrived|started|done|cancelled"),
            OpenApiParameter("car_type", OpenApiTypes.STR, description="start|comfort|cargo"),
            OpenApiParameter("driver_id", OpenApiTypes.INT, description="Haydovchi ID si"),
        ],
    ),
    create=extend_schema(
        tags=["orders"],
        summary="Yangi buyurtma yaratish",
        description=(
            "Yangi buyurtma yaratadi va narxni **avtomatik hisoblaydi**.\n\n"
            "**Billing formulasi (TZ 4.1):**\n"
            "```\nS_jami = S_chaqiruv + (masofa_km × S_km) + rush_fee\n"
            "Komissiya = S_jami × 10%\n```"
        ),
        examples=[
            OpenApiExample(
                "Comfort buyurtma",
                value={
                    "from_address": "Chilonzor 5-kvartal",
                    "from_lat":     41.2995,
                    "from_lng":     69.2401,
                    "to_address":   "Yunusobod 7-kvartal",
                    "to_lat":       41.3600,
                    "to_lng":       69.2835,
                    "car_type":     "comfort",
                    "payment_type": "cash",
                    "rush_fee":     3000,
                },
                request_only=True,
            ),
        ],
        responses={
            201: OpenApiResponse(
                description="Buyurtma yaratildi",
                examples=[
                    OpenApiExample(
                        "Yaratilgan buyurtma",
                        value={
                            "id":           1,
                            "from_address": "Chilonzor 5-kvartal",
                            "to_address":   "Yunusobod 7-kvartal",
                            "car_type":     "comfort",
                            "status":       "new",
                            "distance_km":  7.82,
                            "base_fare":    6500,
                            "rush_fee":     3000,
                            "total_fare":   28268,
                            "commission":   2826,
                            "payment_type": "cash",
                            "created_at":   "2024-01-15T10:30:00+05:00",
                        },
                        response_only=True,
                    ),
                ],
            ),
            400: OpenApiResponse(description="Validatsiya xatosi"),
            403: OpenApiResponse(description="Ruxsat yo'q (operator emas)"),
        },
    ),
    retrieve=extend_schema(
        tags=["orders"],
        summary="Buyurtma batafsil ma'lumoti",
    ),
)


set_status_schema = extend_schema(
    tags=["orders"],
    summary="Buyurtma statusini o'zgartirish",
    description=(
        "Haydovchi buyurtma holatini ketma-ket o'zgartiradi.\n\n"
        "**FSM qoidalari:**\n"
        "```\nnew → accepted → arrived → started → done\n"
        "         ↓          ↓         ↓         ↓\n"
        "      cancelled  cancelled cancelled cancelled\n```\n\n"
        "⚠️ `done` holatiga o'tishdan oldin haydovchi balansi ≥ 5 000 so'm bo'lishi shart."
    ),
    examples=[
        OpenApiExample(
            "Qabul qilish",
            value={"status": "accepted"},
            request_only=True,
        ),
        OpenApiExample(
            "Bekor qilish",
            value={"status": "cancelled"},
            request_only=True,
        ),
    ],
    responses={
        200: OpenApiResponse(description="Status yangilandi"),
        400: OpenApiResponse(
            description="Noto'g'ri o'tish",
            examples=[
                OpenApiExample(
                    "Noto'g'ri o'tish",
                    value={"status": ["'Yangi' holatidan 'Yo'lda' ga o'tib bo'lmaydi."]},
                    response_only=True,
                ),
            ],
        ),
        403: OpenApiResponse(description="Balans yetarli emas yoki boshqa haydovchining buyurtmasi"),
    },
)


assign_driver_schema = extend_schema(
    tags=["orders"],
    summary="Haydovchi biriktirish",
    description="Operator aktiv va onlayn haydovchini buyurtmaga biriktiradi.",
    examples=[
        OpenApiExample(
            "Haydovchi biriktirish",
            value={"driver_id": 42},
            request_only=True,
        ),
    ],
    responses={
        200: OpenApiResponse(description="Haydovchi biriktirildi"),
        400: OpenApiResponse(description="Haydovchi topilmadi yoki aktiv emas"),
    },
)