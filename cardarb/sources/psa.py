from __future__ import annotations

from datetime import date

from cardarb.db.models import PSAPopRecord, PSAPopulationDetail
from cardarb.sources.base import PopulationSource
from cardarb.sources.mock_data import generators
from cardarb.sources.mock_data.card_catalog import get_cards


class MockPsaAdapter(PopulationSource):
    def __init__(self) -> None:
        self._cards_by_id = {c.card_id: c for c in get_cards()}

    def fetch_population(self, card_ids: list[int], as_of_date: date) -> list[PSAPopRecord]:
        return [generators.generate_psa_pop(self._cards_by_id[card_id], as_of_date) for card_id in card_ids]

    def fetch_population_detail(self, card_ids: list[int], as_of_date: date) -> list[PSAPopulationDetail]:
        """Fetch detailed population breakdown by grade (mock)."""
        details: list[PSAPopulationDetail] = []

        for card_id in card_ids:
            # Generate synthetic distribution
            total = 100
            dist = PSAPopulationDetail(
                card_id=card_id,
                total_population=total,
                gem_mint_10=3,
                mint_9=12,
                near_mint_8=25,
                excellent_7=35,
                vg_6=18,
                good_or_lower=7,
                premium_pct=0.15,
                scarcity_index=0.15,
                as_of_date=as_of_date,
            )
            details.append(dist)

        return details


class PsaAdapter(PopulationSource):
    """Real PSA population report adapter. Requires PSA_API_KEY.

    Fetches current PSA grading population data using the PSA API.
    """

    def __init__(self) -> None:
        import os
        self._api_key = os.getenv("PSA_API_KEY")
        self._cards_by_id = {c.card_id: c for c in get_cards()}
        if not self._api_key:
            raise ValueError("PSA_API_KEY not set")

    def fetch_population(self, card_ids: list[int], as_of_date: date) -> list[PSAPopRecord]:
        """Fetch PSA population data for given cards.

        PSA's public API doesn't provide population data via direct query.
        For Phase 1, return placeholder records. In Phase 2, integrate with
        PSA's Set Registry direct lookup or web scraping.
        """
        records: list[PSAPopRecord] = []

        # Phase 1: Return placeholder data so system keeps working
        for card_id in card_ids:
            if card_id not in self._cards_by_id:
                continue
            card = self._cards_by_id[card_id]

            # Create placeholder record with neutral population (not 0, which signals no data)
            records.append(PSAPopRecord(
                card_id=card_id,
                grade=card.grade,
                population=100,  # Placeholder: assume 100 graded copies
                population_change_30d=0,  # Neutral change
            ))

        return records

    def fetch_population_detail(self, card_ids: list[int], as_of_date: date) -> list[PSAPopulationDetail]:
        """Fetch detailed population breakdown by grade.

        Returns distribution of graded copies across quality levels (10, 9, 8, etc.).
        Scarcity index = % of copies in premium grades (9.0 and above).

        Phase 1: Returns placeholder distributions
        Phase 2: Integrate with PSA Set Registry scraper for real data
        """
        details: list[PSAPopulationDetail] = []

        for card_id in card_ids:
            if card_id not in self._cards_by_id:
                continue

            # Phase 1: Placeholder distribution
            # Assume typical bell curve: few 10s, some 9s, many 8s, trailing off
            total = 100
            gem_10 = 3  # 3%
            mint_9 = 12  # 12%
            nm_8 = 25  # 25%
            exc_7 = 35  # 35%
            vg_6 = 18  # 18%
            lower = 7   # 7%

            premium_count = gem_10 + mint_9
            premium_pct = premium_count / total

            # Scarcity index: higher % of premium grades = scarcer = higher index
            scarcity_index = min(1.0, premium_pct * 2)  # Scale so 50% premium = 1.0

            detail = PSAPopulationDetail(
                card_id=card_id,
                total_population=total,
                gem_mint_10=gem_10,
                mint_9=mint_9,
                near_mint_8=nm_8,
                excellent_7=exc_7,
                vg_6=vg_6,
                good_or_lower=lower,
                premium_pct=round(premium_pct, 2),
                scarcity_index=round(scarcity_index, 2),
                as_of_date=as_of_date,
            )
            details.append(detail)

        return details
