# src/core/scanner.py

from __future__ import annotations

import logging
from typing import List, Sequence, Any

from ..models import Market, Opportunity
from ..parser import parse_markets

log = logging.getLogger(__name__)


class Scanner:
    """
    Main coordinator:
    - Fetches markets from Polymarket (client or HTTP fallback)
    - Filters to BTC-related markets
    - Runs all BTC strategies and aggregates opportunities
    """

    def __init__(self, cfg: Any, polymarket_client: Any):
        self.cfg = cfg
        self.client = polymarket_client

        # Local imports to avoid circulars
        from ..strategies.btc_intraday import BTCIntraday
        from ..strategies.btc_price_target import BTCPriceTargets

        # All strategies must inherit BaseStrategy and implement score_many(...)
        self.strats = [
            BTCIntraday(cfg),
            BTCPriceTargets(cfg),
        ]

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #

    def run_scan(self) -> List[Opportunity]:
        """
        Run a single BTC scan:
        - Fetch BTC price
        - Load markets
        - Filter to BTC markets
        - Run each strategy
        """
        log.info("[SCAN] Running BTC mispricing scan…")

        btc_price = self._fetch_btc_price()
        if btc_price <= 0:
            log.warning(
                "[PRICE] BTC price <= 0 (got %.2f). Skipping scan to avoid junk edges.",
                btc_price,
            )
            return []

        markets = self._load_markets(limit=500)
        log.info("[SCAN] Loaded %d open markets before filters", len(markets))

        btc_markets = self._filter_btc_markets(markets)
        log.info(
            "[SCAN] BTC filter: %d/%d markets matched BTC/Bitcoin text",
            len(btc_markets),
            len(markets),
        )

        # Log a few sample BTC markets for sanity
        for m in btc_markets[:5]:
            log.info(
                "    [BTC MARKET] id=%s | q=%s",
                getattr(m, "id", None),
                (m.question or "")[:140],
            )

        if not btc_markets:
            log.info("[SCAN] No BTC markets after filtering. Returning 0 opportunities.")
            return []

        all_opps: List[Opportunity] = []

        for strat in self.strats:
            try:
                strat_name = getattr(strat, "name", strat.__class__.__name__)
                # Every strategy should implement score_many(markets, btc_price)
                strat_opps = strat.score_many(btc_markets, btc_price)
                log.info(
                    "[SCAN] Strategy '%s' produced %d opportunities",
                    strat_name,
                    len(strat_opps),
                )
                all_opps.extend(strat_opps)
            except Exception:
                log.exception(
                    "[SCAN] Strategy '%s' failed during scoring", strat.__class__.__name__
                )

        # Sort by edge descending (best first)
        all_opps.sort(key=lambda o: getattr(o, "edge", 0.0), reverse=True)
        log.info("[SCAN] Scanner returning %d BTC opportunities", len(all_opps))
        return all_opps

    # --------------------------------------------------------------------- #
    # Market Loading
    # --------------------------------------------------------------------- #

    def _load_markets(self, limit: int) -> List[Market]:
        """
        Try Polymarket client first (get_markets / fetch_markets).
        If not available, use HTTP fallback.
        """
        # 1) Gamma/Data client path (if present)
        if hasattr(self.client, "get_markets"):
            try:
                raw = self.client.get_markets(limit=limit)
                log.info("[POLY] client.get_markets() returned %d items", len(raw))
                markets = parse_markets(raw)
                log.info(
                    "[POLY] Parsed %d markets from client.get_markets()",
                    len(markets),
                )
                return markets
            except Exception:
                log.exception("[POLY] Error using client.get_markets(); falling back to HTTP")

        if hasattr(self.client, "fetch_markets"):
            try:
                raw = self.client.fetch_markets(limit=limit)
                log.info("[POLY] client.fetch_markets() returned %d items", len(raw))
                markets = parse_markets(raw)
                log.info(
                    "[POLY] Parsed %d markets from client.fetch_markets()",
                    len(markets),
                )
                return markets
            except Exception:
                log.exception("[POLY] Error using client.fetch_markets(); falling back to HTTP")

        # 2) HTTP fallback
        log.info("[POLY] Client has no get_markets/fetch_markets; using HTTP fallback")
        return self._load_markets_http(limit)

    def _load_markets_http(self, limit: int) -> List[Market]:
        """
        HTTP fallback using Polymarket Gamma Markets API.

        This does NOT require aiopolymarket; it's just raw requests.
        We keep it simple and robust:
        - active=True (open)
        - order=volume (most liquid first)
        """
        import requests

        base_url = "https://gamma-api.polymarket.com/markets"
        params = {
            "active": "true",
            "limit": limit,
            "order": "volume",
            "ascending": "false",
            # you could add more params here if needed
        }

        try:
            resp = requests.get(base_url, params=params, timeout=10)
            resp.raise_for_status()
        except Exception:
            log.exception("[POLY HTTP] Error fetching markets from %s", base_url)
            return []

        try:
            data = resp.json()
        except ValueError:
            log.error("[POLY HTTP] Non-JSON response from %s", base_url)
            return []

        # Gamma API returns a list of market dicts
        if isinstance(data, list):
            raw_markets = data
        elif isinstance(data, dict) and "data" in data:
            # just in case they wrap it
            raw_markets = data["data"]
        else:
            log.error(
                "[POLY HTTP] Unexpected JSON structure from %s: %s",
                base_url,
                type(data).__name__,
            )
            return []

        log.info(
            "[POLY HTTP] fetched %d raw markets from %s (limit=%s)",
            len(raw_markets),
            base_url,
            limit,
        )

        markets = parse_markets(raw_markets)
        log.info("[POLY HTTP] parsed %d usable markets", len(markets))
        return markets

    # --------------------------------------------------------------------- #
    # BTC Filter + Price
    # --------------------------------------------------------------------- #

    def _filter_btc_markets(self, markets: Sequence[Market]) -> List[Market]:
        """
        Super simple text filter for BTC-related markets.
        We keep it intentionally broad so we don't accidentally drop everything.
        """
        btc_markets: List[Market] = []

        for m in markets:
            q = (m.question or "").lower()
            grp = (getattr(m, "markets_group", "") or "").lower()
            # Very loose filter: anything mentioning btc/bitcoin in question or group
            haystack = f"{q} {grp}"
            if "btc" in haystack or "bitcoin" in haystack:
                btc_markets.append(m)

        return btc_markets

    def _fetch_btc_price(self) -> float:
        """
        Uses the shared price feed helper that already does:
        - Binance first
        - Coinbase fallback
        """
        try:
            from ..integrations.price_feeds import get_btc_price
        except ImportError:
            log.error("[PRICE] price_feeds.get_btc_price not found; returning 0")
            return 0.0

        price = 0.0
        try:
            price = float(get_btc_price())
        except Exception:
            log.exception("[PRICE] Error fetching BTC price via price_feeds")
            return 0.0

        log.info("[PRICE] BTC/USD=%.2f", price)
        return price
