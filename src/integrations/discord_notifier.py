import requests
import math

class DiscordNotifier:
    def __init__(self, webhook_url: str):
        self.url = webhook_url

    # ──────────────────────────────────────────────────────────────
    # Safe send: splits messages into Discord-safe chunks (<2000 chars)
    # ──────────────────────────────────────────────────────────────
    def send(self, message: str):
        if not self.url:
            print("[DISCORD] Webhook not set. Message:\n", message)
            return

        chunks = self._split_message(message)

        for chunk in chunks:
            resp = requests.post(
                self.url,
                json={"content": chunk},
                timeout=5
            )

            if resp.status_code >= 300:
                print(f"[DISCORD] Error {resp.status_code}: {resp.text}")

    # ──────────────────────────────────────────────────────────────
    def _split_message(self, text: str) -> list[str]:
        max_len = 1900  # leave buffer below Discord's 2000 limit
        if len(text) <= max_len:
            return [text]

        return [text[i:i+max_len] for i in range(0, len(text), max_len)]

    # ──────────────────────────────────────────────────────────────
    # Format BTC opportunities as compact 1-liners
    # ──────────────────────────────────────────────────────────────
    def format_opportunities(self, opps):
        if not opps:
            return "**No BTC opportunities detected this scan.**"

        intraday = []
        targets = []
        macro = []

        for o in opps:
            line = (
                f"• **{o.type.upper()}** — "
                f"{o.market.question[:70]}... "
                f"→ `{o.side}` @ {o.yes_price:.2f} "
                f"(edge: {o.edge_bp/100:.2f}%)\n"
            )

            if o.type == "intraday":
                intraday.append(line)
            elif o.type == "target":
                targets.append(line)
            else:
                macro.append(line)

        msg = "**BTC Mispriced Opportunities**\n\n"

        if intraday:
            msg += "__**Intraday Markets**__\n" + "".join(intraday) + "\n"

        if targets:
            msg += "__**Price Targets**__\n" + "".join(targets) + "\n"

        if macro:
            msg += "__**Macro / Other BTC**__\n" + "".join(macro) + "\n"

        return msg
