import logging

from aiogram import Bot, Router
from aiogram.types import ErrorEvent

from ilmbot.bot import texts

log = logging.getLogger(__name__)


async def on_error(event: ErrorEvent, bot: Bot) -> bool:
    log.error("Handlerda xatolik", exc_info=event.exception)
    update = event.update
    chat_id = None
    if update.message is not None:
        chat_id = update.message.chat.id
    elif update.callback_query is not None:
        chat_id = update.callback_query.from_user.id
    if chat_id is not None:
        try:
            await bot.send_message(chat_id, texts.ERROR)
        except Exception:  # noqa: BLE001  (foydalanuvchiga xabar yuborib bo'lmasa ham asosiy xato allaqachon yozilgan)
            log.debug("Xato haqida xabar yuborilmadi", exc_info=True)
    return True


def create_router() -> Router:
    router = Router(name="errors")
    router.error.register(on_error)
    return router
