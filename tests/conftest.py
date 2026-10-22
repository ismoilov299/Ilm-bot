"""Umumiy fixture'lar. Testlar **haqiqiy PostgreSQL** ustida ishlaydi (SQLite bilan farq qilmasligi uchun).

Lokal: `docker compose up -d postgres`. CI da PostgreSQL service container ishlatiladi.
Sozlash: `TEST_DATABASE_URL` (default: ilmbot_test bazasi, compose dagi server).
"""

import asyncio
import os
from pathlib import Path

import asyncpg
import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from fakeredis import FakeAsyncRedis
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ilmbot.config import Settings
from ilmbot.seed import seed_all

ROOT = Path(__file__).resolve().parent.parent
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql+asyncpg://ilmbot:ilmbot@localhost:5432/ilmbot_test")


async def _recreate_database(url: str) -> None:
    parsed = make_url(url)
    connection = await asyncpg.connect(
        user=parsed.username, password=parsed.password, host=parsed.host, port=parsed.port, database="postgres"
    )
    try:
        await connection.execute(f'DROP DATABASE IF EXISTS "{parsed.database}" WITH (FORCE)')
        await connection.execute(f'CREATE DATABASE "{parsed.database}"')
    finally:
        await connection.close()


@pytest.fixture(scope="session")
def database_url() -> str:
    """Toza test bazasini yaratadi va Alembic migratsiyalarini bajaradi (migratsiyalarning o'zi ham sinaladi)."""
    try:
        asyncio.run(_recreate_database(TEST_DATABASE_URL))
    except (OSError, asyncpg.PostgresError) as exc:
        pytest.fail(
            f"PostgreSQL ga ulanib bo'lmadi ({exc!r}). Ishga tushiring: docker compose up -d postgres", pytrace=False
        )
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.upgrade(config, "head")
    return TEST_DATABASE_URL


@pytest_asyncio.fixture
async def sessionmaker(database_url: str):
    """Har bir test bitta tashqi tranzaksiyada ishlaydi va oxirida orqaga qaytariladi (testlar bir-biriga
    ta'sir qilmaydi).

    Undan chiqqan sessiyalar `commit()` qilsa ham faqat SAVEPOINT yopiladi, shuning uchun bot middleware'i ham
    xuddi ishlab chiqarishdagidek commit qila oladi.
    """
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                yield async_sessionmaker(
                    bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
                )
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def session(sessionmaker: async_sessionmaker[AsyncSession]):
    async with sessionmaker() as db_session:
        yield db_session


@pytest_asyncio.fixture
async def seeded(session: AsyncSession) -> AsyncSession:
    """Regionlar, masjidlar va menyu daraxti yuklangan sessiya."""
    await seed_all(session)
    await session.flush()
    return session


@pytest_asyncio.fixture
async def redis():
    client = FakeAsyncRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
def settings() -> Settings:
    return Settings(_env_file=None, bot_token="42:TEST", content_channel="@test_channel")
