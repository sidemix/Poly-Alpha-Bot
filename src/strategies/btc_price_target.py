# src/strategies/btc_price_target.py

from __future__ import annotations

from typing import Any, Optional
import re

from .base import BaseStrategy


class BTCPriceTargets(BaseStrategy):
    """
    BTC price target strategy.

    Looks for markets like:
      - "Will Bitcoin be above 95,000 on Nov 30?"
      - "BTC below 80k by year end?"

    Returns a simple dict opportunity or None.
    """

    name = "btc-price-targets"

    def _collect_text(self, market: Any) -> str:
        """Safely combine url/title/question into one lowercase string."""
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

        return " ".join(parts).lower()

    def is_btc_price_target(self, market: Any) -> bool:
        text = self._collect_text(market)
        if not text:
            return False

        # Must clearly be BTC-related
        if "bitcoin" not in text and "btc" not in text:
            return False

        # Words that usually indicate a price target contract
        if not any(
            kw in text
            for kw in [
                "above",
                "below",
                "over",
                "under",
                "at least",
                "at most",
                "greater than",
                "less than",
            ]
        ):
            return False

        # Require a large-ish number (likely the strike)
        cleaned = text.replace(",", "")
        if not re.search(r"\d{4,7}", cleaned):
            return False

        return True

    def score(self, market: Any, btc_price: float) -> Optional[dict]:
        if not self.is_btc_price_target(market):
            return None

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

        # Extract strike from the title text
        cleaned = title.replace(",", "")
        m = re.search(r"(\d{4,7})", cleaned)
        if not m:
            return None
        strike = float(m.group(1))

        tl = title.lower()

        if any(w in tl for w in ["above", "over", "greater than", "at least"]):
            direction = "above"
        elif any(w in tl for w in ["below", "under", "less than", "at most"]):
            direction = "below"
        else:
            direction = "unknown"

        # Very naive "true probability" heuristic based on how far BTC is from the strike
        dist = abs(btc_price - strike) / strike

        if direction == "above":
            if btc_price > strike:
                true_prob = max(0.55, 0.9 - dist * 2.0)
            else:
                true_prob = max(0.05, 0.5 - dist * 2.0)
        elif direction == "below":
            if btc_price < strike:
                true_prob = max(0.55, 0.9 - dist * 2.0)
            else:
                true_prob = max(0.05, 0.5 - dist * 2.0)
        else:
            true_prob = 0.0  # unknown direction => no edge

        edge = true_prob - yes_price

        return {
            "title": title,
            "url": url,
            "direction": direction,
            "yes_price": yes_price,
            "no_price": no_price,
            "strike": strike,
            "btc_price": btc_price,
            "true_prob": true_prob,
            "edge": edge,
            "market": market,
        }
