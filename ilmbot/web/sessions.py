"""Admin sessiyasi: imzolangan cookie (serverda holat saqlanmaydi) va CSRF tokeni."""

import secrets
from dataclasses import dataclass

from itsdangerous import BadSignature, URLSafeTimedSerializer
from starlette.responses import Response

COOKIE_NAME = "ilm_session"
MIN_SECRET_LENGTH = 32


@dataclass(frozen=True, slots=True)
class AdminSession:
    username: str
    csrf: str  # har bir sessiya uchun tasodifiy; POST so'rovlarda forma maydoni bilan solishtiriladi


class SessionManager:
    def __init__(self, secret: str, *, max_age_hours: int, secure: bool):
        if len(secret) < MIN_SECRET_LENGTH:
            raise RuntimeError(f"SESSION_SECRET kamida {MIN_SECRET_LENGTH} belgidan iborat bo'lishi kerak")
        self._serializer = URLSafeTimedSerializer(secret, salt="ilm-admin-session")
        self._max_age = max_age_hours * 3600
        self._secure = secure

    def start(self, response: Response, username: str) -> None:
        token = self._serializer.dumps({"u": username, "c": secrets.token_urlsafe(32)})
        response.set_cookie(
            COOKIE_NAME, token, max_age=self._max_age, httponly=True, samesite="strict", secure=self._secure, path="/"
        )

    def end(self, response: Response) -> None:
        response.delete_cookie(COOKIE_NAME, path="/", httponly=True, samesite="strict", secure=self._secure)

    def read(self, token: str | None) -> AdminSession | None:
        """Imzosi to'g'ri va muddati o'tmagan sessiya, aks holda None."""
        if not token:
            return None
        try:
            data = self._serializer.loads(token, max_age=self._max_age)
            return AdminSession(username=data["u"], csrf=data["c"])
        except (BadSignature, KeyError, TypeError):
            return None
