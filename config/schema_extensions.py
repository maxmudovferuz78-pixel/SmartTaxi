"""
config/schema_extensions.py

drf-spectacular @extend_schema dekoratorlari uchun umumiy yordamchi obyektlar.

Har bir view faylida import qilinadi va @extend_schema bilan ishlatiladi.

Ishlatilish:
    from config.schema_extensions import (
        auth_header_param,
        error_400_response,
        error_401_response,
        error_403_response,
        error_404_response,
    )

    @extend_schema(
        tags=["orders"],
        summary="Yangi buyurtma yaratish",
        responses={201: OrderDetailSerializer, 400: error_400_response},
    )
    def create(self, request): ...
"""

from drf_spectacular.utils import OpenApiExample, OpenApiResponse, inline_serializer
from rest_framework import serializers


# ------------------------------------------------------------------
# Umumiy xato response'lari
# ------------------------------------------------------------------

error_400_response = OpenApiResponse(
    description="Validatsiya xatosi",
    examples=[
        OpenApiExample(
            "Validatsiya xatosi",
            value={"field_name": ["Bu maydon majburiy."]},
            response_only=True,
        )
    ],
)

error_401_response = OpenApiResponse(
    description="Autentifikatsiya talab etiladi",
    examples=[
        OpenApiExample(
            "Token yo'q",
            value={"detail": "Authentication credentials were not provided."},
            response_only=True,
        )
    ],
)

error_403_response = OpenApiResponse(
    description="Ruxsat yo'q",
    examples=[
        OpenApiExample(
            "Ruxsat yo'q",
            value={"detail": "Bu amalni bajarish uchun operator huquqi kerak."},
            response_only=True,
        )
    ],
)

error_404_response = OpenApiResponse(
    description="Topilmadi",
    examples=[
        OpenApiExample(
            "Topilmadi",
            value={"detail": "Topilmadi."},
            response_only=True,
        )
    ],
)