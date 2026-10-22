from aiogram.filters.callback_data import CallbackData


class NodeCb(CallbackData, prefix="n"):
    """Menyu tuguni bilan inline amallar. `act`: o (ochish), p (ro'yxat sahifasi), x (hech narsa)."""

    act: str
    id: int
    page: int = 1
