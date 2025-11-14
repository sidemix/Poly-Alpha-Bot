# src/main.py
from __future__ import annotations

import time

from .utils.config import load_config
from .integrations.polymarket_client import PolymarketClient
from .integrations.discord_notifier import DiscordNotifier
from .core.scanner import Scanner
from .core.risk_engine import RiskEngine


def format_discord_message(opps):
    if not opps:
        return "No BTC up/down opportunities found this scan."

    lines = ["**Polymarket BTC Up/Down Scan**"]
    for i, o in enumerate(opps, start=1):
        title = o.market.question
        url = o.market.url
        yes_cents = round(o.yes_price * 100, 1)
        fair_pct = round(o.fair_prob * 100, 1)
        edge_pct = round(o.edge_bp / 100, 2)

        lines.append(
            f"\n**#{i}** {title}\n"
            f"🌐 {url}\n"
            f"💰 YES: {yes_cents}¢\n"
            f"🎯 Fair Prob: {fair_pct}%\n"
            f"📈 Edge: {edge_pct}% toward **{o.side}**"
        )
    return "\n".join(lines)


def main():
    cfg = load_config()
    client = PolymarketClient()
    scanner = Scanner(cfg, client)
    discord = DiscordNotifier(cfg.discord.webhook_url)
    risk = RiskEngine(cfg)

    print("[BOOT] Polymarket alpha bot (BTC up/down v1) started")

    while True:
        print("[SCAN] Running BTC up/down scan…")
        opps = scanner.run_scan()

        msg = format_discord_message(opps)
        discord.send(msg)

        for o in opps:
            # For now, just log dry-run trade decisions.
            decision = risk.should_trade()
            if not decision.allowed:
                print(f"[TRADE] Skipping trade: {decision.reason}")
                continue

            size = risk.compute_position_size()
            print(
                f"[TRADE-DRY-RUN] Would trade side={o.side}, "
                f"size=${size:.2f} on market='{o.market.question}' "
                f"edge={o.edge_bp/100:.2f}%"
            )

        print(f"[SLEEP] Sleeping {cfg.scan.scan_interval_sec} seconds…")
        time.sleep(cfg.scan.scan_interval_sec)


if __name__ == "__main__":
    main()

