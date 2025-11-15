# src/strategies/base.py

from __future__ import annotations

from typing import Any, Optional


class BaseStrategy:
    """
    Minimal base strategy class.

    Subclasses must implement `score()` and return either:
      - a dict describing an opportunity, or
      - None to skip the market.
    """

    name: str = "base"

    def score(self, market: Any, btc_price: float) -> Optional[dict]:
        raise NotImplementedError("Subclasses must implement score()")
