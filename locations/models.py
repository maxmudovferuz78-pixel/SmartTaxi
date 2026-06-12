from django.db import models
from django.utils.translation import gettext_lazy as _
from drivers.models import Driver


class DriverLocation(models.Model):
    """
    Haydovchining joriy joylashuvi (WebSocket orqali yangilanadi).
    Bu jadval faqat so'nggi nuqtani saqlaydi — tarix uchun LocationHistory ishlatiladi.
    update_or_create() pattern bilan ishlaydi.
    """
    driver     = models.OneToOneField(Driver, on_delete=models.CASCADE,
                                      related_name='location')
    lat        = models.DecimalField(max_digits=9, decimal_places=6)
    lng        = models.DecimalField(max_digits=9, decimal_places=6)
    speed_kmh  = models.FloatField(_('Tezlik (km/s)'), default=0,
                                    help_text='GPS spoofing aniqlash uchun')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _('Haydovchi joylashuvi')
        verbose_name_plural = _('Haydovchilar joylashuvi')

    def __str__(self):
        return f'{self.driver.user.phone} — ({self.lat}, {self.lng})'


class LocationHistory(models.Model):
    """
    GPS koordinatalar tarixi — 7 kun saqlash (TZ talabi).
    Eski yozuvlarni o'chirish: Celery periodic task.
    """
    driver     = models.ForeignKey(Driver, on_delete=models.CASCADE,
                                   related_name='location_history')
    lat        = models.DecimalField(max_digits=9, decimal_places=6)
    lng        = models.DecimalField(max_digits=9, decimal_places=6)
    order      = models.ForeignKey(
        'orders.Order', null=True, blank=True, on_delete=models.SET_NULL,
        help_text='Buyurtma davomidagi koordinata'
    )
    timestamp  = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name        = _('Joylashuv tarixi')
        verbose_name_plural = _('Joylashuv tarixi')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['driver', 'timestamp']),
        ]

    def __str__(self):
        return f'{self.driver.user.phone} — {self.timestamp:%Y-%m-%d %H:%M:%S}'
