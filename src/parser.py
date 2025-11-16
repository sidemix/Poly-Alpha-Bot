import logging
from typing import Any, Dict, List

from .models import Market

logger = logging.getLogger(__name__)


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        if val is None:
            return default
        return float(val)
    except Exception:
        return default


def _normalize_outcomes(raw: Any) -> List[str]:
    """
    Normalize outcomes into a simple list of strings.

    - If list -> cast each element to str
    - If dict -> use values or keys
    - Else -> empty list
    """
    if isinstance(raw, list):
        return [str(x) for x in raw]

    if isinstance(raw, dict):
        # Some APIs use { "YES": {...}, "NO": {...} }
        # We just care about the keys as labels.
        return [str(k) for k in raw.keys()]

    return []


def _build_url(slug: str, raw: Dict[str, Any]) -> str:
    """
    Try to construct a reasonable Polymarket URL for this market.

    Priorities:
      1) raw["url"] if present
      2) eventSlug + market.slug shapes
      3) fallback to /event/{slug}
    """
    # If API already gives us a url, trust it.
    direct = raw.get("url")
    if isinstance(direct, str) and direct.startswith("http"):
        return direct

    slug = slug or str(raw.get("id") or "").strip()

    # Sometimes gamma APIs have 'eventSlug' or 'category'
    event_slug = raw.get("eventSlug") or raw.get("questionSlug")
    if isinstance(event_slug, str) and event_slug:
        # Typical Polymarket style: /event/{eventSlug}
        return f"https://polymarket.com/event/{event_slug}"

    if slug:
        # Fallback: at least build *something* clickable
        return f"https://polymarket.com/event/{slug}"

    # Worst-case: empty string; strategies should handle missing URL gracefully.
    return ""


def parse_markets(raw_markets: List[Dict[str, Any]]) -> List[Market]:
    """
    Parse raw markets from Gamma HTTP API into a list of Market dataclasses.

    This is the ONLY place we should translate the Polymarket JSON shape into
    our internal Market representation.
    """
    parsed: List[Market] = []

    if not isinstance(raw_markets, list):
        logger.warning(
            "[PARSER] Expected list of markets, got %s",
            type(raw_markets),
        )
        return parsed

    for idx, raw in enumerate(raw_markets):
        if not isinstance(raw, dict):
            logger.debug("[PARSER] Skipping non-dict market at index %d: %r", idx, raw)
            continue

        # ---- Core identifiers ----
        market_id = str(
            raw.get("id")
            or raw.get("_id")
            or raw.get("conditionId")
            or raw.get("marketId")
            or f"unknown-{idx}"
        )

        slug = str(raw.get("slug") or raw.get("questionSlug") or market_id).strip()

        title = str(
            raw.get("title")
            or raw.get("question")
            or raw.get("name")
            or raw.get("description")
            or ""
        ).strip()

        if not title:
            logger.debug("[PARSER] Skipping market with empty title: id=%s", market_id)
            continue

        # ---- URL ----
        url = _build_url(slug, raw)
        if not url:
            # Keep going, but log it so we know URL is missing
            logger.debug("[PARSER] Market missing URL: id=%s slug=%s title=%s", market_id, slug, title)

        # ---- Outcomes ----
        outcomes = _normalize_outcomes(raw.get("outcomes"))

        # ---- Volume / Liquidity ----
        volume = _safe_float(
            raw.get("volume")
            or raw.get("volume24h")
            or raw.get("totalVolume")
        )

        liquidity = _safe_float(
            raw.get("liquidity")
            or raw.get("openInterest")
            or raw.get("poolLiquidity")
        )

        # ---- Resolution / end date ----
        end_date = (
            raw.get("endDate")
            or raw.get("expiryDate")
            or raw.get("resolveTime")
            or raw.get("deadline")
        )
        if isinstance(end_date, (int, float)):
            # Leave as numeric timestamp; strategies can interpret if needed.
            end_date = str(end_date)

        resolved = bool(
            raw.get("resolved")
            or raw.get("closed")
            or raw.get("isResolved")
            or raw.get("isClosed")
        )

        market = Market(
            id=market_id,
            slug=slug,
            title=title,
            url=url or None,
            outcomes=outcomes,
            volume=volume,
            liquidity=liquidity,
            end_date=str(end_date) if end_date is not None else None,
            resolved=resolved,
            raw=raw,
        )

        parsed.append(market)

    logger.info(
        "[PARSER] Parsed %d/%d markets into Market objects",
        len(parsed),
        len(raw_markets),
    )
    return parsed
