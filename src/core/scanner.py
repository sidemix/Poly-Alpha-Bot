# src/core/scanner.py

import logging
from typing import List, Sequence, Optional, Any, Dict

import requests

from ..models import Market
from ..strategies.base import BaseStrategy, ScoredOpportunity

logger = logging.getLogger(__name__)


class Scanner:
    """
    Main orchestrator: fetch markets, run each strategy, aggregate and return best opps.
    """

    def __init__(self, cfg, client):
        """
        :param cfg: Config object (has .env, .discord, etc if you need)
        :param client: Polymarket client (whatever your existing code was using)
        """
        self.cfg = cfg
        self.client = client

        # IMPORTANT: strategies are passed in from main.py so we don't change that contract.
        # main.py does: Scanner(cfg, client, [BTCIntraday(cfg), BTCPriceTargets(cfg)])
        self.strats: List[BaseStrategy] = []

    def set_strategies(self, strategies: Sequence[BaseStrategy]) -> None:
        """
        Called by main.py after constructing Scanner so we don't break your existing config.
        """
        self.strats = list(strategies)
        names = ", ".join(s.name for s in self.strats)
        logger.info(f"[SCAN] Registered strategies: {names}")

    # -------------------------
    # Public API
    # -------------------------

    def run_scan(self, limit: int = 500) -> List[ScoredOpportunity]:
        logger.info("[SCAN] Running BTC mispricing scan…")

        # 1) Get markets
        markets = self._load_markets(limit=limit)
        logger.info(f"[SCAN] Loaded {len(markets)} parsed markets from Polymarket")

        if not markets:
            logger.warning("[SCAN] No markets returned; skipping strategies.")
            return []

        # 2) Fetch BTC price (you already have this helper elsewhere)
        btc_price = self._fetch_btc_price()
        logger.info(f"[PRICE] BTC/USD={btc_price:.2f} (via Coinbase)")

        # 3) Run each strategy safely
        all_scored: List[ScoredOpportunity] = []
        for strat in self.strats:
            try:
                scored = strat.score_many(markets, btc_price)
                logger.info(f"[SCAN] Strategy '{strat.name}' produced {len(scored)} opps")
                all_scored.extend(scored)
            except Exception as e:
                logger.exception(f"[SCAN] Strategy '{strat.name}' failed: {e}")

        # 4) Sort by score desc and return
        all_scored.sort(key=lambda o: o.score, reverse=True)
        logger.info(f"[SCAN] Scanner returning {len(all_scored)} BTC opportunities")
        return all_scored

    # -------------------------
    # Market loading
    # -------------------------

    def _load_markets(self, limit: int) -> List[Market]:
        """
        Try official client first; if that fails or returns empty, fall back to HTTP.
        """
        markets: List[Market] = []

        # Try to use client if it has a markets method
        try:
            if hasattr(self.client, "get_markets"):
                logger.info("[POLY] Using client.get_markets()")
                raw = self.client.get_markets(limit=limit)
            elif hasattr(self.client, "fetch_markets"):
                logger.info("[POLY] Using client.fetch_markets()")
                raw = self.client.fetch_markets(limit=limit)
            else:
                logger.warning(
                    "[POLY] Client has no get_markets/fetch_markets; skipping to HTTP fallback"
                )
                raw = None

            if raw:
                logger.info(
                    f"[POLY] client returned {len(raw)} raw markets; parsing via parse_markets()"
                )
                from ..parser import parse_markets

                markets = parse_markets(raw)
                logger.info(
                    f"[POLY] Parsed {len(markets)} usable markets from client response"
                )

            if markets:
                return markets

        except Exception as e:
            logger.exception(f"[POLY] Client market fetch failed: {e}")

        # HTTP fallback
        logger.info(" [POLY HTTP fallback] Trying direct HTTP markets endpoint…")
        raw_http = self._fallback_fetch_markets_http(limit=limit)

        # If *still* nothing, log what happened in detail
        if not raw_http:
            logger.warning(
                "[POLY HTTP fallback] HTTP fetch returned 0 raw markets. "
                "Enable DEBUG logs to see full response details."
            )
            return []

        try:
            from ..parser import parse_markets

            markets = parse_markets(raw_http)
            logger.info(
                f"[POLY HTTP fallback] Parsed {len(markets)} usable markets from HTTP response"
            )
        except Exception as e:
            logger.exception(
                f"[POLY HTTP fallback] Failed to parse HTTP markets response: {e}"
            )
            return []

        return markets

    def _fallback_fetch_markets_http(self, limit: int) -> List[Dict[str, Any]]:
        """
        Call Polymarket public HTTP API directly and log enough that we can see
        why you're getting 0 raw markets.
        """
        # Common public endpoint used by tooling (if this ever changes, we’ll see via logs)
        url = "https://gamma-api.polymarket.com/markets"
        params = {
            "limit": limit,
            "offset": 0,
            "closed": "false",
            # You can add filters like 'category' or 'ticker' later
        }

        try:
            resp = requests.get(url, params=params, timeout=10)
            logger.info(
                f"[POLY HTTP fallback] GET {resp.url} -> {resp.status_code}"
            )

            # Log a small slice of body when nothing comes back
            text_preview = resp.text[:400].replace("\n", " ")
            logger.debug(
                f"[POLY HTTP fallback] Raw body preview (first 400 chars): {text_preview}"
            )

            resp.raise_for_status()
            data = resp.json()

            # Polymarket APIs usually return either:
            # { "markets": [...] } or a raw list
            if isinstance(data, dict) and "markets" in data:
                markets = data["markets"] or []
            elif isinstance(data, list):
                markets = data
            else:
                logger.warning(
                    "[POLY HTTP fallback] Unexpected JSON shape from Polymarket; "
                    f"type={type(data)} keys={list(data.keys()) if isinstance(data, dict) else 'N/A'}"
                )
                markets = []

            logger.info(
                f"[POLY HTTP fallback] fetched {len(markets)} raw markets from HTTP"
            )
            return markets

        except Exception as e:
            logger.exception(f"[POLY HTTP fallback] Exception fetching markets: {e}")
            return []

    # -------------------------
    # BTC price helper
    # -------------------------

    def _fetch_btc_price(self) -> float:
        """
        You already had a Binance + Coinbase fallback in main;
        keep that behavior here for clarity.
        """
        from ..integrations.price_feeds import get_btc_price

        try:
            price = get_btc_price()
            return float(price)
        except Exception as e:
            logger.error(
                f"[PRICE] Failed to fetch BTC price; defaulting to 0. "
                f"Fair prob will degrade. {e}"
            )
            return 0.0
