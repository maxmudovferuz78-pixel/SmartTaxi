"""
tariffs/views.py

Tarif boshqaruv API.

Endpointlar:
    GET    /api/tariffs/              -- Barcha tariflar ro'yxati (IsAuthenticated)
    GET    /api/tariffs/{id}/         -- Bitta tarif (IsAuthenticated)
    POST   /api/tariffs/              -- Yangi tarif (IsAdminUser)
    PUT    /api/tariffs/{id}/         -- Yangilash (IsAdminUser)
    PATCH  /api/tariffs/{id}/         -- Qisman yangilash (IsAdminUser)
    POST   /api/tariffs/calculate/    -- Narx hisoblash (IsAuthenticated)
"""

import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.permissions import IsAdminUser

from .models import Tariff
from tariffs.schema import tariff_viewset_schema, calculate_schema
from .serializers import (
    FareCalculateSerializer,
    TariffSerializer,
    TariffWriteSerializer,
)

logger = logging.getLogger(__name__)


@tariff_viewset_schema
class TariffViewSet(viewsets.ModelViewSet):
    """
    Tariflar uchun CRUD ViewSet.

    Ko'rish (GET)   -- barcha autentifikatsiya foydalanuvchilar
    Yozish (POST/PUT/PATCH/DELETE) -- faqat admin
    """

    queryset = Tariff.objects.all().order_by("category")

    def get_permissions(self):
        """
        Ko'rish endpointlari uchun IsAuthenticated,
        o'zgartirish endpointlari uchun IsAdminUser.
        """
        if self.action in ("list", "retrieve", "calculate"):
            return [IsAuthenticated()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return TariffWriteSerializer
        if self.action == "calculate":
            return FareCalculateSerializer
        return TariffSerializer

    # ------------------------------------------------------------------
    # list  -- barcha faol tariflar
    # ------------------------------------------------------------------

    def list(self, request: Request, *args, **kwargs) -> Response:
        """
        GET /api/tariffs/

        Query parametrlari:
            ?is_active=true|false  -- faol/faolsiz filtri (sukut: hammasi)
        """
        qs = self.get_queryset()

        is_active = request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")

        serializer = TariffSerializer(qs, many=True)
        return Response(serializer.data)

    # ------------------------------------------------------------------
    # create  -- yangi tarif (admin)
    # ------------------------------------------------------------------

    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        POST /api/tariffs/

        Yangi kategoriya uchun tarif yaratadi.
        Har bir kategoriya (start/comfort/cargo) faqat bitta marta bo'ladi.

        Request body:
            {
                "category": "start",
                "base_fare": 4000,
                "per_km": 1800,
                "rush_fee_low": 3000,
                "rush_fee_high": 5000
            }
        """
        serializer = TariffWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tariff = serializer.save()

        logger.info(
            "Yangi tarif yaratildi: %s | admin=%s",
            tariff.category, request.user.phone,
        )

        return Response(
            TariffSerializer(tariff).data,
            status=status.HTTP_201_CREATED,
        )

    # ------------------------------------------------------------------
    # update / partial_update  -- tarif yangilash (admin)
    # ------------------------------------------------------------------

    def update(self, request: Request, *args, **kwargs) -> Response:
        kwargs["partial"] = True
        return self.partial_update(request, *args, **kwargs)

    def partial_update(self, request: Request, *args, **kwargs) -> Response:
        """
        PATCH /api/tariffs/{id}/

        Tarif narxlarini yangilaydi.
        category maydoni o'zgartirilmaydi (unique constraint).
        """
        tariff = self.get_object()
        serializer = TariffWriteSerializer(
            tariff, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        logger.info(
            "Tarif yangilandi: %s | admin=%s",
            tariff.category, request.user.phone,
        )

        return Response(
            TariffSerializer(tariff).data,
            status=status.HTTP_200_OK,
        )

    # ------------------------------------------------------------------
    # calculate  -- narxni oldindan hisoblash
    # ------------------------------------------------------------------

    @calculate_schema
    @action(
        detail=False,
        methods=["post"],
        url_path="calculate",
        permission_classes=[IsAuthenticated],
    )
    def calculate(self, request: Request) -> Response:
        """
        POST /api/tariffs/calculate/

        Buyurtma bermasdan oldin taxminiy narxni hisoblaydi.
        Operator manzilni kiritganda darhol narxni ko'radi.

        Request body:
            {
                "from_lat": 41.2995, "from_lng": 69.2401,
                "to_lat":   41.3600, "to_lng":   69.2835,
                "car_type": "comfort",
                "rush_fee": 3000
            }

        Response 200:
            {
                "distance_km": 7.82,
                "base_fare": 6500,
                "per_km": 2400,
                "fare_no_rush": 25268,
                "fare_with_rush": 28268,
                "commission": 2826,
                "rush_fee": 3000
            }
        """
        serializer = FareCalculateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = serializer.validated_data["_result"]

        logger.debug(
            "Narx hisoblandi: car_type=%s dist=%.2fkm total=%s",
            request.data.get("car_type"),
            result["distance_km"],
            result["fare_with_rush"],
        )

        return Response(result, status=status.HTTP_200_OK)

    # ------------------------------------------------------------------
    # destroy  -- tarif o'chirish o'rniga faolsizlashtirish
    # ------------------------------------------------------------------

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """
        DELETE /api/tariffs/{id}/

        Tarif o'chirilmaydi, faqat is_active=False qilinadi.
        Ma'lumotlar bazasida tarixiy buyurtmalar uchun saqlanadi.
        """
        tariff = self.get_object()

        if not tariff.is_active:
            return Response(
                {"detail": "Tarif allaqachon faolsiz."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        tariff.is_active = False
        tariff.save(update_fields=["is_active", "updated_at"])

        logger.info(
            "Tarif faolsizlashtirildi: %s | admin=%s",
            tariff.category, request.user.phone,
        )

        return Response(
            {"detail": f"'{tariff.get_category_display()}' tarifi faolsizlashtirildi."},
            status=status.HTTP_200_OK,
        )