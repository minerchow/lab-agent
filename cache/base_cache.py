from config.cache_config import get_cache, set_cache, delete_cache, get_json_cache


class BaseCache:
    def __init__(self, prefix: str, default_expire: int = 3600):
        self.prefix = prefix
        self.default_expire = default_expire

    def _get_key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    async def get(self, key: str):
        return await get_cache(self._get_key(key))

    async def get_json(self, key: str):
        return await get_json_cache(self._get_key(key))

    async def set(self, key: str, value, expire: int = None):
        return await set_cache(
            self._get_key(key),
            value,
            expire or self.default_expire
        )

    async def delete(self, key: str):
        return await delete_cache(self._get_key(key))
