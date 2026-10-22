"""Sxema, migratsiya va seed haqiqiy PostgreSQL da."""

import datetime as dt

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ilmbot.db import Base
from ilmbot.db.models import Button, ButtonPost, Mosque, PrayerTime, Region, User
from ilmbot.seed import load_seed, seed_all


async def test_migrations_match_models(session):
    """Alembic migratsiyalari modellar bilan bir xil sxema hosil qiladi (farq bo'lsa yangi migratsiya kerak)."""
    connection = await session.connection()

    diff = await connection.run_sync(
        lambda sync_conn: compare_metadata(MigrationContext.configure(sync_conn), Base.metadata)
    )

    assert diff == []


async def test_telegram_ids_above_32_bit_are_supported(session):
    session.add(User(id=5_670_833_851, name="Katta ID"))
    await session.flush()

    assert await session.scalar(select(User.id)) == 5_670_833_851


async def test_prayer_time_is_unique_per_region_and_date(session):
    region = Region(name="Test", api_name="Test", lat=41.0, lon=69.0)
    session.add(region)
    await session.flush()
    row = {
        "region_id": region.id,
        "date": dt.date(2026, 10, 22),
        **dict.fromkeys(("bomdod", "quyosh", "peshin", "asr", "shom", "xufton"), dt.time(5, 0)),
    }
    session.add(PrayerTime(**row))
    await session.flush()

    session.add(PrayerTime(**row))
    with pytest.raises(IntegrityError):
        await session.flush()


async def test_button_kind_is_constrained(session):
    session.add(Button(name="Noto'g'ri", kind="bunday-tur-yo'q"))

    with pytest.raises(IntegrityError):
        await session.flush()


async def test_deleting_a_button_removes_children_and_posts(session):
    parent = Button(name="Ota", kind="list")
    session.add(parent)
    await session.flush()
    child = Button(name="Bola", kind="post", parent_id=parent.id, posts=[ButtonPost(position=1, message_id=10)])
    session.add(child)
    await session.flush()

    await session.delete(parent)
    await session.flush()

    assert await session.scalar(select(func.count()).select_from(Button)) == 0
    assert await session.scalar(select(func.count()).select_from(ButtonPost)) == 0


async def test_seed_loads_everything_and_builds_the_tree(session):
    counts = await seed_all(session)

    assert counts == {"regions": 13, "mosques": 115, "buttons": 801}
    nodes = load_seed("menu_seed.json")["nodes"]
    assert await session.scalar(select(func.count()).select_from(ButtonPost)) == sum(
        len(n["message_ids"]) for n in nodes
    )
    roots = (await session.scalars(select(Button).where(Button.parent_id.is_(None)).order_by(Button.position))).all()
    assert len(roots) == 10
    assert await session.scalar(select(func.count()).select_from(Button).where(Button.review_note.is_not(None))) == sum(
        1 for n in nodes if n.get("review")
    )
    total = await session.scalar(select(func.count()).select_from(Button))
    with_parent = await session.scalar(select(func.count()).select_from(Button).where(Button.parent_id.is_not(None)))
    assert with_parent == total - len(roots)


async def test_seed_keeps_multiple_posts_in_order(session):
    await seed_all(session)

    book = await session.scalar(select(Button).where(Button.legacy_key == "kitob_9"))
    await session.refresh(book, ["posts"])

    assert [p.message_id for p in book.posts] == list(range(668, 677))
    assert [p.position for p in book.posts] == list(range(1, 10))


async def test_seed_is_idempotent_and_does_not_overwrite_admin_edits(session):
    await seed_all(session)
    button = await session.scalar(select(Button).where(Button.legacy_key == "duo"))
    button.name = "Admin o'zgartirgan nom"
    await session.flush()

    second = await seed_all(session)

    assert second == {"regions": 0, "mosques": 0, "buttons": 0}
    assert await session.scalar(select(Button.name).where(Button.legacy_key == "duo")) == "Admin o'zgartirgan nom"
    assert await session.scalar(select(func.count()).select_from(Mosque)) == 115
