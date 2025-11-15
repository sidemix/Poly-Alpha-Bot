from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

from ..models import Market, Opportunity


@dataclass
class ScoredOpportunity:
    """
    A wrapper that couples an Opportunity with a numeric score
    so the scanner can rank and sort results across strategies.
    """
    opportunity: Opportunity
    score: float


class BaseStrategy:
    """
    Base class for all Polymarket BTC strategies.

    Subclasses should override `score(self, market, ref_price)` and
    return a list of ScoredOpportunity objects (possibly empty).
    """

    def __init__(self, cfg: Any, name: str | None = None) -> None:
        # cfg is your global Config object (or similar)
        self.cfg = cfg
        # If no explicit name is passed, default to the class name
        self.name = name or self.__class__.__name__

    def score(self, market: Market, ref_price: float) -> List[ScoredOpportunity]:
        """
        Evaluate a single market against the strategy.

        :param market: Parsed Market instance
        :param ref_price: Reference BTC price (spot or index)
        :return: A list of ScoredOpportunity instances
        """
        raise NotImplementedError("Subclasses must implement `score`")
