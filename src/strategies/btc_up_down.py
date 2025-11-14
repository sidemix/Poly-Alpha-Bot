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
    """
    Debug-friendly v1:
    - Treat ANY market mentioning 'bitcoin' or 'btc' as a candidate
    - Very simple fair-prob model (flat 0.5 for now)
    - Logs how many BTC markets it saw and how many passed filters
    """

    def __init__(self, config: AppConfig):
        self.cfg = config

    def is_btc_up_down_market(self, market: Market) -> bool:
        q = market.question.lower()
        # LOOSENED FILTER for now – just see all BTC questions
        return "bitcoin" in q or "btc" in q

    def _time_to_expiry_hours(self, end_time: datetime) -> float:
        now = datetime.now(timezone.utc)
        return max((end_time - now).total_seconds() / 3600.0, 0.0)

    def estimate_fair_prob(self, market: Market) -> float:
        """
        Placeholder fair prob model:
        - Just returns 0.5 for now.
        - We’ll replace this with BTC price vs strike once we confirm parsing.
        """
        # You can use time to expiry later if you want:
        # hours = self._time_to_expiry_hours(market.end_time)
        return 0.5

    def score_market(self, market: Market) -> ScoredOpportunity | None:
        if not self.is_btc_up_down_market(market):
            return None

        if len(market.outcomes) < 2:
            return None

        yes = market.outcomes[0]
        no = market.outcomes[1]

        yes_p = yes.price         # expect 0–1 from Gamma
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
        btc_markets = 0
        opps: list[ScoredOpportunity] = []

        for m in markets:
            if self.is_btc_up_down_market(m):
                btc_markets += 1
            scored = self.score_market(m)
            if not scored:
                continue

            # For debugging you can even temporarily ignore the edge filter,
            # or keep it:
            if abs(scored.edge_bp) < self.cfg.scan.min_edge_bp:
                continue

            opps.append(scored)

        print(f"[BTC_STRAT] saw {btc_markets} BTC-related markets, "
              f"{len(opps)} passed edge filter")

        opps.sort(key=lambda o: abs(o.edge_bp), reverse=True)
        return opps
