"""Web reader va yopiq, vaqtinchalik ruxsatli media oqimi."""

import asyncio
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from itsdangerous import BadData, URLSafeTimedSerializer
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.db.models import ButtonKind, ContentPost
from ilmbot.services.content_store import PLAYABLE_MIME, content_for_messages, media_path, visible_content_query
from ilmbot.web.deps import db_session
from ilmbot.web.miniapp_auth import TelegramIdentity
from ilmbot.web.routes_miniapp import identity

router = APIRouter(prefix="/app")
TICKET_MAX_AGE = 3600


def signer(request: Request) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(request.app.state.settings.session_secret, salt="ilm-media-playback-v1")


async def visible_query(request: Request, session: AsyncSession):
    snapshot = await request.app.state.miniapp_menu.snapshot(session)
    active_ids = {mid for node in snapshot.nodes.values() for mid in node.message_ids}
    return visible_content_query(request.app.state.settings.content_channel, active_ids)


async def serialize(request: Request, who: TelegramIdentity, post: ContentPost) -> dict:
    available = False
    if post.storage_key and post.mime_type in PLAYABLE_MIME:
        path = media_path(request.app.state.settings.media_root, post.storage_key)
        available = await asyncio.to_thread(path.is_file)
    url = None
    if available:
        token = signer(request).dumps({"u": who.id, "p": post.id, "k": post.storage_key})
        url = f"/app/media/{post.id}?{urlencode({'ticket': token})}"
    return {
        "id": post.id,
        "message_id": post.message_id,
        "title": post.title,
        "body": post.body,
        "kind": post.kind,
        "file_name": post.file_name,
        "file_size": post.file_size,
        "duration": post.duration,
        "media_url": url,
        "available": post.kind == "text" or available,
    }


@router.get("/api/content/{node_id}")
async def node_content(
    node_id: int,
    request: Request,
    who: TelegramIdentity = Depends(identity),
    session: AsyncSession = Depends(db_session),
):
    snapshot = await request.app.state.miniapp_menu.snapshot(session)
    node = snapshot.get(node_id)
    if node is None or node.kind != ButtonKind.POST:
        raise HTTPException(404, "Kontent topilmadi yoki yashirilgan")
    posts = await content_for_messages(session, request.app.state.settings.content_channel, node.message_ids)
    return {
        "title": node.name,
        "items": [await serialize(request, who, post) for post in posts],
        "pending": len(node.message_ids) - len(posts),
    }


@router.get("/api/library")
async def library(
    request: Request,
    q: str = Query("", max_length=100),
    kind: Literal["", "text", "audio", "video", "photo", "pdf", "document"] = "",
    page: int = Query(1, ge=1, le=10000),
    who: TelegramIdentity = Depends(identity),
    session: AsyncSession = Depends(db_session),
):
    query = await visible_query(request, session)
    if q.strip():
        pattern = f"%{q.strip().replace('%', '').replace('_', '')}%"
        query = query.where(or_(ContentPost.title.ilike(pattern), ContentPost.body.ilike(pattern)))
    if kind:
        query = query.where(ContentPost.kind == kind)
    total = await session.scalar(select(func.count()).select_from(query.subquery()))
    rows = (await session.scalars(query.order_by(ContentPost.message_id).offset((page - 1) * 20).limit(20))).all()
    return {
        "items": [
            {"id": p.id, "title": p.title, "kind": p.kind, "available": p.kind == "text" or bool(p.storage_key)}
            for p in rows
        ],
        "page": page,
        "pages": max(1, (total + 19) // 20),
        "total": total,
    }


@router.get("/api/material/{post_id}")
async def material(
    post_id: int,
    request: Request,
    who: TelegramIdentity = Depends(identity),
    session: AsyncSession = Depends(db_session),
):
    post = await session.scalar((await visible_query(request, session)).where(ContentPost.id == post_id))
    if post is None:
        raise HTTPException(404, "Material topilmadi yoki yashirilgan")
    return {"title": post.title, "items": [await serialize(request, who, post)], "pending": 0}


@router.api_route("/media/{post_id}", methods=["GET", "HEAD"], name="content_media")
async def media(
    post_id: int,
    request: Request,
    ticket: str = Query("", max_length=2048),
    session: AsyncSession = Depends(db_session),
):
    try:
        grant = signer(request).loads(ticket, max_age=TICKET_MAX_AGE)
        if (
            not isinstance(grant, dict)
            or grant.get("p") != post_id
            or type(grant.get("u")) is not int
            or grant["u"] <= 0
        ):
            raise ValueError("invalid grant")
    except (BadData, ValueError, TypeError):
        raise HTTPException(403, "Ko'rish ruxsati tugagan. Materialni qayta oching") from None
    post = await session.scalar((await visible_query(request, session)).where(ContentPost.id == post_id))
    if post is None or not post.storage_key or grant.get("k") != post.storage_key:
        raise HTTPException(404, "Media topilmadi yoki yashirilgan")
    if post.mime_type not in PLAYABLE_MIME:
        raise HTTPException(415, "Bu fayl turi faqat Telegram orqali ochiladi")
    path: Path = media_path(request.app.state.settings.media_root, post.storage_key)
    if not await asyncio.to_thread(path.is_file):
        raise HTTPException(404, "Media hali yuklanmagan")
    mime = {"audio/mp3": "audio/mpeg", "audio/m4a": "audio/mp4"}.get(post.mime_type, post.mime_type)
    return FileResponse(
        path,
        media_type=mime,
        headers={
            "Content-Disposition": "inline",
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
