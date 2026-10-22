"""Boshlang'ich ma'lumotlar: regionlar, masjidlar va menyu daraxti (`seeds/*.json`).

Seed **idempotent va buzmaydi**: faqat yo'q yozuvlarni qo'shadi, mavjudlarini
(admin tahrir qilganlarini ham) o'zgartirmaydi.
"""

import json
from pathlib import Path

from sqlalchemy import insert, select, update
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
        for row in [*load_seed("mosques.json"), *load_seed("mosques_osm.json")]
        if (row["lat"], row["lon"]) not in existing
    ]
    session.add_all(new)
    await session.flush()
    return len(new)


async def seed_menu(session: AsyncSession) -> int:
    """`menu_seed.json` tugunlarini `legacy_key` bo'yicha qo'shadi. Ota-tugunlar ikkinchi o'tishda bog'lanadi."""
    nodes = load_seed("menu_seed.json")["nodes"]
    key_to_id = {key: id_ for key, id_ in (await session.execute(select(Button.legacy_key, Button.id))).all() if key}
    new_nodes = [node for node in nodes if node["key"] not in key_to_id]
    if not new_nodes:
        return 0

    rows = [
        {
            "name": node["name"],
            "kind": node["kind"],
            "action": node.get("action"),
            "text": node.get("text") or "",
            "position": node["position"],
            "legacy_key": node["key"],
            "review_note": node.get("review"),
        }
        for node in new_nodes
    ]
    # Ommaviy yozish (yuzlab tugunni bittadan yozishdan ancha tez); qaytgan ID lar kiritilish tartibida
    result = await session.execute(insert(Button).returning(Button.id, sort_by_parameter_order=True), rows)
    for node, button_id in zip(new_nodes, result.scalars().all(), strict=True):
        key_to_id[node["key"]] = button_id

    parents = []
    for node in new_nodes:
        if node["parent"] is None:
            continue
        if node["parent"] not in key_to_id:
            raise ValueError(f"seed: {node['key']!r} uchun ota-tugun {node['parent']!r} topilmadi")
        parents.append({"id": key_to_id[node["key"]], "parent_id": key_to_id[node["parent"]]})
    if parents:
        await session.execute(update(Button), parents)

    posts = [
        {"button_id": key_to_id[node["key"]], "position": index, "message_id": message_id}
        for node in new_nodes
        for index, message_id in enumerate(node["message_ids"], start=1)
    ]
    if posts:
        await session.execute(insert(ButtonPost), posts)
    await session.flush()
    return len(new_nodes)


async def seed_all(session: AsyncSession) -> dict[str, int]:
    return {
        "regions": await seed_regions(session),
        "mosques": await seed_mosques(session),
        "buttons": await seed_menu(session),
    }
