"""Boshqaruv paneli uchun umumiy ko'rsatkichlar."""

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ilmbot.db.models import BroadcastJob, Button, Region, User


@dataclass(frozen=True, slots=True)
class Overview:
    users: int
    blocked: int
    subscribers: int
    subscribers_by_region: list[tuple[str, int]]
    menu_nodes: int
    nodes_to_review: int
    latest_broadcast: BroadcastJob | None

    @property
    def active(self) -> int:
        return self.users - self.blocked


async def overview(session: AsyncSession) -> Overview:
    users, blocked, subscribers = (
        await session.execute(
            select(
                func.count(),
                func.count().filter(User.is_blocked.is_(True)),
                func.count().filter(User.subscribed.is_(True), User.is_blocked.is_(False)),
            ).select_from(User)
        )
    ).one()
    by_region = (
        await session.execute(
            select(Region.name, func.count(User.id))
            .join(
                User,
                (User.region_id == Region.id) & User.subscribed.is_(True) & User.is_blocked.is_(False),
                isouter=True,
            )
            .where(Region.is_active)
            .group_by(Region.id, Region.name)
            .order_by(func.count(User.id).desc(), Region.name)
        )
    ).all()
    menu_nodes, to_review = (
        await session.execute(
            select(func.count(), func.count().filter(Button.review_note.is_not(None))).select_from(Button)
        )
    ).one()
    latest = await session.scalar(select(BroadcastJob).order_by(BroadcastJob.id.desc()).limit(1))
    return Overview(
        users=users,
        blocked=blocked,
        subscribers=subscribers,
        subscribers_by_region=[(name, count) for name, count in by_region],
        menu_nodes=menu_nodes,
        nodes_to_review=to_review,
        latest_broadcast=latest,
    )
