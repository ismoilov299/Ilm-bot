"""Kanal inventari: biriktirilmagan postlarni ko'rish va menyuga qo'shish."""

import math
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.db.models import ButtonKind
from ilmbot.services.inventory import PER_PAGE, STATUSES, InventoryService
from ilmbot.services.menu import bump_menu_version
from ilmbot.services.menu_admin import MenuAdminError, MenuAdminService
from ilmbot.web.deps import audit, db_session, render, require_admin, verify_csrf
from ilmbot.web.sessions import AdminSession

router = APIRouter(prefix="/inventory")
inventory = InventoryService()
menu = MenuAdminService()

STATUS_LABELS = {
    "unassigned": "Biriktirilmagan",
    "assigned": "Biriktirilgan",
    "ignored": "Axlat deb belgilangan",
    "all": "Hammasi",
}


def _post_link(request: Request, post_id: int) -> str:
    channel = request.app.state.settings.content_channel
    return f"https://t.me/{channel.lstrip('@')}/{post_id}" if channel.startswith("@") else ""


@router.get("")
async def index(
    request: Request,
    status: str = "unassigned",
    type: str = "",
    q: str = "",
    page: int = 1,
    admin: AdminSession = Depends(require_admin),
    session: AsyncSession = Depends(db_session),
):
    status = status if status in STATUSES else "unassigned"
    items, total = await inventory.page(session, status=status, kind=type, query=q, page=page)
    return render(
        request, "inventory.html", admin=admin, nav="inventory", items=items, total=total, status=status, kind=type,
        q=q, page=max(1, page), pages=max(1, math.ceil(total / PER_PAGE)), statuses=STATUS_LABELS,
        types=inventory.types(), link=lambda post_id: _post_link(request, post_id),
    )  # fmt: skip


@router.get("/{post_id}/assign")
async def assign_form(
    request: Request,
    post_id: int,
    q: str = "",
    admin: AdminSession = Depends(require_admin),
    session: AsyncSession = Depends(db_session),
):
    post = inventory.get(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post inventarda topilmadi")
    results = await menu.search(session, q, kinds=("post", "list", "menu")) if q.strip() else []
    return render(
        request, "inventory_assign.html", admin=admin, nav="inventory", post=post, q=q, results=results,
        link=_post_link(request, post_id),
    )  # fmt: skip


@router.post("/{post_id}/assign")
async def assign(
    request: Request,
    post_id: int,
    mode: str = Form(""),
    node_id: int = Form(0),
    name: str = Form(""),
    admin: AdminSession = Depends(require_admin),
    _: None = Depends(verify_csrf),
    session: AsyncSession = Depends(db_session),
):
    post = inventory.get(post_id)
    node = await menu.get(session, node_id)
    if post is None or node is None:
        raise HTTPException(status_code=404, detail="Post yoki tugun topilmadi")
    try:
        if mode == "attach" and node.kind == ButtonKind.POST.value:
            await menu.add_post(session, node, post_id)
        elif mode == "child":
            child = await menu.create(
                session, parent_id=node.id, name=name or post.title[:80], kind=ButtonKind.POST.value
            )
            await menu.set_posts(session, child, [post_id])
        else:
            raise MenuAdminError("Bu tugunga post qo'shib bo'lmaydi")
    except MenuAdminError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await audit(session, admin, "inventory.assign", post_id=post_id, node_id=node.id, mode=mode)
    await session.commit()
    await bump_menu_version(request.app.state.redis)
    return RedirectResponse(f"/inventory?ok={quote(f'Post #{post_id} biriktirildi')}", status_code=303)
