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
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

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
async def session(database_url: str):
    """Har bir test o'z tranzaksiyasida ishlaydi va oxirida orqaga qaytariladi (testlar bir-biriga ta'sir qilmaydi)."""
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            db_session = AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
            try:
                yield db_session
            finally:
                await db_session.close()
                await transaction.rollback()
    finally:
        await engine.dispose()
