
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List
from ..integrations.polymarket_client import Market

@dataclass
class ScoredOpportunity:
    market: Market
    edge_bp: float
    side: str
    fair_prob: float
    yes_price: float
    no_price: float
    type: str  # "intraday", "target", "macro"

class BTCBase:
    def _days_to_expiry(self, end_time: datetime) -> float:
        now = datetime.now(timezone.utc)
        return max((end_time - now).total_seconds() / 86400, 0.0)

    def is_btc_market(self, market: Market) -> bool:
        q = market.question.lower()
        u = market.url.lower()
        return ("bitcoin" in q or "btc" in q or "btc-" in u)
