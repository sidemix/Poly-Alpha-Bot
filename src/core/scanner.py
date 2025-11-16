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
    - Fetches markets from Polymarket (HTTP Gamma API)
    - Filters to BTC-related markets
    - Runs all BTC strategies and aggregates opportunities
    """

    def __init__(self, cfg: Any, polymarket_client: Any | None = None) -> None:
        # we keep client in case we want Gamma client later,
        # but for now we will *always* use HTTP fallback to avoid shape mismatch
        self.cfg = cfg
        self.client = polymarket_client

        # Local imports to avoid circular imports
        from ..strategies.btc_intraday import BTCIntraday
        from ..strategies.btc_price_target import BTCPriceTargets

        # All strategies must implement score_many(markets, btc_price)
        self.strats = [
            BTCIntraday(cfg),
            BTCPriceTargets(cfg),
        ]

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def run_scan(self) -> List[Opportunity]:
        """
        Run a single BTC scan:
        - Fetch BTC price
        - Load markets (HTTP Gamma)
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

        markets = self._load_markets_http(limit=500)
        log.info("[SCAN] Loaded %d open markets before filters", len(markets))

        btc_markets = self._filter_btc_markets(markets)
        log.info(
            "[SCAN] BTC filter: %d/%d markets matched BTC/Bitcoin text",
            len(btc_markets),
            len(markets),
        )

        # Log a few sample BTC markets
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
            strat_name = getattr(strat, "name", strat.__class__.__name__)
            try:
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
                    "[SCAN] Strategy '%s' failed during scoring",
                    strat_name,
                )

        # Sort by edge descending (best first)
        all_opps.sort(key=lambda o: getattr(o, "edge", 0.0), reverse=True)
        log.info("[SCAN] Scanner returning %d BTC opportunities", len(all_opps))
        return all_opps

    # ------------------------------------------------------------------ #
    # Market loading (HTTP Gamma API only)
    # ------------------------------------------------------------------ #

    def _load_markets_http(self, limit: int) -> List[Market]:
        """
        HTTP fallback using Polymarket Gamma Markets API:

        GET https://gamma-api.polymarket.com/markets?active=true&limit=500&order=volume&ascending=false
        """
        import requests

        base_url = "https://gamma-api.polymarket.com/markets"
        params = {
            "active": "true",        # open markets only
            "limit": str(limit),
            "order": "volume",       # most liquid first
            "ascending": "false",
        }

        log.info("[POLY HTTP] Fetching markets from %s with %s", base_url, params)

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

    # ------------------------------------------------------------------ #
    # BTC filter + price
    # ------------------------------------------------------------------ #

    def _filter_btc_markets(self, markets: Sequence[Market]) -> List[Market]:
        """
        Simple text filter for BTC-related markets.
        Intentionally broad so we don't accidentally drop everything.
        """
        btc_markets: List[Market] = []

        for m in markets:
            q = (m.question or "").lower()
            grp = (getattr(m, "markets_group", "") or "").lower()
            text = f"{q} {grp}"
            if "btc" in text or "bitcoin" in text:
                btc_markets.append(m)

        return btc_markets

    def _fetch_btc_price(self) -> float:
        """
        Uses the shared price feed helper that already:
        - tries Binance
        - falls back to Coinbase
        """
        try:
            from ..integrations.price_feeds import get_btc_price
        except ImportError:
            log.error("[PRICE] price_feeds.get_btc_price not found; returning 0")
            return 0.0

        try:
            price = float(get_btc_price())
        except Exception:
            log.exception("[PRICE] Error fetching BTC price via price_feeds")
            return 0.0

        log.info("[PRICE] BTC/USD=%.2f", price)
        return price
