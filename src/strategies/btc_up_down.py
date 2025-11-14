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

    def _days_to_expiry(self, end_time: datetime) -> float:
        now = datetime.now(timezone.utc)
        return max((end_time - now).total_seconds() / 86400.0, 0.0)

    def is_btc_market(self, market: Market) -> bool:
        q = market.question.lower()
        return "bitcoin" in q or "btc" in q

    def is_updown_like(self, market: Market) -> bool:
        """
        Loose classifier for 'up/down' style questions.
        We'll refine this after we see real titles in logs.
        """
        q = market.question.lower()
        keywords = ["up or down", "up/down", "up", "down", "above", "below", "over", "under"]
        return any(k in q for k in keywords)

    def estimate_fair_prob(self, market: Market) -> float:
        # Placeholder: flat 0.5 for now
        return 0.5

    def score_market(self, market: Market) -> ScoredOpportunity | None:
        if not self.is_btc_market(market):
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
        btc_markets = []
        opps: list[ScoredOpportunity] = []

        for m in markets:
            if self.is_btc_market(m):
                btc_markets.append(m)

        # 🔍 DEBUG: print a few BTC markets so we can see how they’re written
        print(f"[BTC_DEBUG] Found {len(btc_markets)} BTC markets total")
        for m in btc_markets[:10]:
            days = self._days_to_expiry(m.end_time)
            print(f"[BTC_DEBUG] '{m.question}' — days_to_expiry={days:.2f}")

        # Now, only treat 'up/down-like' + within max_resolution_days as candidates
        for m in btc_markets:
            days = self._days_to_expiry(m.end_time)
            if days > self.cfg.scan.max_resolution_days:
                continue
            if not self.is_updown_like(m):
                continue

            scored = self.score_market(m)
            if not scored:
                continue

            if abs(scored.edge_bp) < self.cfg.scan.min_edge_bp:
                continue

            opps.append(scored)

        print(
            f"[BTC_STRAT] btc_markets={len(btc_markets)}, "
            f"updown_short_horizon={len(opps)}"
        )

        opps.sort(key=lambda o: abs(o.edge_bp), reverse=True)
        return opps
