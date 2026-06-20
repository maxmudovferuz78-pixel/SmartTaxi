"""
config/celery.py

Celery ilovasi konfiguratsiyasi.

Django settings dan avtomatik konfiguratsiya o'qiladi.

Ishlatilish:
    Worker:  celery -A config worker -l info
    Beat:    celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
    Flower:  celery -A config flower --port=5555

config/__init__.py ga qo'shish:
    from .celery import app as celery_app
    __all__ = ("celery_app",)
"""

import os

from celery import Celery

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "config.settings.development",
)

app = Celery("smarttaxi")

# Django settings modulidan CELERY_ prefiksi bilan boshlanuvchi
# barcha sozlamalarni o'qiydi
app.config_from_object("django.conf:settings", namespace="CELERY")

# Barcha app lardagi tasks.py fayllarini avtomatik topadi
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Celery ishlayotganligini tekshirish uchun test task."""
    print(f"Request: {self.request!r}")