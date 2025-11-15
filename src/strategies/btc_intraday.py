# src/strategies/btc_intraday.py

from __future__ import annotations

from typing import Any, Optional

from .base import BaseStrategy


class BTCIntraday(BaseStrategy):
    """
    Simple intraday BTC mispricing strategy for Polymarket.

    - Filters for BTC intraday / "up or down" style markets.
    - Returns a minimal dict describing an opportunity, or None.

    This version is defensive:
    - Never assumes market.url/title/question are non-null
    - Avoids crashing on weird / malformed markets
    """

    name = "btc-intraday"

    def is_intraday(self, market: Any) -> bool:
        """
        Decide whether this market looks like an intraday BTC market.

        We only use attributes if they exist and are strings; otherwise
        we ignore them. This prevents 'NoneType' errors.
        """
        url = getattr(market, "url", None)
        title = getattr(market, "title", None)
        question = getattr(market, "question", None)

        parts = []
        if isinstance(url, str):
            parts.append(url)
        if isinstance(title, str):
            parts.append(title)
        if isinstance(question, str):
            parts.append(question)

        if not parts:
            # Nothing to inspect, bail out
            return False

        text = " ".join(parts).lower()

        # Must clearly be BTC-related
        if "bitcoin" not in text and "btc" not in text:
            return False

        # Intraday / “up or down today” style markers
        intraday_markers = [
            "up or down",
            "up/down",
            "price to beat",
            "ends today",
            "today's price",
            "today’s price",
        ]

        return any(m in text for m in intraday_markers)

    def score(self, market: Any, btc_price: float) -> Optional[dict]:
        """
        Main scoring function.

        Returns:
            - dict with basic info if it's a tradable opportunity
            - None if we should skip the market

        NOTE: This stays deliberately minimal so it doesn't depend on
        any specific models.py dataclasses. Downstream code can treat
        the dict as an "Opportunity-like" object.
        """
        # First, filter to intraday BTC markets
        if not self.is_intraday(market):
            return None

        # Defensive attribute access
        title = (
            getattr(market, "title", None)
            or getattr(market, "question", None)
            or ""
        )
        url = getattr(market, "url", "") or ""

        yes_price = getattr(market, "yes_price", None)
        no_price = getattr(market, "no_price", None)

        # If we don’t have prices, skip quietly
        if yes_price is None or no_price is None:
            return None

        title_lower = title.lower()

        # Crude direction guess from the text
        if "up" in title_lower and "down" not in title_lower:
            direction = "up"
        elif "down" in title_lower and "up" not in title_lower:
            direction = "down"
        else:
            direction = "unknown"

        # Try to extract a rough strike from the title, e.g. "above 95,000"
        import re

        cleaned = title.replace(",", "")
        m = re.search(r"(\d{4,7})", cleaned)
        strike = float(m.group(1)) if m else None

        edge = 0.0
        if strike is not None:
            # Very naive "edge" heuristic:
            # if BTC is already beyond the strike in the implied direction
            # and YES is still cheap, treat as positive edge.
            if direction == "up" and btc_price > strike:
                # assume "true" probability ~60% if already above strike
                edge = 0.60 - yes_price
            elif direction == "down" and btc_price < strike:
                edge = 0.60 - yes_price

        return {
            "title": title,
            "url": url,
            "direction": direction,
            "yes_price": yes_price,
            "no_price": no_price,
            "edge": edge,
            # keep the raw market object in case downstream wants it
            "market": market,
        }
