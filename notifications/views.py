"""
notifications/views.py

Bildirishnoma endpointlari.

Endpointlar:
    GET  /api/notifications/         -- O'z xabarlari tarixi (IsAuthenticated)
    POST /api/notifications/test/    -- Test xabar yuborish (IsAdminUser)
"""

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminUser

from .models import Notification
from .serializers import NotificationSerializer
from .schema import notification_list_schema, test_notification_schema

logger = logging.getLogger(__name__)


@notification_list_schema
class NotificationListView(APIView):
    """
    GET /api/notifications/

    Foydalanuvchi o'ziga yuborilgan barcha xabarlarni ko'radi.

    Query parametrlari:
        ?channel=sms|push|tg
        ?status=sent|failed
        ?limit=N  (max: 50, sukut: 20)

    Response 200:
        { "count": 5, "results": [ ...NotificationSerializer... ] }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = Notification.objects.filter(
            user=request.user
        ).order_by("-created_at")

        channel = request.query_params.get("channel")
        nstatus = request.query_params.get("status")

        if channel:
            qs = qs.filter(channel=channel)
        if nstatus:
            qs = qs.filter(status=nstatus)

        try:
            limit = min(int(request.query_params.get("limit", 20)), 50)
        except (ValueError, TypeError):
            limit = 20

        total = qs.count()
        qs    = qs[:limit]

        serializer = NotificationSerializer(qs, many=True)
        return Response({"count": total, "results": serializer.data})


@test_notification_schema
class TestNotificationView(APIView):
    """
    POST /api/notifications/test/

    Admin test xabar yuboradi (SMS, Push yoki Telegram).
    Faqat DEBUG yoki staging muhitlarda ishlatiladi.

    Request body:
        {
            "user_id": 5,
            "channel": "sms",
            "message": "Test xabar"
        }

    Response 200:
        { "sent": true, "channel": "sms" }
    """

    permission_classes = [IsAdminUser]

    def post(self, request: Request) -> Response:
        from accounts.models import User  # noqa: PLC0415
        from .services import send_sms, send_push, send_telegram  # noqa: PLC0415

        user_id = request.data.get("user_id")
        channel = request.data.get("channel")
        message = request.data.get("message", "SmartTaxi test xabari")

        if not user_id or not channel:
            return Response(
                {"detail": "user_id va channel majburiy."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": f"User #{user_id} topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        sent = False
        if channel == Notification.Channel.SMS:
            sent = send_sms(user, message)
        elif channel == Notification.Channel.PUSH:
            sent = send_push(user, "Test", message)
        elif channel == Notification.Channel.TELEGRAM:
            sent = send_telegram(user, message)
        else:
            return Response(
                {"detail": "channel: sms | push | tg bo'lishi kerak."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(
            "Test xabar: admin=%s → user=%s | channel=%s | sent=%s",
            request.user.phone, user.phone, channel, sent,
        )

        return Response(
            {"sent": sent, "channel": channel},
            status=status.HTTP_200_OK,
        )