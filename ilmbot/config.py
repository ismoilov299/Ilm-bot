"""Yagona konfiguratsiya manbasi: muhit o'zgaruvchilari va `.env` fayli."""

from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = ""
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
    log_level: str = "INFO"

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
