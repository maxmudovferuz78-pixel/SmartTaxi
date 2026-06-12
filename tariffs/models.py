"""
tariffs/models.py

Tarif konfiguratsiyasi — TZ 4.2-band.

Narx formulasi (TZ 4.1-band):
    S_jami = S_chaqiruv + (L_umumiy * S_km) + S_shoshilinch
    Komissiya = S_jami * 10%
"""

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class Tariff(models.Model):
    """
    Bitta kategoriya uchun tarif sozlamalari.

    TZ 4.2-bandidagi jadval:
        Start   -- 4 000 so'm + 1 800 so'm/km
        Komfort -- 6 500 so'm + 2 400 so'm/km
        Yuk     -- 15 000 so'm + 4 500 so'm/km
    """

    class Category(models.TextChoices):
        START = "start", _("Start")
        COMFORT = "comfort", _("Komfort")
        CARGO = "cargo", _("Yuk taksi")

    category = models.CharField(
        _("Kategoriya"),
        max_length=10,
        choices=Category.choices,
        unique=True,
    )
    base_fare = models.PositiveIntegerField(
        _("Boshlangich narx (som)"),
        validators=[MinValueValidator(1)],
        help_text="S_chaqiruv -- taksi chaqirilishi uchun doimiy tolov",
    )
    per_km = models.PositiveIntegerField(
        _("1 km narxi (som)"),
        validators=[MinValueValidator(1)],
        help_text="S_km -- har kilometr uchun tolov",
    )
    rush_fee_low = models.PositiveIntegerField(
        _("Shoshilinch kam ustama (som)"),
        default=3_000,
        help_text="Oddiy shoshilinch ustama",
    )
    rush_fee_high = models.PositiveIntegerField(
        _("Shoshilinch yuqori ustama (som)"),
        default=5_000,
        help_text="Yuqori shoshilinch ustama",
    )
    is_active = models.BooleanField(_("Faol"), default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Tarif")
        verbose_name_plural = _("Tariflar")
        ordering = ["category"]

    # ------------------------------------------------------------------
    # Biznes mantiq
    # ------------------------------------------------------------------

    def calculate_fare(self, distance_km: float, rush_fee: int = 0) -> int:
        """
        Jami narxni hisoblaydi.

        Formula (TZ 4.1-band):
            S_jami = S_chaqiruv + (L_umumiy * S_km) + S_shoshilinch

        Args:
            distance_km: Marshrut uzunligi (km).
            rush_fee:    Shoshilinch ustama (som). Sukut: 0.

        Returns:
            Jami narx (somda, butun son).

        Raises:
            ValueError: Masofa manfiy bolsa.
        """
        if distance_km < 0:
            raise ValueError("Masofa manfiy bolishi mumkin emas.")
        return self.base_fare + int(distance_km * self.per_km) + rush_fee

    @staticmethod
    def calculate_commission(total_fare: int) -> int:
        """
        Haydovchidan yechilladigan komissiya (TZ: 10%).

        Args:
            total_fare: Jami buyurtma narxi (som).

        Returns:
            Komissiya miqdori (som).
        """
        return int(total_fare * 0.10)

    def __str__(self) -> str:
        return (
            f"{self.get_category_display()} | "
            f"{self.base_fare:,} som + {self.per_km:,}/km"
        )