"""
accounts/permissions.py

Role-based access control (RBAC) — SmartTaxi uchun ruxsatnomalar.

Ierarxiya:
    Admin > Operator > Driver (aktiv) > Driver (passiv) > Client

Ishlatilish:
    class MyView(APIView):
        permission_classes = [IsAuthenticated, IsOperator]
"""

from rest_framework.permissions import BasePermission, IsAuthenticated  # noqa: F401


class IsOperator(BasePermission):
    """
    Faqat admin va operator rolidagi foydalanuvchilarga ruxsat beradi.

    Buyurtma yaratish, haydovchi boshqarish, moliya hisoboti kabi
    operator paneli endpointlarida ishlatiladi.
    """

    message = "Bu amalni bajarish uchun operator yoki admin huquqi kerak."

    def has_permission(self, request, view) -> bool:
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in (
                request.user.Role.ADMIN,
                request.user.Role.OPERATOR,
            )
        )


class IsDriver(BasePermission):
    """
    Faqat haydovchi rolidagi foydalanuvchilarga ruxsat beradi.

    GPS yuborish, buyurtma qabul qilish, hamyon ko'rish
    endpointlarida ishlatiladi.
    """

    message = "Bu amalni bajarish uchun haydovchi huquqi kerak."

    def has_permission(self, request, view) -> bool:
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == request.user.Role.DRIVER
        )


class IsActiveDriver(BasePermission):
    """
    Haydovchi aktiv (is_active=True) bo'lgandagina ruxsat beradi.

    Anti-debt logikasi:
        Wallet.balance < 5 000 so'm  →  Driver.is_active = False
        Driver.is_active = False     →  bu ruxsatnoma INKOR qiladi

    Yangi buyurtma qabul qilish, GPS broadcast endpointlarida
    ishlatiladi. Hamyon to'ldirish uchun IsDriver yetarli —
    IsActiveDriver talab qilinmaydi (aks holda haydovchi
    balansini to'ldira olmaydi).
    """

    message = (
        "Hamyoningiz balansi yetarli emas (minimal: 5 000 so'm). "
        "Iltimos, hamyoningizni to'ldiring."
    )

    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False

        if request.user.role != request.user.Role.DRIVER:
            return False

        # Driver profili mavjudligini tekshiramiz
        # hasattr — driver profili hali yaratilmagan holatni himoya qiladi
        driver = getattr(request.user, "driver", None)
        if driver is None:
            return False

        return driver.is_active


class IsAdminUser(BasePermission):
    """
    Faqat admin rolidagi foydalanuvchilarga ruxsat beradi.

    Tizim sozlamalari, tariflarni o'zgartirish, foydalanuvchini
    bloklash kabi maxsus admin endpointlarida ishlatiladi.
    """

    message = "Bu amalni bajarish uchun admin huquqi kerak."

    def has_permission(self, request, view) -> bool:
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == request.user.Role.ADMIN
        )


class IsOwnerOrOperator(BasePermission):
    """
    Object-level ruxsatnoma.

    Foydalanuvchi o'zining ma'lumotini ko'rishi yoki
    operator/admin istalgan foydalanuvchining ma'lumotini ko'rishi mumkin.

    Ishlatilish:
        permission_classes = [IsAuthenticated, IsOwnerOrOperator]
        # view'da get_object() ishlatilishi kerak
    """

    message = "Siz faqat o'z ma'lumotlaringizga kira olasiz."

    def has_object_permission(self, request, view, obj) -> bool:
        # obj — User instance bo'lishi kerak
        if request.user.role in (
            request.user.Role.ADMIN,
            request.user.Role.OPERATOR,
        ):
            return True

        return obj == request.user