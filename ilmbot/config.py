"""Yagona konfiguratsiya manbasi: muhit o'zgaruvchilari va `.env` fayli."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = ""
    content_channel: str = "@testislomyolida"
    database_url: str = "postgresql+asyncpg://ilmbot:ilmbot@localhost:5432/ilmbot"
    redis_url: str = "redis://localhost:6379/0"
    timezone: str = "Asia/Tashkent"
    admin_username: str = "admin"
    admin_password_hash: str = ""
    session_secret: str = ""
    send_rate_per_sec: int = 25
    log_level: str = "INFO"

    def require_bot_token(self) -> str:
        """Bot va worker ishga tushganda chaqiriladi: token yo'q bo'lsa aniq xato beradi."""
        if not self.bot_token:
            raise RuntimeError("BOT_TOKEN o'rnatilmagan: uni .env fayliga yozing")
        return self.bot_token


@lru_cache
def get_settings() -> Settings:
    return Settings()
