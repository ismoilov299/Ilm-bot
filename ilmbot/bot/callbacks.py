from aiogram.filters.callback_data import CallbackData


class NodeCb(CallbackData, prefix="n"):
    """Menyu tuguni bilan inline amallar. `act`: o (ochish), p (ro'yxat sahifasi), x (hech narsa)."""

    act: str
    id: int
    page: int = 1


class RegionCb(CallbackData, prefix="r"):
    """Namoz vaqtlari uchun region tanlash. `id=0`: shaharlar ro'yxatini ko'rsatish."""

    id: int


class ReminderCb(CallbackData, prefix="rm"):
    """Kunlik eslatmani yoqish (`on=True`) yoki o'chirish."""

    region_id: int
    on: bool


class BroadcastCb(CallbackData, prefix="bc"):
    """Admin: tasdiqlash (go), rad etish (no), to'xtatish, davom ettirish, bekor qilish yoki holatni yangilash."""

    act: str
    id: int = 0
