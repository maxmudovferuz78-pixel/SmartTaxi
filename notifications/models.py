from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import User


class Notification(models.Model):
    """
    Push / SMS bildirishnomalar audit log'i.
    """
    class Channel(models.TextChoices):
        SMS      = 'sms',   'SMS'
        PUSH     = 'push',  'Push (Firebase)'
        TELEGRAM = 'tg',    'Telegram Bot'

    class Status(models.TextChoices):
        SENT   = 'sent',   _('Yuborildi')
        FAILED = 'failed', _('Xatolik')

    user       = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='notifications')
    channel    = models.CharField(max_length=5, choices=Channel.choices)
    message    = models.TextField()
    status     = models.CharField(max_length=8, choices=Status.choices,
                                   default=Status.SENT)
    error_msg  = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = _('Bildirishnoma')
        verbose_name_plural = _('Bildirishnomalar')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.phone} | {self.channel} | {self.get_status_display()}'
