import logging
from typing import List, Any

import requests

from ..parser import parse_markets
from ..strategies.base import BaseStrategy, ScoredOpportunity
from ..strategies.btc_intraday import BTCIntraday
from ..strategies.btc_price_target import BTCPriceTargets

log = logging.getLogger(__name__)


class Scanner:
    """
    Orchestrates:
      - Pull Polymarket BTC markets
      - Get BTC spot price
      - Run all BTC-related strategies
      - Return a flat list of ScoredOpportunity objects
    """

    def __init__(self, cfg: Any, client: Any) -> None:
        # We keep these arguments so main.py can still pass in whatever it wants.
        self.cfg = cfg
        self.client = client

        # All strategies we want to run each scan
        self.strats: List[BaseStrategy] = [
            BTCIntraday(cfg),
            BTCPriceTargets(cfg),
        ]

    # ---------------------------
    # Internal helpers
    # ---------------------------

    def _fetch_raw_markets(self) -> list:
        """
        Fetch a single page of open Polymarket markets (limit=500).
        We can expand this later if we want pagination or different filters.
        """
        url = "https://gamma-api.polymarket.com/markets"
        params = {
            "limit": 500,
            "offset": 0,
            "closed": "false",
        }

        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # Some Polymarket endpoints wrap in {"data": [...]}
        if isinstance(data, dict) and "data" in data:
            return data["data"]

        if isinstance(data, list):
            return data

        log.warning("[POLY] Unexpected markets payload shape, treating as empty: %s", type(data))
        return []

    def _get_btc_price(self) -> float:
        """
        Fetch BTC spot price from Binance as a simple, reliable oracle.
        If anything fails, return 0 (strategies should treat 0 as 'price unavailable').
        """
        try:
            resp = requests.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={"symbol": "BTCUSDT"},
                timeout=5,
            )
            resp.raise_for_status()
            j = resp.json()
            price = float(j["price"])
            log.info("[PRICE] BTC/USD=%s", price)
            return price
        except Exception as e:
            log.warning(
                "[PRICE] Failed to fetch BTC price; defaulting to 0. "
                "Fair prob will degrade. %s",
                e,
            )
            return 0.0

    # ---------------------------
    # Public API
    # ---------------------------

    def run_scan(self) -> List[ScoredOpportunity]:
        """
        Main entry point used in main.py.

        - Fetch BTC-related markets
        - Fetch BTC spot price
        - Run each strategy and collect scored opportunities
        """
        log.info("[SCAN] Running BTC mispricing scan…")

        # 1) Pull markets directly from Polymarket
        raw_markets = self._fetch_raw_markets()

        # 2) Parse & filter to BTC markets using our parser
        markets = parse_markets(raw_markets, ticker_symbol="BTC")
        # parse_markets itself should be logging:
        # "[POLY] fetched X raw markets, parsed Y usable markets"

        # 3) Get BTC price
        btc_price = self._get_btc_price()

        # 4) Run all strategies on all markets
        scored: List[ScoredOpportunity] = []
        for m in markets:
            for strat in self.strats:
                try:
                    opp = strat.score(m, btc_price)
                    if opp is not None:
                        scored.append(opp)
                except Exception as e:
                    log.warning(
                        "[SCAN] Strategy %s failed on market %s: %s",
                        strat.__class__.__name__,
                        getattr(m, "id", "unknown"),
                        e,
                    )

        # 5) Sort by score descending so the best opps are first
        scored.sort(key=lambda o: o.score, reverse=True)
        return scored
