"""Admin veb-panelni sinash vositalari: tayyor mijoz, kirish va CSRF tokenini olish."""

import re
from contextlib import asynccontextmanager

import httpx

from ilmbot.security import hash_password
from ilmbot.services.broadcast import BroadcastService
from ilmbot.web.app import create_app

PASSWORD = "to'g'ri-parol-12345"
ADMIN_TELEGRAM_ID = 111


@asynccontextmanager
async def signed_in_client(sessionmaker, redis, settings):
    settings = settings.model_copy(
        update={
            "admin_password_hash": hash_password(PASSWORD),
            "session_secret": "s" * 48,
            "admins": [ADMIN_TELEGRAM_ID],
            "content_channel": "@test_channel",
        }
    )
    app = create_app(settings=settings, sessionmaker=sessionmaker, redis=redis, broadcasts=BroadcastService())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://panel") as client:
        response = await client.post("/login", data={"username": "admin", "password": PASSWORD})
        assert response.status_code == 303
        yield client


async def csrf(client: httpx.AsyncClient, path: str = "/menu") -> str:
    page = await client.get(path)
    return re.search(r'name="csrf" value="([^"]+)"', page.text).group(1)
