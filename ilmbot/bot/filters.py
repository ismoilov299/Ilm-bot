from aiogram.filters import Filter
from aiogram.types import TelegramObject, User

from ilmbot.config import Settings


class IsAdmin(Filter):
    """Faqat `ADMINS` ro'yxatidagi Telegram ID lar. Admin bo'lmaganlar uchun handler umuman ishlamaydi."""

    async def __call__(self, event: TelegramObject, event_from_user: User | None, settings: Settings) -> bool:
        return event_from_user is not None and event_from_user.id in settings.admins
