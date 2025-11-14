import time
import traceback

from src.utils.config import load_config
from src.integrations.polymarket_client import PolymarketClient
from src.integrations.discord_notifier import DiscordNotifier
from src.core.scanner import Scanner


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

    # BTC Scanner (intraday + price targets + macro)
    scanner = Scanner(cfg, client)

    # Discord notifier
    notifier = DiscordNotifier(cfg.discord.webhook)

    # Scan every N seconds (from config.yaml)
    SCAN_INTERVAL = cfg.scan.interval_seconds

    # ───────────────────────────────────────────────────────────
    # Main Loop
    # ───────────────────────────────────────────────────────────
    while True:
        try:
            print("[SCAN] Running BTC mispricing scan…")

            # Raw scan (returns ALL BTC opportunities)
            opps = scanner.run_scan()

            print(f"[SCAN] Found {len(opps)} BTC markets")

            # Trim to top N results for Discord
            top = opps[:cfg.scan.max_opportunities]

            # Format and send to Discord
            msg = notifier.format_opportunities(top)
            notifier.send(msg)

            # Print local dry-run trades for future auto-exec
            for o in top:
                print(
                    f"[TRADE-DRY-RUN] Would trade side={o.side}, "
                    f"size={cfg.trade.default_size}, "
                    f"market='{o.market.question}', "
                    f"edge={o.edge_bp/100:.2f}%"
                )

        except Exception as e:
            print("[ERROR] Exception during scan:")
            print(e)
            traceback.print_exc()

            # Send error to Discord
            notifier.send(f"**Polymarket BTC Scanner Error:**\n```\n{e}\n```")

        # Sleep between scans
        print(f"[SLEEP] Sleeping {SCAN_INTERVAL} seconds…\n")
        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    main()
