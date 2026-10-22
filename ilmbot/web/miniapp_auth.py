"""Telegram Mini App initData: HMAC imzosi, muddati va foydalanuvchi identifikatsiyasi.

https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
Cookie yoki initDataUnsafe foydalanuvchi identifikatsiyasi uchun ishlatilmaydi.
"""

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl


class InitDataError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TelegramIdentity:
    id: int
    name: str


def validate_init_data(raw: str, bot_token: str, *, max_age: int = 3600, now: float | None = None) -> TelegramIdentity:
    if not raw or len(raw) > 16384 or not bot_token:
        raise InitDataError("Mini App'ni Telegram bot orqali oching")
    try:
        pairs = parse_qsl(raw, keep_blank_values=True, strict_parsing=True, max_num_fields=32)
        data = dict(pairs)
        if len(data) != len(pairs):
            raise ValueError("duplicate fields")
        received_hash = data.pop("hash")
        check = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
        secret = hmac.digest(b"WebAppData", bot_token.encode(), hashlib.sha256)
        expected_hash = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_hash, received_hash):
            raise ValueError("signature")
        age = (time.time() if now is None else now) - int(data["auth_date"])
        if age < -30 or age > max_age:
            raise ValueError("expired")
        user = json.loads(data["user"])
        if not isinstance(user, dict):
            raise ValueError("user")
        user_id = user["id"]
        if type(user_id) is not int or not 0 < user_id < 2**63 or user.get("is_bot"):
            raise ValueError("id")
        first = user.get("first_name")
        last = user.get("last_name", "")
        if not isinstance(first, str) or not first.strip() or not isinstance(last, str):
            raise ValueError("name")
        return TelegramIdentity(user_id, f"{first} {last}".strip()[:255])
    except (ValueError, KeyError, TypeError, UnicodeError) as exc:
        raise InitDataError("Telegram sessiyasi yaroqsiz yoki eskirgan. Ilovani qayta oching") from exc
