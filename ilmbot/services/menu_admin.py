"""Menyu daraxtini tahrirlash (admin panel): qo'shish, o'zgartirish, ko'chirish, tartiblash va postlarni biriktirish."""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.db.models import Button, ButtonAction, ButtonKind, ButtonPost
from ilmbot.services.telegram_html import HtmlError, sanitize

MAX_NAME = 255
MAX_TEXT = 4000
PAGE_SIZE_RANGE = (3, 20)
PARENT_KINDS = (ButtonKind.MENU.value, ButtonKind.LIST.value)  # faqat shular ichida tugun bo'lishi mumkin


class MenuAdminError(ValueError):
    """Foydalanuvchiga ko'rsatiladigan tushunarli xato."""


@dataclass(frozen=True, slots=True)
class Row:
    button: Button
    children: int
    posts: int


class MenuAdminService:
    # --- o'qish ------------------------------------------------------------------------------------------

    async def get(self, session: AsyncSession, node_id: int) -> Button | None:
        return await session.get(Button, node_id, populate_existing=True)

    async def rows(self, session: AsyncSession, parent_id: int | None) -> list[Row]:
        """Berilgan tugunning bolalari (nofaollari ham) bolalar va postlar soni bilan."""
        children = (
            await session.scalars(
                select(Button)
                .where(Button.parent_id.is_(None) if parent_id is None else Button.parent_id == parent_id)
                .order_by(Button.position, Button.id)
            )
        ).all()
        ids = [b.id for b in children]
        child_counts = dict(
            (
                await session.execute(
                    select(Button.parent_id, func.count()).where(Button.parent_id.in_(ids)).group_by(Button.parent_id)
                )
            ).all()
        )
        post_counts = dict(
            (
                await session.execute(
                    select(ButtonPost.button_id, func.count())
                    .where(ButtonPost.button_id.in_(ids))
                    .group_by(ButtonPost.button_id)
                )
            ).all()
        )
        return [Row(b, child_counts.get(b.id, 0), post_counts.get(b.id, 0)) for b in children]

    async def path(self, session: AsyncSession, node: Button | None) -> list[Button]:
        """Ildizdan tugunning o'zigacha bo'lgan zanjir."""
        chain: list[Button] = []
        while node is not None:
            chain.append(node)
            node = await session.get(Button, node.parent_id) if node.parent_id is not None else None
        return chain[::-1]

    async def path_text(self, session: AsyncSession, node: Button) -> str:
        return " › ".join(b.name for b in await self.path(session, node))

    async def post_ids(self, session: AsyncSession, node_id: int) -> list[int]:
        return list(
            (
                await session.scalars(
                    select(ButtonPost.message_id).where(ButtonPost.button_id == node_id).order_by(ButtonPost.position)
                )
            ).all()
        )

    async def search(self, session: AsyncSession, query: str, *, kinds: Sequence[str] | None = None, limit: int = 30):
        """Nom bo'yicha qidirish; (tugun, yo'l matni) juftliklari."""
        pattern = f"%{query.strip().replace('%', '').replace('_', '')}%"
        statement = select(Button).where(Button.name.ilike(pattern)).order_by(Button.name).limit(limit)
        if kinds:
            statement = statement.where(Button.kind.in_(list(kinds)))
        nodes = (await session.scalars(statement)).all()
        return [(node, await self.path_text(session, node)) for node in nodes]

    async def needing_review(self, session: AsyncSession) -> list[tuple[Button, str]]:
        nodes = (await session.scalars(select(Button).where(Button.review_note.is_not(None)).order_by(Button.id))).all()
        return [(node, await self.path_text(session, node)) for node in nodes]

    async def count_descendants(self, session: AsyncSession, node_id: int) -> int:
        tree = select(Button.id).where(Button.parent_id == node_id).cte("tree", recursive=True)
        tree = tree.union_all(select(Button.id).join(tree, Button.parent_id == tree.c.id))
        return await session.scalar(select(func.count()).select_from(tree))

    # --- tekshiruvlar ------------------------------------------------------------------------------------

    @staticmethod
    def _clean(name: str, kind: str, action: str | None, text: str, page_size: int) -> tuple[str, str | None, str, int]:
        name = " ".join(name.split())
        if not name:
            raise MenuAdminError("Tugma nomi bo'sh bo'lmasligi kerak")
        if len(name) > MAX_NAME:
            raise MenuAdminError(f"Tugma nomi {MAX_NAME} belgidan oshmasligi kerak")
        if kind not in {k.value for k in ButtonKind}:
            raise MenuAdminError("Tugun turi noto'g'ri")
        if kind == ButtonKind.ACTION.value:
            if action not in {a.value for a in ButtonAction}:
                raise MenuAdminError("«Amal» turi uchun amalni tanlang")
        else:
            action = None
        if len(text) > MAX_TEXT:
            raise MenuAdminError(f"Matn {MAX_TEXT} belgidan oshmasligi kerak")
        try:
            text = sanitize(text) if text.strip() else ""
        except HtmlError as exc:
            raise MenuAdminError(f"Matn: {exc}") from exc
        low, high = PAGE_SIZE_RANGE
        if not low <= page_size <= high:
            raise MenuAdminError(f"Sahifadagi elementlar soni {low} dan {high} gacha bo'lishi kerak")
        return name, action, text, page_size

    async def _require_parent(self, session: AsyncSession, parent_id: int | None) -> Button | None:
        if parent_id is None:
            return None
        parent = await session.get(Button, parent_id)
        if parent is None:
            raise MenuAdminError("Ota tugun topilmadi")
        if parent.kind not in PARENT_KINDS:
            raise MenuAdminError("Ichiga tugun qo'shish faqat «Menyu» yoki «Ro'yxat» turidagi bo'limda mumkin")
        return parent

    async def _next_position(self, session: AsyncSession, parent_id: int | None) -> int:
        where = Button.parent_id.is_(None) if parent_id is None else Button.parent_id == parent_id
        return (await session.scalar(select(func.coalesce(func.max(Button.position), 0)).where(where))) + 1

    # --- yozish ------------------------------------------------------------------------------------------

    async def create(
        self,
        session: AsyncSession,
        *,
        parent_id: int | None,
        name: str,
        kind: str,
        action: str | None = None,
        text: str = "",
        page_size: int = 8,
    ) -> Button:
        name, action, text, page_size = self._clean(name, kind, action, text, page_size)
        await self._require_parent(session, parent_id)
        node = Button(
            parent_id=parent_id,
            position=await self._next_position(session, parent_id),
            name=name,
            kind=kind,
            action=action,
            text=text,
            page_size=page_size,
        )
        session.add(node)
        await session.flush()
        return node

    async def update(
        self,
        session: AsyncSession,
        node: Button,
        *,
        name: str,
        kind: str,
        action: str | None,
        text: str,
        page_size: int,
        is_active: bool,
    ) -> Button:
        name, action, text, page_size = self._clean(name, kind, action, text, page_size)
        if kind not in PARENT_KINDS and await session.scalar(
            select(func.count()).select_from(Button).where(Button.parent_id == node.id)
        ):
            raise MenuAdminError("Ichida tugunlari bor bo'limni «Post» yoki «Amal» turiga o'zgartirib bo'lmaydi")
        node.name, node.kind, node.action, node.text = name, kind, action, text
        node.page_size, node.is_active = page_size, is_active
        await session.flush()
        return node

    async def move(self, session: AsyncSession, node: Button, new_parent_id: int | None) -> Button:
        """Tugunni boshqa bo'limning oxiriga ko'chiradi (o'zining ichiga ko'chirib bo'lmaydi)."""
        await self._require_parent(session, new_parent_id)
        if new_parent_id is not None and node.id in [
            b.id for b in await self.path(session, await session.get(Button, new_parent_id))
        ]:
            raise MenuAdminError("Tugunni o'zining ichiga ko'chirib bo'lmaydi")
        node.parent_id = new_parent_id
        node.position = await self._next_position(session, new_parent_id)
        await session.flush()
        return node

    async def reorder(self, session: AsyncSession, node: Button, direction: str) -> None:
        """Aka-ukalar orasida bir qadam yuqoriga yoki pastga; tartib raqamlari 1..n ga tuzatiladi."""
        where = Button.parent_id.is_(None) if node.parent_id is None else Button.parent_id == node.parent_id
        siblings = list((await session.scalars(select(Button).where(where).order_by(Button.position, Button.id))).all())
        index = next(i for i, b in enumerate(siblings) if b.id == node.id)
        target = index - 1 if direction == "up" else index + 1
        if 0 <= target < len(siblings):
            siblings[index], siblings[target] = siblings[target], siblings[index]
        for position, sibling in enumerate(siblings, start=1):
            sibling.position = position
        await session.flush()

    async def delete(self, session: AsyncSession, node: Button) -> int:
        """Tugunni ichidagilari bilan o'chiradi; o'chirilgan ichki tugunlar sonini qaytaradi."""
        descendants = await self.count_descendants(session, node.id)
        await session.delete(node)
        await session.flush()
        return descendants

    async def set_posts(self, session: AsyncSession, node: Button, message_ids: Sequence[int]) -> None:
        if any(message_id <= 0 for message_id in message_ids):
            raise MenuAdminError("Post ID lari musbat butun sonlar bo'lishi kerak")
        await session.execute(delete(ButtonPost).where(ButtonPost.button_id == node.id))
        session.add_all(
            ButtonPost(button_id=node.id, position=index, message_id=message_id)
            for index, message_id in enumerate(message_ids, start=1)
        )
        await session.flush()

    async def add_post(self, session: AsyncSession, node: Button, message_id: int) -> None:
        await self.set_posts(session, node, [*await self.post_ids(session, node.id), message_id])

    async def clear_review(self, session: AsyncSession, node: Button) -> None:
        node.review_note = None
        await session.flush()


def parse_post_ids(raw: str) -> list[int]:
    """Vergul yoki yangi qator bilan ajratilgan ID larni ro'yxatga aylantiradi (takrorlar olib tashlanadi)."""
    tokens = raw.replace(",", " ").replace(";", " ").split()
    if not all(token.isdigit() for token in tokens):
        raise MenuAdminError(
            "Post ID lari faqat raqamlardan iborat bo'lishi kerak (vergul yoki yangi qator bilan ajrating)"
        )
    return list(dict.fromkeys(int(token) for token in tokens))
