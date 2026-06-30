"""
config/__init__.py

Django ishga tushganda Celery app ni yuklaymiz.
Bu signal'lar va shared_task lar to'g'ri ishlashi uchun kerak.
"""

from .celery import app as celery_app

__all__ = ("celery_app",)
