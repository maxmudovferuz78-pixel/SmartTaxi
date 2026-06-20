"""
locations/middleware.py

WebSocket uchun JWT autentifikatsiya middleware.

Django Channels standart HTTP middleware larini WebSocket uchun
ishlatmaydi. Shu sababli JWT tokenni WebSocket scope ga inject
qilish uchun maxsus middleware kerak.

Token qabul qilish usullari (ikkalasi ham ishlaydi):
    1. Query param:  ws://host/ws/driver/location/?token=<access_token>
    2. Header:       Authorization: Bearer <access_token>
       (ba'zi frontend kutubxonalari headerdan foydalanadi)

Ishlatilish (config/asgi.py):
    from locations.middleware import JWTAuthMiddlewareStack
    from locations.routing import websocket_urlpatterns

    application = ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": JWTAuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        ),
    })
"""

import logging
from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


class JWTAuthMiddleware(BaseMiddleware):
    """
    WebSocket so'rovida JWT access tokenni tekshirib,
    scope["user"] ni o'rnatadi.

    Token topilmasa yoki yaroqsiz bo'lsa AnonymousUser o'rnatiladi.
    Consumer ichida scope["user"].is_authenticated tekshiriladi.
    """

    async def __call__(self, scope, receive, send):
        scope["user"] = await self._get_user(scope)
        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def _get_user(self, scope):
        """
        Token orqali foydalanuvchini topadi.

        1. Query string dan token olishga harakat qiladi
        2. Topilmasa headers dan olishga harakat qiladi
        3. Token yaroqsiz bo'lsa AnonymousUser qaytaradi
        """
        from rest_framework_simplejwt.exceptions import InvalidToken, TokenError  # noqa: PLC0415
        from rest_framework_simplejwt.tokens import AccessToken  # noqa: PLC0415
        from accounts.models import User  # noqa: PLC0415

        token_str = None

        # 1. Query string: ?token=<access_token>
        query_string = scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        token_list = params.get("token")
        if token_list:
            token_str = token_list[0]

        # 2. Header: Authorization: Bearer <token>
        if not token_str:
            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode("utf-8")
            if auth_header.lower().startswith("bearer "):
                token_str = auth_header[7:].strip()

        if not token_str:
            return AnonymousUser()

        # Token validatsiyasi
        try:
            token   = AccessToken(token_str)
            user_id = token["user_id"]
            return User.objects.get(pk=user_id, is_active=True)
        except (InvalidToken, TokenError) as exc:
            logger.debug("WS JWT xato: %s", exc)
            return AnonymousUser()
        except User.DoesNotExist:
            logger.debug("WS JWT: user_id topilmadi.")
            return AnonymousUser()
        except Exception as exc:
            logger.exception("WS JWT kutilmagan xato: %s", exc)
            return AnonymousUser()


def JWTAuthMiddlewareStack(inner):
    """
    JWTAuthMiddleware + Django Channels AuthMiddlewareStack kombinatsiyasi.

    config/asgi.py da ishlatiladi:
        websocket=JWTAuthMiddlewareStack(URLRouter(websocket_urlpatterns))
    """
    return JWTAuthMiddleware(AuthMiddlewareStack(inner))