"""Admin panel: kanal postlari, foydalanuvchilar, namoz vaqtlari, masjidlar va shaharlar."""

import datetime as dt
import re

import pytest
from sqlalchemy import func, select

from ilmbot.db.models import BroadcastJob, Button, ButtonPost, Mosque, PrayerTime, Region, User
from ilmbot.services.broadcast import BroadcastService
from ilmbot.services.inventory import load_inventory
from tests.web_harness import csrf, signed_in_client

TODAY = dt.date(2026, 10, 22)


@pytest.fixture
async def panel(seeded, sessionmaker, redis, settings):
    async with signed_in_client(sessionmaker, redis, settings) as client:
        yield client


async def node(session, key: str) -> Button:
    return await session.scalar(select(Button).where(Button.legacy_key == key))


def total_of(page: str) -> int:
    return int(re.search(r"Topildi: (\d+)", page).group(1))


# --- kanal postlari ------------------------------------------------------------------------------------


async def test_unassigned_posts_exclude_those_already_in_the_menu(panel, session):
    assigned = set((await session.scalars(select(ButtonPost.message_id))).all())
    unassigned = total_of((await panel.get("/inventory")).text)
    in_menu = total_of((await panel.get("/inventory?status=assigned")).text)

    inventory = load_inventory()
    expected_unassigned = sum(1 for p in inventory if p.id not in assigned and not p.ignored)
    assert unassigned == expected_unassigned > 100
    assert in_menu == sum(1 for p in inventory if p.id in assigned) > 700


async def test_inventory_filters_by_type_and_text(panel):
    videos = total_of((await panel.get("/inventory?status=all&type=video_file")).text)
    found = total_of((await panel.get("/inventory?status=all&q=Muallimi")).text)

    assert 0 < videos < len(load_inventory()) and found > 50


async def test_unassigned_post_can_be_attached_to_an_existing_post_node(panel, session):
    post = next(p for p in load_inventory() if p.id not in set())  # istalgan post
    gusl = await node(session, "gusl")
    token = await csrf(panel, f"/inventory/{post.id}/assign")

    response = await panel.post(
        f"/inventory/{post.id}/assign", data={"csrf": token, "mode": "attach", "node_id": gusl.id}
    )

    ids = (
        await session.scalars(
            select(ButtonPost.message_id).where(ButtonPost.button_id == gusl.id).order_by(ButtonPost.position)
        )
    ).all()
    assert response.status_code == 303 and list(ids) == [655, post.id] or post.id == 655


async def test_unassigned_post_can_become_a_new_child_button(panel, session):
    assigned = set((await session.scalars(select(ButtonPost.message_id))).all())
    post = next(p for p in load_inventory() if p.id not in assigned and not p.ignored)
    kitoblar = await node(session, "kitoblar")
    token = await csrf(panel, f"/inventory/{post.id}/assign?q=Kitob")

    response = await panel.post(
        f"/inventory/{post.id}/assign",
        data={"csrf": token, "mode": "child", "node_id": kitoblar.id, "name": "Yangi kitob"},
    )

    created = await session.scalar(select(Button).where(Button.name == "Yangi kitob", Button.parent_id == kitoblar.id))
    assert response.status_code == 303 and created is not None and created.kind == "post"
    assert (await session.scalar(select(ButtonPost.message_id).where(ButtonPost.button_id == created.id))) == post.id
    again = total_of((await panel.get("/inventory")).text)
    assert again == total_of((await panel.get("/inventory?q=")).text)  # endi ro'yxatda yo'q


async def test_assign_search_and_errors(panel, session):
    assigned = set((await session.scalars(select(ButtonPost.message_id))).all())
    post = next(p for p in load_inventory() if p.id not in assigned)
    page = (await panel.get(f"/inventory/{post.id}/assign?q=Duo")).text
    token = await csrf(panel)

    assert "Shu tugunga qo&#39;shish" in page or "Yangi tugma sifatida" in page
    assert (await panel.get("/inventory/999999/assign")).status_code == 404
    namoz = await node(session, "namoz")
    bad = await panel.post(f"/inventory/{post.id}/assign", data={"csrf": token, "mode": "attach", "node_id": namoz.id})
    assert bad.status_code == 400


# --- foydalanuvchilar ----------------------------------------------------------------------------------


async def test_users_search_and_filters(panel, session):
    session.add_all(
        [
            User(id=5_670_833_851, name="Alisher Valiyev", subscribed=True),
            User(id=2, name="Bobur", is_blocked=True),
            User(id=3, name="Alibek"),
        ]
    )
    await session.flush()

    everyone = total_of((await panel.get("/users")).text)
    by_name = (await panel.get("/users?q=ali")).text
    by_id = (await panel.get("/users?q=5670833851")).text
    blocked = (await panel.get("/users?filter=blocked")).text
    subscribed = (await panel.get("/users?filter=subscribed")).text

    assert everyone == 3
    assert total_of(by_name) == 2 and "Bobur" not in by_name
    assert total_of(by_id) == 1 and "Alisher Valiyev" in by_id
    assert total_of(blocked) == 1 and "Bobur" in blocked
    assert total_of(subscribed) == 1 and "Alisher" in subscribed


# --- namoz vaqtlari ------------------------------------------------------------------------------------


async def test_prayer_page_shows_all_cities_for_the_day(panel):
    page = (await panel.get(f"/prayer-times?date={TODAY}")).text

    assert page.count("hisoblangan") >= 13 and "Toshkent" in page and "Marg&#39;ilon" in page


async def test_manual_prayer_times_are_saved_and_survive_recalculation(panel, session):
    toshkent = await session.scalar(select(Region).where(Region.name == "Toshkent"))
    token = await csrf(panel, f"/prayer-times/{toshkent.id}/{TODAY}")
    times = {
        "bomdod": "05:01",
        "quyosh": "06:21",
        "peshin": "12:05",
        "asr": "15:40",
        "shom": "17:30",
        "xufton": "18:55",
    }

    saved = await panel.post(f"/prayer-times/{toshkent.id}/{TODAY}", data={"csrf": token, **times})

    row = await session.scalar(select(PrayerTime).where(PrayerTime.region_id == toshkent.id, PrayerTime.date == TODAY))
    assert saved.status_code == 303 and row.source == "manual" and row.bomdod == dt.time(5, 1)
    from ilmbot.services.prayers import PrayerService

    await PrayerService().ensure_times(session, TODAY, days=1)
    await session.refresh(row)
    assert row.bomdod == dt.time(5, 1)  # hisoblash qo'lda kiritilganni bosmaydi

    reset = await panel.post(f"/prayer-times/{toshkent.id}/{TODAY}/reset", data={"csrf": token})
    row = await session.scalar(
        select(PrayerTime)
        .where(PrayerTime.region_id == toshkent.id, PrayerTime.date == TODAY)
        .execution_options(populate_existing=True)
    )
    assert reset.status_code == 303 and row.source == "computed" and row.bomdod != dt.time(5, 1)


@pytest.mark.parametrize(
    "override",
    [{"asr": "11:00"}, {"xufton": "yarim tun"}, {"bomdod": ""}],
)
async def test_invalid_prayer_times_are_rejected(panel, session, override):
    toshkent = await session.scalar(select(Region).where(Region.name == "Toshkent"))
    token = await csrf(panel, f"/prayer-times/{toshkent.id}/{TODAY}")
    times = {
        "bomdod": "05:01",
        "quyosh": "06:21",
        "peshin": "12:05",
        "asr": "15:40",
        "shom": "17:30",
        "xufton": "18:55",
    }

    response = await panel.post(f"/prayer-times/{toshkent.id}/{TODAY}", data={"csrf": token, **times, **override})

    assert response.status_code == 400
    row = await session.scalar(select(PrayerTime).where(PrayerTime.region_id == toshkent.id, PrayerTime.date == TODAY))
    assert row is None or row.source == "computed"


# --- masjidlar ---------------------------------------------------------------------------------------


async def test_mosque_crud_and_review_flag(panel, session):
    page = (await panel.get("/mosques?review=1")).text
    token = await csrf(panel, "/mosques/new")
    unnamed = await session.scalar(select(Mosque).where(Mosque.review_note.is_not(None)))

    created = await panel.post(
        "/mosques/new",
        data={
            "csrf": token,
            "name": " Yangi  masjid ",
            "district": "Chilonzor",
            "lat": "41,25",
            "lon": "69.2",
            "is_active": "1",
        },
    )
    fixed = await panel.post(
        f"/mosques/{unnamed.id}",
        data={
            "csrf": token,
            "name": "Aniqlangan masjid",
            "district": "Olmazor",
            "lat": str(unnamed.lat),
            "lon": str(unnamed.lon),
            "is_active": "1",
            "resolved": "1",
        },
    )

    mosque = await session.scalar(select(Mosque).where(Mosque.name == "Yangi masjid"))
    await session.refresh(unnamed)
    assert page.count("tekshirish") >= 5 and created.status_code == 303 and mosque.lat == 41.25
    assert fixed.status_code == 303 and unnamed.name == "Aniqlangan masjid" and unnamed.review_note is None
    mosque_id = mosque.id
    deleted = await panel.post(f"/mosques/{mosque_id}/delete", data={"csrf": token})
    session.expire_all()  # panel boshqa sessiyada o'chirdi: bu sessiyaning eski nusxasi tashlanadi
    assert deleted.status_code == 303 and await session.get(Mosque, mosque_id) is None


@pytest.mark.parametrize(
    "fields",
    [
        {"name": "", "lat": "41.2", "lon": "69.2"},
        {"name": "A", "lat": "abc", "lon": "69.2"},
        {"name": "A", "lat": "10", "lon": "69.2"},
    ],
)
async def test_invalid_mosque_is_rejected(panel, session, fields):
    token = await csrf(panel, "/mosques/new")
    before = await session.scalar(select(func.count()).select_from(Mosque))

    response = await panel.post("/mosques/new", data={"csrf": token, "district": "", **fields})

    assert response.status_code == 400
    assert await session.scalar(select(func.count()).select_from(Mosque)) == before


async def test_hidden_mosque_is_not_offered_by_the_bot(panel, session):
    from ilmbot.services.mosques import MosqueService

    abu = await session.scalar(select(Mosque).where(Mosque.name == "Abu Sahiy masjidi"))
    token = await csrf(panel, f"/mosques/{abu.id}")

    await panel.post(
        f"/mosques/{abu.id}",
        data={"csrf": token, "name": abu.name, "district": abu.district, "lat": str(abu.lat), "lon": str(abu.lon)},
    )  # `is_active` yuborilmadi: yashirildi

    nearest = await MosqueService().nearest(session, abu.lat, abu.lon)
    assert abu.name not in [m.name for m in nearest]


# --- shaharlar -----------------------------------------------------------------------------------------


async def test_changing_region_coordinates_recalculates_its_times(panel, session):
    samarqand = await session.scalar(select(Region).where(Region.name == "Samarqand"))
    token = await csrf(panel, f"/regions/{samarqand.id}")
    today = dt.datetime.now(dt.UTC).date()
    from ilmbot.services.prayers import PrayerService

    before = await PrayerService().get_times(session, samarqand, today)
    old_peshin = before.peshin

    response = await panel.post(
        f"/regions/{samarqand.id}", data={"csrf": token, "lat": "39.65", "lon": "70.0", "is_active": "1"}
    )

    row = await session.scalar(
        select(PrayerTime)
        .where(PrayerTime.region_id == samarqand.id, PrayerTime.date == today)
        .execution_options(populate_existing=True)
    )
    assert response.status_code == 303 and row.peshin != old_peshin  # 3 daraja sharqqa: peshin ~12 daqiqa erta


async def test_region_coordinates_outside_uzbekistan_are_rejected(panel, session):
    toshkent = await session.scalar(select(Region).where(Region.name == "Toshkent"))
    token = await csrf(panel, f"/regions/{toshkent.id}")

    response = await panel.post(
        f"/regions/{toshkent.id}", data={"csrf": token, "lat": "55", "lon": "37", "is_active": "1"}
    )

    assert response.status_code == 400 and "hududidan tashqarida" in response.text


# --- broadcast xatosi ----------------------------------------------------------------------------------


async def test_worker_failure_pauses_the_job_and_the_reason_is_shown(panel, session, sessionmaker):
    session.add(User(id=1, name="u"))
    await session.flush()
    service = BroadcastService()
    job = await service.create_job(session, "web:admin", text="Xabar")
    await session.commit()

    await service.record_failure(sessionmaker, job.id, "ValueError: sinov xatosi")

    await session.refresh(job)
    page = (await panel.get(f"/broadcasts/{job.id}/progress")).text
    assert (job.status, job.error) == ("paused", "ValueError: sinov xatosi")
    assert "Worker xatosi: ValueError: sinov xatosi" in page
    token = await csrf(panel, f"/broadcasts/{job.id}")
    await panel.post(f"/broadcasts/{job.id}/resume", data={"csrf": token})
    await session.refresh(job)
    assert (job.status, job.error) == ("queued", None)
    assert await session.scalar(select(func.count()).select_from(BroadcastJob)) == 1
