"""Menyu daraxti boshqaruvi: ko'rish, qo'shish, tahrirlash, ko'chirish, tartiblash, o'chirish va tasdiqlash."""

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.db.models import Button, ButtonAction, ButtonKind
from ilmbot.services.menu import bump_menu_version
from ilmbot.services.menu_admin import MenuAdminError, MenuAdminService, parse_post_ids
from ilmbot.web.deps import audit, db_session, render, require_admin, verify_csrf
from ilmbot.web.sessions import AdminSession

router = APIRouter(prefix="/menu")
service = MenuAdminService()

KIND_LABELS = {
    ButtonKind.MENU.value: "Menyu (reply tugmalar)",
    ButtonKind.LIST.value: "Ro'yxat (inline, sahifalanadi)",
    ButtonKind.POST.value: "Post (kontent yuboradi)",
    ButtonKind.ACTION.value: "Amal (maxsus bo'lim)",
}
ACTION_LABELS = {
    ButtonAction.PRAYER_TIMES.value: "Namoz vaqtlari",
    ButtonAction.NEAREST_MOSQUES.value: "Yaqin masjidlar",
}


async def _node_or_404(session: AsyncSession, node_id: int) -> Button:
    node = await service.get(session, node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Tugun topilmadi")
    return node


async def _finish(request: Request, session: AsyncSession, admin: AdminSession, action: str, **details) -> None:
    """O'zgarishni saqlaydi, audit yozadi va botdagi menyu keshini darhol bekor qiladi."""
    await audit(session, admin, action, **details)
    await session.commit()
    await bump_menu_version(request.app.state.redis)


def _back(parent_id: int | None, ok: str = "") -> RedirectResponse:
    url = "/menu" + (f"?parent={parent_id}" if parent_id else "")
    if ok:
        url += ("&" if parent_id else "?") + "ok=" + ok
    return RedirectResponse(url, status_code=303)


def _form_context(**extra):
    return {"nav": "menu", "kinds": KIND_LABELS, "actions": ACTION_LABELS, **extra}


@router.get("")
async def browse(
    request: Request,
    parent: int | None = None,
    admin: AdminSession = Depends(require_admin),
    session: AsyncSession = Depends(db_session),
):
    node = await _node_or_404(session, parent) if parent else None
    return render(
        request,
        "menu.html",
        admin=admin,
        nav="menu",
        node=node,
        crumbs=await service.path(session, node),
        rows=await service.rows(session, parent),
        post_ids=await service.post_ids(session, node.id) if node else [],
        kinds=KIND_LABELS,
    )


@router.get("/review")
async def review(
    request: Request, admin: AdminSession = Depends(require_admin), session: AsyncSession = Depends(db_session)
):
    return render(request, "menu_review.html", admin=admin, nav="menu", items=await service.needing_review(session))


@router.get("/new")
async def new_form(
    request: Request,
    parent: int | None = None,
    admin: AdminSession = Depends(require_admin),
    session: AsyncSession = Depends(db_session),
):
    parent_node = await _node_or_404(session, parent) if parent else None
    return render(
        request,
        "menu_form.html",
        admin=admin,
        **_form_context(
            node=None,
            parent=parent_node,
            crumbs=await service.path(session, parent_node),
            form={
                "name": "",
                "kind": "post",
                "action": "",
                "text": "",
                "page_size": 8,
                "is_active": True,
                "post_ids": "",
            },
        ),
    )


@router.post("/new")
async def create(
    request: Request,
    parent: str = Form(""),
    name: str = Form(""),
    kind: str = Form("post"),
    action: str = Form(""),
    text: str = Form(""),
    page_size: int = Form(8),
    post_ids: str = Form(""),
    admin: AdminSession = Depends(require_admin),
    _: None = Depends(verify_csrf),
    session: AsyncSession = Depends(db_session),
):
    parent_id = int(parent) if parent.isdigit() else None
    form = {
        "name": name, "kind": kind, "action": action, "text": text,
        "page_size": page_size, "is_active": True, "post_ids": post_ids,
    }  # fmt: skip
    try:
        node = await service.create(
            session, parent_id=parent_id, name=name, kind=kind, action=action or None, text=text, page_size=page_size
        )
        await service.set_posts(session, node, parse_post_ids(post_ids))
    except MenuAdminError as exc:
        await session.rollback()
        parent_node = await service.get(session, parent_id) if parent_id else None
        return render(
            request, "menu_form.html", status_code=400, admin=admin,
            **_form_context(
                node=None,
                parent=parent_node,
                crumbs=await service.path(session, parent_node),
                form=form,
                error=str(exc),
            ),
        )  # fmt: skip
    await _finish(request, session, admin, "menu.create", node_id=node.id, name=node.name, parent_id=parent_id)
    return _back(parent_id, "Tugun qo'shildi")


@router.get("/{node_id}/edit")
async def edit_form(
    request: Request,
    node_id: int,
    admin: AdminSession = Depends(require_admin),
    session: AsyncSession = Depends(db_session),
):
    node = await _node_or_404(session, node_id)
    form = {
        "name": node.name, "kind": node.kind, "action": node.action or "", "text": node.text,
        "page_size": node.page_size, "is_active": node.is_active,
        "post_ids": "\n".join(map(str, await service.post_ids(session, node.id))),
    }  # fmt: skip
    return render(
        request, "menu_form.html", admin=admin,
        **_form_context(node=node, parent=None, crumbs=await service.path(session, node), form=form),
    )  # fmt: skip


@router.post("/{node_id}/edit")
async def edit(
    request: Request,
    node_id: int,
    name: str = Form(""),
    kind: str = Form("post"),
    action: str = Form(""),
    text: str = Form(""),
    page_size: int = Form(8),
    post_ids: str = Form(""),
    is_active: str = Form(""),
    resolve_review: str = Form(""),
    admin: AdminSession = Depends(require_admin),
    _: None = Depends(verify_csrf),
    session: AsyncSession = Depends(db_session),
):
    node = await _node_or_404(session, node_id)
    form = {
        "name": name, "kind": kind, "action": action, "text": text,
        "page_size": page_size, "is_active": bool(is_active), "post_ids": post_ids,
    }  # fmt: skip
    try:
        await service.update(
            session, node, name=name, kind=kind, action=action or None, text=text,
            page_size=page_size, is_active=bool(is_active),
        )  # fmt: skip
        await service.set_posts(session, node, parse_post_ids(post_ids))
        if resolve_review:
            await service.clear_review(session, node)
    except MenuAdminError as exc:
        await session.rollback()
        node = await _node_or_404(session, node_id)
        return render(
            request, "menu_form.html", status_code=400, admin=admin,
            **_form_context(
                node=node, parent=None, crumbs=await service.path(session, node), form=form, error=str(exc)
            ),
        )  # fmt: skip
    await _finish(request, session, admin, "menu.update", node_id=node.id, name=node.name)
    return _back(node.parent_id, "Saqlandi")


@router.post("/{node_id}/up")
@router.post("/{node_id}/down")
async def reorder(
    request: Request,
    node_id: int,
    admin: AdminSession = Depends(require_admin),
    _: None = Depends(verify_csrf),
    session: AsyncSession = Depends(db_session),
):
    node = await _node_or_404(session, node_id)
    direction = "up" if request.url.path.endswith("/up") else "down"
    await service.reorder(session, node, direction)
    await _finish(request, session, admin, f"menu.{direction}", node_id=node.id)
    return _back(node.parent_id)


@router.post("/{node_id}/toggle")
async def toggle(
    request: Request,
    node_id: int,
    admin: AdminSession = Depends(require_admin),
    _: None = Depends(verify_csrf),
    session: AsyncSession = Depends(db_session),
):
    node = await _node_or_404(session, node_id)
    node.is_active = not node.is_active
    await _finish(request, session, admin, "menu.toggle", node_id=node.id, is_active=node.is_active)
    return _back(node.parent_id)


@router.post("/{node_id}/review-ok")
async def review_ok(
    request: Request,
    node_id: int,
    admin: AdminSession = Depends(require_admin),
    _: None = Depends(verify_csrf),
    session: AsyncSession = Depends(db_session),
):
    node = await _node_or_404(session, node_id)
    await service.clear_review(session, node)
    await _finish(request, session, admin, "menu.review_ok", node_id=node.id)
    return RedirectResponse("/menu/review", status_code=303)


@router.get("/{node_id}/move")
async def move_form(
    request: Request,
    node_id: int,
    q: str = "",
    admin: AdminSession = Depends(require_admin),
    session: AsyncSession = Depends(db_session),
):
    node = await _node_or_404(session, node_id)
    results = await service.search(session, q, kinds=("menu", "list")) if q.strip() else []
    return render(
        request, "menu_move.html", admin=admin, nav="menu", node=node, q=q, results=results,
        current=await service.path_text(session, node),
    )  # fmt: skip


@router.post("/{node_id}/move")
async def move(
    request: Request,
    node_id: int,
    new_parent: str = Form(""),
    admin: AdminSession = Depends(require_admin),
    _: None = Depends(verify_csrf),
    session: AsyncSession = Depends(db_session),
):
    node = await _node_or_404(session, node_id)
    target = int(new_parent) if new_parent.isdigit() else None  # bo'sh qiymat = bosh menyu (ildiz)
    try:
        await service.move(session, node, target)
    except MenuAdminError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await _finish(request, session, admin, "menu.move", node_id=node.id, new_parent=target)
    return _back(target, "Ko'chirildi")


@router.get("/{node_id}/delete")
async def delete_confirm(
    request: Request,
    node_id: int,
    admin: AdminSession = Depends(require_admin),
    session: AsyncSession = Depends(db_session),
):
    node = await _node_or_404(session, node_id)
    return render(
        request, "menu_delete.html", admin=admin, nav="menu", node=node,
        descendants=await service.count_descendants(session, node.id), path=await service.path_text(session, node),
    )  # fmt: skip


@router.post("/{node_id}/delete")
async def delete(
    request: Request,
    node_id: int,
    admin: AdminSession = Depends(require_admin),
    _: None = Depends(verify_csrf),
    session: AsyncSession = Depends(db_session),
):
    node = await _node_or_404(session, node_id)
    parent_id, name = node.parent_id, node.name
    removed = await service.delete(session, node)
    await _finish(request, session, admin, "menu.delete", node_id=node_id, name=name, nested=removed)
    return _back(parent_id, "O'chirildi")
