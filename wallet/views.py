"""
wallet/views.py

Hamyon boshqaruv API.

Endpointlar:
    GET /api/wallet/me/            -- Joriy balans va holat (IsDriver)
    GET /api/wallet/transactions/  -- Tranzaksiyalar tarixi (IsDriver)

Barcha endpointlar faqat autentifikatsiyadan o'tgan haydovchilar uchun.
"""

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsDriver

from wallet.schema import wallet_me_schema, transactions_schema
from .models import Transaction, Wallet
from .serializers import TransactionSerializer, WalletSerializer

logger = logging.getLogger(__name__)

# Tranzaksiyalar tarixida ko'rsatiladigan maksimal yozuvlar soni
_TRANSACTION_PAGE_SIZE = 20


@wallet_me_schema
class WalletMeView(APIView):
    """
    GET /api/wallet/me/

    Haydovchi o'z hamyon balansini va holat ma'lumotlarini ko'radi.

    Response 200:
        {
            "id": 1,
            "driver_phone": "+998901234567",
            "balance": 45000,
            "is_sufficient": true,
            "min_balance": 5000,
            "is_driver_active": true,
            "updated_at": "2024-01-15T10:30:00Z"
        }

    Response 404:
        { "detail": "Hamyon topilmadi." }

    Response 403:
        Haydovchi emas yoki autentifikatsiya yo'q.
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
            wallet = Wallet.objects.get(driver=driver)
        except Wallet.DoesNotExist:
            logger.error(
                "WalletMeView: Haydovchi %s uchun hamyon topilmadi.",
                request.user.phone,
            )
            return Response(
                {"detail": "Hamyon topilmadi. Administrator bilan bog'laning."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = WalletSerializer(wallet)
        return Response(serializer.data, status=status.HTTP_200_OK)


@transactions_schema
class TransactionListView(APIView):
    """
    GET /api/wallet/transactions/

    Haydovchining oxirgi tranzaksiyalar tarixi.
    Sukut: oxirgi 20 ta yozuv.

    Query parametrlari:
        ?limit=N    -- ko'rsatiladigan yozuvlar soni (max: 100)
        ?tx_type=commission|topup|refund|cashback -- tur bo'yicha filtr

    Response 200:
        {
            "count": 5,
            "results": [ ...TransactionSerializer... ]
        }
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
            wallet = Wallet.objects.get(driver=driver)
        except Wallet.DoesNotExist:
            return Response(
                {"detail": "Hamyon topilmadi."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Tranzaksiyalarni olish
        qs = Transaction.objects.filter(wallet=wallet).select_related(
            "order"
        ).order_by("-created_at")

        # tx_type filtri
        tx_type = request.query_params.get("tx_type")
        if tx_type:
            qs = qs.filter(tx_type=tx_type)

        # Limit (max 100)
        try:
            limit = min(int(request.query_params.get("limit", _TRANSACTION_PAGE_SIZE)), 100)
        except (ValueError, TypeError):
            limit = _TRANSACTION_PAGE_SIZE

        qs = qs[:limit]

        serializer = TransactionSerializer(qs, many=True)

        logger.debug(
            "TransactionListView: %s | %d ta yozuv qaytarildi",
            request.user.phone, len(serializer.data),
        )

        return Response(
            {
                "count":   len(serializer.data),
                "balance": wallet.balance,
                "results": serializer.data,
            },
            status=status.HTTP_200_OK,
        )