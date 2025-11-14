# src/strategies/btc_up_down.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

from ..integrations.polymarket_client import Market
from ..utils.config import AppConfig


@dataclass
class ScoredOpportunity:
    market: Market
    edge_bp: float  # basis points
    side: str       # "YES" or "NO"
    fair_prob: float
    yes_price: float
    no_price: float


class BTCUpDownStrategy:
    def __init__(self, config: AppConfig):
        self.cfg = config

    def is_btc_up_down_market(self, market: Market) -> bool:
       q = market.question.lower()
       return "bitcoin" in q and ("up or down" in q or "up/down" in q or "above" in q or "below" in q)


    def _time_to_expiry_hours(self, end_time: datetime) -> float:
        now = datetime.now(timezone.utc)
        return max((end_time - now).total_seconds() / 3600.0, 0.0)

    def estimate_fair_prob(self, market: Market) -> float:
        # placeholder – we’ll later plug in real BTC price vs strike
        hours = self._time_to_expiry_hours(market.end_time)
        base = 0.5
        if hours < 1:
            return base
        elif hours < 6:
            return base
        else:
            return base

    def score_market(self, market: Market) -> ScoredOpportunity | None:
        if not self.is_btc_up_down_market(market):
            return None
        if len(market.outcomes) < 2:
            return None

        yes = market.outcomes[0]
        no = market.outcomes[1]
        yes_p = yes.price
        no_p = no.price

        fair = self.estimate_fair_prob(market)
        edge_bp = (fair - yes_p) * 10000
        side = "YES" if edge_bp > 0 else "NO"

        return ScoredOpportunity(
            market=market,
            edge_bp=edge_bp,
            side=side,
            fair_prob=fair,
            yes_price=yes_p,
            no_price=no_p,
        )

    def find_opportunities(self, markets: List[Market]) -> List[ScoredOpportunity]:
        opps: list[ScoredOpportunity] = []
        for m in markets:
            scored = self.score_market(m)
            if not scored:
                continue
            if abs(scored.edge_bp) < self.cfg.scan.min_edge_bp:
                continue
            opps.append(scored)

        opps.sort(key=lambda o: abs(o.edge_bp), reverse=True)
        return opps

