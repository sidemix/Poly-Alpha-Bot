# src/utils/config.py
import os
from dataclasses import dataclass


@dataclass
class RiskConfig:
    account_value: float
    risk_per_trade_pct: float
    daily_max_loss_pct: float


@dataclass
class ScanConfig:
    scan_interval_sec: int
    min_edge_bp: float
    max_resolution_days: int


@dataclass
class DiscordConfig:
    webhook_url: str | None


@dataclass
class AppConfig:
    risk: RiskConfig
    scan: ScanConfig
    discord: DiscordConfig
    auto_trading_enabled: bool


def load_config() -> AppConfig:
    # You can later extend this to merge with YAML config files
    risk = RiskConfig(
        account_value=float(os.getenv("ACCOUNT_VALUE", "10000")),
        risk_per_trade_pct=float(os.getenv("RISK_PER_TRADE_PCT", "0.005")),  # 0.5%
        daily_max_loss_pct=float(os.getenv("DAILY_MAX_LOSS_PCT", "0.02")),   # 2%
    )

    scan = ScanConfig(
        scan_interval_sec=int(os.getenv("SCAN_INTERVAL_SEC", "600")),  # 10 min
        min_edge_bp=float(os.getenv("MIN_EDGE_BP", "150")),            # 1.5%
        max_resolution_days=int(os.getenv("MAX_RESOLUTION_DAYS", "1")),  # BTC up/down same day
    )

    discord = DiscordConfig(
        webhook_url=os.getenv("DISCORD_WEBHOOK")
    )

    cfg = AppConfig(
        risk=risk,
        scan=scan,
        discord=discord,
        auto_trading_enabled=os.getenv("AUTO_TRADING_ENABLED", "false").lower() == "true",
    )
    return cfg


# convenience global if you want to just import cfg
cfg = load_config()

