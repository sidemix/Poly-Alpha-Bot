from __future__ import annotations

from .btc_base import BTCBase, ScoredOpportunity
from ..utils.config import AppConfig
from ..integrations.polymarket_client import Market



class BTCMacro(BTCBase):
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg

    def score(self, market: Market, current_price: float) -> ScoredOpportunity | None:
        # fallback category: any BTC market not caught by the other strategies
        if not self.is_btc_market(market):
            return None

        q = market.question.lower()

        # ignore intraday + price targets (those are handled by other strategies)
        if any(k in q for k in ["reach", "above", "below", "dip", "up or down", "up/down"]):
            return None

        if len(market.outcomes) < 2:
            return None

        yes = market.outcomes[0].price
        no = market.outcomes[1].price

        # placeholder fair probability (we'll make this smarter later)
        fair = 0.5

        edge_bp = (fair - yes) * 10000
        side = "YES" if edge_bp > 0 else "NO"

        return ScoredOpportunity(
            market=market,
            edge_bp=edge_bp,
            side=side,
            fair_prob=fair,
            yes_price=yes,
            no_price=no,
            type="macro",
        )
