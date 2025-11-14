# src/core/parser.py

from typing import Any, Dict, List
from .models import Market


def _s(x: Any) -> str:
    """
    Normalize arbitrary value to a safe string.
    - str -> stripped str
    - None / other -> ""
    """
    if isinstance(x, str):
        return x.strip()
    return ""


def _flt(x: Any):
    """
    Normalize numeric-ish value to float or None.
    """
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _int(x: Any):
    """
    Normalize numeric-ish value to int or None.
    """
    if x is None:
        return None
    try:
        return int(x)
    except (TypeError, ValueError):
        return None


def to_market(row: Dict[str, Any]) -> Market:
    """
    Convert a raw Polymarket /markets row (or similar structure)
    into our normalized Market model.

    This is defensive:
    - Handles either top-level fields or nested under "market"
    - Nones are converted to "" for string fields, so strategies
      can call `.lower()` / `.strip()` without blowing up.
    """
    # Some APIs wrap it like {"market": {...}}, others just give the dict
    mkt = row.get("market") or row

    # Try several ID-like keys; fall back to "" if totally missing
    market_id = (
        mkt.get("id")
        or mkt.get("slug")
        or mkt.get("conditionId")
        or mkt.get("questionId")
        or ""
    )

    # Time fields vary a lot between endpoints
    raw_end = (
        mkt.get("endDate")
        or mkt.get("endTime")
        or mkt.get("resolutionTime")
        or mkt.get("closeTime")
    )

    # Group / event / tournament-style label
    raw_group = (
        mkt.get("group")
        or mkt.get("event")
        or mkt.get("tournament")
        or mkt.get("collection")
    )

    # yes/no prices can come as "yesPrice"/"noPrice" or various aliases
    yes_price = (
        mkt.get("yesPrice")
        or mkt.get("yes_probability")
        or mkt.get("yes_prob")
        or mkt.get("buy_yes")
    )
    no_price = (
        mkt.get("noPrice")
        or mkt.get("no_probability")
        or mkt.get("no_prob")
        or mkt.get("buy_no")
    )

    # Tags may be missing, None, or non-list types
    raw_tags = mkt.get("tags") or []
    tags: List[str] = [t for t in raw_tags if isinstance(t, str)]

    return Market(
        id=str(market_id),
        url=_s(mkt.get("url") or mkt.get("link") or mkt.get("pageUrl")),
        title=_s(mkt.get("title")),
        question=_s(mkt.get("question") or mkt.get("name")),
        group=_s(raw_group),
        yes_price=_flt(yes_price),
        no_price=_flt(no_price),
        end_ts=_int(raw_end),
        tags=tags,
    )


def parse_markets(raw: Any) -> List[Market]:
    """
    Helper to parse a list of raw markets safely.
    Filters out non-dict items and returns a list of Market objects.
    """
    if not isinstance(raw, list):
        return []
    markets: List[Market] = []
    for item in raw:
        if isinstance(item, dict):
            try:
                markets.append(to_market(item))
            except Exception:
                # swallow a single bad row so the scan still runs
                continue
    return markets
