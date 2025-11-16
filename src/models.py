from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Market:
    """
    Canonical Polymarket market representation used by all strategies.

    We keep this intentionally simple and robust against changing API shapes.
    """
    id: str
    slug: str
    title: str

    url: Optional[str] = None
    outcomes: List[str] = field(default_factory=list)

    volume: float = 0.0
    liquidity: float = 0.0

    end_date: Optional[str] = None
    resolved: bool = False

    raw: dict = field(default_factory=dict)  # full raw JSON for advanced logic

    def is_btc_market(self) -> bool:
        """
        Heuristic: does this market look like a BTC/Bitcoin market?
        We search title, slug, and url for 'btc' or 'bitcoin'.
        """
        text = f"{self.title} {self.slug}".lower()
        if self.url:
            text += " " + self.url.lower()
        return ("bitcoin" in text) or ("btc" in text)

    @property
    def debug_label(self) -> str:
        return f"{self.title} [{self.slug}]"


@dataclass
class Opportunity:
    """
    Base opportunity (unscored). ScoredOpportunity is defined in strategies.base.
    """
    market: Market
    outcome: str  # e.g. "Yes", "No", or specific outcome name
    side: str     # "YES" or "NO"
    yes_price: float
    no_price: float
    fair: float        # fair probability or fair yes-price
    edge: float        # e.g. (fair - price) or similar
    comment: str = ""  # free-form note for Discord messages, etc.
