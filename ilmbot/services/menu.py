"""Menyu daraxti: bazadan o'qiladi, xotirada qisqa muddat keshlanadi (tugunlar ~800 ta, hajmi kichik)."""

import asyncio
import re
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.db.models import Button, ButtonPost

MENU_VERSION_KEY = "menu:version"


async def bump_menu_version(redis) -> None:
    """Admin menyuni o'zgartirgach chaqiradi: bot keyingi so'rovda daraxtni darhol qayta yuklaydi."""
    await redis.incr(MENU_VERSION_KEY)


_APOSTROPHES = re.compile("[‘’ʻʼ`´]")


def normalize(text: str) -> str:
    """Tugma matnlarini solishtirish uchun: bo'shliqlar, registr va apostrof turlari farqini yo'qotadi."""
    return " ".join(_APOSTROPHES.sub("'", text).split()).casefold()


@dataclass(frozen=True, slots=True)
class Node:
    id: int
    parent_id: int | None
    name: str
    kind: str
    action: str | None
    text: str
    page_size: int
    position: int
    message_ids: tuple[int, ...]


class MenuSnapshot:
    """Faol tugunlarning o'zgarmas ko'rinishi. Ota-tuguni faol bo'lmagan tugunlar kirmaydi."""

    def __init__(self, nodes: dict[int, Node], children: dict[int | None, tuple[Node, ...]]):
        self.nodes = nodes
        self._children = children
        self._by_name = {
            parent_id: {normalize(child.name): child for child in reversed(items)}  # takrorlanganda birinchisi yutadi
            for parent_id, items in children.items()
        }

    @property
    def roots(self) -> Sequence[Node]:
        return self._children.get(None, ())

    def children(self, parent_id: int | None) -> Sequence[Node]:
        return self._children.get(parent_id, ())

    def get(self, node_id: int | None) -> Node | None:
        return self.nodes.get(node_id) if node_id is not None else None

    def child_by_name(self, parent_id: int | None, text: str) -> Node | None:
        return self._by_name.get(parent_id, {}).get(normalize(text))


class MenuService:
    def __init__(
        self,
        ttl: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
        version: Callable[[], Awaitable[object]] | None = None,
    ):
        self._ttl = ttl
        self._clock = clock
        self._version = version  # o'zgarish belgisi (masalan, Redis dagi hisoblagich); o'zgarsa kesh bekor bo'ladi
        self._loaded_version: object = None
        self._snapshot: MenuSnapshot | None = None
        self._loaded_at = 0.0
        self._lock = asyncio.Lock()

    def invalidate(self) -> None:
        self._snapshot = None

    async def snapshot(self, session: AsyncSession) -> MenuSnapshot:
        version = await self._version() if self._version else None
        if self._is_fresh(version):
            return self._snapshot
        async with self._lock:
            if not self._is_fresh(version):
                self._snapshot = await self._load(session)
                self._loaded_at = self._clock()
                self._loaded_version = version
            return self._snapshot

    def _is_fresh(self, version: object) -> bool:
        return (
            self._snapshot is not None
            and version == self._loaded_version
            and self._clock() - self._loaded_at < self._ttl
        )

    @staticmethod
    async def _load(session: AsyncSession) -> MenuSnapshot:
        buttons = (await session.scalars(select(Button).where(Button.is_active))).all()
        posts: dict[int, list[int]] = {}
        rows = await session.execute(select(ButtonPost.button_id, ButtonPost.message_id).order_by(ButtonPost.position))
        for button_id, message_id in rows:
            posts.setdefault(button_id, []).append(message_id)

        raw: dict[int | None, list[Button]] = {}
        for button in buttons:
            raw.setdefault(button.parent_id, []).append(button)

        nodes: dict[int, Node] = {}
        children: dict[int | None, tuple[Node, ...]] = {}
        stack: list[int | None] = [None]
        while stack:  # faqat ildizdan faol zanjir orqali yetib boriladigan tugunlar
            parent_id = stack.pop()
            ordered = sorted(raw.get(parent_id, ()), key=lambda b: (b.position, b.id))
            built = tuple(
                Node(
                    id=b.id,
                    parent_id=b.parent_id,
                    name=b.name,
                    kind=b.kind,
                    action=b.action,
                    text=b.text,
                    page_size=b.page_size,
                    position=b.position,
                    message_ids=tuple(posts.get(b.id, ())),
                )
                for b in ordered
            )
            if built:
                children[parent_id] = built
            for node in built:
                nodes[node.id] = node
                stack.append(node.id)
        return MenuSnapshot(nodes, children)
