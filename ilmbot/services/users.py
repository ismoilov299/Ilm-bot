"""Foydalanuvchilar: ro'yxatdan o'tish va faollikni yangilash."""

import datetime as dt

from sqlalchemy import literal_column
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.db.models import User


class UserService:
    async def touch(self, session: AsyncSession, telegram_id: int, name: str) -> bool:
        """Foydalanuvchini qo'shadi yoki yangilaydi. Yangi bo'lsa True qaytaradi.

        Botni oldin bloklagan foydalanuvchi qaytib yozsa, `is_blocked` bekor qilinadi.
        """
        now = dt.datetime.now(dt.UTC)
        statement = (
            insert(User)
            .values(id=telegram_id, name=name[:255], last_seen_at=now)
            .on_conflict_do_update(
                index_elements=[User.id],
                set_={"name": name[:255], "last_seen_at": now, "is_blocked": False},
            )
            .returning(literal_column("(xmax = 0)"))
        )
        return bool(await session.scalar(statement))
