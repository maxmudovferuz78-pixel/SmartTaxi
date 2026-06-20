"""
drivers/serializers.py

Haydovchi profili serializerlari.

Serializerlar:
    DriverRegisterSerializer  -- yangi haydovchi ro'yxatdan o'tishi
    DriverProfileSerializer   -- profilni ko'rish (read-only, batafsil)
    DriverUpdateSerializer    -- mashina ma'lumotlarini yangilash
    DriverListSerializer      -- operator uchun ro'yxat (yengil)
    DriverStatusSerializer    -- onlayn/offline toggle
    NearbyDriverSerializer    -- buyurtma uchun yaqin haydovchilar
"""

import re
import logging

from rest_framework import serializers

from accounts.models import User
from .models import Driver

logger = logging.getLogger(__name__)

_CAR_NUMBER_RE = re.compile(r"^[0-9]{2}[A-Z]{1,2}[0-9]{3,4}[A-Z]{2}$")


def validate_car_number(value: str) -> str:
    """
    O'zbekiston davlat raqami formati: 01A123BC yoki 01AA1234BC.
    Katta harfga o'tkaziladi, bo'sh joylar tozalanadi.
    """
    cleaned = value.strip().upper().replace(" ", "")
    if not _CAR_NUMBER_RE.match(cleaned):
        raise serializers.ValidationError(
            "Davlat raqami noto'g'ri. Namuna: 01A123BC"
        )
    return cleaned


# ======================================================================
# DriverRegisterSerializer
# ======================================================================

class DriverRegisterSerializer(serializers.Serializer):
    """
    Yangi haydovchi ro'yxatdan o'tishi.

    Oqim:
        1. Operator yangi haydovchi uchun User yaratadi (yoki mavjudini beradi)
        2. Bu serializer Driver profili + Wallet yaratadi
        3. Minimal depozit (10 000 so'm) Wallet ga yoziladi (keyinchalik
           haqiqiy to'lov bilan almashtiriladi)

    Kiruvchi maydonlar:
        user_id    -- mavjud User ning ID si (role=driver bo'lishi kerak)
        car_type   -- start | comfort | cargo
        car_number -- O'zbekiston davlat raqami
        car_model  -- mashina modeli (ixtiyoriy)
    """

    user_id    = serializers.IntegerField()
    car_type   = serializers.ChoiceField(choices=Driver.CarType.choices)
    car_number = serializers.CharField(max_length=10)
    car_model  = serializers.CharField(max_length=50, required=False, allow_blank=True)

    def validate_car_number(self, value: str) -> str:
        return validate_car_number(value)

    def validate_user_id(self, value: int) -> int:
        try:
            user = User.objects.get(pk=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Foydalanuvchi topilmadi.")

        if user.role != User.Role.DRIVER:
            raise serializers.ValidationError(
                f"Foydalanuvchi roli 'driver' bo'lishi kerak. "
                f"Hozirgi rol: '{user.get_role_display()}'."
            )
        if hasattr(user, "driver"):
            raise serializers.ValidationError(
                "Bu foydalanuvchi allaqachon haydovchi sifatida ro'yxatdan o'tgan."
            )
        return value

    def validate_car_type(self, value: str) -> str:
        # Tarif bazada mavjudligini tekshiramiz
        from tariffs.models import Tariff  # noqa: PLC0415
        if not Tariff.objects.filter(category=value, is_active=True).exists():
            raise serializers.ValidationError(
                f"'{value}' kategoriyasi uchun faol tarif topilmadi."
            )
        return value

    def create(self, validated_data: dict) -> Driver:
        """
        Driver profili va Wallet yaratadi.
        Wallet.balance = DEPOSIT_MIN (10 000 so'm) bilan boshlanadi.
        """
        from wallet.models import Transaction, Wallet  # noqa: PLC0415
        from django.db import transaction as db_tx  # noqa: PLC0415

        user = User.objects.get(pk=validated_data["user_id"])

        with db_tx.atomic():
            driver = Driver.objects.create(
                user       = user,
                car_type   = validated_data["car_type"],
                car_number = validated_data["car_number"],
                car_model  = validated_data.get("car_model", ""),
                is_active  = True,   # Boshlang'ich depozit kiritiladi, shu sababli aktiv
                is_online  = False,
            )

            wallet = Wallet.objects.create(
                driver  = driver,
                balance = Wallet.DEPOSIT_MIN,
            )

            # Boshlang'ich depozitni yozamiz
            Transaction.objects.create(
                wallet        = wallet,
                amount        = Wallet.DEPOSIT_MIN,
                tx_type       = Transaction.TxType.TOPUP,
                balance_after = Wallet.DEPOSIT_MIN,
            )

        logger.info(
            "Yangi haydovchi ro'yxatdan o'tdi: %s | %s | %s",
            user.phone, driver.car_number, driver.car_type,
        )
        return driver


# ======================================================================
# DriverProfileSerializer  -- batafsil ko'rish (read-only)
# ======================================================================

class DriverProfileSerializer(serializers.ModelSerializer):
    """
    Haydovchi profilini to'liq ko'rish uchun.
    User, Driver va Wallet ma'lumotlari birlashtirilgan.
    """

    phone      = serializers.CharField(source="user.phone",       read_only=True)
    first_name = serializers.CharField(source="user.first_name",  read_only=True)
    last_name  = serializers.CharField(source="user.last_name",   read_only=True)
    balance    = serializers.IntegerField(source="wallet.balance", read_only=True, default=0)
    is_wallet_sufficient = serializers.BooleanField(
        source="wallet.is_sufficient", read_only=True, default=False
    )
    car_type_display = serializers.CharField(source="get_car_type_display", read_only=True)

    # Aktiv buyurtmalar soni
    active_orders_count = serializers.SerializerMethodField()

    class Meta:
        model  = Driver
        fields = [
            "id",
            "phone",
            "first_name",
            "last_name",
            "car_type",
            "car_type_display",
            "car_model",
            "car_number",
            "is_active",
            "is_online",
            "balance",
            "is_wallet_sufficient",
            "current_lat",
            "current_lng",
            "location_updated_at",
            "active_orders_count",
            "joined_at",
        ]
        read_only_fields = fields

    def get_active_orders_count(self, obj: Driver) -> int:
        """Haydovchining hozirda aktiv (yakunlanmagan) buyurtmalari soni."""
        from orders.models import Order  # noqa: PLC0415
        return obj.driver_orders.exclude(
            status__in=[Order.Status.DONE, Order.Status.CANCELLED]
        ).count()


# ======================================================================
# DriverUpdateSerializer  -- mashina ma'lumotlarini yangilash
# ======================================================================

class DriverUpdateSerializer(serializers.ModelSerializer):
    """
    Haydovchi o'z mashina ma'lumotlarini yangilashi uchun.
    Faqat car_model va car_number o'zgartirilishi mumkin.
    car_type va is_active operator tomonidan boshqariladi.
    """

    car_number = serializers.CharField(max_length=10, required=False)

    class Meta:
        model  = Driver
        fields = ["car_model", "car_number"]

    def validate_car_number(self, value: str) -> str:
        cleaned = validate_car_number(value)
        # Boshqa haydovchida bu raqam yo'qligini tekshiramiz
        qs = Driver.objects.filter(car_number=cleaned)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Bu davlat raqami allaqachon ro'yxatdan o'tgan."
            )
        return cleaned


# ======================================================================
# DriverListSerializer  -- operator ro'yxati (yengil)
# ======================================================================

class DriverListSerializer(serializers.ModelSerializer):
    """
    Operator paneli uchun haydovchilar ro'yxati.
    Faqat asosiy maydonlar — tez yuklanadi.
    """

    phone            = serializers.CharField(source="user.phone",       read_only=True)
    full_name        = serializers.SerializerMethodField()
    balance          = serializers.IntegerField(source="wallet.balance", read_only=True, default=0)
    car_type_display = serializers.CharField(source="get_car_type_display", read_only=True)

    class Meta:
        model  = Driver
        fields = [
            "id",
            "phone",
            "full_name",
            "car_type",
            "car_type_display",
            "car_number",
            "is_active",
            "is_online",
            "balance",
        ]

    def get_full_name(self, obj: Driver) -> str:
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.phone


# ======================================================================
# DriverStatusSerializer  -- onlayn/offline toggle
# ======================================================================

class DriverStatusSerializer(serializers.Serializer):
    """
    Haydovchi o'zini onlayn yoki offline qilishi uchun.

    Qoida:
        is_active=False bo'lsa onlayn bo'la olmaydi
        (anti-debt bloki faol).

    Request body:
        { "is_online": true }
    """

    is_online = serializers.BooleanField()

    def validate(self, attrs: dict) -> dict:
        driver = self.context["driver"]

        if attrs["is_online"] and not driver.is_active:
            raise serializers.ValidationError(
                {
                    "is_online": (
                        "Hamyoningiz balansi yetarli emas. "
                        "Onlayn bo'lish uchun kamida 5 000 so'm bo'lishi kerak."
                    )
                }
            )
        return attrs


# ======================================================================
# NearbyDriverSerializer  -- yaqin haydovchilar (buyurtma uchun)
# ======================================================================

class NearbyDriverSerializer(serializers.ModelSerializer):
    """
    Buyurtma paytida yaqin aktiv haydovchilarni ko'rish uchun.
    Faqat is_active=True va is_online=True haydovchilar qaytariladi.
    Masofa view tomonidan annotate qilinadi.
    """

    phone            = serializers.CharField(source="user.phone",       read_only=True)
    full_name        = serializers.SerializerMethodField()
    car_type_display = serializers.CharField(source="get_car_type_display", read_only=True)
    distance_km      = serializers.FloatField(read_only=True, default=None)

    class Meta:
        model  = Driver
        fields = [
            "id",
            "phone",
            "full_name",
            "car_type",
            "car_type_display",
            "car_number",
            "car_model",
            "current_lat",
            "current_lng",
            "distance_km",
        ]

    def get_full_name(self, obj: Driver) -> str:
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.phone