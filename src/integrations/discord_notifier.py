import requests
from .link_resolver import LinkResolver

class DiscordNotifier:
    def __init__(self, webhook_url: str):
        self.url = webhook_url
        self.resolver = LinkResolver(timeout=6, verbose=True)

    def send(self, message: str):
        if not self.url:
            print("[DISCORD] Webhook not set. Message:\n", message)
            return
        for chunk in self._split_message(message):
            resp = requests.post(self.url, json={"content": chunk}, timeout=8)
            if resp.status_code >= 300:
                print(f"[DISCORD] Error {resp.status_code}: {resp.text}")

    def _split_message(self, text: str) -> list[str]:
        max_len = 1900
        if len(text) <= max_len:
            return [text]
        return [text[i:i + max_len] for i in range(0, len(text), max_len)]

    def format_opportunities(self, opps):
        if not opps:
            return "**No BTC opportunities detected this scan.**"

        intraday = []
        targets = []
        macro = []

        for o in opps:
            # Resolve a working URL (tests multiple candidates)
            safe_url = self.resolver.resolve(o.market) or "Link unavailable (resolver failed)"

            strike_txt, expiry_txt = "", ""
            market_prob = getattr(o, "yes_price", 0.0)
            if getattr(o, "meta", None):
                if "strike" in o.meta and o.meta["strike"]:
                    try: strike_txt = f" | K=${int(o.meta['strike']):,}"
                    except: pass
                if "days_to_expiry" in o.meta and o.meta["days_to_expiry"] is not None:
                    try: expiry_txt = f" | T={float(o.meta['days_to_expiry']):.1f}d"
                    except: pass
                market_prob = o.meta.get("market_prob", o.yes_price)

            line = (
                f"• **{o.type.upper()}** — {o.market.question[:70]}...\n"
                f"  → `{o.side}` @ {o.yes_price * 100:.1f}¢"
                f" | mkt={market_prob * 100:.2f}%"
                f" | fair={o.fair_prob * 100:.2f}%"
                f" | edge={o.edge_bp / 100:.2f}%"
                f"{strike_txt}{expiry_txt}\n"
                f"  🌐 {safe_url}\n"
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
