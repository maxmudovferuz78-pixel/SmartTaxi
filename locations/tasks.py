"""
locations/tasks.py

Celery periodic vazifalar — joylashuv tarixi boshqaruvi.

TZ talabi: LocationHistory 7 kun saqlanadi, keyin o'chiriladi.

Celery Beat jadval (config/settings.py ga qo'shish):
    CELERY_BEAT_SCHEDULE = {
        "clean_location_history": {
            "task":     "locations.tasks.clean_location_history",
            "schedule": crontab(hour=3, minute=0),  -- har kecha soat 3:00
        },
    }
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

# Saqlash davri (kun)
_RETENTION_DAYS = 7


@shared_task(
    name="locations.tasks.clean_location_history",
    max_retries=3,
    default_retry_delay=300,
)
def clean_location_history() -> dict:
    """
    7 kundan eski LocationHistory yozuvlarini o'chiradi.

    Har kecha soat 3:00 da Celery Beat tomonidan ishga tushiriladi.
    Katta jadval uchun bulk delete — bittama-bitta emas.

    Returns:
        { "deleted_count": int, "threshold": str }
    """
    from .models import LocationHistory  # noqa: PLC0415

    threshold = timezone.now() - timedelta(days=_RETENTION_DAYS)

    try:
        deleted_count, _ = LocationHistory.objects.filter(
            timestamp__lt=threshold
        ).delete()

        logger.info(
            "LocationHistory tozalandi: %d yozuv o'chirildi (chegara: %s)",
            deleted_count,
            threshold.strftime("%Y-%m-%d %H:%M"),
        )

        return {
            "deleted_count": deleted_count,
            "threshold":     threshold.isoformat(),
        }

    except Exception as exc:
        logger.exception("clean_location_history xatolik: %s", exc)
        raise