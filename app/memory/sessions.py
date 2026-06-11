import time as _time
from app.config import settings

class SessionStore:
    def __init__(self, ttl_sec: int | None = None, now=_time.monotonic, max_turns: int = 12):
        self._ttl = ttl_sec if ttl_sec is not None else settings.session_ttl_sec
        self._now = now
        self._max_turns = max_turns
        self._data: dict[str, dict] = {}  # sid -> {"ts": float, "turns": list}

    def append(self, sid: str | None, role: str, content: str) -> None:
        if not sid:
            return
        entry = self._data.setdefault(sid, {"ts": self._now(), "turns": []})
        entry["ts"] = self._now()
        entry["turns"].append({"role": role, "content": content})
        entry["turns"] = entry["turns"][-self._max_turns:]

    def get(self, sid: str | None) -> list[dict]:
        if not sid or sid not in self._data:
            return []
        entry = self._data[sid]
        if self._now() - entry["ts"] > self._ttl:
            del self._data[sid]
            return []
        return list(entry["turns"])

store = SessionStore()
