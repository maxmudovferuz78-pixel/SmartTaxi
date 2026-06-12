from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import User


class Driver(models.Model):
    """
    Haydovchi profili.
    is_active — anti-debt tizimi tomonidan boshqariladi.
    is_online — haydovchi ilovasi orqali o'zi yoqib/o'chiradi.
    """
    class CarType(models.TextChoices):
        START   = 'start',   _('Start')
        COMFORT = 'comfort', _('Komfort')
        CARGO   = 'cargo',   _('Yuk taksi')

    user        = models.OneToOneField(User, on_delete=models.CASCADE,
                                       related_name='driver')
    car_type    = models.CharField(_('Mashina turi'), max_length=10,
                                    choices=CarType.choices)
    car_number  = models.CharField(_('Davlat raqami'), max_length=10, unique=True)
    car_model   = models.CharField(_('Mashina modeli'), max_length=50, blank=True)

    # Anti-debt: Celery task tomonidan avtomatik o'zgartiriladi
    is_active   = models.BooleanField(
        _('Aktiv (buyurtma olishi mumkin)'),
        default=False,
        help_text='Balans < 5000 som bolsa False ga tushiriladi'
    )
    is_online   = models.BooleanField(_('Onlayn'), default=False)

    # Oxirgi ma'lum joylashuv (WebSocket yangilaydi)
    current_lat = models.DecimalField(max_digits=9, decimal_places=6,
                                       null=True, blank=True)
    current_lng = models.DecimalField(max_digits=9, decimal_places=6,
                                       null=True, blank=True)
    location_updated_at = models.DateTimeField(null=True, blank=True)

    # To'lov kartasi (Anorbank/Payme Epos uchun)
    card_token  = models.CharField(_('Karta tokeni'), max_length=255,
                                    blank=True,
                                    help_text='Anorbank yoki Payme Epos tokenized karta')
    joined_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = _('Haydovchi')
        verbose_name_plural = _('Haydovchilar')
        indexes = [
            models.Index(fields=['is_active', 'is_online', 'car_type']),
        ]

    def __str__(self):
        return f'{self.user.phone} | {self.car_number} ({self.get_car_type_display()})'