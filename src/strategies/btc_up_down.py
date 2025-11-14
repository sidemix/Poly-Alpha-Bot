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
    Strategy for intraday BTC 'up or down' style markets, e.g.:
      - /event/btc-updown-15m-...
      - /event/btc-updown-4h-...
      - /event/bitcoin-up-or-down-november-14-8am-et
      - 'Bitcoin up or down on November 14?'
    """

    def __init__(self, config: AppConfig):
        self.cfg = config

    def _days_to_expiry(self, end_time: datetime) -> float:
        now = datetime.now(timezone.utc)
        return max((end_time - now).total_seconds() / 86400.0, 0.0)

    def is_intraday_btc_updown(self, market: Market) -> bool:
        """
        Use BOTH question text and URL patterns to detect intraday BTC up/down markets.
        """
        q = market.question.lower()
        u = market.url.lower()

        # BTC / Bitcoin check
        if "bitcoin" not in q and "btc" not in q and "btc-" not in u:
            return False

        # Up/down patterns from the links you sent
        patterns = [
            "btc-updown",           # /event/btc-updown-15m-...
            "btc updown",
            "btc up/down",
            "bitcoin up or down",   # /event/bitcoin-up-or-down-...
            "bitcoin-up-or-down",
            "up or down",           # fallback in case 'bitcoin' is only in URL
        ]

        return any(p in q or p in u for p in patterns)

    def estimate_fair_prob(self, market: Market) -> float:
        """
        Placeholder fair probability model.
        Later: plug in live BTC price + time window + vol.
        """
        return 0.5

    def score_market(self, market: Market) -> ScoredOpportunity | None:
        if not self.is_intraday_btc_updown(market):
            return None

        # Only keep markets within configured horizon
        days = self._days_to_expiry(market.end_time)
        if days > self.cfg.scan.max_resolution_days:
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
        btc_updown_markets = 0
        opps: list[ScoredOpportunity] = []

        for m in markets:
            if self.is_intraday_btc_updown(m):
                btc_updown_markets += 1
                scored = self.score_market(m)
                if not scored:
                    continue

                if abs(scored.edge_bp) < self.cfg.scan.min_edge_bp:
                    continue

                opps.append(scored)

        print(
            f"[BTC_STRAT] intraday_btc_updown_markets={btc_updown_markets}, "
            f"opps={len(opps)}"
        )

        opps.sort(key=lambda o: abs(o.edge_bp), reverse=True)
        return opps
