from __future__ import annotations
from typing import List

from ..integrations.polymarket_client import PolymarketClient
from ..integrations.price_feed import PriceFeed
from ..utils.config import AppConfig
from ..strategies.btc_intraday import BTCIntraday
from ..strategies.btc_price_target import BTCPriceTargets

class Scanner:
    def __init__(self, cfg, client):
        self.cfg = cfg
        self.client = client
        self.strategies = [
            BTCIntraday(),
            BTCPriceTargets(),
        ]


    def run_scan(self):
        markets = self.client.fetch_open_markets()

        # Live BTC spot (used by price-target strategy)
        try:
            btc = self.feed.btc_usd()
            print(f"[PRICE] BTC/USD={btc:.2f}")
        except Exception as e:
            print("[PRICE] Failed to fetch BTC price; defaulting to 0. Fair prob will degrade.", e)
            btc = 0.0

        opps = []
        for m in markets:
            ql = m.question.lower()
            if ("bitcoin" not in ql) and ("btc" not in ql):
                continue

            for strat in self.strats:
                scored = strat.score(m, btc)
                if scored and abs(scored.edge_bp) >= self.cfg.scan.min_edge_bp:
                    opps.append(scored)

        opps.sort(key=lambda o: abs(o.edge_bp), reverse=True)
        return opps[:10]
