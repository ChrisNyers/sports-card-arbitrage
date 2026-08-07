"""V1.1 Strategy Modules

Five distinct strategies for sports card arbitrage:
1. CrossMarketStrategy - Buy at market A, sell at market B
2. AuctionToFixedStrategy - Buy at auction, sell at fixed-price
3. RelativeValueStrategy - Identify underpriced vs comparables
4. RawToGradedStrategy - Buy raw, grade, sell graded
5. EventDrivenStrategy - Trade on news/events (secondary)
"""

from .cross_market import CrossMarketStrategy
from .relative_value import RelativeValueStrategy

__all__ = [
    "CrossMarketStrategy",
    "RelativeValueStrategy",
]
