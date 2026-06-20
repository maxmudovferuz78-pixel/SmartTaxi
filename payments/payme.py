"""
payments/payme.py

Payme To'lov Tizimi integratsiyasi.

Payme JSONRPC 2.0 protokoli orqali ishlaydi.
Endpoint: POST /api/payments/payme/

Payme metodlari:
    CheckPerformTransaction  -- To'lovni amalga oshirib bo'ladimi?
    CreateTransaction        -- Tranzaksiya yarating
    PerformTransaction       -- To'lovni tasdiqlang (pul o'tkazildi)
    CancelTransaction        -- Tranzaksiyani bekor qiling
    CheckTransaction         -- Tranzaksiya holatini tekshiring
    GetStatement             -- Hisobot (muayyan vaqt oralig'i)

Autentifikatsiya:
    Basic Auth: login=Payme, password=<PAYME_KEY> (base64)
    PAYME_KEY = settings.PAYME_KEY

Xavfsizlik:
    - Har so'rovda Basic Auth tekshiriladi
    - Idempotentlik: bir xil transaction_id ikki marta ishlanmaydi
    - transaction.atomic() + select_for_update() poyga himoyasi

Docs: https://developer.payme.uz/documentation
"""

import base64
import hashlib
import logging
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from payments.models import PaymentRequest
from wallet.models import Transaction, Wallet

logger = logging.getLogger(__name__)

# Payme so'm ni tiyinda yuboradi (1 so'm = 100 tiyin)
_TIYIN_TO_SOM = 100

# Payme xato kodlari
class PaymeError:
    PARSE_ERROR        = -32700
    METHOD_NOT_FOUND   = -32601
    INVALID_AMOUNT     = -31001
    ACCOUNT_NOT_FOUND  = -31050
    WRONG_AMOUNT       = -31001
    TRANSACTION_NOT_FOUND = -31003
    CANT_PERFORM       = -31008
    CANT_CANCEL        = -31007


# Payme tranzaksiya holatlari (ichki)
class PaymeState:
    PENDING   = 1
    COMPLETED = 2
    CANCELLED = -1
    CANCELLED_AFTER_COMPLETE = -2


def _check_auth(request) -> bool:
    """
    Payme Basic Auth ni tekshiradi.
    Header: Authorization: Basic base64(Payme:<PAYME_KEY>)
    """
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if not auth_header.startswith("Basic "):
        return False

    try:
        decoded   = base64.b64decode(auth_header[6:]).decode("utf-8")
        login, key = decoded.split(":", 1)
        return (
            login == "Payme"
            and key == getattr(settings, "PAYME_KEY", "")
        )
    except Exception:
        return False


def handle_payme_request(data: dict) -> dict:
    """
    Kelgan JSONRPC so'rovni tegishli handler ga yo'naltiradi.

    Args:
        data: Payme dan kelgan JSONRPC 2.0 so'rov (dict).

    Returns:
        JSONRPC 2.0 javob (dict).
    """
    method = data.get("method", "")
    params = data.get("params", {})
    req_id = data.get("id", 1)

    handlers = {
        "CheckPerformTransaction":  _check_perform,
        "CreateTransaction":        _create_transaction,
        "PerformTransaction":       _perform_transaction,
        "CancelTransaction":        _cancel_transaction,
        "CheckTransaction":         _check_transaction,
        "GetStatement":             _get_statement,
    }

    handler = handlers.get(method)
    if handler is None:
        return _error(req_id, PaymeError.METHOD_NOT_FOUND, f"Noto'g'ri metod: {method}")

    try:
        result = handler(params)
        return {"jsonrpc": "2.0", "id": req_id, "result": result}
    except PaymeException as exc:
        logger.warning("Payme xato: method=%s code=%s msg=%s", method, exc.code, exc.message)
        return _error(req_id, exc.code, exc.message)
    except Exception as exc:
        logger.exception("Payme kutilmagan xato: method=%s | %s", method, exc)
        return _error(req_id, PaymeError.CANT_PERFORM, "Ichki xatolik")


# ------------------------------------------------------------------
# Payme metodlari
# ------------------------------------------------------------------

def _check_perform(params: dict) -> dict:
    """
    CheckPerformTransaction -- To'lov amalga oshirilishi mumkinmi?

    Hamyon topiladi va miqdor tekshiriladi.
    """
    amount    = params.get("amount", 0)
    account   = params.get("account", {})
    wallet_id = account.get("wallet_id")

    wallet = _get_wallet(wallet_id)
    _validate_amount(amount)

    return {"allow": True}


def _create_transaction(params: dict) -> dict:
    """
    CreateTransaction -- Yangi Payme tranzaksiyasi yaratiladi.
    Idempotent: bir xil transaction_id kelsa, mavjud qaytariladi.
    """
    transaction_id = params.get("id", "")
    amount         = params.get("amount", 0)
    account        = params.get("account", {})
    wallet_id      = account.get("wallet_id")
    time_ms        = params.get("time", 0)

    wallet = _get_wallet(wallet_id)
    _validate_amount(amount)

    external_id = f"payme_{transaction_id}"

    with transaction.atomic():
        existing = PaymentRequest.objects.filter(
            external_id=external_id
        ).select_for_update().first()

        if existing:
            # Idempotentlik: mavjud tranzaksiyani qaytarish
            if existing.status == PaymentRequest.Status.CANCELLED:
                raise PaymeException(
                    PaymeError.CANT_PERFORM,
                    "Tranzaksiya bekor qilingan."
                )
            return {
                "create_time":    int(existing.created_at.timestamp() * 1000),
                "transaction":    str(existing.pk),
                "state":          PaymeState.PENDING,
            }

        pay_req = PaymentRequest.objects.create(
            wallet      = wallet,
            provider    = PaymentRequest.Provider.PAYME,
            amount      = amount // _TIYIN_TO_SOM,
            status      = PaymentRequest.Status.PENDING,
            external_id = external_id,
            raw_payload = params,
        )

    logger.info(
        "Payme CreateTransaction: wallet=%s amount=%s tiyin | pay_req=#%s",
        wallet_id, amount, pay_req.pk,
    )

    return {
        "create_time": int(pay_req.created_at.timestamp() * 1000),
        "transaction": str(pay_req.pk),
        "state":       PaymeState.PENDING,
    }


def _perform_transaction(params: dict) -> dict:
    """
    PerformTransaction -- Pul o'tkazildi, hamyonni to'ldirish.
    """
    transaction_id = params.get("id", "")
    external_id    = f"payme_{transaction_id}"

    with transaction.atomic():
        pay_req = _get_pay_req_for_update(external_id)

        if pay_req.status == PaymentRequest.Status.COMPLETED:
            # Idempotentlik
            return {
                "transaction":    str(pay_req.pk),
                "perform_time":   int(pay_req.updated_at.timestamp() * 1000),
                "state":          PaymeState.COMPLETED,
            }

        if pay_req.status == PaymentRequest.Status.CANCELLED:
            raise PaymeException(PaymeError.CANT_PERFORM, "Tranzaksiya bekor qilingan.")

        # Hamyonni to'ldirish
        wallet = Wallet.objects.select_for_update().get(pk=pay_req.wallet_id)
        wallet.balance += pay_req.amount
        wallet.save(update_fields=["balance", "updated_at"])

        Transaction.objects.create(
            wallet        = wallet,
            amount        = pay_req.amount,
            tx_type       = Transaction.TxType.TOPUP,
            provider      = Transaction.PaymentProvider.PAYME,
            external_tx_id = external_id,
            balance_after = wallet.balance,
        )

        # Haydovchini faollashtirish (anti-debt)
        if wallet.is_sufficient and not wallet.driver.is_active:
            wallet.driver.is_active = True
            wallet.driver.save(update_fields=["is_active"])
            logger.info(
                "Anti-Debt: haydovchi %s qayta faollashtirildi (Payme to'ldirildi).",
                wallet.driver.user.phone,
            )

        pay_req.status = PaymentRequest.Status.COMPLETED
        pay_req.save(update_fields=["status", "updated_at"])

    logger.info(
        "Payme PerformTransaction: wallet=%s +%s som | yangi balans=%s",
        wallet.pk, pay_req.amount, wallet.balance,
    )

    return {
        "transaction":  str(pay_req.pk),
        "perform_time": int(pay_req.updated_at.timestamp() * 1000),
        "state":        PaymeState.COMPLETED,
    }


def _cancel_transaction(params: dict) -> dict:
    """
    CancelTransaction -- Tranzaksiyani bekor qilish.
    Completed bo'lsa hamyondan pul qaytariladi (refund).
    """
    transaction_id = params.get("id", "")
    reason         = params.get("reason", 0)
    external_id    = f"payme_{transaction_id}"

    with transaction.atomic():
        pay_req = _get_pay_req_for_update(external_id)

        if pay_req.status == PaymentRequest.Status.CANCELLED:
            return {
                "transaction": str(pay_req.pk),
                "cancel_time": int(pay_req.updated_at.timestamp() * 1000),
                "state":       PaymeState.CANCELLED,
            }

        # Completed bo'lsa refund
        if pay_req.status == PaymentRequest.Status.COMPLETED:
            wallet = Wallet.objects.select_for_update().get(pk=pay_req.wallet_id)
            if wallet.balance < pay_req.amount:
                raise PaymeException(
                    PaymeError.CANT_CANCEL,
                    "Hamyonda qaytarish uchun yetarli mablag' yo'q."
                )
            wallet.balance -= pay_req.amount
            wallet.save(update_fields=["balance", "updated_at"])

            Transaction.objects.create(
                wallet        = wallet,
                amount        = -pay_req.amount,
                tx_type       = Transaction.TxType.REFUND,
                provider      = Transaction.PaymentProvider.PAYME,
                external_tx_id = f"{external_id}_refund",
                balance_after = wallet.balance,
            )

        pay_req.status = PaymentRequest.Status.CANCELLED
        pay_req.save(update_fields=["status", "updated_at"])

    logger.info("Payme CancelTransaction: %s | sabab=%s", external_id, reason)

    return {
        "transaction": str(pay_req.pk),
        "cancel_time": int(pay_req.updated_at.timestamp() * 1000),
        "state":       PaymeState.CANCELLED,
    }


def _check_transaction(params: dict) -> dict:
    """CheckTransaction -- Tranzaksiya holatini qaytarish."""
    transaction_id = params.get("id", "")
    external_id    = f"payme_{transaction_id}"

    try:
        pay_req = PaymentRequest.objects.get(external_id=external_id)
    except PaymentRequest.DoesNotExist:
        raise PaymeException(
            PaymeError.TRANSACTION_NOT_FOUND, "Tranzaksiya topilmadi."
        )

    state_map = {
        PaymentRequest.Status.PENDING:   PaymeState.PENDING,
        PaymentRequest.Status.COMPLETED: PaymeState.COMPLETED,
        PaymentRequest.Status.CANCELLED: PaymeState.CANCELLED,
        PaymentRequest.Status.FAILED:    PaymeState.CANCELLED,
    }

    return {
        "create_time":  int(pay_req.created_at.timestamp() * 1000),
        "perform_time": int(pay_req.updated_at.timestamp() * 1000)
                        if pay_req.status == PaymentRequest.Status.COMPLETED else 0,
        "cancel_time":  int(pay_req.updated_at.timestamp() * 1000)
                        if pay_req.status == PaymentRequest.Status.CANCELLED else 0,
        "transaction":  str(pay_req.pk),
        "state":        state_map.get(pay_req.status, PaymeState.CANCELLED),
        "reason":       None,
    }


def _get_statement(params: dict) -> dict:
    """GetStatement -- Vaqt oralig'idagi tranzaksiyalar hisoboti."""
    from_time = params.get("from", 0)
    to_time   = params.get("to", 0)

    from_dt = timezone.datetime.fromtimestamp(from_time / 1000, tz=timezone.utc)
    to_dt   = timezone.datetime.fromtimestamp(to_time   / 1000, tz=timezone.utc)

    pay_reqs = PaymentRequest.objects.filter(
        provider    = PaymentRequest.Provider.PAYME,
        created_at__gte = from_dt,
        created_at__lte = to_dt,
    ).order_by("created_at")

    state_map = {
        PaymentRequest.Status.PENDING:   PaymeState.PENDING,
        PaymentRequest.Status.COMPLETED: PaymeState.COMPLETED,
        PaymentRequest.Status.CANCELLED: PaymeState.CANCELLED,
        PaymentRequest.Status.FAILED:    PaymeState.CANCELLED,
    }

    transactions = []
    for pr in pay_reqs:
        transactions.append({
            "id":           pr.external_id.replace("payme_", ""),
            "time":         int(pr.created_at.timestamp() * 1000),
            "amount":       pr.amount * _TIYIN_TO_SOM,
            "account":      {"wallet_id": pr.wallet_id},
            "create_time":  int(pr.created_at.timestamp() * 1000),
            "perform_time": int(pr.updated_at.timestamp() * 1000)
                            if pr.status == PaymentRequest.Status.COMPLETED else 0,
            "cancel_time":  int(pr.updated_at.timestamp() * 1000)
                            if pr.status == PaymentRequest.Status.CANCELLED else 0,
            "transaction":  str(pr.pk),
            "state":        state_map.get(pr.status, PaymeState.CANCELLED),
            "reason":       None,
        })

    return {"transactions": transactions}


# ------------------------------------------------------------------
# Ichki yordamchilar
# ------------------------------------------------------------------

def _get_wallet(wallet_id) -> Wallet:
    if not wallet_id:
        raise PaymeException(PaymeError.ACCOUNT_NOT_FOUND, "wallet_id berilmagan.")
    try:
        return Wallet.objects.select_related("driver", "driver__user").get(pk=wallet_id)
    except Wallet.DoesNotExist:
        raise PaymeException(PaymeError.ACCOUNT_NOT_FOUND, f"Hamyon #{wallet_id} topilmadi.")


def _validate_amount(amount: int) -> None:
    if not isinstance(amount, int) or amount <= 0:
        raise PaymeException(PaymeError.INVALID_AMOUNT, "Miqdor noto'g'ri.")
    # Minimal: 1 000 so'm = 100 000 tiyin
    if amount < 100_000:
        raise PaymeException(PaymeError.INVALID_AMOUNT, "Minimal miqdor 1 000 so'm.")


def _get_pay_req_for_update(external_id: str) -> PaymentRequest:
    try:
        return PaymentRequest.objects.select_for_update().get(external_id=external_id)
    except PaymentRequest.DoesNotExist:
        raise PaymeException(
            PaymeError.TRANSACTION_NOT_FOUND, "Tranzaksiya topilmadi."
        )


def _error(req_id, code: int, message: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "id":      req_id,
        "error":   {"code": code, "message": message},
    }


class PaymeException(Exception):
    def __init__(self, code: int, message: str):
        self.code    = code
        self.message = message
        super().__init__(message)