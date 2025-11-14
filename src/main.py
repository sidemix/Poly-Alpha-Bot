import time
import traceback

from utils.config import load_config
from integrations.polymarket_client import PolymarketClient
from integrations.discord_notifier import DiscordNotifier
from core.scanner import Scanner


def main():
    print("[BOOT] Polymarket alpha bot (Full BTC Scanner) started")

    # ───────────────────────────────────────────────────────────
    # Load config
    # ───────────────────────────────────────────────────────────
    cfg = load_config()

    # Polymarket API client
    client = PolymarketClient(
        base_url=cfg.polymarket.base_url,
        timeout=cfg.polymarket.timeout
    )

    # Scanner (BTC full scanner: intraday + targets + macro)
    scanner = Scanner(cfg, client)

    # Discord notifier
    notifier = DiscordNotifier(cfg.discord.webhook)

    # Scan interval
    SCAN_INTERVAL = cfg.scan.interval_seconds

    # ───────────────────────────────────────────────────────────
    # Main Loop
    # ───────────────────────────────────────────────────────────
    while True:
        try:
            print("[SCAN] Running BTC mispricing scan…")

            # Fetch opportunities (top 10 raw)
            opps = scanner.run_scan()

            print(f"[SCAN] Found {len(opps)} BTC markets")

            # Limit to top N signals (configurable)
            top = opps[:cfg.scan.max_opportunities]

            # Format Discord message
            msg = notifier.format_opportunities(top)

            # Send to Discord (auto-split)
            notifier.send(msg)

            # Print trade dry-runs
            for o in top:
                print(
                    f"[TRADE-DRY-RUN] Would trade side={o.side}, size={cfg.trade.default_size}, "
                    f"market='{o.market.question}', edge={o.edge_bp/100:.2f}%"
                )

        except Exception as e:
            print("[ERROR] Exception during scan:")
            print(e)
            traceback.print_exc()

            notifier.send(f"**Polymarket BTC Scanner Error:**\n```\n{e}\n```")

        # Sleep between scans
        print(f"[SLEEP] Sleeping {SCAN_INTERVAL} seconds…\n")
        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    main()
