"""
locations/serializers.py

Joylashuv serializerlari — REST API uchun (HTTP).

WebSocket uchun alohida JSON format consumers.py ichida.
"""

from rest_framework import serializers

from .models import DriverLocation, LocationHistory


class DriverLocationSerializer(serializers.ModelSerializer):
    """Haydovchining so'nggi joylashuvi."""

    driver_phone  = serializers.CharField(source="driver.user.phone", read_only=True)
    car_number    = serializers.CharField(source="driver.car_number",  read_only=True)
    car_type      = serializers.CharField(source="driver.car_type",    read_only=True)

    class Meta:
        model  = DriverLocation
        fields = [
            "driver_id",
            "driver_phone",
            "car_number",
            "car_type",
            "lat",
            "lng",
            "speed_kmh",
            "updated_at",
        ]


class LocationHistorySerializer(serializers.ModelSerializer):
    """Haydovchi GPS tarixi (bitta yozuv)."""

    order_id = serializers.IntegerField(source="order.id", read_only=True, default=None)

    class Meta:
        model  = LocationHistory
        fields = ["id", "lat", "lng", "order_id", "timestamp"]