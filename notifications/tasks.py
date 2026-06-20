"""
notifications/tasks.py

Celery asinxron xabar yuborish tasklari.

Har bir task:
    - @shared_task dekoratori bilan belgilangan
    - Avtomatik retry (3 marta, 60 soniya oralig'ida)
    - try/except va logging bilan himoyalangan

Ishlatilish misoli (boshqa app lardan):
    from notifications.tasks import send_sms_otp
    send_sms_otp.delay(user_id=5, code="123456")

    from notifications.tasks import send_push_order_accepted
    send_push_order_accepted.delay(order_id=42)
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


# ======================================================================
# OTP SMS
# ======================================================================

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="notifications.tasks.send_sms_otp",
)
def send_sms_otp(self, user_id: int, code: str) -> bool:
    """
    OTP kodni SMS orqali yuboradi.

    accounts/views.py dagi SendOTPView tomonidan chaqiriladi.
    Hozir u yerda print() ishlatilmoqda —
    bu task ulangandan keyin o'sha joy shu taskka almashtiriladi.

    Args:
        user_id: SMS qabul qiluvchi User ning ID si.
        code:    6 xonali OTP kod.
    """
    from accounts.models import User           # noqa: PLC0415
    from .services import send_sms            # noqa: PLC0415

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error("send_sms_otp: User #%s topilmadi.", user_id)
        return False

    message = f"SmartTaxi: Tasdiqlash kodingiz — {code}. Hech kimga bermang."

    try:
        return send_sms(user, message)
    except Exception as exc:
        logger.exception("send_sms_otp xatolik: user=%s | %s", user_id, exc)
        raise self.retry(exc=exc)


# ======================================================================
# Buyurtma holati xabarlari
# ======================================================================

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name="notifications.tasks.send_push_order_accepted",
)
def send_push_order_accepted(self, order_id: int) -> bool:
    """
    Buyurtma qabul qilinganda mijozga push notification yuboradi.

    orders/signals.py tomonidan chaqirilishi mumkin.

    Args:
        order_id: Qabul qilingan Order ning ID si.
    """
    from orders.models import Order   # noqa: PLC0415
    from .services import send_push  # noqa: PLC0415

    try:
        order = Order.objects.select_related(
            "client", "driver", "driver__user"
        ).get(pk=order_id)
    except Order.DoesNotExist:
        logger.error("send_push_order_accepted: Order #%s topilmadi.", order_id)
        return False

    if not order.client:
        return False

    driver_name = (
        f"{order.driver.user.first_name}".strip()
        if order.driver and order.driver.user.first_name
        else "Haydovchi"
    )
    car_number = order.driver.car_number if order.driver else ""

    try:
        return send_push(
            user  = order.client,
            title = "Haydovchi topildi!",
            body  = f"{driver_name} ({car_number}) yo'lda.",
            data  = {"order_id": str(order_id), "action": "order_accepted"},
        )
    except Exception as exc:
        logger.exception("send_push_order_accepted xatolik: order=%s | %s", order_id, exc)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name="notifications.tasks.send_push_driver_arrived",
)
def send_push_driver_arrived(self, order_id: int) -> bool:
    """
    Haydovchi kelganda mijozga xabar yuboradi.

    Args:
        order_id: Order ID.
    """
    from orders.models import Order   # noqa: PLC0415
    from .services import send_push  # noqa: PLC0415

    try:
        order = Order.objects.select_related("client", "driver").get(pk=order_id)
    except Order.DoesNotExist:
        logger.error("send_push_driver_arrived: Order #%s topilmadi.", order_id)
        return False

    if not order.client:
        return False

    try:
        return send_push(
            user  = order.client,
            title = "Haydovchi keldi!",
            body  = "Haydovchi siz ko'rsatgan manzilda kutmoqda.",
            data  = {"order_id": str(order_id), "action": "driver_arrived"},
        )
    except Exception as exc:
        logger.exception("send_push_driver_arrived xatolik: order=%s | %s", order_id, exc)
        raise self.retry(exc=exc)


# ======================================================================
# Anti-debt xabarlari
# ======================================================================

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="notifications.tasks.send_push_driver_blocked",
)
def send_push_driver_blocked(self, driver_id: int) -> bool:
    """
    Haydovchi balansi yetarli emas va bloklanganda xabar yuboradi.
    wallet/tasks.py dagi deduct_commission tomonidan chaqiriladi.

    Args:
        driver_id: Bloklangan Driver ning ID si.
    """
    from drivers.models import Driver         # noqa: PLC0415
    from .services import send_sms, send_push # noqa: PLC0415

    try:
        driver = Driver.objects.select_related("user", "wallet").get(pk=driver_id)
    except Driver.DoesNotExist:
        logger.error("send_push_driver_blocked: Driver #%s topilmadi.", driver_id)
        return False

    balance = getattr(getattr(driver, "wallet", None), "balance", 0)
    message = (
        f"SmartTaxi: Hisobingiz balansi {balance:,} so'm. "
        f"Buyurtma olish uchun kamida 5,000 so'm to'ldiring."
    )

    try:
        # Push va SMS ikkalasini ham yuboramiz
        push_ok = send_push(
            user  = driver.user,
            title = "Hisob balansi yetarli emas",
            body  = f"Balans: {balance:,} so'm. To'ldiring.",
            data  = {"action": "wallet_low", "balance": str(balance)},
        )
        sms_ok = send_sms(driver.user, message)
        return push_ok or sms_ok

    except Exception as exc:
        logger.exception("send_push_driver_blocked xatolik: driver=%s | %s", driver_id, exc)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="notifications.tasks.send_push_wallet_topped_up",
)
def send_push_wallet_topped_up(self, driver_id: int, amount: int) -> bool:
    """
    Hamyon to'ldirilganda haydovchiga tasdiqlash xabari yuboradi.

    payments/payme.py va payments/click.py PerformTransaction
    tomonidan chaqiriladi.

    Args:
        driver_id: Haydovchi ID si.
        amount:    To'ldirilgan miqdor (so'm).
    """
    from drivers.models import Driver         # noqa: PLC0415
    from .services import send_push, send_telegram  # noqa: PLC0415

    try:
        driver = Driver.objects.select_related("user", "wallet").get(pk=driver_id)
    except Driver.DoesNotExist:
        logger.error("send_push_wallet_topped_up: Driver #%s topilmadi.", driver_id)
        return False

    balance = getattr(getattr(driver, "wallet", None), "balance", 0)
    message = (
        f"✅ Hisobingizga <b>{amount:,} so'm</b> qo'shildi.\n"
        f"Joriy balans: <b>{balance:,} so'm</b>"
    )

    try:
        push_ok = send_push(
            user  = driver.user,
            title = "Hisob to'ldirildi",
            body  = f"+{amount:,} so'm | Balans: {balance:,} so'm",
            data  = {"action": "wallet_topped_up", "amount": str(amount)},
        )
        tg_ok = send_telegram(driver.user, message)
        return push_ok or tg_ok

    except Exception as exc:
        logger.exception(
            "send_push_wallet_topped_up xatolik: driver=%s | %s", driver_id, exc
        )
        raise self.retry(exc=exc)