from django.db import models
from django.utils.translation import gettext_lazy as _
from drivers.models import Driver


class Wallet(models.Model):
    """
    Haydovchining virtual hamyoni.
    balance — so'mda saqlanadi.
    Anti-debt: Celery task balance < 5000 bo'lsa driver.is_active = False qiladi.
    """
    driver     = models.OneToOneField(Driver, on_delete=models.CASCADE,
                                      related_name='wallet')
    balance    = models.IntegerField(_('Balans (som)'), default=0)
    updated_at = models.DateTimeField(auto_now=True)

    MIN_BALANCE    = 5_000   # Bloklash chegarasi
    DEPOSIT_MIN    = 10_000  # Ro'yxatdan o'tishda minimal depozit

    class Meta:
        verbose_name        = _('Hamyon')
        verbose_name_plural = _('Hamyonlar')

    def __str__(self):
        return f'{self.driver.user.phone} — {self.balance:,} som'

    @property
    def is_sufficient(self) -> bool:
        return self.balance >= self.MIN_BALANCE


class Transaction(models.Model):
    """
    Hamyon operatsiyalari audit log'i.
    amount: musbat = kirim, manfiy = chiqim.
    """
    class TxType(models.TextChoices):
        TOPUP      = 'topup',      _('Toldirish')
        COMMISSION = 'commission', _('Komissiya yechish')
        REFUND     = 'refund',     _('Qaytarish')
        CASHBACK   = 'cashback',   _('Cashback')

    class PaymentProvider(models.TextChoices):
        PAYME  = 'payme',  'Payme'
        CLICK  = 'click',  'Click'
        UZUM   = 'uzum',   'Uzum'
        MANUAL = 'manual', _('Qolda')

    wallet     = models.ForeignKey(Wallet, on_delete=models.CASCADE,
                                   related_name='transactions')
    amount     = models.IntegerField(_('Miqdor (som)'),
                                      help_text='Musbat = kirim, manfiy = chiqim')
    tx_type    = models.CharField(_('Tur'), max_length=12, choices=TxType.choices)
    provider   = models.CharField(_('Tolov tizimi'), max_length=10,
                                   choices=PaymentProvider.choices,
                                   default=PaymentProvider.MANUAL)
    order      = models.ForeignKey(
        'orders.Order', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='transactions'
    )
    # To'lov tizimining o'z transaction ID si (idempotentlik uchun)
    external_tx_id = models.CharField(max_length=100, blank=True, db_index=True)
    balance_after  = models.IntegerField(_('Operatsiyadan keyingi balans'), default=0)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = _('Tranzaksiya')
        verbose_name_plural = _('Tranzaksiyalar')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', 'created_at']),
            models.Index(fields=['external_tx_id']),
        ]

    def __str__(self):
        sign = '+' if self.amount >= 0 else ''
        return f'{self.wallet.driver.user.phone} | {sign}{self.amount:,} som ({self.get_tx_type_display()})'
