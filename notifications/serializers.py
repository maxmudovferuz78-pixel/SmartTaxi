"""
notifications/serializers.py

Bildirishnoma serializerlari.
"""

from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """Bildirishnomalar ro'yxati uchun (read-only)."""

    channel_display = serializers.CharField(source="get_channel_display", read_only=True)
    status_display  = serializers.CharField(source="get_status_display",  read_only=True)

    class Meta:
        model  = Notification
        fields = [
            "id",
            "channel",
            "channel_display",
            "message",
            "status",
            "status_display",
            "error_msg",
            "created_at",
        ]
        read_only_fields = fields