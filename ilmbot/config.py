"""Yagona konfiguratsiya manbasi: muhit o'zgaruvchilari va `.env` fayli."""

from functools import lru_cache
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = ""
    mini_app_url: str = ""  # ochiq HTTPS manzil, masalan https://ilm.example/app
    mini_app_auth_max_age: int = 3600
    content_channel: str = "@testislomyolida"
    protect_content: bool = True  # yuborilgan postlarni qayta yuborish/saqlashni cheklash
    database_url: str = "postgresql+asyncpg://ilmbot:ilmbot@localhost:5432/ilmbot"
    redis_url: str = "redis://localhost:6379/0"
    timezone: str = "Asia/Tashkent"
    admin_username: str = "admin"
    admin_password_hash: str = ""
    session_secret: str = ""
    send_rate_per_sec: int = 25  # eslatmalar uchun umumiy Telegram limitidan ajratilgan ulush
    broadcast_rate_per_sec: int = 10  # broadcast eslatmalardan past ustuvorlikda (umumiy hisoblagich)
    admins: Annotated[list[int], NoDecode] = []  # bot ichidagi admin buyruqlari uchun Telegram ID lar (ADMINS=1,2)
    cookie_secure: bool = False  # HTTPS orqasida (productionda) True bo'lishi shart
    session_max_hours: int = 12
    web_host: str = "127.0.0.1"
    web_port: int = 8000
    log_level: str = "INFO"

    @field_validator("mini_app_url")
    @classmethod
    def _mini_app_url(cls, value: str) -> str:
        value = value.strip()
        if value:
            parsed = urlsplit(value)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
                raise ValueError("MINI_APP_URL ochiq HTTPS manzil bo'lishi kerak")
        return value

    @field_validator("mini_app_auth_max_age")
    @classmethod
    def _auth_age(cls, value: int) -> int:
        if not 60 <= value <= 86400:
            raise ValueError("MINI_APP_AUTH_MAX_AGE 60–86400 soniya bo'lishi kerak")
        return value

    @field_validator("admins", mode="before")
    @classmethod
    def _split_admins(cls, value):
        if isinstance(value, str):
            return [int(part) for part in value.replace(";", ",").split(",") if part.strip()]
        return value

    def require_bot_token(self) -> str:
        """Bot va worker ishga tushganda chaqiriladi: token yo'q bo'lsa aniq xato beradi."""
        if not self.bot_token:
            raise RuntimeError("BOT_TOKEN o'rnatilmagan: uni .env fayliga yozing")
        return self.bot_token


@lru_cache
def get_settings() -> Settings:
    return Settings()
