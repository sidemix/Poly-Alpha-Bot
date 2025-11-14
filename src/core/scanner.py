# src/core/scanner.py
from __future__ import annotations

from typing import List

from ..integrations.polymarket_client import PolymarketClient, Market
from ..utils.config import AppConfig
from ..strategies.btc_up_down import BTCUpDownStrategy, ScoredOpportunity


class Scanner:
    def __init__(self, config: AppConfig, client: PolymarketClient):
        self.cfg = config
        self.client = client
        self.btc_strategy = BTCUpDownStrategy(config)

    def run_scan(self) -> List[ScoredOpportunity]:
        markets: list[Market] = self.client.fetch_open_markets()
        opps = self.btc_strategy.find_opportunities(markets)
        return opps[:5]

