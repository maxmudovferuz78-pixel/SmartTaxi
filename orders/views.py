"""
orders/views.py

Buyurtma boshqaruv API.

Endpointlar:
    POST   /api/orders/                    -- Yangi buyurtma (IsOperator)
    GET    /api/orders/                    -- Ro'yxat    (IsOperator)
    GET    /api/orders/{id}/               -- Batafsil   (IsOperator)
    PATCH  /api/orders/{id}/set_status/    -- Status FSM (IsDriver)
    PATCH  /api/orders/{id}/assign_driver/ -- Haydovchi biriktirish (IsOperator)

Ruxsatlar:
    create, list, retrieve, assign_driver -> IsOperator
    set_status                            -> IsDriver
    set_status (done holati)              -> IsDriver + IsActiveDriver
"""

import logging

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.permissions import IsActiveDriver, IsDriver, IsOperator

from .models import Order
from .serializers import (
    OrderCreateSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
    SetStatusSerializer,
)
from .schema import (
    order_viewset_schema,
    set_status_schema,
    assign_driver_schema,
)

logger = logging.getLogger(__name__)


@order_viewset_schema
class OrderViewSet(viewsets.ModelViewSet):
    """
    Buyurtmalar uchun to'liq CRUD ViewSet.

    Serializer strategiyasi:
        create        -> OrderCreateSerializer  (billing bilan)
        list          -> OrderListSerializer    (yengil, tez)
        retrieve      -> OrderDetailSerializer  (to'liq)
        set_status    -> SetStatusSerializer    (FSM)
        assign_driver -> ichki tekshirish
    """

    queryset = Order.objects.select_related(
        "client",
        "driver",
        "driver__user",
    ).order_by("-created_at")

    permission_classes = [IsOperator]

    # ------------------------------------------------------------------
    # Serializer tanlash
    # ------------------------------------------------------------------

    def get_serializer_class(self):
        if self.action == "create":
            return OrderCreateSerializer
        if self.action == "retrieve":
            return OrderDetailSerializer
        if self.action == "set_status":
            return SetStatusSerializer
        return OrderListSerializer

    # ------------------------------------------------------------------
    # create  -- yangi buyurtma + billing
    # ------------------------------------------------------------------

    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        POST /api/orders/

        Yangi buyurtma yaratadi. Narxni avtomatik hisoblaydi.
        Faqat operator va adminlar uchun.

        Request body:
            {
                "from_address": "Chilonzor 5",
                "from_lat": 41.2995, "from_lng": 69.2401,
                "to_address": "Yunusobod 7",
                "to_lat": 41.3600, "to_lng": 69.2835,
                "car_type": "comfort",
                "payment_type": "cash",
                "rush_fee": 3000
            }

        Response 201:
            Hisoblangan narx bilan to'liq buyurtma ma'lumotlari.
        """
        serializer = self.get_serializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()

        logger.info(
            "Yangi buyurtma #%s | operator=%s | %s | total=%s som",
            order.pk, request.user.phone, order.car_type, order.total_fare,
        )

        return Response(
            OrderDetailSerializer(order, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    # ------------------------------------------------------------------
    # list  -- buyurtmalar ro'yxati (filtrlash bilan)
    # ------------------------------------------------------------------

    def list(self, request: Request, *args, **kwargs) -> Response:
        """
        GET /api/orders/

        Query parametrlari:
            ?status=new|accepted|arrived|started|done|cancelled
            ?car_type=start|comfort|cargo
            ?driver_id=<int>
        """
        qs = self.get_queryset()

        order_status = request.query_params.get("status")
        car_type     = request.query_params.get("car_type")
        driver_id    = request.query_params.get("driver_id")

        if order_status:
            qs = qs.filter(status=order_status)
        if car_type:
            qs = qs.filter(car_type=car_type)
        if driver_id:
            qs = qs.filter(driver_id=driver_id)

        serializer = OrderListSerializer(qs, many=True)
        return Response(serializer.data)

    # ------------------------------------------------------------------
    # set_status  -- haydovchi FSM orqali status o'zgartiradi
    # ------------------------------------------------------------------

    @set_status_schema
    @action(
        detail=True,
        methods=["patch"],
        url_path="set_status",
        permission_classes=[IsDriver],
    )
    def set_status(self, request: Request, pk=None) -> Response:
        """
        PATCH /api/orders/{id}/set_status/

        Haydovchi buyurtma holatini ketma-ket o'zgartiradi.

        FSM qoidalari:
            new -> accepted -> arrived -> started -> done
            (istalgan bosqichda) -> cancelled

        Qo'shimcha:
            'done' holatiga o'tishdan oldin IsActiveDriver tekshiriladi
            (haydovchi balansi >= 5 000 so'm shart).

        Request body:
            { "status": "accepted" }

        Response 200:
            Yangilangan buyurtmaning to'liq ma'lumotlari.

        Response 400:
            { "status": ["Noto'g'ri o'tish..."] }

        Response 403:
            Balans yetarli emas YOKI boshqa haydovchining buyurtmasi.
        """
        order  = self.get_object()
        driver = getattr(request.user, "driver", None)

        # Faqat shu buyurtmaga biriktirilgan haydovchi o'zgartira olsin
        if order.driver is not None and driver and order.driver != driver:
            return Response(
                {"detail": "Siz bu buyurtmaga biriktirilmagan haydovchi emassiz."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = SetStatusSerializer(
            data=request.data,
            context={"order": order, "request": request},
        )
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data["status"]

        # 'done' uchun anti-debt tekshiruvi ----------------------------
        if new_status == Order.Status.DONE:
            active_perm = IsActiveDriver()
            if not active_perm.has_permission(request, self):
                wallet_balance = getattr(
                    getattr(driver, "wallet", None), "balance", None
                )
                return Response(
                    {
                        "detail": active_perm.message,
                        "current_balance": wallet_balance,
                        "minimum_required": 5_000,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        # Vaqt belgilarini yangilash -----------------------------------
        update_fields = ["status"]
        order.status  = new_status
        now = timezone.now()

        if new_status == Order.Status.ACCEPTED:
            order.accepted_at = now
            update_fields.append("accepted_at")
        elif new_status == Order.Status.STARTED:
            order.started_at = now
            update_fields.append("started_at")
        elif new_status == Order.Status.DONE:
            order.done_at = now
            update_fields.append("done_at")

        order.save(update_fields=update_fields)

        logger.info(
            "Buyurtma #%s | holat: %s | haydovchi=%s",
            order.pk, new_status, request.user.phone,
        )

        return Response(
            OrderDetailSerializer(order, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )

    # ------------------------------------------------------------------
    # assign_driver  -- operator haydovchi biriktiradi
    # ------------------------------------------------------------------

    @assign_driver_schema
    @action(
        detail=True,
        methods=["patch"],
        url_path="assign_driver",
        permission_classes=[IsOperator],
    )
    def assign_driver(self, request: Request, pk=None) -> Response:
        """
        PATCH /api/orders/{id}/assign_driver/

        Operator aktiv va onlayn haydovchini buyurtmaga biriktiradi.

        Request body:
            { "driver_id": 42 }

        Response 200:
            Yangilangan buyurtma (haydovchi bilan).

        Response 400:
            { "driver_id": "Faol va onlayn haydovchi topilmadi." }
        """
        from drivers.models import Driver  # noqa: PLC0415

        order     = self.get_object()
        driver_id = request.data.get("driver_id")

        if not driver_id:
            return Response(
                {"driver_id": "Bu maydon majburiy."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            driver = Driver.objects.select_related("user").get(
                pk=driver_id,
                is_active=True,
                is_online=True,
            )
        except Driver.DoesNotExist:
            return Response(
                {"driver_id": "Faol va onlayn haydovchi topilmadi."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.driver = driver
        order.save(update_fields=["driver"])

        logger.info(
            "Buyurtma #%s ga haydovchi biriktirildi: %s",
            order.pk, driver.user.phone,
        )

        return Response(
            OrderDetailSerializer(order, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )