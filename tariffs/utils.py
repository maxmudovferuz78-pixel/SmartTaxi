"""
tariffs/utils.py

Masofa hisoblash yordamchilari.

Hozirgi holat : Haversine formulasi (matematik, API kerak emas).
Keyingi bosqich: Yandex Maps Directions API bilan almashtirish.
    Faqat shu faylni o'zgartirish kifoya -- boshqa joyda hech narsa
    o'zgarmaydi, chunki hamma joyda calculate_distance() chaqiriladi.

Haversine vs Yandex Maps:
    Haversine -- to'g'ri chiziq (qush uchishi), ~15-20% kam ko'rsatadi.
    Yandex    -- haqiqiy yo'l masofasi, billing uchun aniqroq.
"""

import logging
import math

logger = logging.getLogger(__name__)

# Yer o'rtacha radiusi (km)
_EARTH_RADIUS_KM: float = 6_371.0

# Minimal qaytariladigan masofa (0 km billing xatosidan saqlanish uchun)
_MIN_DISTANCE_KM: float = 0.1


def calculate_distance(
    from_lat: float,
    from_lng: float,
    to_lat: float,
    to_lng: float,
) -> float:
    """
    Ikki GPS nuqtasi orasidagi masofani Haversine formulasi orqali hisoblaydi.

    Haversine formulasi:
        a = sin^2(dLat/2) + cos(lat1) * cos(lat2) * sin^2(dLng/2)
        c = 2 * atan2( sqrt(a), sqrt(1-a) )
        d = R * c

    Args:
        from_lat: Boshlangich nuqta kengligi (latitude),  -90..90  gradus.
        from_lng: Boshlangich nuqta uzunligi (longitude), -180..180 gradus.
        to_lat:   Oxirgi nuqta kengligi,  -90..90  gradus.
        to_lng:   Oxirgi nuqta uzunligi, -180..180 gradus.

    Returns:
        Masofa kilometrda (float, 2 xonali aniqlik). Minimum: 0.1 km.

    Raises:
        ValueError: Koordinata noto'g'ri diapazondan tashqarida bo'lsa.

    Misol:
        >>> calculate_distance(41.2995, 69.2401, 41.3111, 69.2797)
        3.49
    """
    _validate_coordinates(from_lat, from_lng, label="boshlangich")
    _validate_coordinates(to_lat,   to_lng,   label="oxirgi")

    # Gradusdan radianga o'tkazish
    lat1   = math.radians(from_lat)
    lat2   = math.radians(to_lat)
    d_lat  = math.radians(to_lat  - from_lat)
    d_lng  = math.radians(to_lng  - from_lng)

    # Haversine hisob-kitobi
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(d_lng / 2) ** 2
    )
    c        = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    distance = _EARTH_RADIUS_KM * c

    result = round(max(distance, _MIN_DISTANCE_KM), 2)

    logger.debug(
        "Haversine masofa: (%.6f, %.6f) -> (%.6f, %.6f) = %.2f km",
        from_lat, from_lng, to_lat, to_lng, result,
    )
    return result


# ------------------------------------------------------------------
# Ichki yordamchi
# ------------------------------------------------------------------

def _validate_coordinates(lat: float, lng: float, label: str) -> None:
    """
    Koordinatalar to'g'ri diapazondan ekanligini tekshiradi.

    Args:
        lat:   Kenglik (-90 .. 90).
        lng:   Uzunlik (-180 .. 180).
        label: Xato xabarida ishlatiladi ('boshlangich' / 'oxirgi').

    Raises:
        ValueError: Koordinata chegaradan tashqarida bo'lsa.
    """
    try:
        lat = float(lat)
        lng = float(lng)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{label.capitalize()} koordinatalar son bo'lishi kerak."
        ) from exc

    if not (-90.0 <= lat <= 90.0):
        raise ValueError(
            f"{label.capitalize()} kenglik (lat) noto'g'ri: {lat}. "
            "Qiymat -90 dan 90 gacha bo'lishi kerak."
        )
    if not (-180.0 <= lng <= 180.0):
        raise ValueError(
            f"{label.capitalize()} uzunlik (lng) noto'g'ri: {lng}. "
            "Qiymat -180 dan 180 gacha bo'lishi kerak."
        )