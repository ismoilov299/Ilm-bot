"""Broadcast sahifalari: tuzish, tasdiqlash, jonli progress va boshqarish. Veb-panel o'zi Telegramga yozmaydi:
ishni navbatga qo'yadi, worker bajaradi."""

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.db.models import BroadcastJob
from ilmbot.services.broadcast import FINAL, BroadcastService, JobAction
from ilmbot.services.telegram_html import HtmlError, sanitize
from ilmbot.web.deps import audit, db_session, render, require_admin, verify_csrf
from ilmbot.web.sessions import AdminSession

router = APIRouter(prefix="/broadcasts")

MAX_MESSAGE_ID = 2_000_000_000


def _service(request: Request) -> BroadcastService:
    return request.app.state.broadcasts


def _validate(mode: str, text: str, message_id: str) -> tuple[str | None, int | None]:
    """(tozalangan matn, kanal posti ID si). Noto'g'ri bo'lsa ValueError (foydalanuvchiga ko'rsatiladi)."""
    if mode == "text":
        try:
            return sanitize(text), None
        except HtmlError as exc:
            raise ValueError(str(exc)) from exc
    if mode == "post":
        if not message_id.strip().isdigit() or not 0 < int(message_id) < MAX_MESSAGE_ID:
            raise ValueError("Kanal postining ID si musbat butun son bo'lishi kerak (post havolasining oxirgi raqami)")
        return None, int(message_id)
    raise ValueError("Xabar turi noto'g'ri")


@router.get("")
async def list_jobs(
    request: Request, admin: AdminSession = Depends(require_admin), session: AsyncSession = Depends(db_session)
):
    jobs = (await session.scalars(select(BroadcastJob).order_by(BroadcastJob.id.desc()).limit(50))).all()
    return render(request, "broadcasts.html", admin=admin, nav="broadcasts", jobs=jobs)


@router.get("/new")
async def new_form(request: Request, admin: AdminSession = Depends(require_admin)):
    return render(request, "broadcast_new.html", admin=admin, nav="broadcasts", mode="text", text="", message_id="")


@router.post("/new")
async def preview(
    request: Request,
    mode: str = Form("text"),
    text: str = Form(""),
    message_id: str = Form(""),
    admin: AdminSession = Depends(require_admin),
    _: None = Depends(verify_csrf),
    session: AsyncSession = Depends(db_session),
):
    try:
        clean_text, post_id = _validate(mode, text, message_id)
    except ValueError as exc:
        return render(
            request, "broadcast_new.html", status_code=400, admin=admin, nav="broadcasts",
            mode=mode, text=text, message_id=message_id, error=str(exc),
        )  # fmt: skip
    audience = await _service(request).count_recipients(session)
    return render(
        request, "broadcast_confirm.html", admin=admin, nav="broadcasts",
        mode=mode, text=clean_text, message_id=post_id, audience=audience,
        test_audience=await _service(request).count_recipients(session, request.app.state.settings.admins),
    )  # fmt: skip


@router.post("")
async def create(
    request: Request,
    mode: str = Form("text"),
    text: str = Form(""),
    message_id: str = Form(""),
    target: str = Form("all"),
    admin: AdminSession = Depends(require_admin),
    _: None = Depends(verify_csrf),
    session: AsyncSession = Depends(db_session),
):
    try:
        clean_text, post_id = _validate(mode, text, message_id)  # qayta tekshiriladi: forma maydoniga ishonib bo'lmaydi
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    service = _service(request)
    only = request.app.state.settings.admins if target == "test" else None
    if target == "test" and not await service.count_recipients(session, only):
        raise HTTPException(
            status_code=400,
            detail="Sinov uchun ADMINS dagi hisob botda /start bosgan bo'lishi va ADMINS sozlangan bo'lishi kerak",
        )
    job = await service.create_job(
        session, f"web:{admin.username}", text=clean_text, source_message_id=post_id, only_user_ids=only
    )
    await audit(session, admin, "broadcast.create", job_id=job.id, mode=mode, test=job.is_test, total=job.total)
    await session.commit()
    return RedirectResponse(f"/broadcasts/{job.id}", status_code=303)


async def _job_or_404(session: AsyncSession, request: Request, job_id: int) -> BroadcastJob:
    job = await _service(request).get(session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Broadcast topilmadi")
    return job


@router.get("/{job_id}")
async def detail(
    request: Request,
    job_id: int,
    admin: AdminSession = Depends(require_admin),
    session: AsyncSession = Depends(db_session),
):
    job = await _job_or_404(session, request, job_id)
    return render(request, "broadcast_detail.html", admin=admin, nav="broadcasts", job=job)


@router.get("/{job_id}/progress")
async def progress(
    request: Request,
    job_id: int,
    admin: AdminSession = Depends(require_admin),
    session: AsyncSession = Depends(db_session),
):
    job = await _job_or_404(session, request, job_id)
    return render(request, "_progress.html", admin=admin, job=job, final=job.status in FINAL)


@router.post("/{job_id}/{action}")
async def control(
    request: Request,
    job_id: int,
    action: str,
    admin: AdminSession = Depends(require_admin),
    _: None = Depends(verify_csrf),
    session: AsyncSession = Depends(db_session),
):
    try:
        job_action = JobAction(action)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Noma'lum amal") from exc
    job = await _service(request).apply(session, job_id, job_action)
    if job is None:
        raise HTTPException(status_code=404, detail="Broadcast topilmadi")
    await audit(session, admin, f"broadcast.{action}", job_id=job_id, status=job.status)
    await session.commit()
    return RedirectResponse(f"/broadcasts/{job_id}", status_code=303)
