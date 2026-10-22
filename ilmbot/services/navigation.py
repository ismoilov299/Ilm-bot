"""Foydalanuvchining menyudagi joriy o'rni (reply klaviatura matnlari bir xil bo'lishi mumkin, shuning uchun kerak)."""

from redis.asyncio import Redis

_TTL_SECONDS = 7 * 24 * 3600


class NavigationState:
    def __init__(self, redis: Redis):
        self._redis = redis

    @staticmethod
    def _key(user_id: int) -> str:
        return f"nav:{user_id}"

    async def get(self, user_id: int) -> int | None:
        """Joriy menyu tugunining ID si; ildizda yoki noma'lum bo'lsa None."""
        value = await self._redis.get(self._key(user_id))
        return int(value) if value else None

    async def set(self, user_id: int, node_id: int | None) -> None:
        if node_id is None:
            await self._redis.delete(self._key(user_id))
        else:
            await self._redis.set(self._key(user_id), node_id, ex=_TTL_SECONDS)
