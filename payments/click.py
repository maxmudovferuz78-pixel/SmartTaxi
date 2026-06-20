"""
payments/click.py

Click To'lov Tizimi integratsiyasi.

Click ikki bosqichli webhook orqali ishlaydi:
    1. Prepare  -- To'lovni tekshirish (pul o'tkazilishidan oldin)
    2. Complete -- To'lovni tasdiqlash (pul o'tkazilgandan keyin)

Endpoint: POST /api/payments/click/

Click so'rov formati (form-data yoki JSON):
    click_trans_id  -- Click tranzaksiya ID
    service_id      -- Bizning service ID
    merchant_trans_id -- Bizning wallet_id
    amount          -- Miqdor (so'mda)
    action          -- 0=Prepare, 1=Complete
    error           -- 0=muvaffaqiyat, boshqa=xato
    sign_time       -- Vaqt (YYYY-MM-DD HH:MM:SS)
    sign_string     -- MD5 imzo

Imzo tekshirish:
    MD5(click_trans_id + service_id + CLICK_SECRET_KEY +
        merchant_trans_id + amount + action + sign_time)

Docs: https://docs.click.uz
"""

import hashlib
import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from payments.models import PaymentRequest
from wallet.models import Transaction, Wallet

logger = logging.getLogger(__name__)


# Click xato kodlari
class ClickError:
    SUCCESS            =  0
    SIGN_CHECK_FAILED  = -1
    ORDER_NOT_FOUND    = -5
    ALREADY_PAID       = -4
    TRANSACTION_NOT_FOUND = -6
    BAD_REQUEST        = -8


def _check_sign(data: dict) -> bool:
    """
    Click MD5 imzoni tekshiradi.
    sign_string = MD5(click_trans_id + service_id + CLICK_SECRET_KEY +
                      merchant_trans_id + amount + action + sign_time)
    """
    secret = getattr(settings, "CLICK_SECRET_KEY", "")
    sign_string = (
        str(data.get("click_trans_id", ""))
        + str(data.get("service_id", ""))
        + secret
        + str(data.get("merchant_trans_id", ""))
        + str(data.get("amount", ""))
        + str(data.get("action", ""))
        + str(data.get("sign_time", ""))
    )
    expected = hashlib.md5(sign_string.encode()).hexdigest()
    return expected == data.get("sign_string", "")


def handle_click_request(data: dict) -> dict:
    """
    Click Prepare yoki Complete so'rovini qayta ishlaydi.

    Args:
        data: Click dan kelgan so'rov parametrlari (dict).

    Returns:
        Click javob formati (dict).
    """
    action = int(data.get("action", -1))

    if action == 0:
        return _prepare(data)
    elif action == 1:
        return _complete(data)
    else:
        return _click_error(data, ClickError.BAD_REQUEST, "Noto'g'ri action.")


def _prepare(data: dict) -> dict:
    """
    Prepare -- To'lovni amalga oshirib bo'ladimi?

    Hamyon mavjudligini va miqdorni tekshiradi.
    PaymentRequest PENDING holda yaratiladi.
    """
    if not _check_sign(data):
        return _click_error(data, ClickError.SIGN_CHECK_FAILED, "Imzo xato.")

    click_trans_id    = str(data.get("click_trans_id", ""))
    merchant_trans_id = str(data.get("merchant_trans_id", ""))
    amount            = float(data.get("amount", 0))

    # Hamyon tekshirish
    wallet = _get_wallet(merchant_trans_id)
    if wallet is None:
        return _click_error(data, ClickError.ORDER_NOT_FOUND, "Hamyon topilmadi.")

    # Minimal miqdor: 1 000 so'm
    if amount < 1_000:
        return _click_error(data, ClickError.BAD_REQUEST, "Minimal miqdor 1 000 so'm.")

    external_id = f"click_{click_trans_id}"

    # Idempotentlik tekshiruvi
    if PaymentRequest.objects.filter(external_id=external_id).exists():
        return _click_ok(data, merchant_trans_id)

    PaymentRequest.objects.create(
        wallet      = wallet,
        provider    = PaymentRequest.Provider.CLICK,
        amount      = int(amount),
        status      = PaymentRequest.Status.PENDING,
        external_id = external_id,
        raw_payload = data,
    )

    logger.info(
        "Click Prepare: wallet=%s amount=%.0f so'm | click_id=%s",
        merchant_trans_id, amount, click_trans_id,
    )

    return _click_ok(data, merchant_trans_id)


def _complete(data: dict) -> dict:
    """
    Complete -- Pul o'tkazildi, hamyonni to'ldirish.

    error == 0 bo'lsa muvaffaqiyatli,
    boshqa qiymat bo'lsa Click tomonidan xato (pul qaytarilgan).
    """
    if not _check_sign(data):
        return _click_error(data, ClickError.SIGN_CHECK_FAILED, "Imzo xato.")

    click_trans_id    = str(data.get("click_trans_id", ""))
    merchant_trans_id = str(data.get("merchant_trans_id", ""))
    click_error       = int(data.get("error", 0))
    external_id       = f"click_{click_trans_id}"

    with transaction.atomic():
        try:
            pay_req = PaymentRequest.objects.select_for_update().get(
                external_id=external_id
            )
        except PaymentRequest.DoesNotExist:
            return _click_error(
                data, ClickError.TRANSACTION_NOT_FOUND, "Tranzaksiya topilmadi."
            )

        # Idempotentlik
        if pay_req.status == PaymentRequest.Status.COMPLETED:
            return _click_ok(data, merchant_trans_id)

        # Click tomonidan xato
        if click_error != 0:
            pay_req.status = PaymentRequest.Status.FAILED
            pay_req.save(update_fields=["status", "updated_at"])
            logger.warning(
                "Click Complete xato: click_id=%s error=%s",
                click_trans_id, click_error,
            )
            return _click_error(data, click_error, "Click xato qaytardi.")

        # Hamyonni to'ldirish
        wallet = Wallet.objects.select_for_update().get(pk=pay_req.wallet_id)
        wallet.balance += pay_req.amount
        wallet.save(update_fields=["balance", "updated_at"])

        Transaction.objects.create(
            wallet         = wallet,
            amount         = pay_req.amount,
            tx_type        = Transaction.TxType.TOPUP,
            provider       = Transaction.PaymentProvider.CLICK,
            external_tx_id = external_id,
            balance_after  = wallet.balance,
        )

        # Anti-debt: haydovchini faollashtirish
        if wallet.is_sufficient and not wallet.driver.is_active:
            wallet.driver.is_active = True
            wallet.driver.save(update_fields=["is_active"])
            logger.info(
                "Anti-Debt: haydovchi %s qayta faollashtirildi (Click to'ldirildi).",
                wallet.driver.user.phone,
            )

        pay_req.status = PaymentRequest.Status.COMPLETED
        pay_req.save(update_fields=["status", "updated_at"])

    logger.info(
        "Click Complete: wallet=%s +%s so'm | yangi balans=%s",
        wallet.pk, pay_req.amount, wallet.balance,
    )

    return _click_ok(data, merchant_trans_id)


# ------------------------------------------------------------------
# Ichki yordamchilar
# ------------------------------------------------------------------

def _get_wallet(wallet_id: str):
    try:
        return Wallet.objects.select_related("driver", "driver__user").get(
            pk=int(wallet_id)
        )
    except (Wallet.DoesNotExist, ValueError, TypeError):
        return None


def _click_ok(data: dict, merchant_prepare_id: str) -> dict:
    return {
        "click_trans_id":      data.get("click_trans_id"),
        "merchant_trans_id":   data.get("merchant_trans_id"),
        "merchant_prepare_id": merchant_prepare_id,
        "error":               ClickError.SUCCESS,
        "error_note":          "Success",
    }


def _click_error(data: dict, error_code: int, error_note: str) -> dict:
    return {
        "click_trans_id":    data.get("click_trans_id"),
        "merchant_trans_id": data.get("merchant_trans_id"),
        "error":             error_code,
        "error_note":        error_note,
    }