from aiogram import Router

from ilmbot.bot.handlers import errors, menu, prayer, start


def create_routers() -> list[Router]:
    """Har bir dispatcher uchun yangi routerlar (router faqat bitta dispatcherga ulanishi mumkin).

    Tartib muhim: `menu` dagi umumiy matn handleri oxirida turishi kerak.
    """
    return [errors.create_router(), start.create_router(), prayer.create_router(), menu.create_router()]
