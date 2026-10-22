"""Kanal postlarini botga forward qilib arxivlash (faqat adminlar). 20 MB dan katta fayllar yuklanmaydi.

Forward qilingan postdan kanal va post raqami (`forward_origin`) olinadi, fayl 20 MB gacha bo'lsa yuklab olinadi.
Natija `var/forwarded/`: `index.jsonl` (har post uchun bir qator) va `media/<post_raqami>.<kengaytma>`.
"""

import asyncio
import json
import logging
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.types import Message

from ilmbot.bot.filters import IsAdmin

log = logging.getLogger(__name__)

ARCHIVE_DIR = Path("var/forwarded")
BOT_API_LIMIT = 20 * 1024 * 1024
REPORT_EVERY = 25  # har bir postga javob yozib spam qilmaslik uchun

counters = {"seen": 0, "saved": 0, "too_big": 0, "failed": 0}


def pick_media(message: Message):
    """(tur, fayl obyekti, kengaytma) yoki None."""
    if message.photo:
        return "photo", message.photo[-1], ".jpg"
    for kind in ("audio", "video", "voice", "document", "video_note", "animation"):
        media = getattr(message, kind)
        if media:
            suffix = Path(getattr(media, "file_name", None) or "").suffix
            return kind, media, suffix or {"audio": ".mp3", "video": ".mp4", "voice": ".ogg"}.get(kind, "")
    return None


async def on_forwarded_post(message: Message, bot: Bot):
    origin = message.forward_origin
    picked = pick_media(message)
    if picked is None:
        return
    kind, media, suffix = picked
    await asyncio.to_thread(ARCHIVE_DIR.mkdir, parents=True, exist_ok=True)
    counters["seen"] += 1
    row = {
        "message_id": origin.message_id,
        "chat_id": origin.chat.id,
        "chat": origin.chat.username,
        "kind": kind,
        "size": getattr(media, "file_size", None),
        "file_id": media.file_id,
        "file_unique_id": media.file_unique_id,
        "caption": message.caption,
        "status": "saved",
    }
    if row["size"] and row["size"] > BOT_API_LIMIT:
        row["status"] = "too_big"
        counters["too_big"] += 1
    else:
        target = ARCHIVE_DIR / "media" / f"{origin.message_id}{suffix}"
        try:
            await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)
            await bot.download(media, destination=target)
            row["file"] = f"media/{target.name}"
            counters["saved"] += 1
        except Exception:
            log.exception("Forward qilingan post yuklanmadi: %s", origin.message_id)
            row["status"] = "failed"
            counters["failed"] += 1
    with (ARCHIVE_DIR / "index.jsonl").open("a", encoding="utf-8") as index:
        index.write(json.dumps(row, ensure_ascii=False) + "\n")
    if counters["seen"] % REPORT_EVERY == 1 or row["status"] != "saved":
        await message.answer(
            f"Arxiv: ko'rildi {counters['seen']}, saqlandi {counters['saved']}, "
            f"20 MB dan katta {counters['too_big']}, xato {counters['failed']}"
        )


def create_router() -> Router:
    router = Router(name="archive")
    router.message.register(
        on_forwarded_post,
        IsAdmin(),
        StateFilter(None),
        F.forward_origin.type == "channel",
        F.photo | F.audio | F.video | F.voice | F.document | F.video_note | F.animation,
    )
    return router
