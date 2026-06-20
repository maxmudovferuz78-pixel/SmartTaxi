"""
tariffs/apps.py

Tariffs ilovasi konfiguratsiyasi.
"""

from django.apps import AppConfig


class TariffsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name               = "tariffs"
    verbose_name       = "Tariflar"
