"""
orders/apps.py

Orders ilovasi konfiguratsiyasi.

ready() -- Django serveri ishga tushganda signals.py ni import qiladi.
Bu bo'lmasa signal'lar ro'yxatdan o'tmaydi va deduct_commission
hech qachon chaqirilmaydi.
"""

from django.apps import AppConfig


class OrdersConfig(AppConfig):
    """Orders ilovasi uchun AppConfig."""

    default_auto_field = "django.db.models.BigAutoField"
    name               = "orders"
    verbose_name       = "Buyurtmalar"

    def ready(self) -> None:
        """
        Signal'larni ro'yxatdan o'tkazadi.

        Django documentatsiyasiga ko'ra signal importi shu yerda
        amalga oshirilishi kerak -- models import qilinganidan keyin,
        lekin ilovalar to'liq yuklanmagan holatda ham xavfsiz.
        """
        import orders.signals  # noqa: F401
