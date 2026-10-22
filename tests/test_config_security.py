import pytest

from ilmbot.config import Settings
from ilmbot.security import hash_password, verify_password


def test_settings_read_environment(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123:abc")
    monkeypatch.setenv("SEND_RATE_PER_SEC", "20")

    settings = Settings(_env_file=None)

    assert settings.require_bot_token() == "123:abc"
    assert settings.send_rate_per_sec == 20
    assert settings.timezone == "Asia/Tashkent"
    assert settings.content_channel == "@testislomyolida"


def test_missing_bot_token_gives_clear_error(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="BOT_TOKEN"):
        Settings(_env_file=None).require_bot_token()


def test_password_roundtrip():
    stored = hash_password("to'g'ri-parol-123")

    assert stored.startswith("scrypt$")
    assert verify_password("to'g'ri-parol-123", stored)
    assert not verify_password("noto'g'ri-parol", stored)


def test_same_password_gets_different_hashes():
    assert hash_password("bir-xil-parol-12") != hash_password("bir-xil-parol-12")


@pytest.mark.parametrize("stored", ["", "oddiy-matn", "scrypt$1$2", "bcrypt$1$2$3$4$5", "scrypt$x$y$z$@@$@@"])
def test_malformed_hash_never_verifies(stored):
    assert not verify_password("istalgan", stored)
