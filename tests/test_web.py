"""Admin veb-panel: kirish, CSRF, xavfsizlik sarlavhalari va broadcast oqimi (ASGI orqali, haqiqiy PostgreSQL bilan)."""

import re

import httpx
import pytest
from sqlalchemy import func, select

from ilmbot.db.models import AdminAudit, BroadcastJob, BroadcastRecipient, User
from ilmbot.security import hash_password
from ilmbot.services.broadcast import BroadcastService
from ilmbot.web.app import create_app

PASSWORD = "to'g'ri-parol-12345"
ADMIN_TELEGRAM_ID = 111


@pytest.fixture
async def client(sessionmaker, redis, settings):
    settings = settings.model_copy(
        update={
            "admin_password_hash": hash_password(PASSWORD),
            "session_secret": "s" * 48,
            "admins": [ADMIN_TELEGRAM_ID],
            "content_channel": "@test_channel",
        }
    )
    app = create_app(settings=settings, sessionmaker=sessionmaker, redis=redis, broadcasts=BroadcastService())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://panel") as http:
        yield http


async def sign_in(client: httpx.AsyncClient, password: str = PASSWORD) -> httpx.Response:
    return await client.post("/login", data={"username": "admin", "password": password})


async def csrf_token(client: httpx.AsyncClient, path: str = "/broadcasts/new") -> str:
    page = await client.get(path)
    return re.search(r'name="csrf" value="([^"]+)"', page.text).group(1)


async def add_users(session, ids, **fields):
    session.add_all(User(id=i, name=f"u{i}", **fields) for i in ids)
    await session.flush()


async def preview(client, token, **fields):
    return await client.post("/broadcasts/new", data={"csrf": token, **fields})


async def create(client, token, **fields):
    return await client.post("/broadcasts", data={"csrf": token, **fields})


async def test_pages_require_login(client):
    for path in ("/", "/broadcasts", "/broadcasts/new", "/broadcasts/1", "/broadcasts/1/progress"):
        response = await client.get(path)
        assert (response.status_code, response.headers["location"]) == (303, "/login"), path


async def test_api_docs_are_not_exposed(client):
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert (await client.get(path)).status_code == 404


async def test_wrong_password_is_rejected_without_a_session(client):
    response = await sign_in(client, "noto'g'ri")

    assert response.status_code == 401 and "Login yoki parol" in response.text
    assert "ilm_session" not in response.headers.get("set-cookie", "")
    assert (await client.get("/")).status_code == 303


async def test_login_sets_a_hardened_cookie_and_opens_the_dashboard(client):
    response = await sign_in(client)

    cookie = response.headers["set-cookie"].lower()
    assert response.status_code == 303 and "httponly" in cookie and "samesite=strict" in cookie
    assert (await client.get("/")).status_code == 200


async def test_repeated_failures_lock_the_login_even_for_the_right_password(client):
    for _ in range(5):
        assert (await sign_in(client, "x")).status_code == 401

    assert (await sign_in(client)).status_code == 429


async def test_security_headers_are_present(client):
    response = await client.get("/login")

    assert "default-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "no-store"


async def test_post_without_a_valid_csrf_token_is_forbidden(client):
    await sign_in(client)

    missing = await client.post("/broadcasts/new", data={"mode": "text", "text": "Salom"})
    wrong = await client.post("/broadcasts/new", data={"csrf": "boshqa", "mode": "text", "text": "Salom"})
    logout = await client.post("/logout")

    assert (missing.status_code, wrong.status_code, logout.status_code) == (403, 403, 403)


async def test_dashboard_counts(client, session):
    await add_users(session, [1, 2, 3], subscribed=True)
    await add_users(session, [4], is_blocked=True)
    await sign_in(client)

    page = (await client.get("/")).text

    assert re.search(r"<b>4</b><span>Foydalanuvchilar", page)
    assert re.search(r"<b>3</b><span>Faol", page)
    assert re.search(r"<b>1</b><span>Botni bloklagan", page)


async def test_text_broadcast_is_previewed_sanitized_and_queued(client, session):
    await add_users(session, [1, 2, 3])
    await add_users(session, [4], is_blocked=True)
    await sign_in(client)
    token = await csrf_token(client)

    confirm = await preview(client, token, mode="text", text="Salom <b>hammaga</b> & <i>xayr</i>")
    assert confirm.status_code == 200 and "<b>3</b> ta foydalanuvchi" in confirm.text
    assert "Salom <b>hammaga</b> &amp; <i>xayr</i>" in confirm.text
    assert await session.scalar(select(func.count()).select_from(BroadcastJob)) == 0  # hali yaratilmagan

    sent = await create(client, token, mode="text", text="Salom <b>hammaga</b> & <i>xayr</i>", target="all")

    job = await session.scalar(select(BroadcastJob))
    assert sent.status_code == 303 and sent.headers["location"] == f"/broadcasts/{job.id}"
    assert (job.status, job.total, job.is_test, job.created_by) == ("queued", 3, False, "web:admin")
    assert job.text == "Salom <b>hammaga</b> &amp; <i>xayr</i>"
    assert await session.scalar(select(func.count()).select_from(BroadcastRecipient)) == 3
    assert (await session.scalar(select(AdminAudit.action))) == "broadcast.create"


async def test_dangerous_or_invalid_html_never_reaches_the_queue(client, session):
    await sign_in(client)
    token = await csrf_token(client)

    for bad in ["<script>alert(1)</script>", "<b>yopilmagan", '<a href="javascript:alert(1)">x</a>', "   "]:
        shown = await preview(client, token, mode="text", text=bad)
        forced = await create(client, token, mode="text", text=bad, target="all")
        assert shown.status_code == 400 and forced.status_code == 400, bad
        assert "<script>" not in shown.text.replace("&lt;script&gt;", "")
    assert await session.scalar(select(func.count()).select_from(BroadcastJob)) == 0


async def test_test_broadcast_goes_only_to_the_admin_account(client, session):
    await add_users(session, [ADMIN_TELEGRAM_ID, 2, 3])
    await sign_in(client)
    token = await csrf_token(client)

    await create(client, token, mode="text", text="Sinov", target="test")

    job = await session.scalar(select(BroadcastJob))
    assert (job.is_test, job.total) == (True, 1)
    recipients = (await session.scalars(select(BroadcastRecipient.user_id))).all()
    assert recipients == [ADMIN_TELEGRAM_ID]


async def test_test_broadcast_needs_the_admin_to_have_started_the_bot(client, session):
    await add_users(session, [2, 3])
    await sign_in(client)
    token = await csrf_token(client)

    response = await create(client, token, mode="text", text="Sinov", target="test")

    assert response.status_code == 400 and "ADMINS" in response.text
    assert await session.scalar(select(func.count()).select_from(BroadcastJob)) == 0


async def test_channel_post_broadcast_validates_the_post_id(client, session):
    await add_users(session, [1])
    await sign_in(client)
    token = await csrf_token(client)

    for bad in ["", "abc", "-5", "0", "99999999999"]:
        assert (await preview(client, token, mode="post", message_id=bad)).status_code == 400, bad
    ok = await create(client, token, mode="post", message_id="1539", target="all")

    job = await session.scalar(select(BroadcastJob))
    assert ok.status_code == 303
    assert (job.text, job.source_message_id, job.source_chat_id) == (None, 1539, None)


async def test_job_can_be_paused_resumed_and_cancelled_and_progress_reflects_it(client, session):
    await add_users(session, [1, 2])
    await sign_in(client)
    token = await csrf_token(client)
    await create(client, token, mode="text", text="Xabar", target="all")
    job = await session.scalar(select(BroadcastJob))
    token = await csrf_token(client, f"/broadcasts/{job.id}")

    await client.post(f"/broadcasts/{job.id}/pause", data={"csrf": token})
    await session.refresh(job)
    paused = (await client.get(f"/broadcasts/{job.id}/progress")).text
    assert job.status == "paused" and 'data-final="0"' in paused and "Davom ettirish" in paused

    await client.post(f"/broadcasts/{job.id}/resume", data={"csrf": token})
    await client.post(f"/broadcasts/{job.id}/cancel", data={"csrf": token})
    await session.refresh(job)
    cancelled = (await client.get(f"/broadcasts/{job.id}/progress")).text
    assert job.status == "cancelled" and 'data-final="1"' in cancelled and "Bekor qilish" not in cancelled


async def test_unknown_job_or_action_is_404_and_controls_need_csrf(client, session):
    await add_users(session, [1])
    await sign_in(client)
    token = await csrf_token(client)

    assert (await client.get("/broadcasts/9999")).status_code == 404
    assert (await client.post("/broadcasts/9999/pause", data={"csrf": token})).status_code == 404
    assert (await client.post("/broadcasts/1/explode", data={"csrf": token})).status_code == 404
    assert (await client.post("/broadcasts/1/pause")).status_code == 403
