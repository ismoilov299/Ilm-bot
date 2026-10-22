"""Admin panel: menyu daraxti boshqaruvi va kanal postlarini biriktirish."""

import re

import pytest
from sqlalchemy import func, select

from ilmbot.db.models import Button, ButtonPost
from ilmbot.services.menu import MENU_VERSION_KEY, MenuService
from tests.web_harness import csrf, signed_in_client


@pytest.fixture
async def panel(seeded, sessionmaker, redis, settings):
    async with signed_in_client(sessionmaker, redis, settings) as client:
        yield client


async def node(session, key: str) -> Button:
    return await session.scalar(select(Button).where(Button.legacy_key == key))


async def children_names(session, parent: Button) -> list[str]:
    rows = await session.scalars(select(Button.name).where(Button.parent_id == parent.id).order_by(Button.position))
    return list(rows.all())


async def test_root_lists_the_ten_main_sections(panel):
    page = (await panel.get("/menu")).text

    for name in ("Namoz🕋", "Qur'on📖", "Kitoblar📚", "Yaqin Masjid🕌"):
        assert name.replace("'", "&#39;") in page


async def test_new_node_is_created_at_the_end_and_the_bot_cache_is_invalidated(panel, session, redis):
    sahobalar = await node(session, "sahobalar")
    token = await csrf(panel)
    before = int(await redis.get(MENU_VERSION_KEY) or 0)

    response = await panel.post(
        "/menu/new",
        data={
            "csrf": token,
            "parent": sahobalar.id,
            "name": "  Yangi   sahoba ",
            "kind": "post",
            "post_ids": "1539, 655\n655",
        },
    )

    created = await session.scalar(select(Button).where(Button.name == "Yangi sahoba"))
    assert response.status_code == 303 and response.headers["location"].startswith(f"/menu?parent={sahobalar.id}")
    assert created.position == len(await children_names(session, sahobalar))
    posts = (
        await session.scalars(
            select(ButtonPost.message_id).where(ButtonPost.button_id == created.id).order_by(ButtonPost.position)
        )
    ).all()
    assert list(posts) == [1539, 655]  # takrorlar olib tashlangan, tartib saqlangan
    assert int(await redis.get(MENU_VERSION_KEY)) == before + 1


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"name": "   ", "kind": "post"}, "bo&#39;sh"),
        ({"name": "A", "kind": "yo'q-tur"}, "turi noto&#39;g&#39;ri"),
        ({"name": "A", "kind": "action", "action": ""}, "amalni tanlang"),
        ({"name": "A", "kind": "post", "text": "<script>x</script>"}, "qo&#39;llab-quvvatlanmaydi"),
        ({"name": "A", "kind": "post", "post_ids": "abc"}, "raqamlardan"),
        ({"name": "A", "kind": "list", "page_size": "99"}, "gacha"),
    ],
)
async def test_invalid_node_is_rejected_with_a_clear_message(panel, session, fields, message):
    token = await csrf(panel)
    before = await session.scalar(select(func.count()).select_from(Button))

    response = await panel.post("/menu/new", data={"csrf": token, "parent": "", **fields})

    assert response.status_code == 400 and message in response.text
    assert await session.scalar(select(func.count()).select_from(Button)) == before


async def test_a_post_node_cannot_contain_children(panel, session):
    gusl = await node(session, "gusl")
    token = await csrf(panel)

    response = await panel.post("/menu/new", data={"csrf": token, "parent": gusl.id, "name": "Ichki", "kind": "post"})

    assert response.status_code == 400 and "faqat" in response.text


async def test_edit_updates_the_node_and_replaces_its_posts(panel, session):
    gusl = await node(session, "gusl")
    token = await csrf(panel, f"/menu/{gusl.id}/edit")

    response = await panel.post(
        f"/menu/{gusl.id}/edit",
        data={
            "csrf": token,
            "name": "G'usl",
            "kind": "post",
            "text": "<b>Izoh</b>",
            "page_size": "8",
            "post_ids": "700\n701",
            "is_active": "1",
        },
    )

    await session.refresh(gusl)
    assert response.status_code == 303
    assert (gusl.name, gusl.text, gusl.is_active) == ("G'usl", "<b>Izoh</b>", True)
    posts = (
        await session.scalars(
            select(ButtonPost.message_id).where(ButtonPost.button_id == gusl.id).order_by(ButtonPost.position)
        )
    ).all()
    assert list(posts) == [700, 701]


async def test_a_section_with_children_cannot_become_a_post(panel, session):
    namoz = await node(session, "namoz")
    token = await csrf(panel, f"/menu/{namoz.id}/edit")

    response = await panel.post(
        f"/menu/{namoz.id}/edit",
        data={"csrf": token, "name": namoz.name, "kind": "post", "page_size": "8", "is_active": "1"},
    )

    assert response.status_code == 400 and "o&#39;zgartirib bo&#39;lmaydi" in response.text


async def test_reorder_swaps_neighbours_and_keeps_positions_consecutive(panel, session):
    namoz = await node(session, "namoz")
    before = await children_names(session, namoz)
    first = await node(session, "namoz_vaqt")
    token = await csrf(panel)

    await panel.post(f"/menu/{first.id}/down", data={"csrf": token})
    await session.refresh(first)

    after = await children_names(session, namoz)
    assert after[:2] == [before[1], before[0]] and after[2:] == before[2:]
    positions = (
        await session.scalars(select(Button.position).where(Button.parent_id == namoz.id).order_by(Button.position))
    ).all()
    assert list(positions) == list(range(1, len(before) + 1))
    top = await panel.post(f"/menu/{first.id}/up", data={"csrf": token})  # yana yuqoriga: dastlabki holat
    assert top.status_code == 303 and await children_names(session, namoz) == before


async def test_hidden_node_disappears_from_the_bot_menu(panel, session, redis):
    mosque = await node(session, "masjid")
    token = await csrf(panel)

    await panel.post(f"/menu/{mosque.id}/toggle", data={"csrf": token})

    snapshot = await MenuService(version=lambda: redis.get(MENU_VERSION_KEY)).snapshot(session)
    assert mosque.id not in snapshot.nodes and "Yaqin Masjid🕌" not in [n.name for n in snapshot.roots]


async def test_moving_a_node_into_its_own_subtree_is_refused(panel, session):
    namoz, gusl_menu = await node(session, "namoz"), await node(session, "gusl_tahorat")
    token = await csrf(panel)

    refused = await panel.post(f"/menu/{namoz.id}/move", data={"csrf": token, "new_parent": gusl_menu.id})
    ok = await panel.post(
        f"/menu/{gusl_menu.id}/move", data={"csrf": token, "new_parent": (await node(session, "quran")).id}
    )

    assert refused.status_code == 400 and "o&#39;zining ichiga" in refused.text
    await session.refresh(gusl_menu)
    assert ok.status_code == 303 and gusl_menu.parent_id == (await node(session, "quran")).id


async def test_deleting_a_section_removes_everything_inside_it(panel, session):
    sunnat = await node(session, "sunnat")
    confirm = (await panel.get(f"/menu/{sunnat.id}/delete")).text
    token = await csrf(panel)

    response = await panel.post(f"/menu/{sunnat.id}/delete", data={"csrf": token})

    assert "<b>5</b> ta tugun" in confirm
    assert response.status_code == 303
    assert await node(session, "sunnat") is None and await node(session, "sunnat_shom") is None
    orphans = await session.scalar(
        select(func.count()).select_from(ButtonPost).where(~ButtonPost.button_id.in_(select(Button.id)))
    )
    assert orphans == 0


async def test_review_page_lists_and_confirms_unverified_nodes(panel, session):
    page = (await panel.get("/menu/review")).text
    count = int(re.search(r"\((\d+)\)</h1>", page).group(1))
    target = await node(session, "vojib")
    token = await csrf(panel, "/menu/review")

    await panel.post(f"/menu/{target.id}/review-ok", data={"csrf": token})

    after = int(re.search(r"\((\d+)\)</h1>", (await panel.get("/menu/review")).text).group(1))
    assert count > 0 and after == count - 1


async def test_changes_require_a_csrf_token(panel, session):
    gusl = await node(session, "gusl")

    assert (await panel.post(f"/menu/{gusl.id}/toggle")).status_code == 403
    assert (await panel.post(f"/menu/{gusl.id}/delete", data={"csrf": "x"})).status_code == 403
    assert await node(session, "gusl") is not None


async def test_menu_service_reloads_when_the_version_changes(panel, session, redis):
    service = MenuService(ttl=3600, version=lambda: redis.get(MENU_VERSION_KEY))
    first = await service.snapshot(session)
    gusl = await node(session, "gusl")
    gusl.is_active = False
    await session.flush()

    unchanged = await service.snapshot(session)  # versiya o'zgarmadi: kesh ishlatiladi
    await redis.incr(MENU_VERSION_KEY)
    reloaded = await service.snapshot(session)

    assert unchanged is first and gusl.id in unchanged.nodes
    assert gusl.id not in reloaded.nodes
