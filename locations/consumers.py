"""
locations/consumers.py

WebSocket consumers — real-time GPS oqimi.

Ikki consumer:

1. DriverLocationConsumer  (/ws/driver/location/)
   - Haydovchi Android ilovasi ulanadi
   - GPS koordinatalarini yuboradi (har 3-5 soniyada)
   - DriverLocation (so'nggi nuqta) yangilanadi
   - LocationHistory ga yoziladi
   - GPS spoofing tekshiriladi (tezlik > 200 km/s)
   - Operator xarita guruhiga broadcast qilinadi

2. MapConsumer  (/ws/map/)
   - Operator React paneli ulanadi
   - Barcha aktiv haydovchilarning joylashuvini real-time ko'radi
   - Faqat o'qish (haydovchi yuborgan ma'lumotlarni qabul qiladi)

Xavfsizlik:
   - JWTWebsocketMiddleware: Authorization: Bearer <token> header
     yoki ?token=<access_token> query param orqali autentifikatsiya
   - Rol tekshiruvi: driver -> DriverLocationConsumer
                     operator/admin -> MapConsumer

Kanal arxitekturasi:
   haydovchi → DriverLocationConsumer → channel_layer
             → group: "map_operators" → MapConsumer → operator ekrani
"""

import json
import logging
from datetime import timedelta

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

logger = logging.getLogger(__name__)

# Operator xarita guruhi nomi
_MAP_GROUP = "map_operators"

# GPS spoofing aniqlash: km/s dagi maksimal ruxsat etilgan tezlik
_MAX_SPEED_KMH = 200.0

# LocationHistory saqlash oralig'i: ketma-ket yozuvlar orasidagi minimal vaqt (soniya)
# (har soniyada yozish DB ni tiqilib qoldiradi)
_HISTORY_INTERVAL_SEC = 5


# ======================================================================
# DriverLocationConsumer
# ======================================================================

class DriverLocationConsumer(AsyncWebsocketConsumer):
    """
    Haydovchi GPS ma'lumotlarini qabul qiluvchi WebSocket consumer.

    URL: /ws/driver/location/

    Kiruvchi xabar formati (JSON):
        {
            "lat": 41.299500,
            "lng": 69.240100,
            "speed_kmh": 45.2,      -- ixtiyoriy (Android GPS dan)
            "order_id": 123         -- ixtiyoriy, aktiv buyurtma bo'lsa
        }

    Chiquvchi xabar (tasdiq):
        { "status": "ok", "updated_at": "2024-01-15T10:30:00Z" }

    Xato xabari:
        { "status": "error", "message": "..." }
    """

    async def connect(self) -> None:
        """
        WebSocket ulanish.
        Faqat autentifikatsiya qilingan haydovchilar ulanishi mumkin.
        """
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            logger.warning("WS ulanish rad etildi: autentifikatsiya yo'q.")
            await self.close(code=4001)
            return

        if user.role != user.Role.DRIVER:
            logger.warning(
                "WS ulanish rad etildi: %s driver emas (%s).",
                user.phone, user.role,
            )
            await self.close(code=4003)
            return

        driver = await self._get_driver(user)
        if driver is None:
            logger.warning("WS: %s uchun Driver profili topilmadi.", user.phone)
            await self.close(code=4004)
            return

        self.driver    = driver
        self.driver_id = driver.pk
        self.user      = user

        # Operator xarita guruhiga qo'shilish (broadcast uchun)
        await self.channel_layer.group_add(_MAP_GROUP, self.channel_name)

        await self.accept()
        logger.info("WS ulandi: haydovchi=%s", user.phone)

    async def disconnect(self, close_code: int) -> None:
        """
        Uzilganda haydovchini offline qilish va guruhdan chiqarish.
        """
        if hasattr(self, "driver_id"):
            await self._set_driver_offline(self.driver_id)
            await self.channel_layer.group_discard(_MAP_GROUP, self.channel_name)
            logger.info(
                "WS uzildi: haydovchi=%s | kod=%s",
                getattr(self, "user", {}).phone if hasattr(self, "user") else "?",
                close_code,
            )

    async def receive(self, text_data: str = None, bytes_data: bytes = None) -> None:
        """
        Haydovchidan GPS ma'lumotlarini qabul qiladi.
        """
        # JSON parse
        try:
            data = json.loads(text_data or "{}")
        except json.JSONDecodeError:
            await self._send_error("JSON formati noto'g'ri.")
            return

        lat      = data.get("lat")
        lng      = data.get("lng")
        speed    = float(data.get("speed_kmh", 0.0))
        order_id = data.get("order_id")

        # Koordinata validatsiyasi
        if not _is_valid_coord(lat, lng):
            await self._send_error("lat va lng to'g'ri son bo'lishi kerak.")
            return

        lat   = float(lat)
        lng   = float(lng)
        speed = abs(speed)

        # GPS spoofing tekshiruvi
        if speed > _MAX_SPEED_KMH:
            logger.warning(
                "GPS spoofing shubhasi: haydovchi=%s tezlik=%.1f km/s",
                self.user.phone, speed,
            )
            await self._send_error(
                f"Tezlik chegaradan oshdi ({speed:.0f} km/s). "
                "GPS ma'lumoti rad etildi."
            )
            return

        # DB yangilash
        updated_at = await self._update_location(lat, lng, speed, order_id)

        # Operator panelga broadcast
        await self.channel_layer.group_send(
            _MAP_GROUP,
            {
                "type":      "driver_location_update",
                "driver_id": self.driver_id,
                "lat":       lat,
                "lng":       lng,
                "speed_kmh": speed,
                "order_id":  order_id,
                "updated_at": updated_at.isoformat() if updated_at else None,
            },
        )

        # Haydovchiga tasdiq
        await self.send(json.dumps({
            "status":     "ok",
            "updated_at": updated_at.isoformat() if updated_at else None,
        }))

    # ------------------------------------------------------------------
    # Operator xaritasidan kelgan xabar handler (group_send type)
    # ------------------------------------------------------------------

    async def driver_location_update(self, event: dict) -> None:
        """
        Bu consumer MapConsumer dan kelgan xabarlarni qabul qilmaydi.
        Faqat MapConsumer shu eventni ishlatadi.
        """
        pass  # DriverLocationConsumer faqat yuboradi, qabul qilmaydi

    # ------------------------------------------------------------------
    # Yordamchi metodlar
    # ------------------------------------------------------------------

    async def _send_error(self, message: str) -> None:
        await self.send(json.dumps({"status": "error", "message": message}))

    @database_sync_to_async
    def _get_driver(self, user):
        from drivers.models import Driver  # noqa: PLC0415
        try:
            return Driver.objects.select_related("user").get(user=user)
        except Driver.DoesNotExist:
            return None

    @database_sync_to_async
    def _update_location(self, lat: float, lng: float, speed: float, order_id):
        """
        DriverLocation (so'nggi nuqta) yangilaydi va
        LocationHistory ga yozadi (har 5 soniyada).
        """
        from django.db import transaction  # noqa: PLC0415
        from drivers.models import Driver  # noqa: PLC0415
        from .models import DriverLocation, LocationHistory  # noqa: PLC0415

        now = timezone.now()

        with transaction.atomic():
            # So'nggi joylashuvni yangilash (upsert)
            DriverLocation.objects.update_or_create(
                driver=self.driver,
                defaults={
                    "lat":       lat,
                    "lng":       lng,
                    "speed_kmh": speed,
                },
            )

            # Driver modelidagi current_lat/lng ham yangilash
            Driver.objects.filter(pk=self.driver_id).update(
                current_lat         = lat,
                current_lng         = lng,
                location_updated_at = now,
            )

            # LocationHistory: oxirgi yozuvdan _HISTORY_INTERVAL_SEC o'tgan bo'lsa yoz
            last = (
                LocationHistory.objects
                .filter(driver=self.driver)
                .order_by("-timestamp")
                .first()
            )
            interval = timedelta(seconds=_HISTORY_INTERVAL_SEC)
            should_write = (
                last is None
                or (now - last.timestamp) >= interval
            )

            if should_write:
                order = None
                if order_id:
                    from orders.models import Order  # noqa: PLC0415
                    try:
                        order = Order.objects.get(pk=order_id)
                    except Order.DoesNotExist:
                        pass

                LocationHistory.objects.create(
                    driver    = self.driver,
                    lat       = lat,
                    lng       = lng,
                    order     = order,
                )

        return now

    @database_sync_to_async
    def _set_driver_offline(self, driver_id: int) -> None:
        from drivers.models import Driver  # noqa: PLC0415
        Driver.objects.filter(pk=driver_id).update(is_online=False)


# ======================================================================
# MapConsumer  -- Operator xarita paneli
# ======================================================================

class MapConsumer(AsyncWebsocketConsumer):
    """
    Operator xarita paneli uchun WebSocket consumer.

    URL: /ws/map/

    Operator faqat qabul qiladi — yuborishga hojat yo'q.

    Chiquvchi xabar formati:
        {
            "type": "driver_location_update",
            "driver_id": 42,
            "lat": 41.2995,
            "lng": 69.2401,
            "speed_kmh": 45.2,
            "order_id": 123,
            "updated_at": "2024-01-15T10:30:00Z"
        }
    """

    async def connect(self) -> None:
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        if user.role not in (user.Role.OPERATOR, user.Role.ADMIN):
            logger.warning(
                "MapConsumer: %s operator emas, ulanish rad etildi.",
                user.phone,
            )
            await self.close(code=4003)
            return

        self.user = user
        await self.channel_layer.group_add(_MAP_GROUP, self.channel_name)
        await self.accept()

        # Ulanishda barcha aktiv haydovchilarning so'nggi joylashuvini yuborish
        locations = await self._get_all_active_locations()
        if locations:
            await self.send(json.dumps({
                "type":      "initial_locations",
                "locations": locations,
            }))

        logger.info("MapConsumer ulandi: operator=%s", user.phone)

    async def disconnect(self, close_code: int) -> None:
        await self.channel_layer.group_discard(_MAP_GROUP, self.channel_name)
        logger.info(
            "MapConsumer uzildi: %s | kod=%s",
            getattr(self, "user", {}).phone if hasattr(self, "user") else "?",
            close_code,
        )

    async def receive(self, text_data: str = None, bytes_data: bytes = None) -> None:
        """Operator faqat o'qiydi, yuborishga hojat yo'q."""
        pass

    async def driver_location_update(self, event: dict) -> None:
        """
        DriverLocationConsumer dan broadcast kelganda
        operator brauzeriga yuboradi.
        """
        await self.send(json.dumps(event))

    @database_sync_to_async
    def _get_all_active_locations(self) -> list:
        """
        Ulanishda barcha aktiv va onlayn haydovchilarning
        so'nggi joylashuvini bir yo'la qaytaradi.
        """
        from .models import DriverLocation  # noqa: PLC0415

        locations = (
            DriverLocation.objects
            .filter(
                driver__is_active=True,
                driver__is_online=True,
            )
            .select_related("driver", "driver__user")
            .values(
                "driver_id",
                "lat",
                "lng",
                "speed_kmh",
                "updated_at",
                "driver__car_type",
                "driver__car_number",
                "driver__user__phone",
            )
        )

        result = []
        for loc in locations:
            result.append({
                "driver_id":  loc["driver_id"],
                "lat":        float(loc["lat"]),
                "lng":        float(loc["lng"]),
                "speed_kmh":  loc["speed_kmh"],
                "car_type":   loc["driver__car_type"],
                "car_number": loc["driver__car_number"],
                "phone":      loc["driver__user__phone"],
                "updated_at": loc["updated_at"].isoformat() if loc["updated_at"] else None,
            })
        return result


# ======================================================================
# Yordamchi funksiya
# ======================================================================

def _is_valid_coord(lat, lng) -> bool:
    """lat va lng mavjud, son va to'g'ri diapazondaligini tekshiradi."""
    try:
        lat = float(lat)
        lng = float(lng)
        return (-90 <= lat <= 90) and (-180 <= lng <= 180)
    except (TypeError, ValueError):
        return False