"""
orders/signals.py

Django signal'lari -- Buyurtma holati o'zgarganda avtomatik harakatlar.

TZ 17-bob (Django Signals):
    Order statusi 'done' ga o'tganda -> deduct_commission.delay(order.id)

Muhim:
    Bu fayl orders/apps.py ready() ichida import qilinishi kerak,
    aks holda signal ro'yxatdan o'tmaydi (silent fail).
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Order

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Order)
def order_done_handler(
    sender,
    instance: Order,
    created: bool,
    update_fields,
    **kwargs,
) -> None:
    """
    Buyurtma 'done' (Yakunlandi) holatiga o'tganda komissiya vazifasini
    asinxron ishga tushiradi.

    Qachon ishga tushadi:
        - Yangi yaratilgan emas (created=False)
        - Status 'done' ga o'zgargan
        - Haydovchi biriktirilgan

    Nima qiladi:
        deduct_commission.delay(instance.id) -- Celery orqali
        hamyondan 10% komissiyani asinxron yechadi.

    Args:
        sender:        Order modeli sinfi.
        instance:      O'zgartirilgan Order obyekti.
        created:       True = yangi yaratilgan, False = mavjud yangilangan.
        update_fields: Faqat shu maydonlar yangilangan (yoki None).
    """
    # Yangi yaratilgan buyurtmaga tegmaydi
    if created:
        return

    # Faqat 'done' holatiga o'tganda ishlaydi
    if instance.status != Order.Status.DONE:
        return

    # Haydovchi biriktirilgan bo'lishi shart
    if instance.driver is None:
        logger.warning(
            "Signal: Buyurtma #%s 'done' bo'ldi, lekin haydovchi "
            "biriktirilmagan. Komissiya yechilmaydi.",
            instance.pk,
        )
        return

    # Celery taskni asinxron ishga tushirish
    try:
        from wallet.tasks import deduct_commission  # noqa: PLC0415

        deduct_commission.delay(instance.pk)

        logger.info(
            "Signal: deduct_commission.delay(%s) yuborildi | haydovchi=%s",
            instance.pk,
            instance.driver.user.phone,
        )
    except Exception as exc:
        # Task yuborishda xatolik bo'lsa logga yoziladi,
        # lekin buyurtma saqlash jarayoni to'xtatilmaydi
        logger.exception(
            "Signal: deduct_commission task yuborishda xatolik: "
            "order_id=%s | %s",
            instance.pk, exc,
        )