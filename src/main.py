import time
import traceback

from src.utils.config import load_config
from src.integrations.polymarket_client import PolymarketClient
from src.integrations.discord_notifier import DiscordNotifier
from src.core.scanner import Scanner
from src.core.risk_engine import RiskEngine


def main():
    print("[BOOT] Polymarket alpha bot (Full BTC Scanner) started")

    # ───────────────────────────────────────────────────────────
    # Load config (matches your existing AppConfig)
    # ───────────────────────────────────────────────────────────
    cfg = load_config()

    # Polymarket API client (use defaults from polymarket_client.py)
    client = PolymarketClient()

    # Scanner (BTC: intraday + targets + macro, depending on strategies)
    scanner = Scanner(cfg, client)

    # Discord notifier (your config has `discord.webhook_url`)
    notifier = DiscordNotifier(cfg.discord.webhook_url)

    # Risk engine (for position sizing + daily loss checks)
    risk = RiskEngine(cfg)

    # Scan interval (from your existing ScanConfig)
    SCAN_INTERVAL = cfg.scan.scan_interval_sec

    # ───────────────────────────────────────────────────────────
    # Main Loop
    # ───────────────────────────────────────────────────────────
    while True:
        try:
            print("[SCAN] Running BTC mispricing scan…")

            # Run the scanner – returns a list of ScoredOpportunity
            opps = scanner.run_scan()
            print(f"[SCAN] Scanner returned {len(opps)} BTC opportunities")

            # Limit how many we send to Discord (top N by edge)
            max_opps = 7
            top = opps[:max_opps]

            # Build and send Discord message (auto-splits inside notifier)
            msg = notifier.format_opportunities(top)
            notifier.send(msg)

            # Dry-run trade decisions using RiskEngine
            for o in top:
                decision = risk.should_trade()
                if not decision.allowed:
                    print(f"[TRADE] Skipping trade on '{o.market.question}': {decision.reason}")
                    continue

                size = risk.compute_position_size()
                print(
                    f"[TRADE-DRY-RUN] Would trade side={o.side}, "
                    f"size=${size:.2f}, "
                    f"market='{o.market.question}', "
                    f"edge={o.edge_bp/100:.2f}%"
                )

        except Exception as e:
            print("[ERROR] Exception during scan:")
            print(e)
            traceback.print_exc()

            # Best-effort notify Discord about the error
            try:
                notifier.send(f"**Polymarket BTC Scanner Error:**\n```\n{e}\n```")
            except Exception as inner_e:
                print("[ERROR] Failed to send error to Discord:", inner_e)

        # Sleep between scans
        print(f"[SLEEP] Sleeping {SCAN_INTERVAL} seconds…\n")
        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    main()
