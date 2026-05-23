"""Unit tests for the in-process prompt cache."""

from __future__ import annotations

import time

from services.cache import PromptCache


class TestPromptCache:
    def test_miss_returns_none(self):
        cache = PromptCache()
        key = PromptCache.make_key("sys", "user", "claude-sonnet-4-6")
        assert cache.get(key) is None

    def test_set_then_get_returns_value(self):
        cache = PromptCache()
        key = PromptCache.make_key("sys", "user", "claude-sonnet-4-6")
        cache.set(key, "the response")
        assert cache.get(key) == "the response"

    def test_make_key_is_deterministic(self):
        k1 = PromptCache.make_key("sys", "user", "claude-sonnet-4-6")
        k2 = PromptCache.make_key("sys", "user", "claude-sonnet-4-6")
        assert k1 == k2

    def test_make_key_differs_with_different_model(self):
        k1 = PromptCache.make_key("sys", "user", "claude-sonnet-4-6")
        k2 = PromptCache.make_key("sys", "user", "claude-opus-4-7")
        assert k1 != k2

    def test_make_key_differs_with_different_system_prompt(self):
        k1 = PromptCache.make_key("sys A", "user", "claude-sonnet-4-6")
        k2 = PromptCache.make_key("sys B", "user", "claude-sonnet-4-6")
        assert k1 != k2

    def test_make_key_avoids_separator_collision(self):
        # Concatenation without delimiter could collide:
        # ("ab", "cd") and ("a", "bcd") must hash differently.
        k1 = PromptCache.make_key("ab", "cd", "m")
        k2 = PromptCache.make_key("a", "bcd", "m")
        assert k1 != k2

    def test_ttl_expiry(self):
        cache = PromptCache(ttl_seconds=0)  # immediate expiry
        key = PromptCache.make_key("s", "u", "m")
        cache.set(key, "response")
        # Sleep a hair so monotonic time advances past 0.
        time.sleep(0.01)
        assert cache.get(key) is None

    def test_eviction_at_max_capacity(self):
        cache = PromptCache(ttl_seconds=300, max_entries=2)
        # Fill cache
        k1 = PromptCache.make_key("s", "u1", "m")
        k2 = PromptCache.make_key("s", "u2", "m")
        cache.set(k1, "r1")
        # Force a slightly later created_at — use time.sleep so monotonic advances
        time.sleep(0.001)
        cache.set(k2, "r2")
        # Inserting a third entry should evict k1 (oldest)
        time.sleep(0.001)
        k3 = PromptCache.make_key("s", "u3", "m")
        cache.set(k3, "r3")
        assert cache.get(k1) is None  # evicted
        assert cache.get(k2) == "r2"
        assert cache.get(k3) == "r3"

    def test_stats_snapshot(self):
        cache = PromptCache(ttl_seconds=120, max_entries=10)
        k = PromptCache.make_key("s", "u", "m")
        cache.set(k, "r")
        cache.get(k)  # registers a hit
        stats = cache.stats()
        assert stats["entries"] == 1
        assert stats["max_entries"] == 10
        assert stats["ttl_seconds"] == 120
        assert stats["total_hits"] == 1

    def test_clear(self):
        cache = PromptCache()
        k = PromptCache.make_key("s", "u", "m")
        cache.set(k, "r")
        cache.clear()
        assert cache.get(k) is None
