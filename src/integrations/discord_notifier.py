# src/integrations/discord_notifier.py
from __future__ import annotations

import requests
from typing import Optional


class DiscordNotifier:
    def __init__(self, webhook_url: Optional[str]):
        self.webhook_url = webhook_url

    def send(self, content: str) -> None:
        if not self.webhook_url:
            print("[DISCORD] Webhook not set. Message:\n", content)
            return

        resp = requests.post(self.webhook_url, json={"content": content}, timeout=10)
        if not resp.ok:
            print(f"[DISCORD] Error {resp.status_code}: {resp.text}")

