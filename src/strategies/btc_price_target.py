from __future__ import annotations
import math, os, re
from .btc_base import BTCBase, ScoredOpportunity
from ..utils.config import AppConfig
from ..integrations.polymarket_client import Market

def _phi(x: float) -> float:
    # Standard normal CDF via error function
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

class BTCPriceTargets(BTCBase):
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self._re_price = re.compile(r"\$?\s*([0-9][0-9,]*)")

        # Annualized vol (env override), fallback 0.80 = 80%
        try:
            self.ann_vol = float(os.getenv("BTC_ANNUAL_VOL", "0.80"))
        except Exception:
            self.ann_vol = 0.80

    def is_price_target(self, m: Market) -> bool:
        q = m.question.lower()
        keys = ["reach", "above", "below", "over", "under", "dip"]
        return self.is_btc_market(m) and any(k in q for k in keys)

    def _extract_strike(self, text: str) -> float | None:
        m = self._re_price.search(text.replace(",", ""))
        return float(m.group(1)) if m else None

    def _time_years(self, m: Market) -> float:
        days = self._days_to_expiry(m.end_time)
        return max(days, 0.0001) / 365.0  # avoid zero

    def _fair_prob_end_above(self, s0: float, k: float, Tyrs: float) -> float:
        if s0 <= 0 or k <= 0:
            return 0.5
        sigma = self.ann_vol
        if sigma <= 0:
            return 0.5
        z = math.log(k / s0) / (sigma * math.sqrt(Tyrs))
        return 1.0 - _phi(z)

    def _fair_prob_end_below(self, s0: float, k: float, Tyrs: float) -> float:
        if s0 <= 0 or k <= 0:
            return 0.5
        sigma = self.ann_vol
        if sigma <= 0:
            return 0.5
        z = math.log(k / s0) / (sigma * math.sqrt(Tyrs))
        return _phi(z)

    def score(self, market: Market, current_price: float) -> ScoredOpportunity | None:
        if not self.is_price_target(market):
            return None

        strike = self._extract_strike(market.question)
        if strike is None or len(market.outcomes) < 2:
            return None

        Tyrs = self._time_years(market)
        q = market.question.lower()

        # Decide which side the market implies as "YES"
        # Heuristic: if text says reach/above/over -> YES means end >= strike
        #            if text says dip/below/under -> YES means end <= strike
        if any(k in q for k in ["reach", "above", "over"]):
            fair = self._fair_prob_end_above(current_price, strike, Tyrs)
        elif any(k in q for k in ["dip", "below", "under"]):
            fair = self._fair_prob_end_below(current_price, strike, Tyrs)
        else:
            # fallback
            fair = 0.5

        yes_p = float(market.outcomes[0].price)
        no_p  = float(market.outcomes[1].price)

        edge_bp = (fair - yes_p) * 10000.0
        side = "YES" if edge_bp > 0 else "NO"

        return ScoredOpportunity(
            market=market,
            edge_bp=edge_bp,
            side=side,
            fair_prob=fair,
            yes_price=yes_p,
            no_price=no_p,
            type="target",
        )
