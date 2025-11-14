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
    # Core
    id: str
    question: str
    end_time: datetime
    outcomes: List[Outcome]

    # Possible URL-ish hints directly from API (use when present)
    api_url: Optional[str] = None

    # Identifiers we can compose into working links
    event_slug: Optional[str] = None
    group_slug: Optional[str] = None
    question_slug: Optional[str] = None
    generic_slug: Optional[str] = None
    market_slug: Optional[str] = None
    token_id: Optional[str] = None         # aka tid
    condition_id: Optional[str] = None

    # Final resolved link (filled by resolver)
    url: Optional[str] = None


class PolymarketClient:
    def __init__(self, base_url: str = POLYMARKET_MARKETS_URL, timeout: int = 10):
        self.base_url = base_url
        self.timeout = timeout

    # --- helpers --------------------------------------------------------------

    def _ensure_list(self, value) -> list:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            # Try to parse JSON first, else comma-split
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
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

    def _gx(self, raw: dict[str, Any], *keys: str) -> Optional[str]:
        for k in keys:
            v = raw.get(k)
            if v is not None:
                s = str(v).strip()
                if s:
                    return s
        return None

    def _parse_market(self, raw: dict[str, Any]) -> Optional[Market]:
        market_id    = self._gx(raw, "id", "_id")
        question     = self._gx(raw, "question", "title")
        end_ts       = self._gx(raw, "endDate", "closesAt", "end_time")
        if not market_id or not question or not end_ts:
            return None

        try:
            end_time = datetime.fromisoformat(end_ts.replace("Z", "+00:00")).astimezone(timezone.utc)
        except Exception:
            return None

        outcomes = self._parse_outcomes(raw)
        if len(outcomes) < 2:
            return None

        # URL-ish hints (some feeds include direct 'url' or 'pageUrl')
        api_url = self._gx(raw, "url", "pageUrl", "pageURL")

        # Slugs/IDs for link building
        event_slug    = self._gx(raw, "eventSlug", "event_slug", "groupSlug")
        group_slug    = self._gx(raw, "groupSlug")
        question_slug = self._gx(raw, "questionSlug", "marketSlug")
        generic_slug  = self._gx(raw, "slug")
        market_slug   = self._gx(raw, "marketSlug")
        token_id      = self._gx(raw, "tokenId", "token_id", "tid")
        condition_id  = self._gx(raw, "conditionId", "condition_id")

        return Market(
            id=market_id,
            question=question,
            end_time=end_time,
            outcomes=outcomes,
            api_url=api_url,
            event_slug=event_slug,
            group_slug=group_slug,
            question_slug=question_slug,
            generic_slug=generic_slug,
            market_slug=market_slug,
            token_id=token_id,
            condition_id=condition_id,
            url=None,
        )

    # --- public ---------------------------------------------------------------

    def fetch_open_markets(self, limit: int = 500) -> list[Market]:
        params = {"closed": "false", "limit": limit}
        resp = requests.get(self.base_url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        raw_markets = data if isinstance(data, list) else data.get("markets", [])
        markets: list[Market] = []
        for raw in raw_markets:
            m = self._parse_market(raw)
            if m:
                markets.append(m)

        print(f"[POLY] fetched {len(raw_markets)} raw markets, parsed {len(markets)} usable markets")
        return markets
