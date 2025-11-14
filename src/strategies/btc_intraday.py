from __future__ import annotations

from .btc_base import BTCBase, ScoredOpportunity
from ..utils.config import AppConfig
from ..integrations.polymarket_client import Market


class BTCIntraday(BTCBase):
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg

    def is_intraday(self, market: Market) -> bool:
        q = market.question.lower()
        u = market.url.lower()
        patterns = [
            "btc-updown",
            "up or down",
            "up/down",
            "up or down on",
            "up or down today",
            "8am et",
            "4h",
            "15m"
        ]
        return self.is_btc_market(market) and any(p in q or p in u for p in patterns)

    def fair_prob(self, strike_price: float, current_price: float, hours_left: float):
        """Plug-in model later. Placeholder = 0.5."""
        return 0.5

    def score(self, market: Market, current_price: float) -> ScoredOpportunity | None:
        if not self.is_intraday(market):
            return None

        days = self._days_to_expiry(market.end_time)
        if days > self.cfg.scan.max_resolution_days:
            return None

        # outcomes
        if len(market.outcomes) < 2:
            return None

        yes = market.outcomes[0].price
        fair = 0.5  # placeholder

        edge_bp = (fair - yes) * 10000
        side = "YES" if edge_bp > 0 else "NO"

        return ScoredOpportunity(
            market=market,
            edge_bp=edge_bp,
            side=side,
            fair_prob=fair,
            yes_price=yes,
            no_price=market.outcomes[1].price,
            type="intraday"
        )

