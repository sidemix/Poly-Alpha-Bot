import logging
from typing import Optional
from urllib.parse import urlparse

import requests

log = logging.getLogger(__name__)


class LinkResolver:
    """
    Small helper to normalize and resolve URLs before posting them to Discord.

    - Accepts timeout & verbose kwargs (to match DiscordNotifier usage).
    - Always returns either a final URL string or None (never raises out).
    """

    def __init__(self, timeout: float = 6.0, max_redirects: int = 5, verbose: bool = False):
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.verbose = verbose

    def _normalize(self, url: Optional[str]) -> Optional[str]:
        """Return a cleaned, absolute URL or None if it's unusable."""
        if not url:
            return None

        url = url.strip()
        if not url:
            return None

        parsed = urlparse(url)

        # If no scheme, assume https
        if not parsed.scheme:
            url = "https://" + url

        return url

    def resolve(self, url: Optional[str]) -> Optional[str]:
        """
        Best-effort resolution:
        - Normalize input (add https:// if missing).
        - Follow redirects (up to requests' default / server limits).
        - Return final URL or None on error.
        """
        norm = self._normalize(url)
        if not norm:
            return None

        try:
            resp = requests.get(
                norm,
                timeout=self.timeout,
                allow_redirects=True,
                headers={"User-Agent": "poly-alpha-bot/1.0"},
            )
            final_url = resp.url

            if self.verbose:
                log.info(
                    "[LinkResolver] %s -> %s (status=%s)",
                    url,
                    final_url,
                    resp.status_code,
                )

            return final_url
        except Exception as e:
            log.warning("[LinkResolver] failed to resolve %s: %s", url, e)
            return None
