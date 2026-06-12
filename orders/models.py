from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import User
from drivers.models import Driver


class Order(models.Model):
    """
    Buyurtma — tizimning markaziy modeli.
    status FSM (Finite State Machine):
      new → accepted → arrived → started → done
                    ↘ cancelled (istalgan bosqichda)
    """
    class Status(models.TextChoices):
        NEW       = 'new',       _('Yangi')
        ACCEPTED  = 'accepted',  _('Qabul qilindi')
        ARRIVED   = 'arrived',   _('Haydovchi keldi')
        STARTED   = 'started',   _('Yolda')
        DONE      = 'done',      _('Yakunlandi')
        CANCELLED = 'cancelled', _('Bekor qilindi')

    class CarType(models.TextChoices):
        START   = 'start',   _('Start')
        COMFORT = 'comfort', _('Komfort')
        CARGO   = 'cargo',   _('Yuk taksi')

    class PaymentType(models.TextChoices):
        CASH = 'cash', _('Naqd')
        QR   = 'qr',   _('QR (Click/Payme/Uzum)')

    # Ishtirokchilar
    client = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='client_orders', verbose_name=_('Mijoz')
    )
    driver = models.ForeignKey(
        Driver, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='driver_orders', verbose_name=_('Haydovchi')
    )

    # Manzillar
    from_address = models.CharField(_('Qayerdan'), max_length=255)
    to_address   = models.CharField(_('Qayerga'), max_length=255, blank=True)
    from_lat     = models.DecimalField(max_digits=9, decimal_places=6)
    from_lng     = models.DecimalField(max_digits=9, decimal_places=6)
    to_lat       = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    to_lng       = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Kategoriya va holat
    car_type     = models.CharField(_('Mashina turi'), max_length=10, choices=CarType.choices)
    status       = models.CharField(_('Holat'), max_length=12,
                                     choices=Status.choices, default=Status.NEW, db_index=True)

    # Narx hisob-kitobi (so'mda)
    base_fare    = models.PositiveIntegerField(_('Boshlangich narx'), default=0)
    distance_km  = models.FloatField(_('Masofa (km)'), default=0)
    rush_fee     = models.PositiveIntegerField(_('Shoshilinch ustama'), default=0)
    total_fare   = models.PositiveIntegerField(_('Jami narx'), default=0)
    commission   = models.PositiveIntegerField(_('Komissiya (10%)'), default=0)

    # To'lov
    payment_type = models.CharField(_('Tolov turi'), max_length=10,
                                     choices=PaymentType.choices, default=PaymentType.CASH)
    is_paid      = models.BooleanField(_('Tolangan'), default=False)

    # Shoshilinch buyurtma belgisi (auksion)
    is_urgent    = models.BooleanField(_('Shoshilinch'), default=False)

    # Qariya mijoz oqimi: operator zaxira manzildan foydalandi
    used_saved_address = models.BooleanField(default=False)

    # Vaqt belgilari
    created_at   = models.DateTimeField(auto_now_add=True)
    accepted_at  = models.DateTimeField(null=True, blank=True)
    started_at   = models.DateTimeField(null=True, blank=True)
    done_at      = models.DateTimeField(null=True, blank=True)

    # Operatorning izohi (ixtiyoriy)
    note         = models.TextField(_('Izoh'), blank=True)

    class Meta:
        verbose_name        = _('Buyurtma')
        verbose_name_plural = _('Buyurtmalar')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['driver', 'status']),
            models.Index(fields=['client', 'created_at']),
        ]

    def __str__(self):
        return f'#{self.pk} | {self.from_address} → {self.to_address} [{self.get_status_display()}]'

    def calculate_commission(self) -> int:
        return int(self.total_fare * 0.10)

    def calculate_cashback(self) -> int:
        """Mijoz uchun 2% cashback"""
        return int(self.total_fare * 0.02)
