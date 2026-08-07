"""Simple file-based cache for API responses to manage rate limits."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path


class NewsCache:
    """File-based cache for News API results. Stores per-card, expires after 24 hours."""

    CACHE_DIR = Path(__file__).parent.parent / ".cache"
    CACHE_FILE = CACHE_DIR / "news_cache.json"
    EXPIRY_HOURS = 24

    @classmethod
    def _ensure_cache_dir(cls) -> None:
        """Create cache directory if it doesn't exist."""
        cls.CACHE_DIR.mkdir(exist_ok=True)

    @classmethod
    def _load_cache(cls) -> dict:
        """Load cache from disk. Return empty dict if file doesn't exist."""
        cls._ensure_cache_dir()
        if not cls.CACHE_FILE.exists():
            return {}
        try:
            with open(cls.CACHE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    @classmethod
    def _save_cache(cls, cache_data: dict) -> None:
        """Save cache to disk."""
        cls._ensure_cache_dir()
        try:
            with open(cls.CACHE_FILE, "w") as f:
                json.dump(cache_data, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save cache: {e}")

    @classmethod
    def get(cls, card_id: int) -> list[dict] | None:
        """Get cached news for card_id. Return None if expired or not found."""
        cache_data = cls._load_cache()

        key = str(card_id)
        if key not in cache_data:
            return None

        entry = cache_data[key]
        timestamp_str = entry.get("timestamp")

        if not timestamp_str:
            return None

        # Check if cache is expired
        try:
            cached_time = datetime.fromisoformat(timestamp_str)
            age = datetime.now() - cached_time

            if age > timedelta(hours=cls.EXPIRY_HOURS):
                # Cache expired, delete it
                del cache_data[key]
                cls._save_cache(cache_data)
                return None

            return entry.get("articles", [])
        except (ValueError, TypeError):
            return None

    @classmethod
    def set(cls, card_id: int, articles: list[dict]) -> None:
        """Cache news articles for card_id."""
        cache_data = cls._load_cache()

        cache_data[str(card_id)] = {
            "timestamp": datetime.now().isoformat(),
            "articles": articles,
        }

        cls._save_cache(cache_data)

    @classmethod
    def clear(cls) -> None:
        """Clear all cached data."""
        cls._ensure_cache_dir()
        if cls.CACHE_FILE.exists():
            cls.CACHE_FILE.unlink()
