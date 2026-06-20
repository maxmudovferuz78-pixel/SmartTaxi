"""
wallet/schema.py

wallet app view'lari uchun drf-spectacular @extend_schema dekoratorlari.
"""

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
)
from drf_spectacular.types import OpenApiTypes


wallet_me_schema = extend_schema(
    tags=["wallet"],
    summary="Hamyon holati",
    description=(
        "Haydovchi o'z hamyon balansini ko'radi.\n\n"
        "- `is_sufficient`: balans ≥ 5 000 so'm bo'lsa `true`\n"
        "- `is_driver_active`: anti-debt bloki faolmi"
    ),
    responses={
        200: OpenApiResponse(
            description="Hamyon holati",
            examples=[
                OpenApiExample(
                    "Yetarli balans",
                    value={
                        "id":              1,
                        "driver_phone":    "+998901234567",
                        "balance":         45000,
                        "is_sufficient":   True,
                        "min_balance":     5000,
                        "is_driver_active": True,
                    },
                    response_only=True,
                ),
                OpenApiExample(
                    "Yetarli emas (bloklangan)",
                    value={
                        "id":              1,
                        "balance":         3500,
                        "is_sufficient":   False,
                        "is_driver_active": False,
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)


transactions_schema = extend_schema(
    tags=["wallet"],
    summary="Tranzaksiyalar tarixi",
    description="Haydovchining oxirgi tranzaksiyalari (kirim va chiqim).",
    parameters=[
        OpenApiParameter("tx_type", OpenApiTypes.STR,  description="commission|topup|refund|cashback"),
        OpenApiParameter("limit",   OpenApiTypes.INT,   description="Yozuvlar soni (max: 100, sukut: 20)"),
    ],
    responses={
        200: OpenApiResponse(
            description="Tranzaksiyalar",
            examples=[
                OpenApiExample(
                    "Natija",
                    value={
                        "count":   5,
                        "balance": 45000,
                        "results": [
                            {
                                "id":            1,
                                "amount":        -2500,
                                "tx_type":       "commission",
                                "balance_after": 45000,
                                "is_income":     False,
                                "created_at":    "2024-01-15T10:30:00+05:00",
                            },
                        ],
                    },
                    response_only=True,
                ),
            ],
        ),
    },
)