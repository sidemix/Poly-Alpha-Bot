import logging
from datetime import datetime
from typing import Any, List
from types import SimpleNamespace

log = logging.getLogger(__name__)


def _build_market_url(raw: dict) -> str | None:
    """
    Try to build a nice Polymarket URL for this market.

    We look for:
      - explicit "url" field
      - or "slug" / "slugSuffix"
      - or fall back to id-based URL

    If nothing usable found, return None.
    """
    if not isinstance(raw, dict):
        return None

    # If the API already gives us a URL, use it
    direct = raw.get("url") or raw.get("marketUrl")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    slug = raw.get("slug") or raw.get("slugSuffix") or raw.get("conditionId")
    if isinstance(slug, str) and slug.strip():
        return f"https://polymarket.com/event/{slug.strip()}"

    mid = raw.get("id") or raw.get("_id")
    if isinstance(mid, str) and mid.strip():
        return f"https://polymarket.com/event/{mid.strip()}"

    return None


def _parse_end_time(raw: dict) -> datetime | None:
    """
    Try to parse a resolution / end datetime from common Polymarket fields.
    Returns a timezone-aware datetime in UTC when possible, else None.
    """
    if not isinstance(raw, dict):
        return None

    candidates = [
        raw.get("endDate"),
        raw.get("closeDate"),
        raw.get("closesAt"),
        raw.get("end_time"),
        raw.get("resolutionTime"),
    ]

    for val in candidates:
        if not val:
            continue
        if isinstance(val, (int, float)):
            try:
                # assume seconds
                return datetime.utcfromtimestamp(float(val))
            except Exception:
                continue
        if isinstance(val, str):
            s = val.strip()
            if not s:
                continue
            try:
                # normalize Z suffix to +00:00 to satisfy fromisoformat
                if s.endswith("Z"):
                    s = s[:-1] + "+00:00"
                return datetime.fromisoformat(s)
            except Exception:
                continue

    return None


def _looks_like_btc_market(title: str, ticker_symbol: str) -> bool:
    """
    Heuristic filter: keep only markets that look like BTC/Bitcoin
    so strategies don't waste time on unrelated stuff.
    """
    t = (title or "").lower()
    sym = (ticker_symbol or "").lower()
    if not t:
        return False

    if sym and sym in t:
        return True

    # extra safety: also check for 'bitcoin'
    if "bitcoin" in t:
        return True

    return False


def parse_markets(raw_markets: list[Any], ticker_symbol: str = "BTC") -> List[Any]:
    """
    Convert the raw Polymarket markets payload into a list of
    lightweight objects with attribute access:

        market.id
        market.title
        market.question
        market.url
        market.slug
        market.end_time

    We purposely do NOT depend on src.models.* here, so this stays
    decoupled from whatever dataclasses you already defined.
    """
    parsed: List[Any] = []

    if not isinstance(raw_markets, list):
        log.warning(
            "[POLY] Expected list for raw_markets, got %s – treating as empty",
            type(raw_markets),
        )
        raw_markets = []

    for raw in raw_markets:
        if not isinstance(raw, dict):
            continue

        mid = str(raw.get("id") or raw.get("_id") or "").strip()

        # Title / question text
        question = (
            str(
                raw.get("question")
                or raw.get("title")
                or raw.get("name")
                or ""
            ).strip()
        )
        slug = str(raw.get("slug") or raw.get("slugSuffix") or "").strip()

        # Filter to BTC-related markets
        combined_title = f"{question} {slug}".strip()
        if not _looks_like_btc_market(combined_title, ticker_symbol):
            continue

        url = _build_market_url(raw)
        end_time = _parse_end_time(raw)

        # Fallbacks so strategies don't explode on None
        if not question:
            question = slug or mid or "(untitled market)"

        # Wrap in a SimpleNamespace so we get attribute access
        market = SimpleNamespace(
            id=mid,
            title=question,
            question=question,
            slug=slug,
            url=url,            # can be None; strategies should handle gracefully
            end_time=end_time,  # datetime | None
            raw=raw,            # full underlying dict in case we need it later
        )

        parsed.append(market)

    log.info(
        "[POLY] fetched %s raw markets, parsed %s usable markets",
        len(raw_markets),
        len(parsed),
    )
    return parsed
