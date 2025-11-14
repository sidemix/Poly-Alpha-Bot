# src/core/types.py
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class TradeDecision:
    allowed: bool
    reason: str
