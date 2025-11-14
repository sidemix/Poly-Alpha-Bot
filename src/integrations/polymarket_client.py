from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, List, Optional
import requests

POLYMARKET_MARKETS_URL = "https://gamma-api.polymarket.com/markets"


@dataclass
class Outcome:
    name: str
    price: float  # probability 0–1


@dataclass
class Market:
    id: str
    question: str
    url: str                  # CHOSEN link (we will set this to canonical /market/<id>)
    end_time: datetime
    outcomes: List[Outcome]

    # Optional metadata (debug only; DO NOT USE FOR LINKS)
    market_url: str           # always /market/<id> (stable)
    event_url: Optional[str]  # event slug + tid if present (may 404; debug only)
    event_slug: Optional[str]
    token_id: Optional[str]


class PolymarketClient:
    def __init__(self, base_url: str = POLYMARKET_MARKETS_URL, timeout: int = 10):
        self.base_url = base_url
        self.timeout = timeout

    # --- helpers --------------------------------------------------------------

    def _ensure_list(self, value) -> list:
        """Polymarket sometimes returns JSON strings for outcomes/prices."""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            # try JSON first
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                # last resort: comma-split
                return [v.strip() for v in value.split(",") if v.strip()]
        return []

    def _parse_outcomes(self, raw: dict[str, Any]) -> List[Outcome]:
        names = self._ensure_list(raw.get("outcomes"))
        prices = self._ensure_list(raw.get("outcomePrices"))

        outcomes: list[Outcome] = []
        for i, p in enumerate(prices):
            try:
                price = float(p)
            except (TypeError, ValueError):
                continue
            name = names[i] if i < len(names) else f"Outcome {i}"
            outcomes.append(Outcome(name=name, price=price))
        return outcomes

    def _parse_market(self, raw: dict[str, Any]) -> Optional[Market]:
        # id
        market_id = str(raw.get("id") or raw.get("_id") or "").strip()
        if not market_id:
            return None

        # question
        question = (raw.get("question") or raw.get("title") or "").strip()
        if not question:
            return None

        # end time
        end_ts = raw.get("endDate") or raw.get("closesAt") or raw.get("end_time")
        if not end_ts:
            return None
        try:
            end_time = datetime.fromisoformat(end_ts.replace("Z", "+00:00")).astimezone(timezone.utc)
        except Exception:
            return None

        # outcomes
        outcomes = self._parse_outcomes(raw)
        if len(outcomes) < 2:
            return None

        # Optional event metadata (debug only)
        event_slug = (
            raw.get("eventSlug")
            or raw.get("event_slug")
            or raw.get("groupSlug")
            or raw.get("slug")
        )
        token_id = (
            raw.get("tokenId")
            or raw.get("token_id")
            or raw.get("conditionId")
            or raw.get("tid")
        )
        if event_slug:
            event_slug = str(event_slug).strip()
        if token_id:
            token_id = str(token_id).strip()

        # Canonical market link (STABLE)
        market_url = f"https://polymarket.com/market/{market_id}"

        # Event URL (often fragile; keep only for debugging)
        event_url = f"https://polymarket.com/event/{event_slug}?tid={token_id}" if (event_slug and token_id) else None

        # 🚨 CHOOSE CANONICAL URL — never event_url
        chosen_url = market_url

        return Market(
            id=market_id,
            question=question,
            url=chosen_url,         # <— canonical
            end_time=end_time,
            outcomes=outcomes,
            market_url=market_url,  # debug
            event_url=event_url,    # debug
            event_slug=event_slug,  # debug
            token_id=token_id,      # debug
        )

    # --- public ---------------------------------------------------------------

    def fetch_open_markets(self, limit: int = 500) -> list[Market]:
        params = {
            "closed": "false",
            "limit": limit,
        }
        resp = requests.get(self.base_url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

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
