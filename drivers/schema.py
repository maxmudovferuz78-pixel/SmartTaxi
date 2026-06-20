"""
drivers/schema.py

drivers app view'lari uchun drf-spectacular @extend_schema dekoratorlari.
"""

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from drf_spectacular.types import OpenApiTypes


driver_viewset_schema = extend_schema_view(
    list=extend_schema(
        tags=["drivers"],
        summary="Haydovchilar ro'yxati",
        parameters=[
            OpenApiParameter("car_type",  OpenApiTypes.STR,  description="start|comfort|cargo"),
            OpenApiParameter("is_active", OpenApiTypes.BOOL, description="true|false"),
            OpenApiParameter("is_online", OpenApiTypes.BOOL, description="true|false"),
        ],
    ),
    create=extend_schema(
        tags=["drivers"],
        summary="Yangi haydovchi ro'yxatdan o'tkazish",
        description=(
            "Yangi haydovchi profili yaratadi.\n\n"
            "Driver profili + Wallet (`DEPOSIT_MIN = 10 000 so'm`) bitta tranzaksiyada yaratiladi."
        ),
        examples=[
            OpenApiExample(
                "Yangi haydovchi",
                value={
                    "user_id":    5,
                    "car_type":   "comfort",
                    "car_number": "01A123BC",
                    "car_model":  "Chevrolet Malibu 2022",
                },
                request_only=True,
            ),
        ],
        responses={
            201: OpenApiResponse(description="Haydovchi yaratildi"),
            400: OpenApiResponse(description="Validatsiya xatosi"),
        },
    ),
    retrieve=extend_schema(
        tags=["drivers"],
        summary="Haydovchi batafsil profili",
    ),
)


me_schema = extend_schema(
    tags=["drivers"],
    summary="O'z profili (haydovchi)",
    description="Haydovchi o'z profili, balansi va aktiv buyurtmalar sonini ko'radi.",
    responses={
        200: OpenApiResponse(description="Haydovchi profili"),
        404: OpenApiResponse(description="Profil topilmadi"),
    },
)


set_status_schema = extend_schema(
    tags=["drivers"],
    summary="Onlayn / Offline o'tish",
    description=(
        "Haydovchi o'zini onlayn yoki offline qiladi.\n\n"
        "⚠️ Balans < 5 000 so'm bo'lsa onlayn bo'lib bo'lmaydi."
    ),
    examples=[
        OpenApiExample("Onlayn",  value={"is_online": True},  request_only=True),
        OpenApiExample("Offline", value={"is_online": False}, request_only=True),
    ],
    responses={
        200: OpenApiResponse(
            description="Holat yangilandi",
            examples=[
                OpenApiExample(
                    "Muvaffaqiyat",
                    value={"is_online": True, "message": "Siz onlayn holatga o'tdingiz."},
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(description="Balans yetarli emas"),
    },
)


nearby_schema = extend_schema(
    tags=["drivers"],
    summary="Yaqin haydovchilar",
    description="Berilgan koordinatga yaqin aktiv va onlayn haydovchilarni qaytaradi.",
    parameters=[
        OpenApiParameter("lat",      OpenApiTypes.FLOAT, required=True,  description="Kenglik (41.2995)"),
        OpenApiParameter("lng",      OpenApiTypes.FLOAT, required=True,  description="Uzunlik (69.2401)"),
        OpenApiParameter("car_type", OpenApiTypes.STR,   required=False, description="start|comfort|cargo"),
        OpenApiParameter("radius",   OpenApiTypes.FLOAT, required=False, description="Radius km (sukut: 10)"),
    ],
    responses={
        200: OpenApiResponse(
            description="Yaqin haydovchilar ro'yxati (masofaga ko'ra tartiblangan)",
            examples=[
                OpenApiExample(
                    "Natija",
                    value={
                        "count":   2,
                        "radius":  10.0,
                        "results": [
                            {
                                "id":          3,
                                "phone":       "+998901234567",
                                "car_type":    "comfort",
                                "car_number":  "01A123BC",
                                "distance_km": 1.2,
                            },
                        ],
                    },
                    response_only=True,
                ),
            ],
        ),
        400: OpenApiResponse(description="lat va lng parametrlari yo'q"),
    },
)


toggle_active_schema = extend_schema(
    tags=["drivers"],
    summary="Haydovchini bloklash / faollashtirish",
    description="Operator haydovchini bloklaydi yoki qayta faollashtiradi.",
    examples=[
        OpenApiExample(
            "Bloklash sababi",
            value={"reason": "Balans to'lanmagan"},
            request_only=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            description="Holat o'zgartirildi",
            examples=[
                OpenApiExample(
                    "Bloklandi",
                    value={
                        "id":        1,
                        "is_active": False,
                        "is_online": False,
                        "message":   "Haydovchi bloklandi.",
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)