"""
wallet/serializers.py

Hamyon va tranzaksiya serializerlari.

Endpointlar:
    GET /api/wallet/me/           -- Haydovchi o'z hamyon balansini ko'radi
    GET /api/wallet/transactions/ -- Oxirgi tranzaksiyalar tarixi
"""

from rest_framework import serializers

from .models import Transaction, Wallet


class TransactionSerializer(serializers.ModelSerializer):
    """
    Bitta tranzaksiya ma'lumotlari.
    amount: musbat = kirim (to'ldirish), manfiy = chiqim (komissiya).
    """

    tx_type_display  = serializers.CharField(source="get_tx_type_display", read_only=True)
    provider_display = serializers.CharField(source="get_provider_display", read_only=True)
    is_income        = serializers.SerializerMethodField()
    order_id         = serializers.IntegerField(source="order.id", read_only=True, default=None)

    class Meta:
        model  = Transaction
        fields = [
            "id",
            "amount",
            "tx_type",
            "tx_type_display",
            "provider",
            "provider_display",
            "order_id",
            "balance_after",
            "is_income",
            "created_at",
        ]

    def get_is_income(self, obj: Transaction) -> bool:
        """Tranzaksiya kirim (True) yoki chiqim (False) ekanligini qaytaradi."""
        return obj.amount > 0


class WalletSerializer(serializers.ModelSerializer):
    """
    Haydovchi hamyonining to'liq holati.
    Balans, minimal talab va bloklanganlik holati ko'rsatiladi.
    """

    driver_phone    = serializers.CharField(source="driver.user.phone",    read_only=True)
    driver_name     = serializers.CharField(source="driver.user.first_name", read_only=True)
    is_sufficient   = serializers.BooleanField(read_only=True)
    min_balance     = serializers.SerializerMethodField()
    is_driver_active = serializers.BooleanField(source="driver.is_active", read_only=True)

    class Meta:
        model  = Wallet
        fields = [
            "id",
            "driver_phone",
            "driver_name",
            "balance",
            "is_sufficient",
            "min_balance",
            "is_driver_active",
            "updated_at",
        ]

    def get_min_balance(self, obj: Wallet) -> int:
        """Minimal talab qilinadigan balans (5 000 so'm)."""
        return Wallet.MIN_BALANCE