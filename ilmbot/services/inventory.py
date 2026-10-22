"""Kontent kanalidagi postlar inventari (`seeds/channel_inventory.json`) va ularning menyuga biriktirilganligi."""

import json
from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.db.models import ButtonPost
from ilmbot.seed import SEEDS_DIR

PER_PAGE = 50
STATUSES = ("unassigned", "assigned", "ignored", "all")


@dataclass(frozen=True, slots=True)
class InventoryPost:
    id: int
    date: str
    type: str
    title: str
    ignored: bool  # inventar tuzilganda axlat deb belgilangan (zip, sinov yozuvlari...)


@lru_cache
def load_inventory() -> tuple[InventoryPost, ...]:
    path = SEEDS_DIR / "channel_inventory.json"
    if not path.exists():
        return ()
    rows = json.loads(path.read_text(encoding="utf-8"))
    return tuple(InventoryPost(r["id"], r["date"], r["type"], r["title"], r["status"] == "ignore") for r in rows)


class InventoryService:
    async def assigned_ids(self, session: AsyncSession) -> set[int]:
        return set((await session.scalars(select(ButtonPost.message_id))).all())

    def types(self) -> list[str]:
        return sorted({post.type for post in load_inventory()})

    async def page(
        self,
        session: AsyncSession,
        *,
        status: str = "unassigned",
        kind: str = "",
        query: str = "",
        page: int = 1,
    ) -> tuple[list[tuple[InventoryPost, bool]], int]:
        """(sahifadagi (post, biriktirilganmi) juftliklari, filtrga mos jami soni)."""
        assigned = await self.assigned_ids(session)
        needle = query.strip().casefold()
        matches = []
        for post in load_inventory():
            is_assigned = post.id in assigned
            if status == "unassigned" and (is_assigned or post.ignored):
                continue
            if status == "assigned" and not is_assigned:
                continue
            if status == "ignored" and (is_assigned or not post.ignored):
                continue
            if kind and post.type != kind:
                continue
            if needle and needle not in post.title.casefold() and needle != str(post.id):
                continue
            matches.append((post, is_assigned))
        start = (max(1, page) - 1) * PER_PAGE
        return matches[start : start + PER_PAGE], len(matches)

    def get(self, post_id: int) -> InventoryPost | None:
        return next((post for post in load_inventory() if post.id == post_id), None)
