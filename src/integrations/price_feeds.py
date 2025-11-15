import logging
from typing import Any
import requests


def get_btc_price(*args: Any, **kwargs: Any) -> float:
    """
    Return BTC/USD price using public HTTP APIs.

    This function is intentionally flexible:
    - It accepts any *args / **kwargs so it won't break if the caller
      passes (cfg), (cfg, logger=...), or just (logger=...).
    - It looks for a 'logger' kwarg; if missing, it creates its own logger.

    Order:
      1) Binance (may fail with 451 in some regions)
      2) Coinbase fallback
    """
    logger = kwargs.get("logger", logging.getLogger("price_feeds"))

    # --- Try Binance first ---
    binance_url = "https://api.binance.com/api/v3/ticker/price"
    params = {"symbol": "BTCUSDT"}

    try:
        resp = requests.get(binance_url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        price = float(data["price"])
        logger.info("[PRICE] BTC/USD=%s (via Binance)", price)
        return price
    except Exception as e:
        logger.warning(
            "[PRICE] Binance price fetch failed: %s. Falling back to Coinbase...",
            e,
        )

    # --- Coinbase fallback ---
    cb_url = "https://api.exchange.coinbase.com/products/BTC-USD/ticker"

    try:
        resp = requests.get(cb_url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        # Coinbase returns e.g. {"price": "95321.23", ...}
        price = float(data["price"])
        logger.info("[PRICE] BTC/USD=%s (via Coinbase)", price)
        return price
    except Exception as e:
        logger.error("[PRICE] Coinbase price fetch failed: %s", e)

    # If everything fails, raise a hard error so the caller can decide
    raise RuntimeError("All BTC price feeds failed (Binance + Coinbase).")
