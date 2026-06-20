"""
locations/schema.py

locations app view'lari uchun drf-spectacular @extend_schema dekoratorlari.
"""

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from drf_spectacular.types import OpenApiTypes


active_locations_schema = extend_schema(
    tags=["locations"],
    summary="Barcha aktiv haydovchilar joylashuvi",
    description=(
        "Aktiv va onlayn haydovchilarning so'nggi GPS koordinatalarini qaytaradi.\n\n"
        "**Real-time uchun** WebSocket ishlatiladi: `ws://host/ws/map/`\n\n"
        "Bu endpoint operator paneli dastlab yuklanayotganda (initial load) ishlatiladi."
    ),
    parameters=[
        OpenApiParameter("car_type", OpenApiTypes.STR, description="start|comfort|cargo"),
    ],
    responses={
        200: OpenApiResponse(
            description="Haydovchilar joylashuvi",
            examples=[
                OpenApiExample(
                    "Natija",
                    value={
                        "count": 2,
                        "results": [
                            {
                                "driver_id":    1,
                                "driver_phone": "+998901234567",
                                "car_number":   "01A123BC",
                                "car_type":     "comfort",
                                "lat":          41.2995,
                                "lng":          69.2401,
                                "speed_kmh":    0.0,
                                "updated_at":   "2024-01-15T10:30:00+05:00",
                            }
                        ],
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)


driver_location_detail_schema = extend_schema(
    tags=["locations"],
    summary="Bitta haydovchi joylashuvi",
    description="Berilgan ID li haydovchining so'nggi GPS koordinatasi.",
    responses={
        200: OpenApiResponse(description="Haydovchi joylashuvi"),
        404: OpenApiResponse(description="Joylashuv topilmadi"),
    },
)


location_history_schema = extend_schema(
    tags=["locations"],
    summary="GPS koordinatalar tarixi",
    description=(
        "Haydovchining GPS tarixi (TZ: 7 kun saqlanadi).\n\n"
        "`?order_id=N` bilan faqat bitta buyurtma davomidagi koordinatalarni filtrlash mumkin."
    ),
    parameters=[
        OpenApiParameter("limit",    OpenApiTypes.INT, description="Yozuvlar soni (max: 200, sukut: 50)"),
        OpenApiParameter("order_id", OpenApiTypes.INT, description="Buyurtma ID si bo'yicha filtr"),
    ],
    responses={
        200: OpenApiResponse(description="GPS tarixi"),
        404: OpenApiResponse(description="Haydovchi topilmadi"),
    },
)


my_location_schema = extend_schema(
    tags=["locations"],
    summary="O'z joylashuvi (haydovchi)",
    description="Haydovchi o'zining so'nggi yuborilgan GPS koordinatasini ko'radi.",
    responses={
        200: OpenApiResponse(description="So'nggi joylashuv"),
        404: OpenApiResponse(description="GPS hali yuborilmagan"),
    },
)