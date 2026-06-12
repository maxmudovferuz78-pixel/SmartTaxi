"""
orders/serializers.py

Buyurtma serializerlari.

TZ 4.1-band (Billing algoritmi):
    S_jami    = S_chaqiruv + (L_umumiy * S_km) + S_shoshilinch
    Komissiya = S_jami * 10%
    Cashback  = S_jami * 2%

Serializerlar:
    OrderCreateSerializer  -- yangi buyurtma + billing
    OrderListSerializer    -- ro'yxat uchun yengil ko'rinish
    OrderDetailSerializer  -- bitta buyurtmaning to'liq ma'lumotlari
    SetStatusSerializer    -- haydovchi tomonidan status o'zgartirish (FSM)
"""

import logging

from rest_framework import serializers

from tariffs.models import Tariff
from tariffs.utils import calculate_distance

from .models import Order

logger = logging.getLogger(__name__)


# ======================================================================
# OrderCreateSerializer
# ======================================================================

class OrderCreateSerializer(serializers.ModelSerializer):
    """
    Yangi buyurtma yaratish uchun serializer.

    Kiruvchi maydonlar:
        from_address, from_lat, from_lng  -- ketish nuqtasi (majburiy)
        to_address, to_lat, to_lng        -- manzil nuqtasi (ixtiyoriy)
        car_type                          -- start | comfort | cargo
        payment_type                      -- cash | qr
        rush_fee                          -- shoshilinch ustama, som (sukut: 0)
        note                              -- operator izohi (ixtiyoriy)

    Chiquvchi (hisoblangan, read-only):
        distance_km, base_fare, total_fare, commission, status, created_at
    """

    rush_fee = serializers.IntegerField(
        min_value=0,
        default=0,
        help_text="Shoshilinch ustama (som). 0 = shoshilinch emas.",
    )

    class Meta:
        model  = Order
        fields = [
            # Kiruvchi
            "from_address", "from_lat", "from_lng",
            "to_address",   "to_lat",   "to_lng",
            "car_type",
            "payment_type",
            "rush_fee",
            "note",
            # Chiquvchi (read-only)
            "id",
            "distance_km",
            "base_fare",
            "total_fare",
            "commission",
            "status",
            "created_at",
        ]
        read_only_fields = [
            "id", "distance_km", "base_fare",
            "total_fare", "commission", "status", "created_at",
        ]

    # ------------------------------------------------------------------
    # Maydon validatsiyalari
    # ------------------------------------------------------------------

    def validate_car_type(self, value: str) -> str:
        """Faqat bazada faol tarifi bor kategoriyalarni qabul qiladi."""
        if not Tariff.objects.filter(category=value, is_active=True).exists():
            raise serializers.ValidationError(
                f"'{value}' kategoriyasi uchun faol tarif topilmadi."
            )
        return value

    def validate_rush_fee(self, value: int) -> int:
        """Shoshilinch ustama manfiy bo'lmasligi kerak."""
        if value < 0:
            raise serializers.ValidationError(
                "Shoshilinch ustama manfiy bo'lishi mumkin emas."
            )
        return value

    def validate(self, attrs: dict) -> dict:
        """
        Cross-field validatsiya:
        to_lat va to_lng ikkalasi birga yoki ikkalasi ham yo'q bo'lishi kerak.
        """
        to_lat = attrs.get("to_lat")
        to_lng = attrs.get("to_lng")

        if (to_lat is None) != (to_lng is None):
            raise serializers.ValidationError(
                {"to_lat": "to_lat va to_lng ikkalasi birga berilishi kerak."}
            )
        return attrs

    # ------------------------------------------------------------------
    # create() -- billing algoritmi (TZ 4.1-band)
    # ------------------------------------------------------------------

    def create(self, validated_data: dict) -> Order:
        """
        Buyurtmani billing bilan saqlaydi.

        Bosqichlar:
            1. Koordinatalardan masofani hisoblash (Haversine)
            2. Bazadan faol tarifni olish
            3. Narx formulasini qo'llash:
               S_jami = S_chaqiruv + (L_umumiy * S_km) + S_shoshilinch
            4. Komissiyani hisoblash: S_jami * 10%
            5. Order bazaga saqlanadi

        Returns:
            Yangi saqlangan Order obyekti.

        Raises:
            serializers.ValidationError: Tarif topilmasa yoki
                koordinatalar noto'g'ri bo'lsa.
        """
        rush_fee = validated_data.pop("rush_fee", 0)
        car_type = validated_data["car_type"]

        # ---- 1. Masofa -----------------------------------------------
        distance_km = 0.0
        has_destination = (
            validated_data.get("to_lat") is not None
            and validated_data.get("to_lng") is not None
        )
        if has_destination:
            try:
                distance_km = calculate_distance(
                    float(validated_data["from_lat"]),
                    float(validated_data["from_lng"]),
                    float(validated_data["to_lat"]),
                    float(validated_data["to_lng"]),
                )
            except ValueError as exc:
                raise serializers.ValidationError(
                    {"coordinates": str(exc)}
                ) from exc

        # ---- 2. Tarif ------------------------------------------------
        try:
            tariff = Tariff.objects.get(category=car_type, is_active=True)
        except Tariff.DoesNotExist:
            raise serializers.ValidationError(
                {"car_type": f"'{car_type}' uchun faol tarif topilmadi."}
            )

        # ---- 3-4. Narx formulasi (TZ 4.1-band) -----------------------
        total_fare = tariff.calculate_fare(distance_km, rush_fee)
        commission = Tariff.calculate_commission(total_fare)

        logger.info(
            "Buyurtma narxi: car_type=%s | dist=%.2f km | "
            "base=%s | rush=%s | total=%s | commission=%s",
            car_type, distance_km,
            tariff.base_fare, rush_fee, total_fare, commission,
        )

        # ---- 5. Saqlash ----------------------------------------------
        request = self.context.get("request")
        client  = getattr(request, "user", None)

        return Order.objects.create(
            **validated_data,
            client      = client,
            distance_km = distance_km,
            base_fare   = tariff.base_fare,
            rush_fee    = rush_fee,
            total_fare  = total_fare,
            commission  = commission,
            is_urgent   = rush_fee > 0,
        )


# ======================================================================
# OrderListSerializer  -- ro'yxat uchun yengil ko'rinish
# ======================================================================

class OrderListSerializer(serializers.ModelSerializer):
    """Buyurtmalar ro'yxati uchun optimallashtirilgan serializer."""

    client_phone     = serializers.CharField(source="client.phone",       read_only=True, default=None)
    driver_phone     = serializers.CharField(source="driver.user.phone",  read_only=True, default=None)
    status_display   = serializers.CharField(source="get_status_display", read_only=True)
    car_type_display = serializers.CharField(source="get_car_type_display", read_only=True)

    class Meta:
        model  = Order
        fields = [
            "id",
            "client_phone",
            "driver_phone",
            "from_address",
            "to_address",
            "car_type",
            "car_type_display",
            "status",
            "status_display",
            "total_fare",
            "payment_type",
            "is_urgent",
            "created_at",
        ]


# ======================================================================
# OrderDetailSerializer  -- bitta buyurtmaning to'liq ma'lumotlari
# ======================================================================

class OrderDetailSerializer(serializers.ModelSerializer):
    """Bitta buyurtmaning barcha maydonlari (retrieve endpointi)."""

    client_phone     = serializers.CharField(source="client.phone",       read_only=True, default=None)
    driver_phone     = serializers.CharField(source="driver.user.phone",  read_only=True, default=None)
    driver_car       = serializers.CharField(source="driver.car_number",  read_only=True, default=None)
    status_display   = serializers.CharField(source="get_status_display",   read_only=True)
    car_type_display = serializers.CharField(source="get_car_type_display", read_only=True)
    cashback         = serializers.SerializerMethodField()

    class Meta:
        model  = Order
        fields = "__all__"

    def get_cashback(self, obj: Order) -> int:
        """Mijoz uchun 2% cashback miqdori."""
        return obj.calculate_cashback()


# ======================================================================
# SetStatusSerializer  -- haydovchi status o'zgartiradi (FSM)
# ======================================================================

class SetStatusSerializer(serializers.Serializer):
    """
    Buyurtma statusini o'zgartirish uchun (set_status action).

    Ruxsat etilgan o'tishlar:
        new       -> accepted | cancelled
        accepted  -> arrived  | cancelled
        arrived   -> started  | cancelled
        started   -> done     | cancelled
        done      -> (yakuniy holat)
        cancelled -> (yakuniy holat)
    """

    VALID_TRANSITIONS: dict = {
        Order.Status.NEW:       [Order.Status.ACCEPTED, Order.Status.CANCELLED],
        Order.Status.ACCEPTED:  [Order.Status.ARRIVED,  Order.Status.CANCELLED],
        Order.Status.ARRIVED:   [Order.Status.STARTED,  Order.Status.CANCELLED],
        Order.Status.STARTED:   [Order.Status.DONE,     Order.Status.CANCELLED],
        Order.Status.DONE:      [],
        Order.Status.CANCELLED: [],
    }

    status = serializers.ChoiceField(
        choices=[
            Order.Status.ACCEPTED,
            Order.Status.ARRIVED,
            Order.Status.STARTED,
            Order.Status.DONE,
            Order.Status.CANCELLED,
        ]
    )

    def validate(self, attrs: dict) -> dict:
        """
        FSM qoidasiga ko'ra o'tish to'g'riligini tekshiradi.

        Raises:
            serializers.ValidationError: Noto'g'ri o'tish so'ralsa.
        """
        order      = self.context["order"]
        new_status = attrs["status"]
        allowed    = self.VALID_TRANSITIONS.get(order.status, [])

        if new_status not in allowed:
            allowed_labels = (
                [Order.Status(s).label for s in allowed]
                if allowed else ["yo'q (yakuniy holat)"]
            )
            raise serializers.ValidationError(
                {
                    "status": (
                        f"'{order.get_status_display()}' holatidan "
                        f"'{Order.Status(new_status).label}' ga o'tib bo'lmaydi. "
                        f"Ruxsat etilganlar: {allowed_labels}."
                    )
                }
            )
        return attrs