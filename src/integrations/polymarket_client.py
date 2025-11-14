# src/integrations/polymarket_client.py
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, List
import requests


POLYMARKET_MARKETS_URL = "https://gamma-api.polymarket.com/markets"


@dataclass
class Outcome:
    name: str
    price: float  # 0–1 probability


@dataclass
class Market:
    id: str
    question: str
    url: str
    end_time: datetime
    outcomes: List[Outcome]


class PolymarketClient:
    def __init__(self, base_url: str = POLYMARKET_MARKETS_URL, timeout: int = 10):
        self.base_url = base_url
        self.timeout = timeout

    def _parse_outcomes(self, raw: dict[str, Any]) -> List[Outcome]:
        """
        outcomes / outcomePrices often come back as JSON-encoded strings.
        We:
          - parse both
          - pair names + prices by index
          - fall back to generic names if needed
        """
        outcomes_field = raw.get("outcomes")
        prices_field = raw.get("outcomePrices")

        def ensure_list(value):
            if value is None:
                return []
            if isinstance(value, list):
                return value
            if isinstance(value, str):
                try:
                    parsed = json.loads(value)
                    # some responses use '["YES","NO"]' style
                    return parsed
                except Exception:
                    # if it's a comma-separated string, last resort
                    return [v.strip() for v in value.split(",")]
            return []

        names = ensure_list(outcomes_field)
        prices = ensure_list(prices_field)

        outcomes: list[Outcome] = []
        for i, p in enumerate(prices):
            try:
                price = float(p)
            except (TypeError, ValueError):
                continue
            name = names[i] if i < len(names) else f"Outcome {i}"
            outcomes.append(Outcome(name=name, price=price))

        return outcomes

    def _parse_market(self, raw: dict[str, Any]) -> Market | None:
        question = raw.get("question") or raw.get("title")
        if not question:
            return None

        market_id = str(raw.get("id") or raw.get("_id") or "")
        if not market_id:
            return None

        # end date
        end_ts = raw.get("endDate") or raw.get("closesAt") or raw.get("end_time")
        if not end_ts:
            return None
        try:
            end_time = datetime.fromisoformat(end_ts.replace("Z", "+00:00")).astimezone(
                timezone.utc
            )
        except Exception:
            return None

        outcomes = self._parse_outcomes(raw)
        if len(outcomes) < 2:
            return None

        slug = raw.get("slug") or ""
        url = raw.get("url") or ""
        if not url:
            if slug:
                url = f"https://polymarket.com/event/{slug}"
            else:
                url = "https://polymarket.com/"

        return Market(
            id=market_id,
            question=question,
            url=url,
            end_time=end_time,
            outcomes=outcomes,
        )

    def fetch_open_markets(self, limit: int = 500) -> list[Market]:
        """
        Fetch active/open markets from Gamma.
        """
        params = {
            "closed": "false",
            "limit": limit,
            # "active": "true",  # can be added if needed
        }
        resp = requests.get(self.base_url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        # The API returns a raw list, not wrapped
        if isinstance(data, list):
            raw_markets = data
        elif isinstance(data, dict) and "markets" in data:
            raw_markets = data["markets"]
        else:
            raw_markets = []

        markets: list[Market] = []
        for raw in raw_markets:
            m = self._parse_market(raw)
            if m:
                markets.append(m)

        print(f"[POLY] fetched {len(raw_markets)} raw markets, parsed {len(markets)} usable markets")
        return markets
