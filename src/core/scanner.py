import logging
from typing import List

from ..config import Config
from ..models import Market
from ..parser import parse_markets
from ..strategies.base import BaseStrategy, ScoredOpportunity
from ..strategies.btc_intraday import BTCIntraday
from ..strategies.btc_price_target import BTCPriceTargets

logger = logging.getLogger(__name__)


class Scanner:
    """
    Main Polymarket BTC scanner.

    - Loads markets from Gamma HTTP API
    - Parses them into Market objects
    - Filters to BTC/Bitcoin markets
    - Runs each strategy's score_many()
    """

    def __init__(self, cfg: Config, client) -> None:
        self.cfg = cfg
        self.client = client

        # All strategies must subclass BaseStrategy and implement score_many()
        self.strats: List[BaseStrategy] = [
            BTCIntraday(name="BTCIntraday", cfg=cfg),
            BTCPriceTargets(name="BTCPriceTargets", cfg=cfg),
        ]
        logger.info(
            "[SCAN] Scanner initialized with %d strategies: %s",
            len(self.strats),
            ", ".join(s.name for s in self.strats),
        )

    # ---------- Public API ----------

    def run_scan(self) -> List[ScoredOpportunity]:
        """
        Run one full BTC mispricing scan and return scored opportunities.
        """

        logger.info("[SCAN] Running BTC mispricing scan…")

        # 1) Fetch BTC price (Binance → Coinbase fallback is inside get_btc_price)
        btc_price = self._fetch_btc_price()
        logger.info("[PRICE] BTC/USD=%.2f", btc_price)

        # 2) Fetch open markets from Gamma HTTP API
        raw_markets = self._load_markets_http(limit=500)
        logger.info("[SCAN] Loaded %d raw open markets from Polymarket", len(raw_markets))

        # 3) Parse into Market objects
        markets: List[Market] = parse_markets(raw_markets)
        logger.info("[SCAN] Parsed %d markets after cleaning", len(markets))

        if not markets:
            logger.warning("[SCAN] No markets parsed; returning 0 opportunities")
            return []

        # 4) Filter to BTC/Bitcoin markets using Market.is_btc_market()
        btc_markets: List[Market] = [m for m in markets if m.is_btc_market()]
        logger.info(
            "[SCAN] BTC filter: %d / %d markets mention BTC or Bitcoin",
            len(btc_markets),
            len(markets),
        )

        # Log a few sample BTC markets so we can see what the bot is seeing
        for m in btc_markets[:5]:
            logger.info(
                "[SCAN] Sample BTC market: '%s' | slug=%s | outcomes=%s",
                m.title,
                m.slug,
                ",".join(m.outcomes or []),
            )

        if not btc_markets:
            logger.warning("[SCAN] No BTC markets found in latest batch; returning 0 opportunities")
            return []

        # 5) Run strategies
        all_scored: List[ScoredOpportunity] = []

        for strat in self.strats:
            try:
                scored = strat.score_many(btc_markets, btc_price)
                logger.info(
                    "[SCAN] Strategy '%s' produced %d candidates",
                    strat.name,
                    len(scored),
                )
                all_scored.extend(scored)
            except Exception:
                logger.exception("[SCAN] Strategy '%s' failed", strat.name)

        # 6) Sort by score (highest first) and return
        all_scored.sort(key=lambda s: s.score, reverse=True)
        logger.info("[SCAN] Scanner returning %d BTC opportunities", len(all_scored))
        return all_scored

    # ---------- Internals ----------

    def _fetch_btc_price(self) -> float:
        """
        Use shared price_feeds helper (Binance → Coinbase fallback).
        """
        from ..integrations.price_feeds import get_btc_price

        try:
            return float(get_btc_price())
        except Exception as e:
            logger.exception(
                "[PRICE] Fatal error fetching BTC price; defaulting to 0. %s",
                e,
            )
            return 0.0

    def _load_markets_http(self, limit: int = 500):
        """
        Fetch markets directly from Gamma HTTP API.

        Docs: https://gamma-api.polymarket.com/markets
        """
        import requests

        base_url = "https://gamma-api.polymarket.com/markets"
        params = {
            "active": "true",   # active markets only
            "limit": str(limit)
            # you *can* add "closed": "false" but docs say active=true is enough
        }

        try:
            resp = requests.get(base_url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, list):
                logger.info(
                    "[POLY HTTP] Fetched %d markets via Gamma (active=true, limit=%s)",
                    len(data),
                    params["limit"],
                )
                return data

            logger.warning(
                "[POLY HTTP] Unexpected /markets JSON shape (type=%s): %s",
                type(data),
                str(data)[:200],
            )
            return []
        except Exception:
            logger.exception("[POLY HTTP] Error fetching markets from Gamma")
            return []
