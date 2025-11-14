"""
Base class for trading strategies used by the Polymarket scanner.

Right now this is intentionally very minimal — it just gives BTCIntraday
(and any future strategies) a common parent type and a few helper hooks
the scanner *might* call.
"""

from __future__ import annotations

from typing import List, Optional
from ..models import Market, Opportunity


class BaseStrategy:
    """
    Base class for all strategies.

    You can extend this later with shared helpers (logging, filters,
    risk constraints, etc.) without touching the scanner.
    """

    # Human-readable name for logs / Discord, etc.
    name: str = "base-strategy"

    def filter_markets(self, markets: List[Market]) -> List[Market]:
        """
        Optional pre-filter hook.

        Default: return markets unchanged.
        If a strategy wants to only look at BTC markets, or only sports,
        it can override this.
        """
        return markets

    def score(self, market: Market, ref_price: float) -> Optional[Opportunity]:
        """
        Main scoring interface.

        Strategy should return:
        - an Opportunity instance when the market looks interesting, OR
        - None if this market should be ignored.

        This is meant to be overridden by concrete strategies like
        BTCIntraday.
        """
        raise NotImplementedError("score() must be implemented by strategy subclasses")
