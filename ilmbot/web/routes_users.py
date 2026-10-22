import math

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.services.users_admin import FILTERS, PER_PAGE, list_users
from ilmbot.web.deps import db_session, render, require_admin
from ilmbot.web.sessions import AdminSession

router = APIRouter(prefix="/users")

FILTER_LABELS = {"all": "Hammasi", "active": "Faol", "subscribed": "Eslatma obunachilari", "blocked": "Botni bloklagan"}


@router.get("")
async def index(
    request: Request,
    q: str = "",
    filter: str = "all",
    page: int = 1,
    admin: AdminSession = Depends(require_admin),
    session: AsyncSession = Depends(db_session),
):
    flt = filter if filter in FILTERS else "all"
    rows, total = await list_users(session, query=q, flt=flt, page=page)
    return render(
        request, "users.html", admin=admin, nav="users", rows=rows, total=total, q=q, flt=flt, filters=FILTER_LABELS,
        page=max(1, page), pages=max(1, math.ceil(total / PER_PAGE)),
    )  # fmt: skip
