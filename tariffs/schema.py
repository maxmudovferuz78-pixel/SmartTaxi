"""
tariffs/schema.py

tariffs app view'lari uchun drf-spectacular @extend_schema dekoratorlari.
"""

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)


tariff_viewset_schema = extend_schema_view(
    list=extend_schema(
        tags=["tariffs"],
        summary="Barcha tariflar",
        description="Barcha kategoriyalar uchun tarif jadvalini qaytaradi.",
    ),
    retrieve=extend_schema(
        tags=["tariffs"],
        summary="Bitta tarif",
    ),
    create=extend_schema(
        tags=["tariffs"],
        summary="Yangi tarif yaratish (admin)",
        examples=[
            OpenApiExample(
                "Start tarifi",
                value={
                    "category":      "start",
                    "base_fare":     4000,
                    "per_km":        1800,
                    "rush_fee_low":  3000,
                    "rush_fee_high": 5000,
                },
                request_only=True,
            ),
        ],
    ),
    partial_update=extend_schema(
        tags=["tariffs"],
        summary="Tarif narxlarini yangilash (admin)",
    ),
    destroy=extend_schema(
        tags=["tariffs"],
        summary="Tarifni faolsizlashtirish (admin)",
        description="Tarif o'chirilmaydi — faqat `is_active=False` qilinadi.",
    ),
)


calculate_schema = extend_schema(
    tags=["tariffs"],
    summary="Narxni oldindan hisoblash",
    description=(
        "Buyurtma bermasdan oldin taxminiy narxni hisoblaydi.\n\n"
        "**Formula:** `S_jami = base_fare + (km × per_km) + rush_fee`"
    ),
    examples=[
        OpenApiExample(
            "Comfort 7.8 km",
            value={
                "from_lat":  41.2995, "from_lng": 69.2401,
                "to_lat":    41.3600, "to_lng":   69.2835,
                "car_type":  "comfort",
                "rush_fee":  3000,
            },
            request_only=True,
        ),
    ],
    responses={
        200: OpenApiResponse(
            description="Hisoblangan narx",
            examples=[
                OpenApiExample(
                    "Natija",
                    value={
                        "distance_km":    7.82,
                        "base_fare":      6500,
                        "per_km":         2400,
                        "fare_no_rush":   25268,
                        "fare_with_rush": 28268,
                        "commission":     2826,
                        "rush_fee":       3000,
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)