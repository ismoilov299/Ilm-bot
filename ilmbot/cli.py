"""Buyruq satri: `python -m ilmbot.cli seed` va `python -m ilmbot.cli hash-password`."""

import argparse
import asyncio
import getpass
import sys

from ilmbot.config import get_settings
from ilmbot.db import make_engine, make_sessionmaker
from ilmbot.security import hash_password
from ilmbot.seed import seed_all


async def _seed() -> dict[str, int]:
    engine = make_engine(get_settings().database_url)
    try:
        async with make_sessionmaker(engine)() as session, session.begin():
            return await seed_all(session)
    finally:
        await engine.dispose()


def _cmd_seed(_: argparse.Namespace) -> int:
    counts = asyncio.run(_seed())
    print("Qo'shildi:", ", ".join(f"{name}={count}" for name, count in counts.items()))
    return 0


def _cmd_hash_password(_: argparse.Namespace) -> int:
    password = getpass.getpass("Admin paroli: ")
    if password != getpass.getpass("Parolni takrorlang: "):
        print("Parollar mos kelmadi", file=sys.stderr)
        return 1
    if len(password) < 12:
        print("Parol kamida 12 belgidan iborat bo'lsin", file=sys.stderr)
        return 1
    print("\n.env fayliga yozing:\nADMIN_PASSWORD_HASH=" + hash_password(password))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ilmbot")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("seed", help="regionlar, masjidlar va menyuni bazaga qo'shadi (idempotent)").set_defaults(
        func=_cmd_seed
    )
    sub.add_parser("hash-password", help="admin paroli uchun xesh yaratadi").set_defaults(func=_cmd_hash_password)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
