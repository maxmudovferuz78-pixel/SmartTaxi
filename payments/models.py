from django.db import models
from django.utils.translation import gettext_lazy as _
from orders.models import Order
from wallet.models import Wallet


class PaymentRequest(models.Model):
    """
    To'lov so'rovi — Payme/Click/Uzum dan kelgan to'lovlar.
    Idempotentlik: external_id takrorlanmasligi shart.
    """
    class Provider(models.TextChoices):
        PAYME = 'payme', 'Payme'
        CLICK = 'click', 'Click'
        UZUM  = 'uzum',  'Uzum'

    class Status(models.TextChoices):
        PENDING   = 'pending',   _('Kutilmoqda')
        COMPLETED = 'completed', _('Bajarildi')
        FAILED    = 'failed',    _('Xatolik')
        CANCELLED = 'cancelled', _('Bekor qilindi')

    wallet      = models.ForeignKey(Wallet, on_delete=models.CASCADE,
                                    related_name='payment_requests')
    order       = models.ForeignKey(Order, null=True, blank=True,
                                    on_delete=models.SET_NULL)
    provider    = models.CharField(max_length=10, choices=Provider.choices)
    amount      = models.PositiveIntegerField(_('Miqdor (som)'))
    status      = models.CharField(max_length=12, choices=Status.choices,
                                    default=Status.PENDING)

    # To'lov tizimidan kelgan ID (idempotentlik)
    external_id = models.CharField(max_length=100, unique=True)
    raw_payload = models.JSONField(_('Xom malumot'), default=dict,
                                    help_text='Webhook dan kelgan toliq JSON')
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _('Tolov sorovi')
        verbose_name_plural = _('Tolov sorovlari')
        indexes = [
            models.Index(fields=['external_id']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f'{self.provider} | {self.amount:,} som | {self.get_status_display()}'
