import logging
from typing import List

from ..models import Market
from ..parser import parse_markets
from ..strategies.base import BaseStrategy, ScoredOpportunity
from ..strategies.btc_intraday import BTCIntraday
from ..strategies.btc_price_target import BTCPriceTargets

logger = logging.getLogger(__name__)


class Scanner:
    """
    Orchestrates:
      1) Fetching markets from Polymarket (client or HTTP fallback)
      2) Filtering BTC markets
      3) Running all BTC strategies and aggregating scored opportunities
    """

    def __init__(self, cfg, client):
        self.cfg = cfg
        self.client = client

        # Register all strategies here
        self.strats: List[BaseStrategy] = [
            BTCIntraday(cfg, name="BTCIntraday"),
            BTCPriceTargets(cfg, name="BTCPriceTargets"),
        ]

    def run_scan(self) -> List[ScoredOpportunity]:
        """
        High-level scan pipeline. Called from main.py every loop.
        """
        logger.info("[SCAN] Running BTC mispricing scan…")

        # 1) Fetch BTC price
        btc_price = self._fetch_btc_price()
        logger.info("[PRICE] BTC/USD=%.2f", btc_price)

        # 2) Load and parse markets
        markets: List[Market] = self._load_markets(limit=500)
        if not markets:
            logger.warning("[SCAN] No markets loaded; returning 0 opportunities")
            return []

        # 3) Filter to BTC markets using Market.is_btc_market()
        btc_markets: List[Market] = [m for m in markets if m.is_btc_market()]
        logger.info(
            "[SCAN] Loaded %d total markets; %d BTC markets after filter",
            len(markets),
            len(btc_markets),
        )

        if not btc_markets:
            logger.warning("[SCAN] No BTC-like markets found; returning 0 opportunities")
            return []

        # 4) Run each strategy and aggregate opportunities
        all_opps: List[ScoredOpportunity] = []

        for strat in self.strats:
            try:
                strat_opps = strat.score_many(btc_markets, btc_price)
                logger.info(
                    "[SCAN] Strategy '%s' produced %d opportunities",
                    strat.name,
                    len(strat_opps),
                )
                all_opps.extend(strat_opps)
            except Exception:
                logger.exception("[SCAN] Strategy '%s' failed", strat.name)

        # 5) Sort by score descending
        all_opps.sort(key=lambda o: o.score, reverse=True)

        logger.info(
            "[SCAN] Scanner returning %d BTC opportunities (post-aggregation)",
            len(all_opps),
        )
        return all_opps

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_markets(self, limit: int = 500) -> List[Market]:
        """
        Try Polymarket client first. If client doesn't expose get_markets/fetch_markets
        or returns nothing, fall back to Gamma HTTP API.
        """
        raw = None

        # --- 1) Try client-based fetch if available ---
        if self.client is not None:
            try:
                if hasattr(self.client, "get_markets"):
                    logger.info("[POLY] Fetching markets via client.get_markets(limit=%d)…", limit)
                    raw = self.client.get_markets(limit=limit)
                elif hasattr(self.client, "fetch_markets"):
                    logger.info("[POLY] Fetching markets via client.fetch_markets(limit=%d)…", limit)
                    raw = self.client.fetch_markets(limit=limit)
                else:
                    logger.info(
                        "[POLY] Client has no get_markets/fetch_markets; skipping to HTTP fallback"
                    )

                if isinstance(raw, (list, tuple)) and raw:
                    parsed = parse_markets(list(raw))
                    logger.info(
                        "[POLY] Client returned %d raw markets, parsed %d usable markets",
                        len(raw),
                        len(parsed),
                    )
                    return parsed
            except Exception:
                logger.exception("[POLY] Error fetching markets from client; falling back to HTTP")

        # --- 2) HTTP fallback (Gamma API) ---
        try:
            import requests

            url = (
                "https://gamma-api.polymarket.com/markets?"
                f"limit={limit}&active=true&closed=false"
            )
            logger.info("[POLY HTTP fallback] GET %s", url)
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            raw = resp.json() or []
            if not isinstance(raw, list):
                logger.warning(
                    "[POLY HTTP fallback] Expected list from Gamma, got %s",
                    type(raw),
                )
                return []

            parsed = parse_markets(raw)
            logger.info(
                "[POLY HTTP fallback] fetched %d raw markets, parsed %d usable markets",
                len(raw),
                len(parsed),
            )
            return parsed

        except Exception as e:
            logger.error(
                "[POLY HTTP fallback] failed to fetch markets: %s",
                e,
                exc_info=True,
            )
            return []

    def _fetch_btc_price(self) -> float:
        """
        Unified BTC price helper – delegates to integrations.price_feeds.get_btc_price.
        """
        try:
            from ..integrations.price_feeds import get_btc_price

            return float(get_btc_price())
        except Exception as e:
            logger.error(
                "[PRICE] Failed to fetch BTC price; defaulting to 0. Error: %s",
                e,
                exc_info=True,
            )
            return 0.0
