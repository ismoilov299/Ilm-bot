"""Botni haqiqiy Telegramsiz sinash vositalari: soxta sessiya va update yaratuvchilar."""

import datetime as dt
from collections.abc import Callable

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.enums import ParseMode
from aiogram.filters.callback_data import CallbackData
from aiogram.methods import AnswerCallbackQuery, CopyMessage, EditMessageText, SendMessage, TelegramMethod
from aiogram.types import CallbackQuery, Chat, Location, Message, MessageEntity, MessageId, Update, User

NOW = dt.datetime(2026, 10, 22, 12, 0, tzinfo=dt.UTC)


class FakeSession(BaseSession):
    """Telegramga so'rov yubormaydi: barcha so'rovlarni yig'adi va mos javob qaytaradi."""

    def __init__(self):
        super().__init__()
        self.requests: list[TelegramMethod] = []
        self._failures: list[tuple[Callable[[TelegramMethod], bool], Exception]] = []
        self._next_id = 1000

    def fail_when(self, predicate: Callable[[TelegramMethod], bool], error: Exception) -> None:
        """Shart bajarilgan birinchi so'rov xato bilan tugaydi (bir marta)."""
        self._failures.append((predicate, error))

    async def close(self) -> None:
        return None

    async def stream_content(self, *args, **kwargs):  # pragma: no cover - ishlatilmaydi
        yield b""

    async def make_request(self, bot: Bot, method: TelegramMethod, timeout: int | None = None):  # noqa: ASYNC109
        for index, (predicate, error) in enumerate(self._failures):
            if predicate(method):
                del self._failures[index]
                raise error
        self.requests.append(method)
        self._next_id += 1
        if isinstance(method, SendMessage):
            return Message(
                message_id=self._next_id, date=NOW, chat=Chat(id=method.chat_id, type="private"), text=method.text
            )
        if isinstance(method, CopyMessage):
            return MessageId(message_id=self._next_id)
        if isinstance(method, EditMessageText | AnswerCallbackQuery):
            return True
        return True


def make_bot() -> Bot:
    return Bot("42:TEST", session=FakeSession(), default=DefaultBotProperties(parse_mode=ParseMode.HTML))


def _user(user_id: int) -> User:
    return User(id=user_id, is_bot=False, first_name="Sinov", last_name="Foydalanuvchi")


def _message(user_id: int, text: str, message_id: int = 1) -> Message:
    entities = None
    if text.startswith("/"):
        entities = [MessageEntity(type="bot_command", offset=0, length=len(text.split()[0]))]
    return Message(
        message_id=message_id,
        date=NOW,
        chat=Chat(id=user_id, type="private"),
        from_user=_user(user_id),
        text=text,
        entities=entities,
    )


class Harness:
    """Dispatcher + soxta bot: foydalanuvchi nomidan matn yuborish yoki tugma bosish."""

    def __init__(self, dp: Dispatcher, bot: Bot):
        self.dp = dp
        self.bot = bot
        self._update_id = 0

    @property
    def session(self) -> FakeSession:
        return self.bot.session  # type: ignore[return-value]

    async def _feed(self, **kwargs) -> list[TelegramMethod]:
        self._update_id += 1
        self.session.requests.clear()
        await self.dp.feed_update(self.bot, Update(update_id=self._update_id, **kwargs))
        return list(self.session.requests)

    async def say(self, text: str, user_id: int = 111) -> list[TelegramMethod]:
        return await self._feed(message=_message(user_id, text))

    async def send_location(self, lat: float, lon: float, user_id: int = 111) -> list[TelegramMethod]:
        message = Message(
            message_id=1,
            date=NOW,
            chat=Chat(id=user_id, type="private"),
            from_user=_user(user_id),
            location=Location(latitude=lat, longitude=lon),
        )
        return await self._feed(message=message)

    async def press(self, data: str | CallbackData, user_id: int = 111) -> list[TelegramMethod]:
        packed = data.pack() if isinstance(data, CallbackData) else data
        query = CallbackQuery(
            id=str(self._update_id + 1),
            from_user=_user(user_id),
            chat_instance="test",
            data=packed,
            message=_message(user_id, "Oldingi xabar", message_id=500),
        )
        return await self._feed(callback_query=query)


def keyboard_texts(method: TelegramMethod) -> list[str]:
    """Reply yoki inline klaviaturadagi barcha tugma matnlari (qatorlar tartibida)."""
    markup = method.reply_markup
    rows = markup.keyboard if hasattr(markup, "keyboard") else markup.inline_keyboard
    return [button.text for row in rows for button in row]


def callback_datas(method: TelegramMethod) -> list[str]:
    return [
        button.callback_data for row in method.reply_markup.inline_keyboard for button in row if button.callback_data
    ]
