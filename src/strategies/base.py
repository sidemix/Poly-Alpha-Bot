from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Union
from abc import ABC, abstractmethod

from ..models import Market, Opportunity


@dataclass
class ScoredOpportunity:
    """
    Wrapper tying a raw trading opportunity to a numeric score and
    strategy name, so the scanner can sort and display them.
    """
    opportunity: Opportunity
    score: float
    strategy: str  # e.g. "BTC Intraday" or "BTC Price Targets"


class BaseStrategy(ABC):
    """
    Common parent for all strategies.

    Each strategy:
      - gets a reference to the global config (cfg)
      - has a human-readable name
      - implements score(market, btc_price)
    """

    def __init__(self, cfg, name: str) -> None:
        self.cfg = cfg
        self.name = name

    @abstractmethod
    def score(
        self,
        market: Market,
        btc_price: float,
    ) -> Optional[ScoredOpportunity] | List[ScoredOpportunity]:
        """
        Inspect a single Polymarket market + current BTC price and decide
        whether there is a trade.

        Returns:
          - None  -> no trade
          - ScoredOpportunity  -> one trade
          - list[ScoredOpportunity] -> multiple related trades
        """
        raise NotImplementedError
