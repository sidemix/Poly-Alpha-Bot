from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

from ..models import Market, Opportunity


@dataclass
class ScoredOpportunity:
    """
    Wrapper for a single strategy recommendation on a given market.
    """
    market: Market
    opportunity: Opportunity
    score: float
    strategy: str


class BaseStrategy:
    """
    Base class for all Polymarket BTC strategies.

    Every strategy must implement:
      - score(market, btc_price) -> Optional[ScoredOpportunity]

    And gets for free:
      - score_many(markets, btc_price) -> List[ScoredOpportunity]
    """

    def __init__(self, cfg: Any, name: str) -> None:
        self.cfg = cfg
        self.name = name

    # ------------------------------------------------------------------ #
    # ABSTRACT PER-MARKET SCORING
    # ------------------------------------------------------------------ #

    def score(
        self,
        market: Market,
        btc_price: float,
    ) -> Optional[ScoredOpportunity]:
        """
        Evaluate a single market for edge.

        Must return:
          - ScoredOpportunity if the market is interesting
          - None if no trade should be taken
        """
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    # BATCH SCORING (USED BY Scanner)
    # ------------------------------------------------------------------ #

    def score_many(
        self,
        markets: List[Market],
        btc_price: float,
    ) -> List[ScoredOpportunity]:
        """
        Default batch implementation:
        - loops over markets
        - calls self.score(...)
        - catches per-market errors so one bad market doesn't kill the scan
        """
        results: List[ScoredOpportunity] = []

        for m in markets:
            try:
                scored = self.score(m, btc_price)
                if scored is not None:
                    results.append(scored)
            except Exception as e:
                mid = (
                    getattr(m, "id", None)
                    or getattr(m, "condition_id", None)
                    or "?"
                )
                print(f"[{self.name}] failed on market {mid}: {e}")

        return results
