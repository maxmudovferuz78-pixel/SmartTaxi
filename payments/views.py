"""
payments/views.py

To'lov endpointlari.

Endpointlar:
    POST /api/payments/payme/    -- Payme JSONRPC webhook (autentifikatsiya: Basic Auth)
    POST /api/payments/click/    -- Click webhook (autentifikatsiya: sign imzo)
    POST /api/payments/topup/    -- To'ldirish linki olish (IsDriver)
    GET  /api/payments/history/  -- To'lov tarixi (IsDriver)
    GET  /api/payments/          -- Barcha to'lovlar (IsOperator)
"""

import logging

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsDriver, IsOperator

from payments.schema import topup_schema, payme_webhook_schema, click_webhook_schema, history_schema
from .models import PaymentRequest
from .payme import _check_auth as payme_check_auth
from .payme import handle_payme_request
from .click import handle_click_request
from .serializers import PaymentRequestSerializer, TopupInitSerializer

logger = logging.getLogger(__name__)


# ======================================================================
# Payme webhook
# ======================================================================

@payme_webhook_schema
class PaymeWebhookView(APIView):
    """
    POST /api/payments/payme/

    Payme JSONRPC 2.0 webhook.
    Autentifikatsiya: Basic Auth (Payme:<PAYME_KEY>).
    CSRF exempt — tashqi tizimdan keladi.
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # SimpleJWT o'chiriladi, Basic Auth ishlatiladi

    def post(self, request: Request) -> Response:
        # Basic Auth tekshiruvi
        if not payme_check_auth(request):
            logger.warning(
                "Payme webhook: autentifikatsiya muvaffaqiyatsiz | IP=%s",
                request.META.get("REMOTE_ADDR"),
            )
            return Response(
                {
                    "jsonrpc": "2.0",
                    "id":      request.data.get("id", 0),
                    "error":   {"code": -32504, "message": "Autentifikatsiya xato."},
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        result = handle_payme_request(request.data)

        logger.debug(
            "Payme webhook: method=%s | result_keys=%s",
            request.data.get("method"), list(result.keys()),
        )

        return Response(result, status=status.HTTP_200_OK)


# ======================================================================
# Click webhook
# ======================================================================

@click_webhook_schema
class ClickWebhookView(APIView):
    """
    POST /api/payments/click/

    Click Prepare/Complete webhook.
    Autentifikatsiya: MD5 imzo (sign_string).
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request: Request) -> Response:
        result = handle_click_request(request.data)

        logger.debug(
            "Click webhook: action=%s | result=%s",
            request.data.get("action"), result.get("error"),
        )

        return Response(result, status=status.HTTP_200_OK)


# ======================================================================
# Haydovchi to'ldirish
# ======================================================================

@topup_schema
class TopupInitView(APIView):
    """
    POST /api/payments/topup/

    Haydovchi hamyonini to'ldirish uchun to'lov linki oladi.
    Tizim Payme/Click/Uzum ga redirect URL qaytaradi.

    Request body:
        { "provider": "payme", "amount": 50000 }

    Response 200:
        {
            "provider": "payme",
            "amount": 50000,
            "payment_url": "https://checkout.paycom.uz/...",
            "wallet_id": 3
        }
    """

    permission_classes = [IsAuthenticated, IsDriver]

    def post(self, request: Request) -> Response:
        driver = getattr(request.user, "driver", None)
        if driver is None:
            return Response(
                {"detail": "Haydovchi profili topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = TopupInitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        provider = serializer.validated_data["provider"]
        amount   = serializer.validated_data["amount"]

        try:
            wallet = driver.wallet
        except Exception:
            return Response(
                {"detail": "Hamyon topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        payment_url = self._build_payment_url(provider, wallet.pk, amount)

        logger.info(
            "Topup initlandi: haydovchi=%s provider=%s amount=%s",
            request.user.phone, provider, amount,
        )

        return Response(
            {
                "provider":    provider,
                "amount":      amount,
                "wallet_id":   wallet.pk,
                "payment_url": payment_url,
            },
            status=status.HTTP_200_OK,
        )

    def _build_payment_url(self, provider: str, wallet_id: int, amount: int) -> str:
        """
        Har bir provayder uchun to'lov URL ini yaratadi.

        Payme:  base64(m=<MERCHANT_ID>;ac.wallet_id=<id>;a=<tiyin>)
        Click:  merchant_id + service_id + amount + wallet_id
        Uzum:   merchant_id + amount + wallet_id
        """
        import base64  # noqa: PLC0415

        if provider == "payme":
            merchant_id = getattr(settings, "PAYME_MERCHANT_ID", "")
            # amount tiyinda (1 so'm = 100 tiyin)
            tiyin       = amount * 100
            raw         = f"m={merchant_id};ac.wallet_id={wallet_id};a={tiyin}"
            encoded     = base64.b64encode(raw.encode()).decode()
            return f"https://checkout.paycom.uz/{encoded}"

        if provider == "click":
            service_id  = getattr(settings, "CLICK_SERVICE_ID", "")
            merchant_id = getattr(settings, "CLICK_MERCHANT_ID", "")
            return (
                f"https://my.click.uz/services/pay"
                f"?service_id={service_id}"
                f"&merchant_id={merchant_id}"
                f"&amount={amount}"
                f"&transaction_param={wallet_id}"
            )

        if provider == "uzum":
            merchant_id = getattr(settings, "UZUM_MERCHANT_ID", "")
            return (
                f"https://merchant.apelsin.uz/pay"
                f"?merchant_id={merchant_id}"
                f"&amount={amount}"
                f"&account={wallet_id}"
            )

        return ""


# ======================================================================
# To'lov tarixi
# ======================================================================

@history_schema
class PaymentHistoryView(APIView):
    """
    GET /api/payments/history/

    Haydovchi o'z to'lov tarixini ko'radi.

    Response 200:
        { "count": 3, "results": [ ...PaymentRequestSerializer... ] }
    """

    permission_classes = [IsAuthenticated, IsDriver]

    def get(self, request: Request) -> Response:
        driver = getattr(request.user, "driver", None)
        if driver is None:
            return Response(
                {"detail": "Haydovchi profili topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            wallet = driver.wallet
        except Exception:
            return Response({"count": 0, "results": []})

        qs = PaymentRequest.objects.filter(
            wallet=wallet
        ).order_by("-created_at")[:20]

        serializer = PaymentRequestSerializer(qs, many=True)
        return Response({"count": len(serializer.data), "results": serializer.data})


# ======================================================================
# Operator: barcha to'lovlar
# ======================================================================

class AllPaymentsView(APIView):
    """
    GET /api/payments/

    Operator barcha to'lovlarni ko'radi.

    Query parametrlari:
        ?provider=payme|click|uzum
        ?status=pending|completed|failed|cancelled
    """

    permission_classes = [IsOperator]

    def get(self, request: Request) -> Response:
        qs = PaymentRequest.objects.select_related(
            "wallet", "wallet__driver", "wallet__driver__user"
        ).order_by("-created_at")

        provider = request.query_params.get("provider")
        pstatus  = request.query_params.get("status")

        if provider:
            qs = qs.filter(provider=provider)
        if pstatus:
            qs = qs.filter(status=pstatus)

        qs = qs[:50]
        serializer = PaymentRequestSerializer(qs, many=True)
        return Response({"count": len(serializer.data), "results": serializer.data})