"""Foydalanuvchilar ro'yxati (admin panel): qidiruv, filtr va sahifalash."""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.db.models import Region, User

PER_PAGE = 50
FILTERS = ("all", "active", "subscribed", "blocked")


async def list_users(
    session: AsyncSession, *, query: str = "", flt: str = "all", page: int = 1
) -> tuple[list[tuple[User, str | None]], int]:
    """(sahifadagi (foydalanuvchi, shahar nomi) juftliklari, filtrga mos jami soni)."""
    conditions = []
    query = query.strip()
    if query:
        by_name = User.name.ilike(f"%{query.replace('%', '').replace('_', '')}%")
        conditions.append(or_(by_name, User.id == int(query)) if query.isdigit() and len(query) < 19 else by_name)
    if flt == "active":
        conditions.append(User.is_blocked.is_(False))
    elif flt == "subscribed":
        conditions.extend([User.subscribed.is_(True), User.is_blocked.is_(False)])
    elif flt == "blocked":
        conditions.append(User.is_blocked.is_(True))

    total = await session.scalar(select(func.count()).select_from(User).where(*conditions))
    rows = await session.execute(
        select(User, Region.name)
        .join(Region, Region.id == User.region_id, isouter=True)
        .where(*conditions)
        .order_by(User.created_at.desc(), User.id)
        .limit(PER_PAGE)
        .offset((max(1, page) - 1) * PER_PAGE)
    )
    return [(user, region) for user, region in rows], total
