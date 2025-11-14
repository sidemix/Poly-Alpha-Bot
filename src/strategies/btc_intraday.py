# src/strategies/btc_intraday.py

from dataclasses import dataclass
from typing import Optional
from .base import BaseStrategy

def _s(x: Optional[str]) -> str:
    return x.lower().strip() if isinstance(x, str) else ""

@dataclass
class MarketView:
    id: str
    url: Optional[str]
    title: Optional[str]
    question: Optional[str]
    group: Optional[str]
    yes_price: Optional[float]
    no_price: Optional[float]
    end_ts: Optional[int]
    tags: Optional[list]

class BTCIntraday(BaseStrategy):
    """
    Scores Polymarket 'Bitcoin up or down' / intraday price-to-beat style markets.
    Hardened against None url/title/etc.
    """

    INTRADAY_HINTS = (
        "bitcoin up or down",
        "btc up or down",
        "price to beat",
        "up or down",
        "intraday",
        "today",
        "within 24h",
        "24h",
    )

    BTC_HINTS = (
        "btc", "bitcoin", "xbt"
    )

    def is_intraday(self, market: MarketView) -> bool:
        u   = _s(market.url)
        ttl = _s(market.title) or _s(market.question)
        grp = _s(market.group)

        text = " ".join([u, ttl, grp]).strip()
        if not text:
            return False

        # Must reference BTC/Bitcoin
        if not any(h in text for h in self.BTC_HINTS):
            return False

        # Must look like an intraday/short-horizon structure
        if not any(h in text for h in self.INTRADAY_HINTS):
            return False

        return True

    def score(self, market: MarketView, btc_spot: float) -> Optional[float]:
        # Filter to intraday BTC markets only (safe guard)
        if not self.is_intraday(market):
            return None

        # Require prices
        y, n = market.yes_price, market.no_price
        if y is None and n is None:
            return None

        # Simple asymmetry: look for implied probs 0.10–0.18 on either side
        # (you can customize your exact mispricing math here)
        score = 0.0
        if y is not None:
            p_yes = y
            if 0.10 <= p_yes <= 0.18:
                score += (0.18 - p_yes) * 10
        if n is not None:
            p_no = n
            if 0.10 <= p_no <= 0.18:
                score += (0.18 - p_no) * 10

        # Nudge for recency if end time is soon
        if market.end_ts:
            # sooner expiry → larger score
            score += self._soon_bonus(market.end_ts)

        return round(score, 4) if score > 0 else None
