import logging
from typing import List

from ..parser import parse_markets
from ..models import Market, Opportunity
from ..strategies.btc_intraday import BTCIntraday
from ..strategies.btc_price_target import BTCPriceTargets

logger = logging.getLogger(__name__)


class Scanner:
    def __init__(self, cfg, client):
        self.cfg = cfg
        self.client = client
        self.strats = [
            BTCIntraday(cfg),
            BTCPriceTargets(cfg),
        ]

    def _load_markets(self, limit: int = 500) -> List[Market]:
        """
        Load raw markets from Polymarket, then parse -> List[Market].
        We try client methods first; if not available, we fall back to HTTP.
        """
        raw_markets = []

        # Try client methods first
        if hasattr(self.client, "fetch_markets"):
            logger.info("[POLY] Using client.fetch_markets(limit=%d)", limit)
            raw_markets = self.client.fetch_markets(limit=limit)
        elif hasattr(self.client, "get_markets"):
            logger.info("[POLY] Using client.get_markets(limit=%d)", limit)
            raw_markets = self.client.get_markets(limit=limit)
        else:
            logger.info("[POLY] Client has no get_markets/fetch_markets; skipping to HTTP fallback")
            try:
                from ..integrations.poly_http import fetch_markets_http

                raw_markets = fetch_markets_http(limit=limit)
            except Exception as e:
                logger.exception("[POLY HTTP fallback] Failed to fetch markets via HTTP: %s", e)
                raw_markets = []

        logger.info("[POLY] fetched %d raw markets", len(raw_markets))
        markets = parse_markets(raw_markets)
        logger.info("[POLY] parsed %d usable markets into Market objects", len(markets))
        return markets

    def run_scan(self) -> List[Opportunity]:
        logger.info("[SCAN] Running BTC mispricing scan…")

        markets: List[Market] = self._load_markets(limit=500)
        logger.info("[SCAN DEBUG] Total markets loaded: %d", len(markets))

        # 🔍 Simple BTC filter by title or ticker so we’re not over-restrictive
        btc_markets: List[Market] = [
            m for m in markets
            if (
                getattr(m, "title", "") and "bitcoin" in m.title.lower()
            ) or (
                getattr(m, "ticker", "") and "btc" in m.ticker.lower()
            )
        ]
        logger.info(
            "[SCAN DEBUG] BTC-related markets after filter: %d",
            len(btc_markets),
        )

        if not btc_markets:
            logger.info("[SCAN] No BTC markets found after filtering; nothing to score.")
            return []

        # 🔢 Fetch BTC price once per scan
        from ..integrations.price_feeds import get_btc_price

        btc_price = get_btc_price()
        logger.info("[PRICE] BTC/USD=%s (from price_feeds.get_btc_price)", btc_price)

        all_opps: List[Opportunity] = []

        for strat in self.strats:
            try:
                logger.info("[SCAN DEBUG] Running strategy '%s' on %d BTC markets…", strat.name, len(btc_markets))
                # Each strategy must implement score_many(markets, btc_price) -> List[Opportunity]
                strat_opps = strat.score_many(btc_markets, btc_price)
                logger.info(
                    "[SCAN DEBUG] Strategy '%s' produced %d opportunities before aggregation",
                    strat.name,
                    len(strat_opps),
                )
                all_opps.extend(strat_opps)
            except Exception as e:
                logger.exception("[SCAN] Strategy '%s' failed: %s", strat.name, e)

        logger.info(
            "[SCAN] Scanner returning %d BTC opportunities (post-aggregation)",
            len(all_opps),
        )
        return all_opps
