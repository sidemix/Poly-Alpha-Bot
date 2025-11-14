from __future__ import annotations
from typing import List
from src.strategies.btc_intraday import BTCIntraday
from src.strategies.btc_price_target import BTCPriceTargets
from src.strategies.btc_macro import BTCMacro
from src.integrations.polymarket_client import PolymarketClient
from src.utils.config import AppConfig



class Scanner:
    def __init__(self, cfg: AppConfig, client: PolymarketClient):
        self.cfg = cfg
        self.client = client

        self.strats = [
            BTCIntraday(cfg),
            BTCPriceTargets(cfg),
            BTCMacro(cfg)
        ]

    def get_btc_price(self):
        # placeholder: soon we plug Binance/Coinbase API here
        return None

    def run_scan(self):
        markets = self.client.fetch_open_markets()
        current_price = 0  # plug in real BTC later

        opps = []
        for m in markets:
            if not ("bitcoin" in m.question.lower() or "btc" in m.question.lower()):
                continue

            for strat in self.strats:
                scored = strat.score(m, current_price)
                if scored:
                    opps.append(scored)

        opps.sort(key=lambda o: abs(o.edge_bp), reverse=True)
        return opps[:10]
