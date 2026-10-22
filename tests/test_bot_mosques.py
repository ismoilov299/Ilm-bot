"""Yaqin masjidlar: masofa va botdagi oqim."""

import pytest
from aiogram.methods import SendLocation, SendMessage

from ilmbot.bot import texts
from ilmbot.bot.main import create_dispatcher
from ilmbot.services.mosques import MosqueService, distance_km
from tests.bot_harness import Harness, keyboard_texts, make_bot


def test_distance_matches_known_values():
    assert distance_km(0, 0, 0, 1) == pytest.approx(111.19, abs=0.05)
    assert distance_km(41.2995, 69.2401, 39.6542, 66.9597) == pytest.approx(266, abs=1)
    assert distance_km(41.3, 69.2, 41.3, 69.2) == 0


@pytest.fixture
async def bot(seeded, sessionmaker, redis, settings) -> Harness:
    dp = create_dispatcher(sessionmaker=sessionmaker, redis=redis, settings=settings, throttle_interval=0.0)
    return Harness(dp, make_bot())


async def test_nearest_returns_the_closest_mosques_in_order(seeded):
    found = await MosqueService().nearest(seeded, 41.248203831616344, 69.16538754002481)  # Abu Sahiy masjidi

    assert [m.name for m in found][0] == "Abu Sahiy masjidi"
    assert found[0].km < 0.01 <= found[1].km


async def test_mosque_section_asks_for_a_location(bot):
    await bot.say("/start")

    [reply] = await bot.say("Yaqin Masjid🕌")

    assert reply.text == texts.MOSQUES_PROMPT
    assert keyboard_texts(reply) == [texts.SEND_LOCATION, texts.BACK]
    assert reply.reply_markup.keyboard[0][0].request_location is True


async def test_location_gets_two_mosques_with_links_and_map_pins(bot):
    await bot.say("/start")

    requests = await bot.send_location(41.2482, 69.1654)

    [message] = [r for r in requests if isinstance(r, SendMessage)]
    assert message.text.count("Uzoqlik:") == 2 and "Abu Sahiy masjidi" in message.text
    assert message.text.count("google.com/maps") == 2
    assert len([r for r in requests if isinstance(r, SendLocation)]) == 2


async def test_location_far_from_tashkent_is_answered_honestly(bot):
    await bot.say("/start")

    [message, *_] = await bot.send_location(39.6542, 66.9597)  # Samarqand

    assert message.text.startswith(texts.MOSQUES_FAR)
