from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any

from ..integrations.polymarket_client import Market


@dataclass
class ScoredOpportunity:
    market: Market
    edge_bp: float            # (fair_prob - market_yes_prob) * 10,000
    side: str                 # "YES" or "NO"
    fair_prob: float          # 0..1
    yes_price: float          # 0..1
    no_price: float           # 0..1
    type: str                 # "intraday" | "target" | "macro"
    meta: Dict[str, Any] = field(default_factory=dict)  # extra fields (strike, spot, T, etc.)

class BTCBase:
    def _days_to_expiry(self, end_time: datetime) -> float:
        now = datetime.now(timezone.utc)
        return max((end_time - now).total_seconds() / 86400.0, 0.0)

    def is_btc_market(self, market: Market) -> bool:
        q = market.question.lower()
        u = market.url.lower()
        return ("bitcoin" in q) or ("btc" in q) or ("btc-" in u)
