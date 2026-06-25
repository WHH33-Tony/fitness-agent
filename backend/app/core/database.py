from __future__ import annotations

from collections.abc import Generator

from redis import Redis
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

def _create_engine(url: str):
    # SQLite 在桌面端常见于多线程（FastAPI + 背景任务/WS），需要关闭同线程检查
    if url.startswith("sqlite"):
        return create_engine(url, pool_pre_ping=True, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True)


users_engine = _create_engine(settings.users_database_url)
sports_engine = _create_engine(settings.sports_database_url)

UsersSessionLocal = sessionmaker(bind=users_engine, autoflush=False, autocommit=False)
SportsSessionLocal = sessionmaker(bind=sports_engine, autoflush=False, autocommit=False)


class UsersBase(DeclarativeBase):
    pass


class SportsBase(DeclarativeBase):
    pass


def get_users_db() -> Generator[Session, None, None]:
    db = UsersSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_sports_db() -> Generator[Session, None, None]:
    db = SportsSessionLocal()
    try:
        yield db
    finally:
        db.close()


class _MemoryRedis:
    def __init__(self):
        self._kv: dict[str, tuple[str, float | None]] = {}
        self._lists: dict[str, list[str]] = {}

    def _now(self) -> float:
        import time

        return time.time()

    def _expired(self, exp: float | None) -> bool:
        return exp is not None and exp <= self._now()

    def get(self, key: str):
        item = self._kv.get(key)
        if not item:
            return None
        val, exp = item
        if self._expired(exp):
            self._kv.pop(key, None)
            return None
        return val

    def setex(self, key: str, seconds: int, value: str):
        self._kv[key] = (value, self._now() + int(seconds))
        return True

    def delete(self, key: str):
        self._kv.pop(key, None)
        self._lists.pop(key, None)
        return True

    def lrange(self, key: str, start: int, end: int):
        arr = self._lists.get(key, [])
        if end == -1:
            return arr[start:]
        return arr[start : end + 1]

    def lpush(self, key: str, value: str):
        arr = self._lists.setdefault(key, [])
        arr.insert(0, value)
        return len(arr)

    def ltrim(self, key: str, start: int, end: int):
        arr = self._lists.get(key, [])
        if end == -1:
            self._lists[key] = arr[start:]
        else:
            self._lists[key] = arr[start : end + 1]
        return True

    def expire(self, key: str, seconds: int):
        # best-effort: set expiry for string key only
        if key in self._kv:
            val, _ = self._kv[key]
            self._kv[key] = (val, self._now() + int(seconds))
        return True


_memory_redis_singleton: _MemoryRedis | None = None


def get_redis() -> Redis:
    global _memory_redis_singleton
    if settings.redis_url.startswith("memory://"):
        if _memory_redis_singleton is None:
            _memory_redis_singleton = _MemoryRedis()
        return _memory_redis_singleton  # type: ignore[return-value]
    return Redis.from_url(settings.redis_url, decode_responses=True)
