"""
tariffs/serializers.py

Tarif serializerlari.

Serializerlar:
    TariffSerializer       -- tarif ko'rish (read-only, barcha foydalanuvchilar)
    TariffWriteSerializer  -- tarif yaratish va yangilash (faqat admin)
    FareCalculateSerializer -- narx oldindan hisoblash (operator/mijoz uchun)
"""

from rest_framework import serializers

from .models import Tariff
from .utils import calculate_distance


# ======================================================================
# TariffSerializer  -- read-only
# ======================================================================

class TariffSerializer(serializers.ModelSerializer):
    """
    Tarif ma'lumotlarini ko'rish uchun.
    Barcha autentifikatsiyadan o'tgan foydalanuvchilar uchun ochiq.
    """

    category_display = serializers.CharField(
        source="get_category_display", read_only=True
    )
    example_fare_5km = serializers.SerializerMethodField()

    class Meta:
        model  = Tariff
        fields = [
            "id",
            "category",
            "category_display",
            "base_fare",
            "per_km",
            "rush_fee_low",
            "rush_fee_high",
            "is_active",
            "example_fare_5km",
            "updated_at",
        ]
        read_only_fields = fields

    def get_example_fare_5km(self, obj: Tariff) -> dict:
        """
        5 km uchun misol narxlar (oddiy va shoshilinch).
        Operator panelida tarif jadvalini ko'rsatish uchun qulay.
        """
        return {
            "normal":    obj.calculate_fare(5.0, 0),
            "rush_low":  obj.calculate_fare(5.0, obj.rush_fee_low),
            "rush_high": obj.calculate_fare(5.0, obj.rush_fee_high),
        }


# ======================================================================
# TariffWriteSerializer  -- yaratish / yangilash (admin)
# ======================================================================

class TariffWriteSerializer(serializers.ModelSerializer):
    """
    Tarif yaratish va yangilash uchun (faqat admin).
    category unique bo'lgani uchun update da tekshiruv kerak.
    """

    class Meta:
        model  = Tariff
        fields = [
            "category",
            "base_fare",
            "per_km",
            "rush_fee_low",
            "rush_fee_high",
            "is_active",
        ]

    def validate(self, attrs: dict) -> dict:
        """rush_fee_low <= rush_fee_high bo'lishi kerak."""
        low  = attrs.get("rush_fee_low",  getattr(self.instance, "rush_fee_low",  0))
        high = attrs.get("rush_fee_high", getattr(self.instance, "rush_fee_high", 0))

        if low > high:
            raise serializers.ValidationError(
                {"rush_fee_low": "Kam ustama yuqori ustamadan katta bo'lishi mumkin emas."}
            )
        return attrs


# ======================================================================
# FareCalculateSerializer  -- narxni oldindan hisoblash
# ======================================================================

class FareCalculateSerializer(serializers.Serializer):
    """
    Buyurtma bermasdan oldin narxni oldindan hisoblash.
    Operator yoki mijoz manzil kiritsа, tizim taxminiy narx ko'rsatadi.

    Kiruvchi maydonlar:
        from_lat, from_lng  -- ketish nuqtasi koordinatalari
        to_lat, to_lng      -- manzil koordinatalari
        car_type            -- start | comfort | cargo
        rush_fee            -- shoshilinch ustama (som, ixtiyoriy)

    Chiquvchi maydonlar:
        distance_km   -- hisoblangan masofa
        base_fare     -- boshlangich narx
        per_km        -- 1 km narxi
        fare_no_rush  -- shoshilinchistz narx
        fare_with_rush -- shoshilinch bilan narx
        commission    -- 10% komissiya
    """

    from_lat  = serializers.FloatField()
    from_lng  = serializers.FloatField()
    to_lat    = serializers.FloatField()
    to_lng    = serializers.FloatField()
    car_type  = serializers.ChoiceField(choices=Tariff.Category.choices)
    rush_fee  = serializers.IntegerField(min_value=0, default=0)

    def validate_car_type(self, value: str) -> str:
        if not Tariff.objects.filter(category=value, is_active=True).exists():
            raise serializers.ValidationError(
                f"'{value}' kategoriyasi uchun faol tarif topilmadi."
            )
        return value

    def validate(self, attrs: dict) -> dict:
        """Koordinatalarni tekshirib, masofa va narxni hisoblaydi."""
        try:
            distance_km = calculate_distance(
                attrs["from_lat"], attrs["from_lng"],
                attrs["to_lat"],   attrs["to_lng"],
            )
        except ValueError as exc:
            raise serializers.ValidationError({"coordinates": str(exc)}) from exc

        try:
            tariff = Tariff.objects.get(
                category=attrs["car_type"], is_active=True
            )
        except Tariff.DoesNotExist:
            raise serializers.ValidationError(
                {"car_type": "Faol tarif topilmadi."}
            )

        rush_fee      = attrs["rush_fee"]
        fare_no_rush  = tariff.calculate_fare(distance_km, 0)
        fare_with_rush = tariff.calculate_fare(distance_km, rush_fee)

        attrs["_result"] = {
            "distance_km":    distance_km,
            "base_fare":      tariff.base_fare,
            "per_km":         tariff.per_km,
            "fare_no_rush":   fare_no_rush,
            "fare_with_rush": fare_with_rush,
            "commission":     Tariff.calculate_commission(fare_with_rush),
            "rush_fee":       rush_fee,
        }
        return attrs