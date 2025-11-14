from __future__ import annotations
import requests

class PriceFeed:
    def __init__(self, timeout: int = 5):
        self.timeout = timeout

    def btc_usd(self) -> float:
        # Simple, fast public endpoints. Try Coinbase first, fall back to Binance.
        try:
            r = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=self.timeout)
            r.raise_for_status()
            return float(r.json()["data"]["amount"])
        except Exception:
            r = requests.get("https://api.binance.com/api/v3/ticker/price", params={"symbol": "BTCUSDT"}, timeout=self.timeout)
            r.raise_for_status()
            return float(r.json()["price"])
