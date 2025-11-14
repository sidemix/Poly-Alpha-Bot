"""
Simple, defensive link resolver for Polymarket markets.

This is intentionally very forgiving so it won't crash even if it's given
None, strings, dicts, or Market-like objects. It just tries to return a
reasonable URL string, or "" as a safe fallback.
"""

from __future__ import annotations
from typing import Any, Optional


class LinkResolver:
    """
    Resolves a "best" URL for a market or raw API object.

    Designed to be extremely defensive so that any call pattern from
    DiscordNotifier won't blow up:
    - resolve(...)
    - for_market(...)
    - for_url(...)
    - resolve_or_default(...)
    - __call__(...)
    all route to the same core logic.
    """

    def __init__(self, default_base: str = "https://polymarket.com"):
        self.default_base = default_base.rstrip("/")

    # --- Public API -----------------------------------------------------

    def resolve(
        self,
        market: Any = None,
        url: Optional[str] = None,
        default: str = "",
        **_: Any,
    ) -> str:
        """
        Try to extract a URL from:
        - explicit `url` parameter
        - market.url attribute
        - market.link / market.pageUrl attributes
        - dict-like keys: "url", "link", "pageUrl", "slug"
        If nothing works, return `default` (or "").
        """
        # 1) explicit url wins
        if isinstance(url, str) and url.strip():
            return self._normalize(url)

        # 2) Market-like object with attributes
        if market is not None:
            # if it's already a string, treat as url/slug
            if isinstance(market, str):
                return self._normalize(market)

            # object with attributes
            attr_url = getattr(market, "url", None) or getattr(market, "link", None) or getattr(market, "pageUrl", None)
            if isinstance(attr_url, str) and attr_url.strip():
                return self._normalize(attr_url)

            # 3) dict-like access
            if isinstance(market, dict):
                raw = (
                    market.get("url")
                    or market.get("link")
                    or market.get("pageUrl")
                    or market.get("slug")
                    or market.get("id")
                )
                if isinstance(raw, str) and raw.strip():
                    return self._normalize(raw)

        # 4) Fallback to provided default or empty string
        if isinstance(default, str):
            return default
        return ""

    def for_market(self, market: Any, **kwargs: Any) -> str:
        """Alias: resolve based on a market object."""
        return self.resolve(market=market, **kwargs)

    def for_url(self, url: str, **kwargs: Any) -> str:
        """Alias: resolve based on a raw URL/slug."""
        return self.resolve(url=url, **kwargs)

    def resolve_or_default(self, market: Any = None, url: Optional[str] = None, default: str = "") -> str:
        """Explicit alias some codebases like to call."""
        return self.resolve(market=market, url=url, default=default)

    def __call__(self, *args: Any, **kwargs: Any) -> str:
        """
        Allow instances to be used like a function:
        link_resolver(market) -> url
        """
        return self.resolve(*args, **kwargs)

    # --- Internal helpers -----------------------------------------------

    def _normalize(self, raw: str) -> str:
        """
        Normalize Polymarket URLs:
        - If already an absolute URL, return as-is.
        - If it's a slug like '/event/...' or 'event/...' -> attach base.
        - If it's something else, just return stripped.
        """
        if not isinstance(raw, str):
            return ""

        s = raw.strip()
        if not s:
            return ""

        lower = s.lower()
        if lower.startswith("http://") or lower.startswith("https://"):
            return s

        # handle slugs like "/event/..." or "event/..."
        if lower.startswith("/event/") or lower.startswith("event/"):
            if not s.startswith("/"):
                s = "/" + s
            return f"{self.default_base}{s}"

        # unknown pattern, just return stripped
        return s
