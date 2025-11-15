from __future__ import annotations

from typing import Any, Dict, List, Optional


class Market:
    """
    Lightweight, flexible container for a Polymarket market.

    Designed so parse_markets(...) can do something like:
        Market(
            id=raw["id"],
            question=raw.get("question") or raw.get("title") or "",
            url=raw.get("url"),
            group=raw.get("groupName"),
            outcomes=...,
            # plus any extra kwargs
        )

    Any extra keyword arguments are simply attached as attributes so
    strategies can reference things like `market.slug`, `market.end_time`,
    `market.group`, etc. without us having to define them all here.
    """

    def __init__(
        self,
        id: str,
        question: str,
        url: Optional[str] = None,
        group: Optional[str] = None,
        outcomes: Optional[List[Dict[str, Any]]] = None,
        **extra: Any,
    ) -> None:
        self.id = id
        self.question = question
        self.url = url
        self.group = group
        self.outcomes = outcomes or []

        # Attach any extra fields (end_time, slug, volume, etc.)
        for key, value in extra.items():
            setattr(self, key, value)

    def __repr__(self) -> str:
        return f"<Market id={self.id!r} question={self.question!r}>"


class Opportunity:
    """
    A trading recommendation on a single market & outcome.

    Fields here are intentionally minimal; we also allow extra kwargs which
    will be attached as attributes so Discord formatting / strategies
    can tack on whatever they need (fair_prob, mispricing_bps, notes, etc.).
    """

    def __init__(
        self,
        market: Market,
        outcome: str,
        side: str,
        limit_price: float,
        edge_bps: float,
        notes: Optional[str] = None,
        **extra: Any,
    ) -> None:
        # Core fields
        self.market = market          # Market object
        self.outcome = outcome        # e.g. "Yes", "No", "UP", "DOWN", "Shelton"
        self.side = side              # "BUY" / "SELL" or similar
        self.limit_price = float(limit_price)
        self.edge_bps = float(edge_bps)  # edge in basis points
        self.notes = notes

        # Attach any extra metadata your strategies want to include
        for key, value in extra.items():
            setattr(self, key, value)

    def __repr__(self) -> str:
        return (
            f"<Opportunity market={getattr(self.market, 'id', '?')!r} "
            f"outcome={self.outcome!r} side={self.side!r} "
            f"limit={self.limit_price:.4f} edge_bps={self.edge_bps:.1f}>"
        )

