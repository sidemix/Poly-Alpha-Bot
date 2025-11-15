from __future__ import annotations

from typing import List, Callable, Any
import requests

from ..parser import parse_markets
from ..models import Market
from ..strategies.base import BaseStrategy, ScoredOpportunity
from ..strategies.btc_intraday import BTCIntraday
from ..strategies.btc_price_target import BTCPriceTargets


class Scanner:
    """
    Main coordinator for:
    - Fetching markets from Polymarket
    - Normalizing them into Market models
    - Fetching BTC spot price
    - Running all BTC strategies and returning scored opportunities
    """

    def __init__(self, cfg: Any, client: Any) -> None:
        """
        :param cfg: your loaded Config object (or simple dict-like)
        :param client: Polymarket client (still passed in for future use,
                       but market loading now has an HTTP fallback)
        """
        self.cfg = cfg
        self.client = client

        # All active BTC strategies live here
        self.strats: List[BaseStrategy] = [
            BTCIntraday(cfg),
            BTCPriceTargets(cfg),
        ]

        # Last parsed markets feed (for debugging / reuse)
        self.feed: List[Market] = []

    # --------------------------------------------------------------------- #
    # BTC PRICE FETCHING
    # --------------------------------------------------------------------- #

    def _fetch_btc_price(self) -> float:
        """
        Try multiple public endpoints to get a BTC/USD (or USDT) spot price.
        Falls back through Binance → Coinbase → CoinGecko.

        Returns 0.0 only if everything fails.
        """

        endpoints: List[tuple[str, str, Callable[[dict], float]]] = [
            (
                "Binance",
                "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
                lambda d: float(d["price"]),
            ),
            (
                "Coinbase",
                "https://api.exchange.coinbase.com/products/BTC-USD/ticker",
                lambda d: float(d["price"]),
            ),
            (
                "CoinGecko",
                "https://api.coingecko.com/api/v3/simple/price"
                "?ids=bitcoin&vs_currencies=usd",
                lambda d: float(d["bitcoin"]["usd"]),
            ),
        ]

        for name, url, extractor in endpoints:
            try:
                resp = requests.get(url, timeout=5)
                resp.raise_for_status()
                data = resp.json()
                price = extractor(data)
                print(f"[PRICE] BTC/USD={price:.2f} (via {name})")
                return price
            except Exception as e:
                print(f"[PRICE] {name} price fetch failed: {e}")

        print("[PRICE] All BTC price endpoints failed; defaulting to 0.")
        return 0.0

    # --------------------------------------------------------------------- #
    # MARKET LOADING
    # --------------------------------------------------------------------- #

    def _load_markets(self, limit: int = 500) -> List[Market]:
        """
        Fetch raw markets from Polymarket, parse into Market models,
        store them on self.feed, and return.

        Order of preference:
        1) client.fetch_markets(limit=...)
        2) client.get_markets(limit=...)
        3) direct HTTP call to Polymarket /markets endpoint (fallback)
        """

        raw = None

        # 1) client.fetch_markets
        fetch_fn = getattr(self.client, "fetch_markets", None)
        if callable(fetch_fn):
            try:
                raw = fetch_fn(limit=limit)
            except Exception as e:
                print(f"[POLY] client.fetch_markets failed: {e}")

        # 2) client.get_markets
        if raw is None:
            get_fn = getattr(self.client, "get_markets", None)
            if callable(get_fn):
                try:
                    raw = get_fn(limit=limit)
                except Exception as e:
                    print(f"[POLY] client.get_markets failed: {e}")

        # 3) HTTP fallback directly to Polymarket
        if raw is None:
            try:
                # This pattern matches what your sports tracker logs show:
                # /markets?closed=false&limit=500&offset=0
                url = (
                    "https://clob.polymarket.com/markets"
                    f"?closed=false&limit={limit}&offset=0"
                )
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                data = resp.json()
                # Some endpoints return a dict with "markets", others a bare list
                if isinstance(data, list):
                    raw = data
                else:
                    raw = data.get("markets", [])
                print(" [POLY HTTP fallback]", end="")
            except Exception as e:
                print(f"[POLY] HTTP fallback /markets failed: {e}")
                raw = []

        raw_len = len(raw) if raw is not None else 0
        print(f"[POLY] fetched {raw_len} raw markets", end="")

        markets: List[Market] = parse_markets(raw or [])
        print(f", parsed {len(markets)} usable markets")

        self.feed = markets
        return markets

    # --------------------------------------------------------------------- #
    # MAIN SCAN LOOP
    # --------------------------------------------------------------------- #

    def run_scan(self) -> List[ScoredOpportunity]:
        """
        Run full BTC mispricing scan:
        - fetch BTC price
        - fetch & parse markets
        - run each strategy
        - return all scored opportunities sorted by score desc
        """

        print("[SCAN] Running BTC mispricing scan…")

        btc_price = self._fetch_btc_price()
        markets = self._load_markets(limit=500)

        # If BTC price is 0, you *can* early-exit, but for now we just warn.
        if btc_price <= 0:
            print(
                "[SCAN] BTC price unavailable or zero; strategies may produce no edge."
            )

        all_scored: List[ScoredOpportunity] = []

        for strat in self.strats:
            try:
                scored = strat.score_many(markets, btc_price)
                all_scored.extend(scored)
            except Exception as e:
                # Protect the whole scanner from one bad strategy
                print(f"[SCAN] Strategy '{strat.name}' failed: {e}")

        # Sort by score, highest first
        all_scored.sort(key=lambda s: s.score, reverse=True)

        print(f"[SCAN] Scanner returned {len(all_scored)} BTC opportunities")
        return all_scored
