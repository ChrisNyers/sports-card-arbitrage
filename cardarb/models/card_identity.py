"""Canonical card identity schema for matching and comparison.

A card identity represents a unique, verifiable card definition that can be
used to match the same card across different markets (eBay, PWCC, etc.).

Every card identity must reach confidence > 0.95 before using it for price
comparison or recommendation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class CardIdentity:
    """Complete card definition with confidence scoring."""

    # === Sport & Player ===
    sport: str  # "football", "baseball", "basketball", "hockey"
    player_name: str
    year: int  # Issue year
    manufacturer: str  # "Panini", "Topps", "Upper Deck", etc.
    product: str  # "Donruss", "Prizm", "Bowman", etc.
    card_number: str = ""  # Card number within set

    # === Optional Player Info ===
    player_birth_date: Optional[datetime] = None
    player_position: Optional[str] = None
    player_id: Optional[str] = None  # External ID (nfl.com, mlb.com, etc.)

    # === Optional Card Details ===
    product_type: str = "Base"  # "Base", "Hobby", "Retail", etc.
    set_name: str = ""  # Specific set within product

    # === Variants & Special Versions ===
    parallel: Optional[str] = None  # "Chrome", "Numbered", "Gold", etc.
    parallel_count: Optional[int] = None  # /999, /50, etc.
    variation: Optional[str] = None  # "Photo variation", "Error card", etc.
    is_rookie: bool = False  # Rookie card designation
    is_autograph: bool = False  # Signed card
    autograph_type: Optional[str] = None  # "On-card", "Sticker", "Cut"
    is_relic: bool = False  # Game-worn, jersey, patch
    relic_type: Optional[str] = None  # "Jersey", "Patch", "Bat", etc.

    # === Grading (if graded) ===
    grading_company: Optional[str] = None  # "PSA", "BGS", "SGC", "CGC"
    grade: Optional[float] = None  # 1.0-10.0
    grade_qualifiers: list[str] = field(default_factory=list)  # "OC", "MC", etc.
    cert_number: Optional[str] = None  # Certification number

    # === Status ===
    is_raw: bool = True  # True if ungraded
    is_graded: bool = False  # True if graded

    # === Identity Confidence ===
    identity_confidence: float = 0.0  # 0.0-1.0
    confidence_notes: str = ""  # Why confident/uncertain?
    confidence_factors: dict = field(default_factory=dict)  # Component confidences
    last_verified: datetime = field(default_factory=datetime.now)

    # === Image Verification ===
    image_fingerprint: Optional[str] = None  # Hash for duplicate detection
    image_urls: list[str] = field(default_factory=list)  # Source images

    # === Metadata ===
    language: str = "English"
    country_of_origin: str = "USA"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def is_valid(self) -> bool:
        """Can this identity be used for price comparison?"""
        return self.identity_confidence > 0.95

    def is_graded_card(self) -> bool:
        """Is this card graded?"""
        return self.is_graded and self.grading_company is not None

    def canonical_key(self) -> str:
        """Generate a deterministic key for this card for matching."""
        parts = [
            self.sport.lower(),
            self.player_name.lower().replace(" ", "_"),
            str(self.year),
            self.manufacturer.lower().replace(" ", "_"),
            self.product.lower().replace(" ", "_"),
            self.set_name.lower().replace(" ", "_") or "default",
            self.card_number or "unknown",
            self.parallel or "base",
            str(self.grade) if self.is_graded else "raw",
        ]
        return "|".join(parts)

    def short_description(self) -> str:
        """Human-readable card description."""
        parts = []

        # Player + position
        player_info = self.player_name
        if self.player_position:
            player_info += f" ({self.player_position})"
        parts.append(player_info)

        # Year + product
        card_info = f"{self.year} {self.manufacturer} {self.product}"
        if self.set_name:
            card_info += f" {self.set_name}"
        parts.append(card_info)

        # Card number
        if self.card_number:
            parts.append(f"#{self.card_number}")

        # Special attributes
        attributes = []
        if self.is_rookie:
            attributes.append("RC")
        if self.is_autograph:
            attributes.append("Auto")
        if self.is_relic:
            attributes.append(f"Relic ({self.relic_type})")
        if self.parallel and self.parallel != "Base":
            attributes.append(self.parallel)
        if self.parallel_count:
            attributes.append(f"/{self.parallel_count}")

        if attributes:
            parts.append(" ".join(attributes))

        # Grade
        if self.is_graded:
            grade_str = f"{self.grading_company} {self.grade}"
            if self.grade_qualifiers:
                grade_str += f" {','.join(self.grade_qualifiers)}"
            parts.append(grade_str)

        return " - ".join(parts)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "sport": self.sport,
            "player_name": self.player_name,
            "player_birth_date": self.player_birth_date.isoformat() if self.player_birth_date else None,
            "player_position": self.player_position,
            "player_id": self.player_id,
            "year": self.year,
            "manufacturer": self.manufacturer,
            "product": self.product,
            "product_type": self.product_type,
            "set_name": self.set_name,
            "card_number": self.card_number,
            "parallel": self.parallel,
            "parallel_count": self.parallel_count,
            "variation": self.variation,
            "is_rookie": self.is_rookie,
            "is_autograph": self.is_autograph,
            "autograph_type": self.autograph_type,
            "is_relic": self.is_relic,
            "relic_type": self.relic_type,
            "grading_company": self.grading_company,
            "grade": self.grade,
            "grade_qualifiers": self.grade_qualifiers,
            "cert_number": self.cert_number,
            "is_raw": self.is_raw,
            "is_graded": self.is_graded,
            "identity_confidence": self.identity_confidence,
            "confidence_notes": self.confidence_notes,
            "confidence_factors": self.confidence_factors,
            "last_verified": self.last_verified.isoformat(),
            "image_fingerprint": self.image_fingerprint,
            "image_urls": self.image_urls,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @staticmethod
    def from_dict(data: dict) -> CardIdentity:
        """Create CardIdentity from dictionary."""
        # Convert ISO datetime strings back to datetime
        if isinstance(data.get("player_birth_date"), str):
            data["player_birth_date"] = datetime.fromisoformat(data["player_birth_date"])
        if isinstance(data.get("last_verified"), str):
            data["last_verified"] = datetime.fromisoformat(data["last_verified"])
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("updated_at"), str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        return CardIdentity(**data)


@dataclass
class CardIdentityMatcher:
    """Matches cards across listings to determine if they're the same."""

    required_fields = ["sport", "player_name", "year", "manufacturer", "product", "card_number"]
    optional_fields = ["grade", "parallel", "cert_number", "grading_company"]

    @staticmethod
    def match_confidence(card1: CardIdentity, card2: CardIdentity, verbose: bool = False) -> tuple[float, dict]:
        """Calculate confidence that two cards are identical.

        Returns:
            (confidence: 0.0-1.0, factors: dict of component scores)
        """
        factors = {}
        weights = {}

        # Required field checks (each worth 12.5% = 7 fields * 1/7)
        for field_name in CardIdentityMatcher.required_fields:
            val1 = getattr(card1, field_name, None)
            val2 = getattr(card2, field_name, None)

            if field_name == "player_name":
                # Fuzzy match on player name (allowing minor variations)
                match = _fuzzy_match(val1, val2)
            elif field_name == "grade":
                # Allow ±0.5 grade difference
                match = (
                    isinstance(val1, (int, float))
                    and isinstance(val2, (int, float))
                    and abs(val1 - val2) <= 0.5
                )
            else:
                # Exact match
                match = str(val1).lower() == str(val2).lower()

            factor_score = 1.0 if match else 0.0
            factors[field_name] = factor_score
            weights[field_name] = 1.0 / len(CardIdentityMatcher.required_fields)

        # Optional field checks (each worth up to 5% = 4 fields * 1/20)
        for field_name in CardIdentityMatcher.optional_fields:
            val1 = getattr(card1, field_name, None)
            val2 = getattr(card2, field_name, None)

            # If either is None, don't penalize
            if val1 is None or val2 is None:
                factor_score = 1.0
            else:
                factor_score = 1.0 if str(val1).lower() == str(val2).lower() else 0.0

            factors[field_name] = factor_score
            weights[field_name] = 1.0 / 20.0  # Up to 5% bonus

        # Calculate weighted confidence
        confidence = sum(factors.get(field, 0.0) * weights.get(field, 0.0) for field in factors.keys())

        if verbose:
            print(f"\nCard Match Analysis:")
            print(f"  {card1.short_description()}")
            print(f"  vs")
            print(f"  {card2.short_description()}")
            print(f"\nComponent Scores:")
            for field_name in sorted(factors.keys()):
                print(f"  {field_name}: {factors[field_name]:.0%}")
            print(f"\nOverall Confidence: {confidence:.1%}")

        return confidence, factors

    @staticmethod
    def should_compare_prices(card: CardIdentity) -> tuple[bool, str]:
        """Determine if this card's identity is certain enough for price comparison.

        Returns:
            (can_compare: bool, reason: str)
        """
        if card.identity_confidence < 0.70:
            return False, "Identity confidence too low (<70%)"
        elif card.identity_confidence < 0.85:
            return False, "Identity confidence moderate (70-85%), requires manual review"
        elif card.identity_confidence < 0.95:
            return False, "Identity confidence good (85-95%), need more data"
        elif card.identity_confidence >= 0.95:
            return True, "Identity confidence high (>95%), safe for price comparison"

        return False, "Unknown confidence state"


def _fuzzy_match(s1: str, s2: str, threshold: float = 0.85) -> bool:
    """Simple fuzzy string matching for player names.

    Allows for:
    - Case differences
    - Minor spelling variations
    - Middle name variations
    """
    if not s1 or not s2:
        return False

    s1 = s1.lower().strip()
    s2 = s2.lower().strip()

    # Exact match
    if s1 == s2:
        return True

    # Split by space and check if major components match
    parts1 = s1.split()
    parts2 = s2.split()

    # If first and last names match, consider it a match
    if len(parts1) > 0 and len(parts2) > 0:
        if parts1[0] == parts2[0] and parts1[-1] == parts2[-1]:
            return True

    # Levenshtein distance (simple implementation)
    # If strings are very similar, accept them
    similarity = _levenshtein_similarity(s1, s2)
    return similarity >= threshold


def _levenshtein_similarity(s1: str, s2: str) -> float:
    """Calculate similarity as 1 - (distance / max_length)."""
    if not s1 or not s2:
        return 0.0

    distance = _levenshtein_distance(s1, s2)
    max_len = max(len(s1), len(s2))
    return 1.0 - (distance / max_len)


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


if __name__ == "__main__":
    # Example usage
    card1 = CardIdentity(
        sport="football",
        player_name="Patrick Mahomes",
        player_position="QB",
        year=2020,
        manufacturer="Panini",
        product="Donruss",
        product_type="Hobby",
        set_name="Donruss",
        card_number="201",
        parallel="Red",
        parallel_count=100,
        grading_company="PSA",
        grade=8.0,
        is_graded=True,
        identity_confidence=0.98,
        confidence_notes="Exact match on all fields + cert number verified",
    )

    card2 = CardIdentity(
        sport="football",
        player_name="Pat Mahomes",
        player_position="QB",
        year=2020,
        manufacturer="Panini",
        product="Donruss",
        product_type="Hobby",
        set_name="Donruss",
        card_number="201",
        parallel="Red",
        parallel_count=100,
        grading_company="PSA",
        grade=8.0,
        is_graded=True,
        identity_confidence=0.92,
        confidence_notes="Slight name variation, otherwise exact",
    )

    # Test matching
    confidence, factors = CardIdentityMatcher.match_confidence(card1, card2, verbose=True)

    # Test validation
    can_compare, reason = CardIdentityMatcher.should_compare_prices(card1)
    print(f"\nCard1 can compare prices: {can_compare} ({reason})")

    can_compare, reason = CardIdentityMatcher.should_compare_prices(card2)
    print(f"Card2 can compare prices: {can_compare} ({reason})")

    # Test description
    print(f"\n{card1.short_description()}")
    print(f"\n{card2.short_description()}")
