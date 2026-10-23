"""Kanaldagi barcha materiallarni lokal papkaga yuklab oladi va jarayonni foizda ko'rsatadi.

Telegram foydalanuvchi akkaunti orqali (Telethon) ishlaydi, shuning uchun bot API dagi 20 MB cheklovi yo'q.
Uzilsa qayta ishga tushiring: yuklab bo'lingan fayllar o'tkazib yuboriladi.

  uv run --group tools python tools/tg_download/download_channel.py login      # bir marta: telefon va kod
  uv run --group tools python tools/tg_download/download_channel.py download   # yuklash
  uv run --group tools python tools/tg_download/download_channel.py download --limit 5   # sinov uchun

`.env` da `TG_API_ID` va `TG_API_HASH` bo'lishi kerak (my.telegram.org). Natija `var/channel_dump/`:
`media/<id>.<kengaytma>`, `manifest.json` (postlar tavsifi) va `progress.json`. Sessiya `var/telegram.session`.
Hammasi `var/` ichida, shuning uchun gitga tushmaydi.
Colab: tools/tg_download/colab.ipynb (TG_OUT, TG_SESSION, TG_TMP muhit o'zgaruvchilari).
"""

import argparse
import asyncio
import json
import os
import shutil
import sys
import time
from pathlib import Path

from telethon import TelegramClient
from telethon.tl.types import DocumentAttributeAudio, DocumentAttributeFilename

_PARENTS = Path(__file__).resolve().parents
ROOT = _PARENTS[2] if len(_PARENTS) > 2 else Path.cwd()
# Colab kabi muhitda papkalar TG_OUT, TG_SESSION, TG_TMP orqali o'zgartiriladi (modulni import qilishdan oldin)
DUMP = Path(os.environ.get("TG_OUT") or ROOT / "var" / "channel_dump")
SESSION = Path(os.environ.get("TG_SESSION") or ROOT / "var" / "telegram")
TMP = Path(os.environ["TG_TMP"]) if os.environ.get("TG_TMP") else None  # yarim fayllar uchun tez lokal disk
DEFAULT_CHANNEL = "@testislomyolida"


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    path = ROOT / ".env"
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, _, value = line.partition("=")
                values[key.strip()] = value.strip().strip("\"'")
    return {**values, **{k: v for k, v in os.environ.items() if k.startswith("TG_")}}


def make_client() -> TelegramClient:
    env = load_env()
    if not env.get("TG_API_ID") or not env.get("TG_API_HASH"):
        sys.exit(".env da TG_API_ID va TG_API_HASH yo'q (my.telegram.org dan oling)")
    SESSION.parent.mkdir(parents=True, exist_ok=True)
    return TelegramClient(str(SESSION), int(env["TG_API_ID"]), env["TG_API_HASH"], flood_sleep_threshold=600)


def cryptg_installed() -> bool:
    try:
        import cryptg  # noqa: F401
    except ImportError:
        return False
    return True


def human(size: float) -> str:
    return f"{size / 1024**3:.2f} GB" if size >= 1024**3 else f"{size / 1024**2:.1f} MB"


def clock(seconds: float) -> str:
    seconds = int(max(seconds, 0))
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def describe(message) -> dict:
    """Postning web nusxasi uchun kerakli maydonlar (Telegram Desktop eksportiga yaqin nomlar bilan)."""
    row: dict = {
        "id": message.id,
        "date": message.date.isoformat(),
        "text": message.raw_text or "",
        "kind": "text",
    }
    if message.photo:
        row["kind"] = "photo"
    elif message.document:
        mime = message.document.mime_type or ""
        row["mime_type"] = mime
        row["kind"] = (
            "audio"
            if mime.startswith("audio/")
            else "video"
            if mime.startswith("video/")
            else "pdf"
            if mime == "application/pdf"
            else "document"
        )
        for attribute in message.document.attributes:
            if isinstance(attribute, DocumentAttributeFilename):
                row["file_name"] = attribute.file_name
            if isinstance(attribute, DocumentAttributeAudio):
                row["duration"] = attribute.duration
                row["title"] = attribute.title
    if message.file:
        row["size"] = message.file.size or 0
    return row


class Progress:
    """Umumiy foiz: yuklangan baytlar / jami baytlar. Bir qatorda yangilanadi va `progress.json` ga yoziladi."""

    def __init__(self, posts: int, total_bytes: int, already_posts: int, already_bytes: int) -> None:
        self.posts, self.total_bytes = posts, total_bytes
        self.done_posts, self.done_bytes = already_posts, already_bytes
        self.started = time.monotonic()
        self.start_bytes = already_bytes
        self.last_write = 0.0
        self.last_json = 0.0
        self.current = ""

    def percent(self, extra: int = 0) -> float:
        if self.total_bytes:
            return min(100.0, (self.done_bytes + extra) * 100 / self.total_bytes)
        return 100.0 * self.done_posts / self.posts if self.posts else 100.0

    def show(self, extra: int = 0, force: bool = False) -> None:
        now = time.monotonic()
        if not force and now - self.last_write < 0.5:
            return
        self.last_write = now
        elapsed = max(now - self.started, 1e-6)
        speed = (self.done_bytes + extra - self.start_bytes) / elapsed
        left = (self.total_bytes - self.done_bytes - extra) / speed if speed > 0 else 0
        line = (
            f"[{self.percent(extra):5.1f}%] {self.done_posts}/{self.posts} post | "
            f"{human(self.done_bytes + extra)} / {human(self.total_bytes)} | "
            f"{human(speed)}/s | qoldi {clock(left)} | {self.current}"
        )
        print("\r" + line[:150].ljust(150), end="", flush=True)
        if not force and now - self.last_json < 5:
            return
        self.last_json = now
        DUMP.mkdir(parents=True, exist_ok=True)
        (DUMP / "progress.json").write_text(
            json.dumps(
                {
                    "percent": round(self.percent(extra), 1),
                    "posts_done": self.done_posts,
                    "posts_total": self.posts,
                    "bytes_done": self.done_bytes + extra,
                    "bytes_total": self.total_bytes,
                    "updated": time.time(),
                }
            ),
            encoding="utf-8",
        )


def save_manifest(manifest: dict[str, dict]) -> None:
    DUMP.mkdir(parents=True, exist_ok=True)
    temporary = DUMP / "manifest.json.tmp"
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(temporary, DUMP / "manifest.json")


async def download(channel: str, limit: int | None, workers: int = 8) -> int:
    """`workers` ta faylni bir vaqtda yuklaydi (Telegram bitta fayl tezligini cheklaydi, parallel esa tezlashtiradi)."""
    if not cryptg_installed():
        print("OGOHLANTIRISH: cryptg o'rnatilmagan, shifrlash sof Pythonda va juda sekin (pip install cryptg).")
    media_dir = DUMP / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict] = {}
    if (DUMP / "manifest.json").is_file():
        manifest = json.loads((DUMP / "manifest.json").read_text(encoding="utf-8"))

    async with make_client() as client:
        entity = await client.get_entity(channel)
        print(f"Kanal: {getattr(entity, 'title', channel)}. Postlar ro'yxati olinmoqda...")
        messages = [m async for m in client.iter_messages(entity, reverse=True, limit=limit) if not m.action]
        rows = [(m, describe(m)) for m in messages]
        total_bytes = sum(row.get("size", 0) for _, row in rows)

        def target(message) -> Path | None:
            return media_dir / f"{message.id}{message.file.ext or ''}" if message.file else None

        def finished(message, row) -> bool:
            path = target(message)
            return path is not None and path.is_file() and path.stat().st_size == row.get("size", -1)

        pending = []
        done_bytes = 0
        for message, row in rows:
            path = target(message)
            if path is not None:
                row["file"] = f"media/{path.name}"
            if path is None or finished(message, row):
                manifest[str(message.id)] = row
                done_bytes += row.get("size", 0)
            else:
                pending.append((message, row))
        progress = Progress(len(rows), total_bytes, len(rows) - len(pending), done_bytes)
        print(
            f"Jami {len(rows)} post, {human(total_bytes)}. "
            f"Allaqachon tayyor: {len(rows) - len(pending)}. Parallel: {workers}."
        )
        progress.show(force=True)

        failed: list[int] = []
        inflight: dict[int, int] = {}
        queue = list(reversed(pending))

        async def worker() -> None:
            while queue:
                message, row = queue.pop()
                path = target(message)
                progress.current = f"#{message.id} {row.get('kind')}"
                partial = (TMP or media_dir) / (path.name + ".part")
                partial.parent.mkdir(parents=True, exist_ok=True)
                partial.unlink(missing_ok=True)
                inflight[message.id] = 0

                def on_chunk(received: int, _total: int, key: int = message.id) -> None:
                    inflight[key] = received
                    progress.show(sum(inflight.values()))

                try:
                    await client.download_media(message, file=str(partial), progress_callback=on_chunk)
                    # TMP boshqa diskda (Drive) bo'lishi mumkin; ko'chirish event loopni bloklamasin
                    await asyncio.to_thread(shutil.move, str(partial), str(path))
                    progress.done_bytes += row.get("size", 0)
                    manifest[str(message.id)] = row
                except Exception as error:  # noqa: BLE001  (bitta fayl butun jarayonni to'xtatmasin)
                    partial.unlink(missing_ok=True)
                    failed.append(message.id)
                    print(f"\n#{message.id} yuklanmadi: {error!r}")
                finally:
                    inflight.pop(message.id, None)
                    progress.done_posts += 1
                    progress.show(sum(inflight.values()))
                if len(manifest) % 25 == 0:
                    save_manifest(manifest)

        await asyncio.gather(*(worker() for _ in range(max(1, workers))))
        save_manifest(manifest)
        progress.show(force=True)

    print(f"\nTayyor. Postlar: {len(manifest)}. Xato: {len(failed)}" + (f" {failed}" if failed else ""))
    return 1 if failed else 0


async def login() -> int:
    async with make_client() as client:  # telefon va kod terminalda so'raladi
        me = await client.get_me()
        print(f"Kirildi: {me.first_name}. Sessiya saqlandi: {SESSION}.session")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("login", help="bir marta: Telegram akkauntga kirish")
    run = sub.add_parser("download", help="kanalni yuklash")
    run.add_argument("--channel", default=DEFAULT_CHANNEL)
    run.add_argument("--limit", type=int, help="faqat dastlabki N ta post (sinov uchun)")
    run.add_argument("--workers", type=int, default=8, help="bir vaqtda nechta fayl (standart 8)")
    args = parser.parse_args()
    if args.command == "login":
        return asyncio.run(login())
    return asyncio.run(download(args.channel, args.limit, args.workers))


if __name__ == "__main__":
    sys.exit(main())
