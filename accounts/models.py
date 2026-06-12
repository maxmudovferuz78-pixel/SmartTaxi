from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Markaziy foydalanuvchi modeli.
    phone — login sifatida ishlatiladi (username o'rniga).
    """
    class Role(models.TextChoices):
        ADMIN    = 'admin',    _('Admin')
        OPERATOR = 'operator', _('Operator')
        DRIVER   = 'driver',   _('Haydovchi')
        CLIENT   = 'client',   _('Mijoz')

    phone      = models.CharField(_('Telefon raqam'), max_length=13, unique=True)
    role       = models.CharField(_('Rol'), max_length=10, choices=Role.choices)
    is_elderly = models.BooleanField(
        _('Qariya mijoz'),
        default=False,
        help_text='True bolsa operator paneliga ogohlantirish chiqadi'
    )
    telegram_id = models.BigIntegerField(_('Telegram ID'), null=True, blank=True, unique=True)
    cashback_balance = models.PositiveIntegerField(_('Cashback balansi (som)'), default=0)

    # phone orqali kirish
    USERNAME_FIELD  = 'phone'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name        = _('Foydalanuvchi')
        verbose_name_plural = _('Foydalanuvchilar')
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f'{self.phone} ({self.get_role_display()})'


class OTPCode(models.Model):
    """
    SMS orqali yuborilgan bir martalik parol.
    created_at + 3 daqiqa — muddati tugaydi.
    """
    phone      = models.CharField(_('Telefon'), max_length=13, db_index=True)
    code       = models.CharField(_('Kod'), max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used    = models.BooleanField(default=False)

    class Meta:
        verbose_name        = _('OTP kod')
        verbose_name_plural = _('OTP kodlar')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.phone} — {self.code}'


class SavedAddress(models.Model):
    """
    Zaxira manzillar — ayniqsa qariya mijozlar uchun.
    Operator 'Doimiy manzil mavjud' ogohlantirishini shu jadvaldan oladi.
    """
    user       = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='saved_addresses')
    label      = models.CharField(_('Nom'), max_length=50,
                                   help_text='Masalan: Uy, Ish, Shifoxona')
    address    = models.CharField(_('Manzil matni'), max_length=255)
    lat        = models.DecimalField(max_digits=9, decimal_places=6)
    lng        = models.DecimalField(max_digits=9, decimal_places=6)
    is_default = models.BooleanField(_('Asosiy manzil'), default=False)

    class Meta:
        verbose_name        = _('Saqlangan manzil')
        verbose_name_plural = _('Saqlangan manzillar')

    def __str__(self):
        return f'{self.user.phone} — {self.label}'