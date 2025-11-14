from __future__ import annotations
from .btc_base import BTCBase, ScoredOpportunity

class BTCMacro(BTCBase):
    def score(self, market, current_price: float) -> ScoredOpportunity | None:
        # fallback category: any BTC market not caught by the other strategies
        if not self.is_btc_market(market):
            return None

        # ignore intraday + price targets (handled earlier)
        q = market.question.lower()
        if any(k in q for k in ["reach", "above", "below", "dip", "up or down", "up/down"]):
            return None

        yes = market.outcomes[0].price
        fair = 0.5

        edge_bp = (fair - yes) * 10000
        side = "YES" if edge_bp > 0 else "NO"

        return ScoredOpportunity(
            market=market,
            edge_bp=edge_bp,
            side=side,
            fair_prob=fair,
            yes_price=yes,
            no_price=market.outcomes[1].price,
            type="macro"
        )

