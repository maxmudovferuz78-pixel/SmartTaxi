"""
wallet/tasks.py

Celery asinxron vazifalari — hamyon operatsiyalari.

TZ 4.3-band (Virtual hamyon va Anti-Debt tizimi):
    1. Buyurtma yakunlanganda (done) komissiya (10%) haydovchi
       hamyonidan yechiladi.
    2. Balans MIN_BALANCE (5 000 so'm) dan tushib ketsa haydovchi
       bloklanadi (is_active = False).
    3. Bloklanganlik haydovchiga SMS/Push orqali xabar qilinadi
       (keyingi bosqich: notifications.tasks).

Xavfsizlik mexanizmlari:
    select_for_update() -- poyga holati (race condition) dan saqlaydi.
    transaction.atomic() -- bir butun tranzaksiya: yoki hammasi
                            saqlanadi, yoki hech narsa.
    Idempotentlik       -- bir xil order uchun ikki marta ishlamaydi
                           (Transaction.objects.get_or_create pattern).
"""

import logging

from celery import shared_task
from django.db import transaction

from wallet.models import Transaction, Wallet

logger = logging.getLogger(__name__)

# Anti-debt chegarasi (Wallet.MIN_BALANCE bilan bir xil)
_MIN_BALANCE = 5_000


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,        # 60 soniya kutib qayta urinadi
    acks_late=True,                # Worker avval bajaradi, keyin ACK
    name="wallet.tasks.deduct_commission",
)
def deduct_commission(self, order_id: int) -> dict:
    """
    Buyurtma yakunlanganda haydovchi hamyonidan 10% komissiya yechadi.

    Bosqichlar:
        1. Buyurtmani va haydovchini topish.
        2. Hamyonni select_for_update() bilan qulflash.
        3. Komissiyani hamyon balansidan ayirish.
        4. Transaction yozuvi yaratish (audit log).
        5. Anti-Debt: balans < 5 000 so'm bo'lsa haydovchini bloklash.

    Args:
        order_id: Yakunlangan buyurtmaning ID si.

    Returns:
        {
            "order_id": int,
            "commission": int,
            "new_balance": int,
            "driver_blocked": bool,
        }

    Raises:
        self.retry(): Vaqtinchalik xatolik (DB timeout va h.k.) bo'lsa
                      3 marta qayta urinadi.
    """
    # Import ichkarida -- circular import dan saqlanish
    from orders.models import Order  # noqa: PLC0415

    logger.info("deduct_commission boshlandi: order_id=%s", order_id)

    try:
        with transaction.atomic():
            # -- 1. Buyurtmani topish ----------------------------------
            try:
                order = (
                    Order.objects.select_related(
                        "driver",
                        "driver__user",
                        "driver__wallet",
                    ).get(pk=order_id)
                )
            except Order.DoesNotExist:
                logger.error("deduct_commission: Buyurtma #%s topilmadi.", order_id)
                return {"error": f"Order #{order_id} not found"}

            # -- Haydovchi tekshiruvi ----------------------------------
            driver = order.driver
            if driver is None:
                logger.warning(
                    "deduct_commission: Buyurtma #%s ga haydovchi biriktirilmagan.",
                    order_id,
                )
                return {"error": "Driver not assigned"}

            # -- 2. Hamyonni qulflash (race condition himoyasi) --------
            try:
                wallet = (
                    Wallet.objects.select_for_update()
                    .get(driver=driver)
                )
            except Wallet.DoesNotExist:
                logger.error(
                    "deduct_commission: Haydovchi %s uchun hamyon topilmadi.",
                    driver.user.phone,
                )
                return {"error": "Wallet not found"}

            # -- Idempotentlik: bir xil buyurtma uchun ikki marta -----
            # komissiya yechilmasligi uchun tekshiruv
            already_deducted = Transaction.objects.filter(
                wallet=wallet,
                order=order,
                tx_type=Transaction.TxType.COMMISSION,
            ).exists()

            if already_deducted:
                logger.warning(
                    "deduct_commission: Buyurtma #%s uchun komissiya "
                    "allaqachon yechilgan. Takroriy ishga tushirish e'tiborga olinmadi.",
                    order_id,
                )
                return {
                    "order_id": order_id,
                    "skipped": True,
                    "reason": "already_deducted",
                }

            # -- 3. Komissiyani yechish --------------------------------
            commission     = order.commission  # avval hisoblangan va saqlangan
            new_balance    = wallet.balance - commission
            wallet.balance = new_balance
            wallet.save(update_fields=["balance", "updated_at"])

            # -- 4. Transaction yozuvi (audit log) --------------------
            Transaction.objects.create(
                wallet        = wallet,
                amount        = -commission,           # manfiy = chiqim
                tx_type       = Transaction.TxType.COMMISSION,
                order         = order,
                balance_after = new_balance,
            )

            # -- 5. Anti-Debt logikasi ---------------------------------
            driver_blocked = False
            if new_balance < _MIN_BALANCE:
                driver.is_active = False
                driver.save(update_fields=["is_active"])
                driver_blocked = True

                logger.warning(
                    "Anti-Debt: Haydovchi %s bloklandi. "
                    "Balans: %s so'm (minimum: %s so'm).",
                    driver.user.phone, new_balance, _MIN_BALANCE,
                )
                # TODO: notifications.tasks.send_push_blocked.delay(driver.id)
            else:
                logger.info(
                    "Komissiya yechildi: haydovchi=%s | order=#%s | "
                    "commission=%s | yangi balans=%s",
                    driver.user.phone, order_id, commission, new_balance,
                )

        return {
            "order_id":      order_id,
            "commission":    commission,
            "new_balance":   new_balance,
            "driver_blocked": driver_blocked,
        }

    except Exception as exc:
        logger.exception(
            "deduct_commission xatolik: order_id=%s | %s",
            order_id, exc,
        )
        # Vaqtinchalik xatolik bo'lsa qayta urinish (max 3 marta)
        raise self.retry(exc=exc)