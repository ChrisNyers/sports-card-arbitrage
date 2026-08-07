"""Adapter interfaces. Each has a Mock implementation (used until real API
credentials are configured) and a Real implementation stub (raises
NotImplementedError with a pointer to what needs to be built).

These are read-only market-data interfaces only — no adapter here ever
places an order, lists an item, or moves money.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from cardarb.db.models import ListingRecord, NewsRecord, PSAPopRecord, SocialMentionRecord


class ListingsSource(ABC):
    @abstractmethod
    def fetch_listings(self, card_ids: list[int], as_of_date: date, lookback_days: int = 30) -> list[ListingRecord]:
        ...


class SocialSource(ABC):
    @abstractmethod
    def fetch_mentions(
        self, card_ids: list[int], as_of_date: date, lookback_days: int = 7
    ) -> list[SocialMentionRecord]:
        ...


class PopulationSource(ABC):
    @abstractmethod
    def fetch_population(self, card_ids: list[int], as_of_date: date) -> list[PSAPopRecord]:
        ...


class NewsSource(ABC):
    @abstractmethod
    def fetch_news(self, card_ids: list[int], as_of_date: date, lookback_days: int = 7) -> list[NewsRecord]:
        ...
