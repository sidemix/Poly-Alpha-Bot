# src/core/risk_engine.py
from __future__ import annotations

from dataclasses import dataclass
from .types import TradeDecision
from ..utils.config import AppConfig


@dataclass
class RiskState:
    daily_realized_pnl: float = 0.0
    trades_today: int = 0


class RiskEngine:
    def __init__(self, config: AppConfig):
        self.cfg = config
        self.state = RiskState()

    def hit_daily_loss_limit(self) -> bool:
        max_loss = -self.cfg.risk.account_value * self.cfg.risk.daily_max_loss_pct
        return self.state.daily_realized_pnl <= max_loss

    def compute_position_size(self) -> float:
        # Simple fixed % of account value
        return self.cfg.risk.account_value * self.cfg.risk.risk_per_trade_pct

    def register_trade_result(self, realized_pnl: float) -> None:
        self.state.daily_realized_pnl += realized_pnl
        self.state.trades_today += 1

    def should_trade(self) -> TradeDecision:
        if self.hit_daily_loss_limit():
            return TradeDecision(allowed=False, reason="Daily loss limit reached")
        return TradeDecision(allowed=True, reason="OK")

