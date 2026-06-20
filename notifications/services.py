"""
notifications/services.py

Xabar yuborish servis qatlami.

Har bir kanal uchun alohida funksiya:
    send_sms()      -- Eskiz/PlayMobile SMS API
    send_push()     -- Firebase FCM push notification
    send_telegram() -- Telegram Bot API

Har bir funksiya:
    - Xabarni yuboradi
    - Notification modeliga yozadi (audit log)
    - Muvaffaqiyat/xato natijasini qaytaradi

DEV muhit:
    SMS_BACKEND = "console" bo'lsa xabarlar terminalga chiqariladi,
    haqiqiy SMS yuborilmaydi.

Ishlatilish (tasks.py dan chaqiriladi):
    from notifications.services import send_sms
    send_sms(user, "Sizning kodingiz: 123456")
"""

import logging

import requests
from django.conf import settings

from accounts.models import User
from .models import Notification

logger = logging.getLogger(__name__)

# Sukut timeout (soniya)
_REQUEST_TIMEOUT = 10


# ======================================================================
# SMS
# ======================================================================

def send_sms(user: User, message: str) -> bool:
    """
    Foydalanuvchiga SMS yuboradi.

    DEV: SMS_BACKEND="console" bo'lsa terminalga print qiladi.
    PROD: Eskiz yoki PlayMobile API ga so'rov yuboradi.

    Args:
        user:    SMS qabul qiluvchi User obyekti.
        message: Xabar matni.

    Returns:
        True -- muvaffaqiyat, False -- xato.
    """
    backend = getattr(settings, "SMS_BACKEND", "console")

    if backend == "console":
        return _sms_console(user, message)
    elif backend == "eskiz":
        return _sms_eskiz(user, message)
    elif backend == "playmobile":
        return _sms_playmobile(user, message)
    else:
        logger.error("Noto'g'ri SMS_BACKEND: %s", backend)
        return False


def _sms_console(user: User, message: str) -> bool:
    """DEV: SMS ni terminalga chiqaradi."""
    print(f"\n{'='*50}")
    print(f"  📱 SMS → {user.phone}")
    print(f"  {message}")
    print(f"{'='*50}\n")

    _log_notification(
        user=user,
        channel=Notification.Channel.SMS,
        message=message,
        status=Notification.Status.SENT,
    )
    return True


def _sms_eskiz(user: User, message: str) -> bool:
    """
    Eskiz SMS API orqali yuboradi.
    Docs: https://eskiz.uz/api/docs
    """
    token = getattr(settings, "ESKIZ_TOKEN", "")
    if not token:
        logger.error("ESKIZ_TOKEN sozlanmagan.")
        _log_notification(user, Notification.Channel.SMS, message,
                          Notification.Status.FAILED, "ESKIZ_TOKEN yo'q")
        return False

    try:
        resp = requests.post(
            "https://notify.eskiz.uz/api/message/sms/send",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "mobile_phone": user.phone.lstrip("+"),
                "message":      message,
                "from":         getattr(settings, "ESKIZ_FROM", "4546"),
            },
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") == "waiting":
            _log_notification(user, Notification.Channel.SMS, message,
                              Notification.Status.SENT)
            logger.info("Eskiz SMS yuborildi: %s", user.phone)
            return True
        else:
            error = str(data)
            _log_notification(user, Notification.Channel.SMS, message,
                              Notification.Status.FAILED, error)
            logger.warning("Eskiz SMS xato: %s | %s", user.phone, error)
            return False

    except requests.RequestException as exc:
        _log_notification(user, Notification.Channel.SMS, message,
                          Notification.Status.FAILED, str(exc))
        logger.exception("Eskiz SMS so'rov xatosi: %s | %s", user.phone, exc)
        return False


def _sms_playmobile(user: User, message: str) -> bool:
    """
    PlayMobile SMS API orqali yuboradi.
    Docs: https://playmobile.uz/api
    """
    login    = getattr(settings, "PLAYMOBILE_LOGIN", "")
    password = getattr(settings, "PLAYMOBILE_PASSWORD", "")
    originator = getattr(settings, "PLAYMOBILE_ORIGINATOR", "SmartTaxi")

    if not login or not password:
        logger.error("PLAYMOBILE_LOGIN yoki PLAYMOBILE_PASSWORD sozlanmagan.")
        _log_notification(user, Notification.Channel.SMS, message,
                          Notification.Status.FAILED, "Credentials yo'q")
        return False

    try:
        resp = requests.post(
            "https://messages.playmobile.uz/api/send-sms",
            auth=(login, password),
            json={
                "messages": [{
                    "recipient": user.phone.lstrip("+"),
                    "message-id": f"smarttaxi_{user.pk}_{id(message)}",
                    "sms": {
                        "originator": originator,
                        "content":    {"text": message},
                    },
                }]
            },
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()

        _log_notification(user, Notification.Channel.SMS, message,
                          Notification.Status.SENT)
        logger.info("PlayMobile SMS yuborildi: %s", user.phone)
        return True

    except requests.RequestException as exc:
        _log_notification(user, Notification.Channel.SMS, message,
                          Notification.Status.FAILED, str(exc))
        logger.exception("PlayMobile SMS xatosi: %s | %s", user.phone, exc)
        return False


# ======================================================================
# Firebase FCM Push
# ======================================================================

def send_push(user: User, title: str, body: str, data: dict = None) -> bool:
    """
    Firebase FCM orqali push notification yuboradi.

    Foydalanuvchining FCM token'i Driver.card_token yoki
    alohida DeviceToken modelida saqlanishi mumkin.
    Hozirgi versiyada User modelida fcm_token maydoni yo'q —
    bu funksiya token mavjud bo'lganda ishlaydi.

    Args:
        user:  Push qabul qiluvchi User.
        title: Bildirishnoma sarlavhasi.
        body:  Bildirishnoma matni.
        data:  Qo'shimcha ma'lumotlar (dict, ixtiyoriy).

    Returns:
        True -- muvaffaqiyat, False -- xato yoki token yo'q.
    """
    # FCM token: haydovchi uchun driver.card_token emas,
    # keyinchalik alohida UserDevice modeli qo'shiladi.
    # Hozircha placeholder.
    fcm_token = getattr(user, "fcm_token", None)

    if not fcm_token:
        logger.debug("FCM push: %s uchun token yo'q, o'tkazib yuborildi.", user.phone)
        return False

    server_key = getattr(settings, "FCM_SERVER_KEY", "")
    if not server_key:
        logger.error("FCM_SERVER_KEY sozlanmagan.")
        return False

    message = f"{title}: {body}"

    try:
        payload = {
            "to": fcm_token,
            "notification": {"title": title, "body": body},
        }
        if data:
            payload["data"] = data

        resp = requests.post(
            "https://fcm.googleapis.com/fcm/send",
            headers={
                "Authorization": f"key={server_key}",
                "Content-Type":  "application/json",
            },
            json=payload,
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        result = resp.json()

        if result.get("success") == 1:
            _log_notification(user, Notification.Channel.PUSH, message,
                              Notification.Status.SENT)
            logger.info("FCM push yuborildi: %s | %s", user.phone, title)
            return True
        else:
            error = str(result.get("results", ""))
            _log_notification(user, Notification.Channel.PUSH, message,
                              Notification.Status.FAILED, error)
            logger.warning("FCM push xato: %s | %s", user.phone, error)
            return False

    except requests.RequestException as exc:
        _log_notification(user, Notification.Channel.PUSH, message,
                          Notification.Status.FAILED, str(exc))
        logger.exception("FCM push so'rov xatosi: %s | %s", user.phone, exc)
        return False


# ======================================================================
# Telegram Bot
# ======================================================================

def send_telegram(user: User, message: str) -> bool:
    """
    Telegram Bot API orqali xabar yuboradi.

    Foydalanuvchi avval botni start qilgan va user.telegram_id
    saqlangan bo'lishi kerak.

    Args:
        user:    User (telegram_id maydoni bo'lishi kerak).
        message: Xabar matni (HTML formati qo'llab-quvvatlanadi).

    Returns:
        True -- muvaffaqiyat, False -- telegram_id yo'q yoki xato.
    """
    if not user.telegram_id:
        logger.debug("Telegram: %s uchun telegram_id yo'q.", user.phone)
        return False

    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN sozlanmagan.")
        return False

    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                "chat_id":    user.telegram_id,
                "text":       message,
                "parse_mode": "HTML",
            },
            timeout=_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        result = resp.json()

        if result.get("ok"):
            _log_notification(user, Notification.Channel.TELEGRAM, message,
                              Notification.Status.SENT)
            logger.info("Telegram yuborildi: %s", user.phone)
            return True
        else:
            error = result.get("description", "Noma'lum xato")
            _log_notification(user, Notification.Channel.TELEGRAM, message,
                              Notification.Status.FAILED, error)
            logger.warning("Telegram xato: %s | %s", user.phone, error)
            return False

    except requests.RequestException as exc:
        _log_notification(user, Notification.Channel.TELEGRAM, message,
                          Notification.Status.FAILED, str(exc))
        logger.exception("Telegram so'rov xatosi: %s | %s", user.phone, exc)
        return False


# ======================================================================
# Yordamchi: audit log
# ======================================================================

def _log_notification(
    user: User,
    channel: str,
    message: str,
    status: str,
    error_msg: str = "",
) -> Notification:
    """
    Har bir yuborilgan (yoki muvaffaqiyatsiz) xabarni
    Notification jadvaliga yozadi.
    """
    return Notification.objects.create(
        user      = user,
        channel   = channel,
        message   = message[:500],   # Uzun xabarlarni qisqartirish
        status    = status,
        error_msg = error_msg[:255],
    )