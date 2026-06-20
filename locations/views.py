"""
locations/views.py

Joylashuv REST API endpointlari (HTTP).

WebSocket oqimi consumers.py da — bu yerda faqat HTTP endpointlari.

Endpointlar:
    GET /api/locations/                    -- Barcha aktiv haydovchilar (IsOperator)
    GET /api/locations/{driver_id}/        -- Bitta haydovchi so'nggi joylashuvi (IsOperator)
    GET /api/locations/{driver_id}/history/ -- GPS tarixi (IsOperator)
"""

import logging

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsDriver, IsOperator

from .models import DriverLocation, LocationHistory
from .serializers import DriverLocationSerializer, LocationHistorySerializer
from .schema import (
    active_locations_schema,
    driver_location_detail_schema,
    location_history_schema,
    my_location_schema,
)

logger = logging.getLogger(__name__)

_HISTORY_PAGE_SIZE = 50


@active_locations_schema
class ActiveLocationsView(APIView):
    """
    GET /api/locations/

    Barcha aktiv va onlayn haydovchilarning so'nggi joylashuvlari.
    Operator panelida xaritani yuklashda ishlatiladi (HTTP fallback).
    Real-time uchun WebSocket /ws/map/ ishlatiladi.

    Response 200:
        { "count": 5, "results": [ ...DriverLocationSerializer... ] }
    """

    permission_classes = [IsOperator]

    def get(self, request: Request) -> Response:
        locations = (
            DriverLocation.objects
            .filter(
                driver__is_active=True,
                driver__is_online=True,
            )
            .select_related("driver", "driver__user")
        )

        car_type = request.query_params.get("car_type")
        if car_type:
            locations = locations.filter(driver__car_type=car_type)

        serializer = DriverLocationSerializer(locations, many=True)
        return Response(
            {"count": locations.count(), "results": serializer.data}
        )


@driver_location_detail_schema
class DriverLocationDetailView(APIView):
    """
    GET /api/locations/{driver_id}/

    Bitta haydovchining so'nggi joylashuvi.

    Response 200: DriverLocationSerializer
    Response 404: Joylashuv topilmadi
    """

    permission_classes = [IsOperator]

    def get(self, request: Request, driver_id: int) -> Response:
        try:
            loc = DriverLocation.objects.select_related(
                "driver", "driver__user"
            ).get(driver_id=driver_id)
        except DriverLocation.DoesNotExist:
            return Response(
                {"detail": "Bu haydovchi uchun joylashuv ma'lumoti topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(DriverLocationSerializer(loc).data)


@location_history_schema
class LocationHistoryView(APIView):
    """
    GET /api/locations/{driver_id}/history/

    Haydovchining GPS koordinatalar tarixi.
    TZ: 7 kun saqlanadi (clean_location_history Celery task tomonidan tozalanadi).

    Query parametrlari:
        ?limit=N     -- yozuvlar soni (max: 200, sukut: 50)
        ?order_id=N  -- faqat shu buyurtmadagi koordinatalar

    Response 200:
        { "count": 120, "results": [ ...LocationHistorySerializer... ] }
    """

    permission_classes = [IsOperator]

    def get(self, request: Request, driver_id: int) -> Response:
        from drivers.models import Driver  # noqa: PLC0415

        if not Driver.objects.filter(pk=driver_id).exists():
            return Response(
                {"detail": "Haydovchi topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        qs = LocationHistory.objects.filter(
            driver_id=driver_id
        ).select_related("order").order_by("-timestamp")

        order_id = request.query_params.get("order_id")
        if order_id:
            qs = qs.filter(order_id=order_id)

        try:
            limit = min(int(request.query_params.get("limit", _HISTORY_PAGE_SIZE)), 200)
        except (ValueError, TypeError):
            limit = _HISTORY_PAGE_SIZE

        total = qs.count()
        qs    = qs[:limit]

        serializer = LocationHistorySerializer(qs, many=True)
        return Response({"count": total, "results": serializer.data})


@my_location_schema
class MyLocationView(APIView):
    """
    GET /api/locations/me/

    Haydovchi o'z so'nggi joylashuvini ko'radi.

    Response 200: DriverLocationSerializer
    Response 404: Joylashuv hali yo'q (GPS yuborilmagan)
    """

    permission_classes = [IsDriver]

    def get(self, request: Request) -> Response:
        driver = getattr(request.user, "driver", None)
        if driver is None:
            return Response(
                {"detail": "Haydovchi profili topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            loc = DriverLocation.objects.select_related(
                "driver", "driver__user"
            ).get(driver=driver)
        except DriverLocation.DoesNotExist:
            return Response(
                {"detail": "Joylashuv ma'lumoti hali yuborilmagan."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(DriverLocationSerializer(loc).data)