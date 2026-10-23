"""Telegram Desktop eksportini web katalogiga va yopiq fayl omboriga import qilish."""

import asyncio
import hashlib
import json
import os
import re
import tempfile
from collections import Counter
from pathlib import Path, PurePosixPath

from sqlalchemy import exists, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.db.models import ButtonPost, ContentPost
from ilmbot.services.inventory import load_inventory

STORAGE_KEY = re.compile(r"[a-f0-9]{64}")
PLAYABLE_MIME = {
    "audio/mpeg",
    "audio/mp3",
    "audio/mp4",
    "audio/m4a",
    "audio/ogg",
    "audio/opus",
    "audio/wav",
    "video/mp4",
    "video/webm",
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "application/pdf",
}


def normalize_channel(channel: str) -> str:
    return channel.strip().casefold()


def plain_text(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(
            part if isinstance(part, str) else str(part.get("text", ""))
            for part in value
            if isinstance(part, str | dict)
        )
    return ""


def export_file(root: Path, value: str | None) -> Path | None:
    if not value or value.startswith("("):
        return None
    relative = PurePosixPath(value.replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts or ":" in value:
        raise ValueError("Eksportdagi fayl yo'li xavfsiz emas")
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root.resolve()):
        raise ValueError("Eksport fayli berilgan papkadan tashqarida")
    return candidate if candidate.is_file() else None


def media_path(root: Path, key: str) -> Path:
    if not STORAGE_KEY.fullmatch(key):
        raise ValueError("Media kaliti noto'g'ri")
    resolved_root = root.resolve()
    candidate = (resolved_root / key[:2] / key).resolve()
    if not candidate.is_relative_to(resolved_root):
        raise ValueError("Media yo'li ombordan tashqarida")
    return candidate


def store_file(source: Path, root: Path) -> tuple[str, int]:
    root.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size = 0
    with tempfile.NamedTemporaryFile(dir=root, suffix=".part", delete=False) as temporary:
        temporary_path = Path(temporary.name)
        try:
            with source.open("rb") as incoming:
                while chunk := incoming.read(1024 * 1024):
                    digest.update(chunk)
                    temporary.write(chunk)
                    size += len(chunk)
        except BaseException:
            temporary.close()
            temporary_path.unlink(missing_ok=True)
            raise
    key = digest.hexdigest()
    destination = media_path(root, key)
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.is_file() and destination.stat().st_size == size:
            temporary_path.unlink()
        else:
            os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)
    return key, size


def metadata(message: dict, channel: str, title: str = "") -> dict:
    body = plain_text(message.get("text"))
    mime = message.get("mime_type")
    media = message.get("media_type", "")
    if message.get("photo"):
        kind, mime = "photo", "image/jpeg"
    elif media in {"audio_file", "voice_message"}:
        kind = "audio"
    elif media in {"video_file", "video_message", "animation"}:
        kind = "video"
    elif mime == "application/pdf":
        kind = "pdf"
    elif mime in {"image/jpeg", "image/png", "image/webp", "image/gif"}:
        kind = "photo"
    elif message.get("file"):
        kind = "document"
    else:
        kind = "text"
    return {
        "channel": normalize_channel(channel),
        "message_id": message["id"],
        "kind": kind,
        "title": message.get("title") or message.get("file_name") or title or body[:160] or f"Material {message['id']}",
        "body": body,
        "mime_type": mime,
        "file_name": message.get("file_name"),
        "file_size": message.get("file_size", message.get("photo_file_size")),
        "duration": message.get("duration_seconds"),
    }


async def import_export(session: AsyncSession, export: Path, channel: str, media_root: Path) -> dict[str, int]:
    data = await asyncio.to_thread(lambda: json.loads(export.read_text(encoding="utf-8")))
    if not isinstance(data, dict) or not isinstance(data.get("messages"), list):
        raise ValueError("Telegram JSON eksportida messages ro'yxati yo'q")
    inventory = {p.id: p for p in load_inventory()}
    counts: Counter = Counter()
    for message in data["messages"]:
        if message.get("type") != "message" or type(message.get("id")) is not int:
            continue
        item = inventory.get(message["id"])
        row = metadata(message, channel, item.title if item else "")
        row["is_active"] = not (item and item.ignored)
        source = export_file(export.parent, message.get("photo") or message.get("file"))
        if source is not None:
            row["storage_key"], row["file_size"] = await asyncio.to_thread(store_file, source, media_root)
            counts["files"] += 1
        elif row["kind"] != "text":
            counts["missing_files"] += 1
        statement = insert(ContentPost).values(**row)
        # Metadata-only reimport allaqachon mavjud mediani o'chirmaydi.
        statement = statement.on_conflict_do_update(
            index_elements=[ContentPost.channel, ContentPost.message_id],
            set_={
                key: getattr(statement.excluded, key)
                for key in row
                if key not in {"channel", "message_id", "is_active"}
            },
        )
        await session.execute(statement)
        counts["posts"] += 1
    await session.flush()
    return dict(counts)


async def content_for_messages(session: AsyncSession, channel: str, message_ids: tuple[int, ...]) -> list[ContentPost]:
    if not message_ids:
        return []
    posts = (
        await session.scalars(
            select(ContentPost).where(
                ContentPost.channel == normalize_channel(channel),
                ContentPost.message_id.in_(message_ids),
                ContentPost.is_active,
            )
        )
    ).all()
    by_id = {post.message_id: post for post in posts}
    return [by_id[mid] for mid in message_ids if mid in by_id]


def visible_content_query(channel: str, active_ids: set[int]):
    """Yashirilgan bo'limdagilar kutubxona, bot va stream orqali ham ko'rinmasin."""
    linked = exists(select(ButtonPost.id).where(ButtonPost.message_id == ContentPost.message_id))
    return select(ContentPost).where(
        ContentPost.channel == normalize_channel(channel),
        ContentPost.is_active,
        or_(ContentPost.message_id.in_(active_ids), ~linked),
    )
