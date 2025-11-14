# src/core/models.py

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class Market:
    """
    Normalized view of a Polymarket market used by scanners/strategies.

    All string-ish fields default to empty string "" so that calling `.lower()`
    or `.strip()` downstream is always safe.
    """

    id: str
    url: str = ""          # normalized to "" instead of None
    title: str = ""        # normalized to "" instead of None
    question: str = ""     # normalized to "" instead of None
    group: str = ""        # event/tournament/group name if available

    yes_price: Optional[float] = None
    no_price: Optional[float] = None

    # unix timestamp (seconds) for resolution / end time, if known
    end_ts: Optional[int] = None

    # arbitrary tags from API
    tags: List[str] = field(default_factory=list)


@dataclass
class WalletTrade:
    """
    Optional: normalized trade record (if you use it elsewhere).
    Safe defaults so you don't crash on missing fields.
    """
    tx_id: str
    wallet: str
    market_id: str
    outcome: str
    side: str             # "BUY" / "SELL"
    price: float
    size: float
    timestamp: int        # unix seconds


@dataclass
class WalletPosition:
    """
    Optional: normalized position snapshot on a market.
    """
    wallet: str
    market_id: str
    outcome: str
    size: float
    avg_price: float
    mark_price: Optional[float] = None
    pnl: Optional[float] = None
