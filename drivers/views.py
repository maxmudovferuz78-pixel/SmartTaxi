"""
drivers/views.py

Haydovchi boshqaruv API.

Endpointlar:
    POST   /api/drivers/                       -- Yangi haydovchi (IsOperator)
    GET    /api/drivers/                       -- Ro'yxat (IsOperator)
    GET    /api/drivers/{id}/                  -- Batafsil (IsOperator | IsDriver)
    PATCH  /api/drivers/{id}/                  -- Yangilash (IsDriver o'zi | IsOperator)
    GET    /api/drivers/me/                    -- O'z profili (IsDriver)
    PATCH  /api/drivers/me/status/             -- Onlayn/offline (IsDriver)
    PATCH  /api/drivers/{id}/toggle_active/    -- Bloklash/faollashtirish (IsOperator)
    GET    /api/drivers/nearby/                -- Yaqin haydovchilar (IsOperator)
"""

import logging

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.permissions import IsDriver, IsOperator

from .models import Driver
from drf_spectacular.utils import extend_schema
from drivers.schema import (
    driver_viewset_schema,
    me_schema,
    set_status_schema as driver_set_status_schema,
    nearby_schema,
    toggle_active_schema,
)
from .serializers import (
    DriverListSerializer,
    DriverProfileSerializer,
    DriverRegisterSerializer,
    DriverStatusSerializer,
    DriverUpdateSerializer,
    NearbyDriverSerializer,
)

logger = logging.getLogger(__name__)


@driver_viewset_schema
class DriverViewSet(viewsets.ModelViewSet):
    """
    Haydovchilar uchun to'liq CRUD ViewSet.

    Serializer strategiyasi:
        create         -> DriverRegisterSerializer
        list           -> DriverListSerializer
        retrieve       -> DriverProfileSerializer
        update/partial -> DriverUpdateSerializer
        me             -> DriverProfileSerializer
        set_status     -> DriverStatusSerializer
        toggle_active  -> ichki (is_active toggle)
        nearby         -> NearbyDriverSerializer
    """

    queryset = Driver.objects.select_related(
        "user", "wallet"
    ).order_by("-joined_at")

    permission_classes = [IsOperator]

    # ------------------------------------------------------------------
    # Serializer tanlash
    # ------------------------------------------------------------------

    def get_serializer_class(self):
        if self.action == "create":
            return DriverRegisterSerializer
        if self.action in ("retrieve", "me"):
            return DriverProfileSerializer
        if self.action in ("update", "partial_update"):
            return DriverUpdateSerializer
        if self.action == "set_status":
            return DriverStatusSerializer
        if self.action == "nearby":
            return NearbyDriverSerializer
        return DriverListSerializer

    # ------------------------------------------------------------------
    # create  -- yangi haydovchi ro'yxatdan o'tkazish
    # ------------------------------------------------------------------

    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        POST /api/drivers/

        Yangi haydovchi ro'yxatdan o'tkazadi.
        Driver profili + Wallet avtomatik yaratiladi.
        Faqat operatorlar uchun.

        Request body:
            {
                "user_id": 5,
                "car_type": "comfort",
                "car_number": "01A123BC",
                "car_model": "Chevrolet Malibu"
            }

        Response 201:
            Haydovchining to'liq profili.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        driver = serializer.save()

        logger.info(
            "Yangi haydovchi ro'yxatdan o'tdi: #%s | operator=%s",
            driver.pk, request.user.phone,
        )

        return Response(
            DriverProfileSerializer(driver).data,
            status=status.HTTP_201_CREATED,
        )

    # ------------------------------------------------------------------
    # list  -- haydovchilar ro'yxati (filtrlash bilan)
    # ------------------------------------------------------------------

    def list(self, request: Request, *args, **kwargs) -> Response:
        """
        GET /api/drivers/

        Query parametrlari:
            ?car_type=start|comfort|cargo
            ?is_active=true|false
            ?is_online=true|false
        """
        qs = self.get_queryset()

        car_type  = request.query_params.get("car_type")
        is_active = request.query_params.get("is_active")
        is_online = request.query_params.get("is_online")

        if car_type:
            qs = qs.filter(car_type=car_type)
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        if is_online is not None:
            qs = qs.filter(is_online=is_online.lower() == "true")

        serializer = DriverListSerializer(qs, many=True)
        return Response(serializer.data)

    # ------------------------------------------------------------------
    # me  -- haydovchi o'z profilini ko'radi
    # ------------------------------------------------------------------

    @me_schema
    @action(
        detail=False,
        methods=["get"],
        url_path="me",
        permission_classes=[IsDriver],
    )
    def me(self, request: Request) -> Response:
        """
        GET /api/drivers/me/

        Haydovchi o'z profilini, balansini va aktiv buyurtmalarini ko'radi.

        Response 200:
            DriverProfileSerializer ma'lumotlari.

        Response 404:
            Haydovchi profili topilmadi (driver ro'li bor lekin profil yo'q).
        """
        driver = getattr(request.user, "driver", None)
        if driver is None:
            return Response(
                {"detail": "Haydovchi profili topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = DriverProfileSerializer(driver)
        return Response(serializer.data)

    # ------------------------------------------------------------------
    # set_status  -- onlayn / offline toggle
    # ------------------------------------------------------------------

    @driver_set_status_schema
    @action(
        detail=False,
        methods=["patch"],
        url_path="me/status",
        permission_classes=[IsDriver],
    )
    def set_status(self, request: Request) -> Response:
        """
        PATCH /api/drivers/me/status/

        Haydovchi o'zini onlayn yoki offline qiladi.

        Qoidalar:
            is_active=False bo'lsa onlayn bo'la olmaydi.
            Offline bo'lganda current_lat/lng tozalanmaydi
            (xaritada oxirgi joylashuv saqlanadi).

        Request body:
            { "is_online": true }

        Response 200:
            { "is_online": true, "message": "..." }

        Response 400:
            Balans yetarli emas (anti-debt bloki).
        """
        driver = getattr(request.user, "driver", None)
        if driver is None:
            return Response(
                {"detail": "Haydovchi profili topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = DriverStatusSerializer(
            data=request.data,
            context={"driver": driver},
        )
        serializer.is_valid(raise_exception=True)

        is_online = serializer.validated_data["is_online"]
        driver.is_online = is_online
        driver.save(update_fields=["is_online"])

        action_str = "onlayn" if is_online else "offline"
        logger.info("Haydovchi %s %s bo'ldi.", request.user.phone, action_str)

        return Response(
            {
                "is_online": is_online,
                "message":   f"Siz {action_str} holatga o'tdingiz.",
            },
            status=status.HTTP_200_OK,
        )

    # ------------------------------------------------------------------
    # update_profile  -- haydovchi o'z mashina ma'lumotlarini yangilaydi
    # ------------------------------------------------------------------

    @extend_schema(tags=["drivers"], summary="Mashina ma'lumotlarini yangilash")
    @action(
        detail=False,
        methods=["patch"],
        url_path="me/profile",
        permission_classes=[IsDriver],
    )
    def update_profile(self, request: Request) -> Response:
        """
        PATCH /api/drivers/me/profile/

        Haydovchi o'z mashina ma'lumotlarini yangilaydi.
        Faqat car_model va car_number o'zgartirilishi mumkin.

        Request body:
            { "car_model": "Chevrolet Malibu 2022", "car_number": "01B456CD" }

        Response 200:
            Yangilangan profil.
        """
        driver = getattr(request.user, "driver", None)
        if driver is None:
            return Response(
                {"detail": "Haydovchi profili topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = DriverUpdateSerializer(
            driver,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        logger.info(
            "Haydovchi profili yangilandi: %s", request.user.phone
        )

        return Response(
            DriverProfileSerializer(driver).data,
            status=status.HTTP_200_OK,
        )

    # ------------------------------------------------------------------
    # toggle_active  -- operator haydovchini bloklaydi / faollashtiradi
    # ------------------------------------------------------------------

    @toggle_active_schema
    @action(
        detail=True,
        methods=["patch"],
        url_path="toggle_active",
        permission_classes=[IsOperator],
    )
    def toggle_active(self, request: Request, pk=None) -> Response:
        """
        PATCH /api/drivers/{id}/toggle_active/

        Operator haydovchini bloklaydi yoki qayta faollashtiradi.
        Bloklaganda is_online ham False ga o'zgartiriladi.

        Request body (ixtiyoriy):
            { "reason": "Balans uchun qo'lda bloklash" }

        Response 200:
            {
                "id": 1,
                "is_active": false,
                "is_online": false,
                "message": "Haydovchi bloklandi."
            }
        """
        driver    = self.get_object()
        new_state = not driver.is_active

        update_fields = ["is_active"]
        driver.is_active = new_state

        if not new_state:
            driver.is_online = False
            update_fields.append("is_online")

        driver.save(update_fields=update_fields)

        action_str = "faollashtirildi" if new_state else "bloklandi"
        reason = request.data.get("reason", "")

        logger.info(
            "Haydovchi #%s %s | operator=%s%s",
            driver.pk, action_str, request.user.phone,
            f" | sabab: {reason}" if reason else "",
        )

        return Response(
            {
                "id":        driver.pk,
                "is_active": driver.is_active,
                "is_online": driver.is_online,
                "message":   f"Haydovchi {action_str}.",
            },
            status=status.HTTP_200_OK,
        )

    # ------------------------------------------------------------------
    # nearby  -- yaqin aktiv haydovchilar
    # ------------------------------------------------------------------

    @nearby_schema
    @action(
        detail=False,
        methods=["get"],
        url_path="nearby",
        permission_classes=[IsOperator],
    )
    def nearby(self, request: Request) -> Response:
        """
        GET /api/drivers/nearby/?lat=41.2995&lng=69.2401&car_type=comfort

        Berilgan koordinatga yaqin aktiv va onlayn haydovchilarni qaytaradi.
        Masofa Haversine formulasi bilan hisoblanadi.

        Query parametrlari (majburiy):
            lat      -- kenglik
            lng      -- uzunlik
        Query parametrlari (ixtiyoriy):
            car_type -- start | comfort | cargo
            radius   -- km, sukut: 10

        Response 200:
            Masofaga ko'ra tartiblangan haydovchilar ro'yxati.
        """
        from tariffs.utils import calculate_distance  # noqa: PLC0415

        lat_str = request.query_params.get("lat")
        lng_str = request.query_params.get("lng")

        if not lat_str or not lng_str:
            return Response(
                {"detail": "lat va lng parametrlari majburiy."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            lat = float(lat_str)
            lng = float(lng_str)
        except ValueError:
            return Response(
                {"detail": "lat va lng son bo'lishi kerak."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        radius   = float(request.query_params.get("radius", 10))
        car_type = request.query_params.get("car_type")

        qs = Driver.objects.filter(
            is_active=True,
            is_online=True,
            current_lat__isnull=False,
            current_lng__isnull=False,
        ).select_related("user")

        if car_type:
            qs = qs.filter(car_type=car_type)

        # Masofani hisoblash va filtrlash (Python darajasida)
        # Ko'p haydovchi bo'lsa PostGIS ishlatish tavsiya etiladi
        nearby_drivers = []
        for driver in qs:
            try:
                dist = calculate_distance(
                    lat, lng,
                    float(driver.current_lat),
                    float(driver.current_lng),
                )
                if dist <= radius:
                    driver.distance_km = dist
                    nearby_drivers.append(driver)
            except (ValueError, TypeError):
                continue

        # Masofaga ko'ra tartiblash
        nearby_drivers.sort(key=lambda d: d.distance_km)

        serializer = NearbyDriverSerializer(nearby_drivers, many=True)
        return Response(
            {
                "count":   len(nearby_drivers),
                "radius":  radius,
                "results": serializer.data,
            }
        )

    # ------------------------------------------------------------------
    # update / partial_update  -- operator tomonidan yangilash
    # ------------------------------------------------------------------

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        """
        PATCH /api/drivers/{id}/

        Operator haydovchi ma'lumotlarini yangilaydi.
        """
        driver     = self.get_object()
        serializer = DriverUpdateSerializer(
            driver, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        logger.info(
            "Haydovchi #%s yangilandi | operator=%s",
            driver.pk, request.user.phone,
        )

        return Response(
            DriverProfileSerializer(driver).data,
            status=status.HTTP_200_OK,
        )

    def update(self, request: Request, *args, **kwargs) -> Response:
        kwargs["partial"] = True
        return self.partial_update(request, *args, **kwargs)