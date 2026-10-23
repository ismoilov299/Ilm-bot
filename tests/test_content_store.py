import hashlib
import json

import pytest
from sqlalchemy import func, select

from ilmbot.db.models import ContentPost
from ilmbot.services.content_store import export_file, import_export, media_path, metadata, store_file


def test_media_is_content_addressed_and_deduplicated(tmp_path):
    source = tmp_path / "sample.mp3"
    source.write_bytes(b"test audio bytes")
    root = tmp_path / "private"
    first = store_file(source, root)
    second = store_file(source, root)
    assert first == second == (hashlib.sha256(source.read_bytes()).hexdigest(), source.stat().st_size)
    assert media_path(root, first[0]).read_bytes() == source.read_bytes()
    assert len([p for p in root.rglob("*") if p.is_file()]) == 1


@pytest.mark.parametrize("value", ["../secret.env", "..\\secret.env", "/etc/passwd", "C:/secret.env"])
def test_export_cannot_read_outside_its_directory(tmp_path, value):
    with pytest.raises(ValueError):
        export_file(tmp_path, value)


@pytest.mark.parametrize("key", ["../secret", "a" * 63, "g" * 64, "A" * 64])
def test_storage_does_not_accept_arbitrary_paths(tmp_path, key):
    with pytest.raises(ValueError):
        media_path(tmp_path, key)


def test_metadata_flattens_telegram_entities_without_creating_html():
    row = metadata({"id": 1, "text": ["Duo ", {"type": "bold", "text": "<script>"}]}, "@Channel")
    assert row["body"] == "Duo <script>" and row["kind"] == "text" and row["channel"] == "@channel"


async def test_import_keeps_order_metadata_and_existing_files(session, tmp_path):
    audio = tmp_path / "files" / "lecture.mp3"
    audio.parent.mkdir()
    audio.write_bytes(b"ID3-audio")
    export = tmp_path / "result.json"
    messages = [
        {"id": 90001, "type": "message", "text": "Matn"},
        {
            "id": 90002,
            "type": "message",
            "media_type": "audio_file",
            "mime_type": "audio/mpeg",
            "file": "files/lecture.mp3",
            "file_name": "lecture.mp3",
            "text": "Dars",
            "duration_seconds": 60,
        },
        {
            "id": 90003,
            "type": "message",
            "media_type": "video_file",
            "mime_type": "video/mp4",
            "file": "(File not included. Change data exporting settings to download.)",
            "text": "Video",
        },
    ]
    export.write_text(json.dumps({"messages": messages}), encoding="utf-8")
    root = tmp_path / "private"
    counts = await import_export(session, export, "@channel", root)
    assert counts == {"posts": 3, "files": 1, "missing_files": 1}
    post = await session.scalar(select(ContentPost).where(ContentPost.message_id == 90002))
    key = post.storage_key
    assert media_path(root, key).read_bytes() == audio.read_bytes()
    assert (post.kind, post.duration, post.body) == ("audio", 60, "Dars")
    messages[1]["file"] = "(File not included)"
    export.write_text(json.dumps({"messages": messages}), encoding="utf-8")
    await import_export(session, export, "@channel", root)
    await session.refresh(post)
    assert post.storage_key == key
    assert await session.scalar(select(func.count()).select_from(ContentPost)) == 3
