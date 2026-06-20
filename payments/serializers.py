"""
payments/serializers.py

To'lov serializerlari.
"""

from rest_framework import serializers

from .models import PaymentRequest


class PaymentRequestSerializer(serializers.ModelSerializer):
    """To'lov so'rovlarini ko'rish uchun (read-only)."""

    provider_display = serializers.CharField(source="get_provider_display", read_only=True)
    status_display   = serializers.CharField(source="get_status_display",   read_only=True)
    wallet_driver    = serializers.CharField(
        source="wallet.driver.user.phone", read_only=True, default=None
    )

    class Meta:
        model  = PaymentRequest
        fields = [
            "id",
            "wallet_driver",
            "provider",
            "provider_display",
            "amount",
            "status",
            "status_display",
            "external_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TopupInitSerializer(serializers.Serializer):
    """
    To'ldirish so'rovini boshlash uchun.
    Haydovchi miqdor va provayder tanlaydi.
    Tizim to'lov linkini qaytaradi.

    Kiruvchi:
        provider -- payme | click | uzum
        amount   -- so'm (min: 10 000)
    """

    PROVIDER_CHOICES = [
        ("payme", "Payme"),
        ("click", "Click"),
        ("uzum",  "Uzum"),
    ]

    provider = serializers.ChoiceField(choices=PROVIDER_CHOICES)
    amount   = serializers.IntegerField(min_value=10_000)