from types import SimpleNamespace

import httpx
import pytest
from aiogram.exceptions import TelegramNetworkError
from aiogram.methods import GetMe

from ilmbot.integrations import bot_identity


class IdentityBot:
    closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        self.closed = True

    async def get_me(self):
        return SimpleNamespace(username="auto_bot")


async def test_username_is_resolved_from_token_and_session_closes(monkeypatch):
    bot = IdentityBot()
    seen = []

    def make_bot(token):
        seen.append(token)
        return bot

    monkeypatch.setattr(bot_identity, "Bot", make_bot)
    assert await bot_identity.resolve_bot_username("test-token") == "auto_bot"
    assert seen == ["test-token"] and bot.closed


async def test_resolution_failure_is_clear_and_does_not_leak_token(monkeypatch):
    class FailingBot(IdentityBot):
        async def get_me(self):
            raise TelegramNetworkError(method=GetMe(), message="request with secret-token failed")

    bot = FailingBot()
    monkeypatch.setattr(bot_identity, "Bot", lambda _: bot)
    with pytest.raises(RuntimeError, match="getMe") as error:
        await bot_identity.resolve_bot_username("secret-token")
    assert "secret-token" not in str(error.value) and bot.closed


async def test_tunnel_factory_hides_admin_and_resolves_username(monkeypatch, settings):
    from ilmbot.web import main

    configured = settings.model_copy(update={"admin_password_hash": "test", "session_secret": "s" * 48})
    monkeypatch.setattr(main, "get_settings", lambda: configured)
    seen = []

    async def resolve(token):
        seen.append(token)
        return "from_token_bot"

    monkeypatch.setattr(main, "resolve_bot_username", resolve)
    app = main.build_mini_app()
    async with app.router.lifespan_context(app):
        assert app.state.bot_username == "from_token_bot" and seen == [configured.bot_token]
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://local") as client:
            assert (await client.get("/app")).status_code == 200
            assert (await client.get("/static/miniapp.js")).status_code == 200
            for path in ("/", "/login", "/users", "/broadcasts", "/static/app.js"):
                assert (await client.get(path)).status_code == 404
