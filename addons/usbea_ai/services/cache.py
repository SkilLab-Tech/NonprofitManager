"""In-process prompt cache for the AI router.

Cache key is SHA256 over (system_prompt + first N tokens of user prompt).
TTL defaults to 5 minutes to align with Anthropic's prompt-cache window.

For multi-worker Odoo deployments, this cache is per-worker (not shared).
That is acceptable because:
- Anthropic's prompt-cache itself provides cross-worker dedup at the API layer
- Local cache only saves the request round-trip; cache-hit logging still occurs
- A shared (Redis) cache can be wired in later by swapping this class out
"""

from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import dataclass


@dataclass
class CacheEntry:
    response: str
    created_at: float
    hits: int = 0


class PromptCache:
    """Thread-safe LRU-ish TTL cache.

    Not a perfect LRU — we evict on TTL expiry first, then by oldest when full.
    For an Odoo worker with bounded concurrent users this is sufficient.
    """

    def __init__(self, ttl_seconds: int = 300, max_entries: int = 256):
        self._ttl = ttl_seconds
        self._max = max_entries
        self._store: dict[str, CacheEntry] = {}
        self._lock = threading.RLock()

    @staticmethod
    def make_key(system_prompt: str, user_prompt: str, model: str) -> str:
        """Build a stable cache key.

        We include the model in the key so two different models don't share
        responses (haiku vs opus behavior differs).
        """
        h = hashlib.sha256()
        h.update(model.encode("utf-8"))
        h.update(b"\x00")
        h.update(system_prompt.encode("utf-8"))
        h.update(b"\x00")
        h.update(user_prompt.encode("utf-8"))
        return h.hexdigest()

    def get(self, key: str) -> str | None:
        """Return cached response or None if absent/expired."""
        now = time.monotonic()
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if now - entry.created_at > self._ttl:
                self._store.pop(key, None)
                return None
            entry.hits += 1
            return entry.response

    def set(self, key: str, response: str) -> None:
        """Insert a response into the cache, evicting oldest if at capacity."""
        with self._lock:
            if len(self._store) >= self._max:
                # Evict oldest by created_at — O(n) but n is bounded by max_entries.
                oldest_key = min(
                    self._store, key=lambda k: self._store[k].created_at,
                )
                self._store.pop(oldest_key, None)
            self._store[key] = CacheEntry(
                response=response, created_at=time.monotonic(),
            )

    def stats(self) -> dict:
        """Snapshot of cache state for observability."""
        with self._lock:
            total_hits = sum(e.hits for e in self._store.values())
            return {
                "entries": len(self._store),
                "max_entries": self._max,
                "ttl_seconds": self._ttl,
                "total_hits": total_hits,
            }

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
