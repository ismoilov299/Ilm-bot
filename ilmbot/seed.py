"""Boshlang'ich ma'lumotlar: regionlar, masjidlar va menyu daraxti (`seeds/*.json`).

Seed **idempotent va buzmaydi**: faqat yo'q yozuvlarni qo'shadi, mavjudlarini
(admin tahrir qilganlarini ham) o'zgartirmaydi.
"""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.db.models import Button, ButtonPost, Mosque, Region

SEEDS_DIR = Path(__file__).resolve().parent.parent / "seeds"


def load_seed(name: str):
    return json.loads((SEEDS_DIR / name).read_text(encoding="utf-8"))


async def seed_regions(session: AsyncSession) -> int:
    existing = set((await session.scalars(select(Region.name))).all())
    new = [Region(**row) for row in load_seed("regions.json") if row["name"] not in existing]
    session.add_all(new)
    await session.flush()
    return len(new)


async def seed_mosques(session: AsyncSession) -> int:
    existing = set((await session.execute(select(Mosque.lat, Mosque.lon))).all())
    new = [
        Mosque(
            name=row["name"],
            district=row.get("district"),
            lat=row["lat"],
            lon=row["lon"],
            review_note=row.get("review"),
        )
        for row in load_seed("mosques.json")
        if (row["lat"], row["lon"]) not in existing
    ]
    session.add_all(new)
    await session.flush()
    return len(new)


async def seed_menu(session: AsyncSession) -> int:
    """`menu_seed.json` tugunlarini `legacy_key` bo'yicha qo'shadi. Ota-tugunlar ikkinchi o'tishda bog'lanadi."""
    nodes = load_seed("menu_seed.json")["nodes"]
    key_to_id = {key: id_ for key, id_ in (await session.execute(select(Button.legacy_key, Button.id))).all() if key}

    created: list[tuple[Button, dict]] = []
    for node in nodes:
        if node["key"] in key_to_id:
            continue
        button = Button(
            name=node["name"],
            kind=node["kind"],
            action=node.get("action"),
            text=node.get("text") or "",
            position=node["position"],
            legacy_key=node["key"],
            review_note=node.get("review"),
        )
        button.posts = [ButtonPost(position=i, message_id=mid) for i, mid in enumerate(node["message_ids"], start=1)]
        session.add(button)
        created.append((button, node))
    await session.flush()

    key_to_id.update({node["key"]: button.id for button, node in created})
    for button, node in created:
        parent_key = node["parent"]
        if parent_key is None:
            continue
        if parent_key not in key_to_id:
            raise ValueError(f"seed: {node['key']!r} uchun ota-tugun {parent_key!r} topilmadi")
        button.parent_id = key_to_id[parent_key]
    await session.flush()
    return len(created)


async def seed_all(session: AsyncSession) -> dict[str, int]:
    return {
        "regions": await seed_regions(session),
        "mosques": await seed_mosques(session),
        "buttons": await seed_menu(session),
    }
