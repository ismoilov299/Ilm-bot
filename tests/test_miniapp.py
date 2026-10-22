"""Telegram HMAC, API izolyatsiyasi va Mini App/bot umumiy sozlamalari."""

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import httpx
import pytest

from ilmbot.bot.main import create_dispatcher
from ilmbot.db.models import Button, ButtonPost, Region, User
from ilmbot.security import hash_password
from ilmbot.services.broadcast import BroadcastService
from ilmbot.web.app import create_app
from ilmbot.web.miniapp_auth import InitDataError, validate_init_data
from tests.bot_harness import Harness, make_bot

TOKEN = "42:TEST"


def signed_data(*, user=None, auth_date=None, **extra):
    data = {
        "auth_date": str(int(time.time()) if auth_date is None else auth_date),
        "user": json.dumps(user if user is not None else {"id": 111, "first_name": "Asadbek"}, ensure_ascii=False),
        "query_id": "test-query",
        **extra,
    }
    secret = hmac.digest(b"WebAppData", TOKEN.encode(), hashlib.sha256)
    check = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    return urlencode({**data, "hash": hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()})


def test_init_data_signature_and_unicode_name():
    raw = signed_data(user={"id": 5_670_833_851, "first_name": "O‘tkir", "last_name": "Ismoilov"}, auth_date=1000)
    identity = validate_init_data(raw, TOKEN, now=1030)
    assert (identity.id, identity.name) == (5_670_833_851, "O‘tkir Ismoilov")


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "user=111",
        "hash=bad&auth_date=1000&user=%7B%7D",
        signed_data(auth_date=1000) + "&auth_date=1000",
        signed_data(auth_date=1000).replace("auth_date=1000", "auth_date=1001"),
        signed_data(auth_date=1),
        signed_data(auth_date=2000),
        signed_data(user={"id": True, "first_name": "A"}, auth_date=1000),
        signed_data(user={"id": "111", "first_name": "A"}, auth_date=1000),
        signed_data(user={"id": -1, "first_name": "A"}, auth_date=1000),
        signed_data(user={"id": 2**63, "first_name": "A"}, auth_date=1000),
        signed_data(user={"id": 111, "first_name": []}, auth_date=1000),
        signed_data(user=[111], auth_date=1000),
    ],
)
def test_forged_expired_future_or_malformed_identity_is_refused(raw):
    with pytest.raises(InitDataError):
        validate_init_data(raw, TOKEN, now=1030, max_age=60)


def app_for(settings, redis, sessionmaker=None):
    configured = settings.model_copy(
        update={
            "admin_password_hash": hash_password("test-password"),
            "session_secret": "s" * 48,
            "mini_app_url": "https://ilm.example/app",
        }
    )
    app = create_app(settings=configured, sessionmaker=sessionmaker, redis=redis, broadcasts=BroadcastService())
    app.state.bot_username = "ilm_test_bot"  # Testda haqiqiy Telegram chaqirilmaydi
    return app


async def test_no_telegram_identity_or_admin_cookie_can_access_user_api(redis, settings):
    app = app_for(settings, redis)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="https://ilm.example") as client:
        # User API admin login'ga yo'naltirmaydi va hech qachon oddiy Telegram ID ga ishonmaydi.
        for auth in ("", "Bearer 111", "tma hash=invalid", "tma " + signed_data(auth_date=1)):
            response = await client.get("/app/api/me", headers={"Authorization": auth})
            assert response.status_code == 401
            assert "detail" in response.json()
        response = await client.get("/users", headers={"Authorization": "tma " + signed_data()})
        assert (response.status_code, response.headers["location"]) == (303, "/login")


async def test_miniapp_shell_allows_telegram_frames_but_admin_keeps_its_protection(redis, settings):
    app = app_for(settings, redis)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://ilm.example") as client:
        response = await client.get("/app")
        assert response.status_code == 200 and "miniapp.js" in response.text
        assert "https://telegram.org/js/telegram-web-app.js" in response.text
        assert "X-Frame-Options" not in response.headers
        assert "https://web.telegram.org" in response.headers["Content-Security-Policy"]
        assert response.headers["Cache-Control"] == "no-store"
        admin = await client.get("/login")
        assert admin.headers["X-Frame-Options"] == "DENY"
        assert "frame-ancestors 'none'" in admin.headers["Content-Security-Policy"]
        assert (await client.get("/static/miniapp.css")).status_code == 200
        assert (await client.get("/static/miniapp.js")).status_code == 200


@pytest.mark.parametrize("url", ["http://example.com/app", "javascript:alert(1)", "https://a:b@example.com/app"])
def test_miniapp_requires_https_url(settings, url):
    with pytest.raises(ValueError):
        type(settings)(_env_file=None, mini_app_url=url)


@pytest.fixture
async def mini_world(session, sessionmaker, redis, settings):
    region = Region(name="Mini shahar", api_name="Mini", lat=41.3, lon=69.24)
    root = Button(name="Kitoblar", kind="list", position=1)
    session.add_all([region, root, User(id=222, name="Boshqa foydalanuvchi")])
    await session.flush()
    child = Button(name="Kitob", kind="post", text="<b>Foydali</b>", parent_id=root.id)
    hidden = Button(name="Yashirin", kind="list", is_active=False)
    session.add_all([child, hidden])
    await session.flush()
    session.add_all(
        [
            ButtonPost(button_id=child.id, position=1, message_id=123),
            Button(name="Yashirin bola", kind="post", parent_id=hidden.id),
        ]
    )
    await session.commit()
    app = app_for(settings, redis, sessionmaker)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="https://ilm.example",
        headers={"Authorization": "tma " + signed_data()},
    ) as client:
        yield client, region, child, hidden, app


async def test_profile_preferences_and_prayers_share_bot_database(mini_world, session):
    client, region, *_ = mini_world
    me = (await client.get("/app/api/me")).json()
    assert me["user"]["id"] == 111 and me["bot_url"] == "https://t.me/ilm_test_bot"
    result = await client.put("/app/api/preferences", json={"region_id": region.id, "subscribed": True})
    assert result.status_code == 200 and result.json()["user"]["subscribed"] is True
    user = await session.get(User, 111, populate_existing=True)
    assert user.region_id == region.id and user.subscribed
    assert (await session.get(User, 222)).region_id is None
    times = await client.get("/app/api/prayers")
    assert times.status_code == 200 and len(times.json()["times"]) == 6
    assert times.json()["region"]["id"] == region.id
    assert (await client.get("/app/api/prayers?day=2000-01-01")).status_code == 400
    assert (await client.put("/app/api/preferences", json={"region_id": region.id, "user_id": 222})).status_code == 422
    assert (await client.put("/app/api/preferences", json={"region_id": 999999})).status_code == 404


async def test_menu_hides_inactive_ancestors_and_strips_html(mini_world):
    client, _, child, *_ = mini_world
    nodes = (await client.get("/app/api/menu")).json()["nodes"]
    assert {n["name"] for n in nodes} == {"Kitoblar", "Kitob"}
    item = next(n for n in nodes if n["id"] == child.id)
    assert item["text"] == "Foydali" and item["post_count"] == 1
    assert "message_ids" not in item


async def test_api_rate_limit_and_coordinate_validation(mini_world, redis):
    client, *_ = mini_world
    assert (await client.get("/app/api/mosques?lat=91&lon=69")).status_code == 422
    assert (await client.get("/app/api/mosques?lat=nan&lon=69")).status_code == 422
    assert (await client.get("/app/api/mosques?lat=41&lon=69")).json()["mosques"] == []
    slot = int(time.time()) // 60
    await redis.set(f"miniapp:api:111:{slot}", 120, ex=120)
    assert (await client.get("/app/api/regions")).status_code == 429


async def test_opening_miniapp_does_not_unblock_user(mini_world, session):
    client, *_ = mini_world
    session.add(User(id=111, name="Old", is_blocked=True))
    await session.commit()
    assert (await client.get("/app/api/me")).status_code == 200
    user = await session.get(User, 111, populate_existing=True)
    assert user.is_blocked and user.name == "Asadbek"


async def test_bot_deep_link_sends_active_content_and_keeps_old_menu(mini_world, sessionmaker, redis, settings):
    _, _, child, hidden, _ = mini_world
    bot = Harness(
        create_dispatcher(
            sessionmaker=sessionmaker,
            redis=redis,
            settings=settings,
            throttle_interval=0,
        ),
        make_bot(),
    )
    requests = await bot.say(f"/start content_{child.id}")
    assert requests[0].message_id == 123 and requests[0].chat_id == 111
    requests = await bot.say(f"/start content_{hidden.id}")
    assert "topilmadi" in requests[0].text
    requests = await bot.say("/start")
    assert requests[0].reply_markup.keyboard[0][0].text == "Kitoblar"


async def test_app_command_uses_https_web_app_button(mini_world, sessionmaker, redis):
    _, _, _, _, app = mini_world
    bot = Harness(
        create_dispatcher(
            sessionmaker=sessionmaker,
            redis=redis,
            settings=app.state.settings,
            throttle_interval=0,
        ),
        make_bot(),
    )
    [message] = await bot.say("/app")
    assert message.reply_markup.inline_keyboard[0][0].web_app.url == "https://ilm.example/app"
