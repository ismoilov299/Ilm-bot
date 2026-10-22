"""Bot menyusi: handlerlar `dp.feed_update` orqali, soxta Telegram sessiyasi va haqiqiy PostgreSQL bilan."""

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import AnswerCallbackQuery, CopyMessage, EditMessageText, SendMessage
from sqlalchemy import select

from ilmbot.bot import texts
from ilmbot.bot.callbacks import NodeCb
from ilmbot.bot.main import create_dispatcher
from ilmbot.db.models import Button, ButtonPost, User
from ilmbot.seed import load_seed
from tests.bot_harness import Harness, callback_datas, keyboard_texts, make_bot

ROOT_NAMES = [
    n["name"] for n in sorted(load_seed("menu_seed.json")["nodes"], key=lambda n: n["position"]) if n["parent"] is None
]


@pytest.fixture
def make_harness(sessionmaker, redis, settings):
    def factory(throttle_interval: float = 0.0) -> Harness:
        dp = create_dispatcher(
            sessionmaker=sessionmaker, redis=redis, settings=settings, throttle_interval=throttle_interval
        )
        return Harness(dp, make_bot())

    return factory


@pytest.fixture
async def bot(seeded, make_harness) -> Harness:
    return make_harness()


async def node_id(session, legacy_key: str) -> int:
    return await session.scalar(select(Button.id).where(Button.legacy_key == legacy_key))


def only(requests, method_type):
    found = [r for r in requests if isinstance(r, method_type)]
    assert len(found) == 1, f"{method_type.__name__}: {len(found)} ta (kutilgan: 1)"
    return found[0]


async def test_start_registers_new_user_and_shows_root_menu(bot, session):
    [reply] = await bot.say("/start")

    assert isinstance(reply, SendMessage)
    assert reply.text.startswith("Assalomu alaykum, Sinov Foydalanuvchi!")
    assert keyboard_texts(reply) == ROOT_NAMES
    assert await session.scalar(select(User.name).where(User.id == 111)) == "Sinov Foydalanuvchi"


async def test_returning_user_gets_short_greeting(bot):
    await bot.say("/start")

    [reply] = await bot.say("/start")

    assert reply.text.startswith("Qaytganingizdan xursandmiz")


async def test_blocked_user_is_unblocked_when_they_return(bot, session):
    await bot.say("/start")
    user = await session.get(User, 111)
    user.is_blocked = True
    await session.flush()

    await bot.say("/start")
    await session.refresh(user)

    assert user.is_blocked is False


async def test_help_mentions_admins(bot):
    [reply] = await bot.say("/help")

    assert "@ismoilov299" in reply.text


async def test_opening_a_section_shows_its_children_and_back(bot):
    await bot.say("/start")

    [reply] = await bot.say("Namoz🕋")

    assert keyboard_texts(reply) == [
        "Namoz vaqtlari",
        "G'usul va Tahorat",
        "Namoz turlari",
        "Zam suralar",
        "Namozni o'rganish",
        texts.BACK,
    ]


async def test_back_goes_one_level_up_then_to_root(bot):
    await bot.say("/start")
    await bot.say("Namoz🕋")
    [reply] = await bot.say("G'usul va Tahorat")
    assert keyboard_texts(reply) == ["G'usul", "Tahorat", texts.BACK]

    [one_up] = await bot.say(texts.BACK)
    [root] = await bot.say(texts.BACK)

    assert "Namoz vaqtlari" in keyboard_texts(one_up) and texts.BACK in keyboard_texts(one_up)
    assert keyboard_texts(root) == ROOT_NAMES


async def test_leaf_post_is_copied_from_the_content_channel(bot, settings):
    await bot.say("/start")
    await bot.say("Namoz🕋")
    await bot.say("G'usul va Tahorat")

    requests = await bot.say("G'usul")

    copy = only(requests, CopyMessage)
    assert (copy.chat_id, copy.from_chat_id, copy.message_id) == (111, settings.content_channel, 655)
    assert copy.protect_content is True


async def test_same_button_text_in_two_menus_resolves_by_current_menu(seeded, make_harness):
    """Reply klaviaturada matn takrorlanishi mumkin: bosilgan tugma joriy menyu bolalari ichidan topilishi kerak."""
    for position, (name, message_id) in enumerate([("Birinchi menyu", 1), ("Ikkinchi menyu", 2)], start=100):
        menu = Button(name=name, kind="menu", position=position, text=name)
        menu.children = [
            Button(name="Ichki post", kind="post", position=1, posts=[ButtonPost(position=1, message_id=message_id)])
        ]
        seeded.add(menu)
    await seeded.flush()
    harness = make_harness()
    await harness.say("/start")

    await harness.say("Birinchi menyu")
    first = only(await harness.say("Ichki post"), CopyMessage)
    await harness.say(texts.BACK)
    await harness.say("Ikkinchi menyu")
    second = only(await harness.say("Ichki post"), CopyMessage)

    assert (first.message_id, second.message_id) == (1, 2)


async def test_root_section_is_reachable_from_a_deeper_menu(bot):
    await bot.say("/start")
    await bot.say("Namoz🕋")

    [reply] = await bot.say("Qur'on📖")

    assert texts.BACK in keyboard_texts(reply)
    assert "Qur'onga o'tish" in keyboard_texts(reply)


async def test_list_shows_first_page_with_navigation(bot):
    await bot.say("/start")

    [reply] = await bot.say("Kitoblar📚")

    buttons = keyboard_texts(reply)
    assert buttons[:8] == [
        "Musulmonning odobi",
        "Vijdon azobi",
        "Payg'ambarlar tarixi",
        "Oisha r.a",
        "Qiyomat va Oxirat",
        "Ibodati islomiya",
        "Tarixi Muhammadiy",
        "Saodat asri qissalari",
    ]
    assert buttons[8:] == ["1/2", "›"]


async def test_list_page_is_edited_in_place(bot, session):
    await bot.say("/start")
    await bot.say("Kitoblar📚")

    requests = await bot.press(NodeCb(act="p", id=await node_id(session, "kitoblar"), page=2))

    edit = only(requests, EditMessageText)
    assert keyboard_texts(edit) == ["Hadis va Hayot (9 juz)", "Qirq hadisi qudusiy", "Boshqa kitoblar", "‹", "2/2"]


async def test_list_item_with_several_posts_sends_all_in_order(bot, session):
    await bot.say("/start")
    await bot.say("Kitoblar📚")

    requests = await bot.press(NodeCb(act="o", id=await node_id(session, "kitob_8")))

    copies = [r for r in requests if isinstance(r, CopyMessage)]
    assert [c.message_id for c in copies] == [273, 274, 275, 276]


async def test_nested_list_offers_inline_back_button(bot, session):
    await bot.say("/start")
    await bot.say("Kitoblar📚")

    requests = await bot.press(NodeCb(act="o", id=await node_id(session, "kitoblar_qoshimcha")))

    edit = only(requests, EditMessageText)
    assert keyboard_texts(edit)[-1] == f"‹ {texts.BACK}"
    assert callback_datas(edit)[-1] == NodeCb(act="p", id=await node_id(session, "kitoblar")).pack()


async def test_noop_button_just_acknowledges(bot, session):
    requests = await bot.press(NodeCb(act="x", id=await node_id(session, "kitoblar")))

    assert [type(r) for r in requests] == [AnswerCallbackQuery]
    assert requests[0].show_alert is None


async def test_all_callback_data_fit_telegram_limit(seeded, make_harness):
    from ilmbot.bot.keyboards import inline_list, page_count
    from ilmbot.services.menu import MenuService

    snapshot = await MenuService().snapshot(seeded)
    checked = 0
    for node in snapshot.nodes.values():
        children = snapshot.children(node.id)
        for page in range(1, page_count(len(children), node.page_size) + 1):
            if not children:
                continue
            markup = inline_list(node, children, page=page, back_to=node.parent_id)
            for row in markup.inline_keyboard:
                for button in row:
                    assert len(button.callback_data.encode()) <= 64, button.callback_data
                    checked += 1
    assert checked > 800


async def test_unknown_text_shows_hint_and_menu(bot):
    await bot.say("/start")

    [reply] = await bot.say("bunaqa bo'lim yo'q")

    assert reply.text == texts.NOT_UNDERSTOOD
    assert keyboard_texts(reply) == ROOT_NAMES


async def test_mosque_section_asks_for_a_location(bot):
    await bot.say("/start")

    [reply] = await bot.say("Yaqin Masjid🕌")

    assert reply.text == texts.MOSQUES_PROMPT


async def test_stale_inline_button_is_answered_with_an_alert(bot):
    requests = await bot.press(NodeCb(act="o", id=999_999))

    answer = only(requests, AnswerCallbackQuery)
    assert (answer.text, answer.show_alert) == (texts.STALE_BUTTON, True)


async def test_unknown_callback_format_never_spins(bot):
    requests = await bot.press("eski_format:123")

    assert only(requests, AnswerCallbackQuery).show_alert is True


async def test_throttling_drops_a_second_message_sent_too_quickly(seeded, make_harness):
    harness = make_harness(throttle_interval=5.0)

    first = await harness.say("/start")
    second = await harness.say("/start")

    assert len(first) == 1
    assert second == []


async def test_invalid_admin_html_falls_back_to_plain_text(seeded, make_harness, session):
    await session.execute(Button.__table__.update().where(Button.legacy_key == "namoz").values(text="<b>yopilmagan"))
    await session.flush()
    harness = make_harness()
    harness.session.fail_when(
        lambda m: isinstance(m, SendMessage) and m.text == "<b>yopilmagan" and m.parse_mode is not None,
        TelegramBadRequest(method=SendMessage(chat_id=1, text="x"), message="Bad Request: can't parse entities"),
    )
    await harness.say("/start")

    [reply] = await harness.say("Namoz🕋")

    assert reply.text == "<b>yopilmagan"
    assert reply.parse_mode is None


async def test_unexpected_error_tells_the_user_and_does_not_crash(bot, session):
    await bot.say("/start")
    await bot.say("Namoz🕋")
    await bot.say("G'usul va Tahorat")
    bot.session.fail_when(lambda m: isinstance(m, CopyMessage), RuntimeError("kutilmagan"))

    requests = await bot.say("G'usul")

    assert only(requests, SendMessage).text == texts.ERROR
