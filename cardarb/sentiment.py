"""Advanced sentiment encoding for sports news and events.

Replaces simple keyword counting with severity-weighted, context-aware scoring.
Features:
- Severity-weighted rules (-1.0 worst to +1.0 best)
- Context awareness (trade destination, injury prognosis)
- Source credibility weighting
- Recency decay (fresh news weighted higher)
- Injury timeline extraction
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional


@dataclass
class SentimentScore:
    """Detailed sentiment analysis result."""

    overall_score: float  # -1.0 to +1.0
    event_type: str  # "injury", "trade", "milestone", etc.
    severity: float  # Raw severity before weighting
    confidence: float  # 0.0 to 1.0 (how confident in this score)
    keywords_matched: list[str]  # What triggered the score
    reasoning: str  # Human-readable explanation


class SentimentEncoder:
    """Advanced sentiment scoring with sport-specific rules.

    Features:
    - Severity-weighted injury classifications
    - Context-aware trade scoring
    - Source credibility multipliers
    - Recency decay (older news = lower weight)
    - Injury timeline extraction
    """

    # Source credibility weights (ESPN more reliable than blogs)
    SOURCE_WEIGHTS = {
        "espn": 1.0,
        "nba.com": 1.0,
        "nfl.com": 1.0,
        "mlb.com": 1.0,
        "athletic": 0.95,
        "yahoo": 0.85,
        "cbs": 0.85,
        "nbc": 0.85,
        "ap": 0.9,
        "reuters": 0.9,
        "default": 0.7,  # Unknown source
    }

    # Injury severity rules (NEGATIVE)
    INJURY_RULES = [
        # Career-ending injuries
        (r"\b(career-ending|career over|never play again|permanent|irreversible)\b", "injury", -1.0, "Career-ending"),
        (r"\b(torn ACL|ACL tear|major surgery|spinal|paralyz)\b", "injury", -0.95, "Severe injury"),

        # Season-ending injuries
        (r"\b(season-ending|out for season|rest of season|missed rest of season)\b", "injury", -0.75, "Season-ending"),
        (r"\b(6 months?|end of year|remainder of season)\b", "injury", -0.7, "Long-term"),

        # Significant injuries (4+ weeks)
        (r"\b(indefinitely|4-6 weeks?|multiple weeks?|extended absence)\b", "injury", -0.5, "Significant injury"),
        (r"\b(out (at least )?(\d+ weeks?)|sidelined (\d+ weeks?))\b", "injury", -0.45, "Multi-week injury"),

        # Moderate injuries (2-4 weeks)
        (r"\b(2-4 weeks?|several weeks?|mid-range)\b", "injury", -0.35, "Moderate injury"),

        # Minor/questionable (day-to-day to 1-2 weeks)
        (r"\b(day-to-day|daily check|probable|questionable)\b", "injury", -0.15, "Minor/questionable"),
        (r"\b(1-2 weeks?|week-to-week|week or two)\b", "injury", -0.25, "Short-term"),

        # Return news (POSITIVE - mitigates injury)
        (r"\b(cleared to play|return|back|expected to return|targeting return|hopeful)\b", "injury", +0.3, "Return imminent"),
        (r"\b(returns? (this week|next week|soon)|heading back)\b", "injury", +0.4, "Confirmed return"),
    ]

    # Trade rules (MIXED - depends on destination)
    TRADE_RULES = [
        # Positive trades (to contenders, upgrades)
        (r"\b(traded to|trade deadline|traded .{0,50}(contender|champion|playoff team|leader))\b", "trade", +0.6, "Traded to strong team"),
        (r"\b(trade .{0,50}(championship contender|title chase|playoff race))\b", "trade", +0.65, "Championship pursuit"),
        (r"\b(reunited with|joining|stars|superstar)\b", "trade", +0.5, "Star power move"),

        # Negative trades (to rebuilding/worse teams)
        (r"\b(trade .{0,50}(rebuilding|tanking|last place|struggling))\b", "trade", -0.4, "Traded to weak team"),
        (r"\b(waived|claimed off waivers|minor league)\b", "trade", -0.5, "Demotion"),
        (r"\b(released|let go|cut|unconditional)\b", "trade", -0.8, "Release/cut"),

        # Neutral trades
        (r"\b(traded|trade agreement|swap|exchange)\b", "trade", +0.1, "Neutral trade"),
    ]

    # Milestone/achievement rules (POSITIVE)
    MILESTONE_RULES = [
        # Historic achievements
        (r"\b(1000th (career |)(point|assist|rebound|hit|home run)|first .{0,30}(1000))\b", "milestone", +0.85, "Career 1000 milestone"),
        (r"\b(Hall of Fame|HoF|immortal|greatest|all-time)\b", "milestone", +0.9, "Hall of Fame level"),

        # Season/career records
        (r"\b(season (high|record)|career (high|record|best))\b", "milestone", +0.7, "Personal record"),
        (r"\b(tied the record|broke the record|new mark)\b", "milestone", +0.75, "Record breaker"),

        # Consecutive achievements
        (r"\b(consecutive (double-double|triple-double|games?)|streak).*(\d{2,})\b", "milestone", +0.65, "Impressive streak"),
        (r"\b(\d{2,}(th|st|nd|rd) (consecutive|in a row))\b", "milestone", +0.6, "Consecutive games"),

        # Award/recognition
        (r"\b(player of the week|player of the month|MVP|award|selected|named|honored)\b", "milestone", +0.7, "Award/honor"),

        # Contract extension (positive for player)
        (r"\b(signed (extension|new contract)|contract (extension|renewal))\b", "milestone", +0.65, "Contract reward"),
    ]

    # Performance rules (POSITIVE/NEGATIVE)
    PERFORMANCE_RULES = [
        # Elite performance
        (r"\b(leading the league|league leader|top scorer|elite|dominant|unstoppable)\b", "performance", +0.75, "Elite performance"),
        (r"\b(MVP-caliber|all-star caliber|superstar form)\b", "performance", +0.8, "Superstar form"),

        # Strong performance
        (r"\b(career year|breakout|emerging|star|standout|impressive)\b", "performance", +0.6, "Strong performance"),
        (r"\b(double-double|triple-double|historic night)\b", "performance", +0.7, "Great game"),

        # Decline/poor performance
        (r"\b(decline|slump|struggles|underperform|regression|decline)\b", "performance", -0.5, "Performance decline"),
        (r"\b(bench|benched|loses starting spot|demoted|relegated)\b", "performance", -0.55, "Loss of playing time"),

        # Injury-related performance drop
        (r"\b(playing through pain|hobbled|compromised)\b", "performance", -0.3, "Playing injured"),
    ]

    # Miscellaneous context
    CONTEXT_RULES = [
        # Positive context
        (r"\b(breakthrough|promising|potential|upside|undervalued)\b", "context", +0.25, "Positive context"),
        (r"\b(league interest|bidding war|high demand)\b", "context", +0.35, "High demand signal"),

        # Negative context
        (r"\b(concerns|worried|uncertain|risky|red flag)\b", "context", -0.25, "Negative context"),
        (r"\b(controversy|suspended|investigation|charges)\b", "context", -0.6, "Legal/conduct issue"),
    ]

    # All rules combined
    ALL_RULES = INJURY_RULES + TRADE_RULES + MILESTONE_RULES + PERFORMANCE_RULES + CONTEXT_RULES

    @classmethod
    def _extract_injury_timeline(cls, text: str) -> tuple[str, int]:
        """Extract injury timeline from text.

        Returns: (timeline_type, days_estimated)
        Examples: ("career-ending", 10000), ("week-to-week", 7), ("day-to-day", 1)
        """
        text_lower = text.lower()

        # Career-ending
        if re.search(r"\b(career-ending|career over|never return)\b", text_lower):
            return "career-ending", 10000

        # Season-ending
        if re.search(r"\b(season-ending|out for season|rest of season)\b", text_lower):
            return "season-ending", 180  # Estimate rest of season

        # Extract specific timeline (e.g., "4-6 weeks")
        match = re.search(r"(\d+)[-–](\d+)\s*(weeks?|days?|months?)", text_lower)
        if match:
            num1, num2, unit = int(match.group(1)), int(match.group(2)), match.group(3).lower()
            avg = (num1 + num2) / 2
            if "week" in unit:
                return f"{num1}-{num2} weeks", int(avg * 7)
            elif "month" in unit:
                return f"{num1}-{num2} months", int(avg * 30)
            elif "day" in unit:
                return f"{num1}-{num2} days", int(avg)

        # Single number timeline
        match = re.search(r"(\d+)\s*(weeks?|days?|months?)", text_lower)
        if match:
            num, unit = int(match.group(1)), match.group(2).lower()
            if "week" in unit:
                return f"{num} weeks", num * 7
            elif "month" in unit:
                return f"{num} months", num * 30
            elif "day" in unit:
                return f"{num} days", num

        # No specific timeline
        return "unknown", 0

    @classmethod
    def _apply_recency_decay(cls, score: float, published_at: datetime) -> float:
        """Apply recency decay: fresher news scores higher.

        Fresh (< 2 hours): 1.0x weight
        Recent (2-6 hours): 0.9x weight
        Stale (6-24 hours): 0.7x weight
        Old (24+ hours): 0.5x weight
        """
        now = datetime.now()
        age_hours = (now - published_at).total_seconds() / 3600

        if age_hours < 2:
            decay_factor = 1.0
        elif age_hours < 6:
            decay_factor = 0.9
        elif age_hours < 24:
            decay_factor = 0.7
        else:
            decay_factor = 0.5

        # Adjust score toward neutral (0.5) based on age
        decayed = 0.5 + (score - 0.5) * decay_factor
        return round(decayed, 2)

    @classmethod
    def _get_source_weight(cls, source_text: str) -> float:
        """Get credibility weight for news source."""
        source_lower = source_text.lower() if source_text else ""

        for source_key, weight in cls.SOURCE_WEIGHTS.items():
            if source_key in source_lower:
                return weight

        return cls.SOURCE_WEIGHTS["default"]

    @classmethod
    def score_text(
        cls,
        headline: str,
        description: str = "",
        event_type: Optional[str] = None,
        published_at: Optional[datetime] = None,
        source: Optional[str] = None,
    ) -> SentimentScore:
        """Score sentiment of news headline + description.

        Args:
            headline: Article title
            description: Article description/excerpt
            event_type: Optional hint about event type (injury, trade, etc.)
            published_at: Article publication timestamp (for recency decay)
            source: News source (for credibility weighting)

        Returns:
            SentimentScore with overall score (-1.0 to +1.0) and details
        """
        text = f"{headline} {description}".lower()
        matched_keywords = []
        scores = []
        event_types = []

        # Check all rules
        for pattern, etype, severity, reason in cls.ALL_RULES:
            if re.search(pattern, text):
                matched_keywords.append(reason)
                scores.append(severity)
                event_types.append(etype)

        if not scores:
            # No match - neutral
            return SentimentScore(
                overall_score=0.5,
                event_type="neutral",
                severity=0.0,
                confidence=0.3,
                keywords_matched=[],
                reasoning="No strong signals detected",
            )

        # Calculate weighted score
        overall_score = sum(scores) / len(scores)  # Average severity

        # Clamp to -1.0 to +1.0, then normalize to 0.1 to 0.9 for compatibility
        overall_score = max(-1.0, min(1.0, overall_score))
        normalized_score = 0.5 + (overall_score * 0.4)  # Map [-1, +1] to [0.1, 0.9]

        # Apply recency decay if we have publication time
        if published_at:
            normalized_score = cls._apply_recency_decay(normalized_score, published_at)

        # Apply source credibility weighting
        if source:
            source_weight = cls._get_source_weight(source)
            normalized_score = 0.5 + (normalized_score - 0.5) * source_weight

        # Determine confidence (more matches = more confident)
        confidence = min(0.95, 0.5 + (len(scores) * 0.1))

        # Pick most specific event type
        primary_event_type = event_types[scores.index(max(scores, key=abs))] if scores else "neutral"

        # Extract injury timeline if applicable
        timeline_info = ""
        if primary_event_type == "injury":
            timeline_type, days = cls._extract_injury_timeline(text)
            if timeline_type != "unknown":
                timeline_info = f" ({timeline_type})"

        return SentimentScore(
            overall_score=round(normalized_score, 2),
            event_type=primary_event_type,
            severity=round(overall_score, 2),
            confidence=round(confidence, 2),
            keywords_matched=matched_keywords[:3],  # Top 3 matches
            reasoning=f"{primary_event_type.title()}: {', '.join(matched_keywords[:2])}{timeline_info}",
        )

    @classmethod
    def score_event(cls, event_type: str, detail: Optional[str] = None, severity: Optional[str] = None) -> float:
        """Score event based on type + details.

        For events that have already been classified (from EventDetector).
        Returns a single sentiment score (-1.0 to +1.0).
        """
        text = f"{event_type} {detail or ''} {severity or ''}".lower()

        # Find matching rule for this event
        for pattern, etype, rule_severity, _ in cls.ALL_RULES:
            if etype == event_type and re.search(pattern, text):
                # Found a rule for this event
                normalized = 0.5 + (rule_severity * 0.4)
                return round(normalized, 2)

        # Default scoring by event type
        defaults = {
            "injury": 0.2,  # Negative
            "trade": 0.5,  # Neutral (depends on destination)
            "milestone": 0.8,  # Positive
            "performance": 0.6,  # Positive lean
            "season": 0.6,  # Positive
            "draft": 0.7,  # Positive
        }

        return defaults.get(event_type, 0.5)


# Example usage
if __name__ == "__main__":
    test_cases = [
        ("Star player ruled out for season", "Torn ACL, career at risk"),
        ("Player traded to championship contender", "Blockbuster trade"),
        ("Day-to-day with ankle concern", "Expected to play"),
        ("Breaks franchise record in career night", "27 points, 11 assists"),
        ("Benched after poor performance", "Coach loses confidence"),
    ]

    for headline, description in test_cases:
        result = SentimentEncoder.score_text(headline, description)
        print(f"\n📰 {headline}")
        print(f"   Score: {result.overall_score} | Event: {result.event_type} | Confidence: {result.confidence}")
        print(f"   Reasoning: {result.reasoning}")
        print(f"   Matched: {result.keywords_matched}")
