"""Ma'lumotlar modeli (docs/ARCHITECTURE.md, 5-bo'lim)."""

import datetime as dt
import enum

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ilmbot.db.base import Base


class ButtonKind(enum.StrEnum):
    MENU = "menu"  # reply klaviatura
    LIST = "list"  # inline, sahifalanadi
    POST = "post"  # kontent yuboradi
    ACTION = "action"  # maxsus handler


class ButtonAction(enum.StrEnum):
    PRAYER_TIMES = "prayer_times"
    NEAREST_MOSQUES = "nearest_mosques"


class JobStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    DONE = "done"
    CANCELLED = "cancelled"


class RecipientStatus(enum.StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    BLOCKED = "blocked"


def _values(enum_cls: type[enum.StrEnum]) -> str:
    return ", ".join(f"'{member.value}'" for member in enum_cls)


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    api_name: Mapped[str] = mapped_column(String(64))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_reminders", "region_id", "subscribed", "is_blocked"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)  # Telegram ID
    name: Mapped[str] = mapped_column(String(255))
    region_id: Mapped[int | None] = mapped_column(ForeignKey("regions.id", ondelete="SET NULL"))
    subscribed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    region: Mapped[Region | None] = relationship()


class PrayerTime(Base):
    __tablename__ = "prayer_times"
    __table_args__ = (UniqueConstraint("region_id", "date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id", ondelete="CASCADE"))
    date: Mapped[dt.date] = mapped_column(Date)
    bomdod: Mapped[dt.time] = mapped_column(Time)
    quyosh: Mapped[dt.time] = mapped_column(Time)
    peshin: Mapped[dt.time] = mapped_column(Time)
    asr: Mapped[dt.time] = mapped_column(Time)
    shom: Mapped[dt.time] = mapped_column(Time)
    xufton: Mapped[dt.time] = mapped_column(Time)
    source: Mapped[str] = mapped_column(String(16), default="computed", server_default="computed")
    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Button(Base):
    """Menyu daraxtining tuguni. Kontent `ButtonPost` orqali bog'lanadi."""

    __tablename__ = "buttons"
    __table_args__ = (
        CheckConstraint(f"kind IN ({_values(ButtonKind)})", name="kind"),
        CheckConstraint(f"action IS NULL OR action IN ({_values(ButtonAction)})", name="action"),
        Index("ix_buttons_parent_position", "parent_id", "position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("buttons.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(16))
    action: Mapped[str | None] = mapped_column(String(32))
    text: Mapped[str] = mapped_column(Text, default="", server_default="")
    page_size: Mapped[int] = mapped_column(Integer, default=8, server_default="8")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    legacy_key: Mapped[str | None] = mapped_column(String(64), unique=True)
    review_note: Mapped[str | None] = mapped_column(Text)

    parent: Mapped["Button | None"] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[list["Button"]] = relationship(
        back_populates="parent",
        order_by="Button.position, Button.id",
        cascade="all, delete-orphan",
        passive_deletes=True,  # yuklanmagan bolalarni bazadagi ON DELETE CASCADE o'chiradi
    )
    posts: Mapped[list["ButtonPost"]] = relationship(
        back_populates="button",
        order_by="ButtonPost.position",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ButtonPost(Base):
    """Tugmaga biriktirilgan kanal posti. Bitta tugma bir nechta postga ega bo'lishi mumkin."""

    __tablename__ = "button_posts"
    __table_args__ = (UniqueConstraint("button_id", "position"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    button_id: Mapped[int] = mapped_column(ForeignKey("buttons.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer)
    message_id: Mapped[int] = mapped_column(BigInteger)

    button: Mapped[Button] = relationship(back_populates="posts")


class ContentPost(Base):
    """Telegram postining web nusxasi. Katta fayllar bazada emas, yopiq media omborida."""

    __tablename__ = "content_posts"
    __table_args__ = (UniqueConstraint("channel", "message_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    channel: Mapped[str] = mapped_column(String(255))
    message_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(Text, default="", server_default="")
    body: Mapped[str] = mapped_column(Text, default="", server_default="")  # plain text
    kind: Mapped[str] = mapped_column(String(16))  # text, photo, audio, video, pdf, document
    mime_type: Mapped[str | None] = mapped_column(String(127))
    file_name: Mapped[str | None] = mapped_column(Text)
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    duration: Mapped[int | None] = mapped_column(Integer)
    storage_key: Mapped[str | None] = mapped_column(String(64))  # SHA256, hech qachon foydalanuvchi yo'li emas
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    imported_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Mosque(Base):
    __tablename__ = "mosques"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    district: Mapped[str | None] = mapped_column(String(64))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    review_note: Mapped[str | None] = mapped_column(Text)


class BroadcastJob(Base):
    __tablename__ = "broadcast_jobs"
    __table_args__ = (
        CheckConstraint(f"status IN ({_values(JobStatus)})", name="status"),
        # Mazmun: tayyor matn (veb panel) yoki nusxalanadigan xabar. Chat ko'rsatilmasa kontent kanali nazarda tutiladi
        CheckConstraint("text IS NOT NULL OR source_message_id IS NOT NULL", name="content"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    created_by: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default=JobStatus.QUEUED.value, server_default="queued")
    text: Mapped[str | None] = mapped_column(Text)  # tozalangan Telegram HTML; None bo'lsa xabar nusxalanadi
    source_chat_id: Mapped[int | None] = mapped_column(BigInteger)
    source_message_id: Mapped[int | None] = mapped_column(BigInteger)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    error: Mapped[str | None] = mapped_column(Text)  # worker xatosi sababi (ish to'xtatiladi)
    total: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    sent: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    failed: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    blocked: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class BroadcastRecipient(Base):
    __tablename__ = "broadcast_recipients"
    __table_args__ = (
        CheckConstraint(f"status IN ({_values(RecipientStatus)})", name="status"),
        Index("ix_broadcast_recipients_job_status", "job_id", "status"),
    )

    job_id: Mapped[int] = mapped_column(ForeignKey("broadcast_jobs.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    status: Mapped[str] = mapped_column(String(16), default=RecipientStatus.PENDING.value, server_default="pending")


class ReminderRun(Base):
    """Bitta (sana, namoz, region) uchun eslatma yuborish holati: takrorlanmaslik va davom ettirish uchun."""

    __tablename__ = "reminder_runs"
    __table_args__ = (UniqueConstraint("date", "prayer", "region_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[dt.date] = mapped_column(Date)
    prayer: Mapped[str] = mapped_column(String(16))
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(16), default="running", server_default="running")
    last_user_id: Mapped[int | None] = mapped_column(BigInteger)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class AdminAudit(Base):
    __tablename__ = "admin_audit"

    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    details: Mapped[dict | None] = mapped_column(JSON)
