# src/integrations/polymarket_client.py
from __future__ import annotations

import requests
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


POLYMARKET_MARKETS_URL = "https://gamma-api.polymarket.com/markets"


@dataclass
class Outcome:
    name: str
    price: float


@dataclass
class Market:
    id: str
    question: str
    url: str
    end_time: datetime
    outcomes: list[Outcome]


class PolymarketClient:
    def __init__(self, base_url: str = POLYMARKET_MARKETS_URL, timeout: int = 10):
        self.base_url = base_url
        self.timeout = timeout

    def _parse_market(self, raw: dict[str, Any]) -> Market | None:
        # NOTE: you will need to confirm these keys match actual API response
        question = raw.get("question") or raw.get("title")
        if not question or "bitcoin" not in question.lower():
            return None

        market_id = str(raw.get("id") or raw.get("_id") or "")
        if not market_id:
            return None

        # resolution / end date
        end_ts = raw.get("endDate") or raw.get("closesAt") or raw.get("end_time")
        if not end_ts:
            return None

        # Convert ISO string to datetime
        end_time = datetime.fromisoformat(end_ts.replace("Z", "+00:00")).astimezone(timezone.utc)

        # outcomes / prices
        outcomes_raw = raw.get("outcomes") or raw.get("outcomePrices") or []
        outcomes: list[Outcome] = []

        # outcomes_raw format can vary; here's a generic attempt
        if isinstance(outcomes_raw, list):
            for o in outcomes_raw:
                if isinstance(o, dict):
                    name = o.get("name") or o.get("outcome") or ""
                    price = o.get("price") or o.get("yesPrice") or o.get("probability")
                else:
                    continue

                if price is None:
                    continue
                outcomes.append(Outcome(name=name, price=float(price)))
        else:
            # unknown structure, skip
            return None

        if len(outcomes) < 2:
            return None

        url = raw.get("slug") or raw.get("url") or ""
        if url and not url.startswith("http"):
            url = f"https://polymarket.com/event/{url}"

        return Market(
            id=market_id,
            question=question,
            url=url,
            end_time=end_time,
            outcomes=outcomes,
        )

    def fetch_open_markets(self, limit: int = 500) -> list[Market]:
        params = {"closed": "false", "limit": limit}
        resp = requests.get(self.base_url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and "markets" in data:
            raw_markets = data["markets"]
        elif isinstance(data, list):
            raw_markets = data
        else:
            raw_markets = []

        markets: list[Market] = []
        for raw in raw_markets:
            m = self._parse_market(raw)
            if m:
                markets.append(m)
        return markets

