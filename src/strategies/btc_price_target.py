from __future__ import annotations
import re
from .btc_base import BTCBase, ScoredOpportunity
from ..utils.config import AppConfig

class BTCPriceTargets(BTCBase):
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self.price_re = re.compile(r"\$?(\d{2,7})")

    def is_price_target(self, market):
        q = market.question.lower()
        keywords = ["reach", "dip", "above", "below", "over", "under"]
        return self.is_btc_market(market) and any(k in q for k in keywords)

    def extract_strike(self, question: str) -> float | None:
        match = self.price_re.search(question.replace(",", ""))
        if match:
            return float(match.group(1))
        return None

    def score(self, market, current_price: float) -> ScoredOpportunity | None:
        if not self.is_price_target(market):
            return None

        strike = self.extract_strike(market.question)
        if strike is None:
            return None

        yes = market.outcomes[0].price

        # placeholder fair probability
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
            type="target"
        )

