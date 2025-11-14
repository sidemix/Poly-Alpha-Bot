from __future__ import annotations
import requests
from typing import List, Optional
from .polymarket_client import Market

BASE = "https://polymarket.com"

class LinkResolver:
    def __init__(self, timeout: int = 6, verbose: bool = True):
        self.timeout = timeout
        self.verbose = verbose

    def _ok(self, status: int) -> bool:
        return 200 <= status < 400

    def _probe(self, url: str) -> bool:
        try:
            # HEAD first
            r = requests.head(url, timeout=self.timeout, allow_redirects=True)
            if self._ok(r.status_code):
                return True
            # GET fallback (some endpoints block HEAD)
            r = requests.get(url, timeout=self.timeout, allow_redirects=True)
            return self._ok(r.status_code)
        except Exception:
            return False

    def _candidates(self, m: Market) -> List[str]:
        cands: List[str] = []

        # 0) If API gave us a first-party page URL, try it first.
        if m.api_url:
            cands.append(m.api_url)

        # 1) Event-style with ?tid=
        slugs = [m.event_slug, m.group_slug, m.generic_slug, m.question_slug, m.market_slug]
        slugs = [s for s in slugs if s]
        uniq_slugs: List[str] = []
        for s in slugs:
            if s not in uniq_slugs:
                uniq_slugs.append(s)

        if m.token_id:
            for s in uniq_slugs:
                cands.append(f"{BASE}/event/{s}?tid={m.token_id}")

        # 2) Event-style without tid (often lists outcomes and still works)
        for s in uniq_slugs:
            cands.append(f"{BASE}/event/{s}")

        # 3) Canonical market pages with various IDs Polymarket uses
        # Note: simple numeric id often fails, but we still try it early.
        if m.id:
            cands.append(f"{BASE}/market/{m.id}")
        if m.condition_id:
            cands.append(f"{BASE}/market/{m.condition_id}")
        if m.token_id:
            cands.append(f"{BASE}/market/{m.token_id}")

        # 4) Canonical + tid combos
        if m.id and m.token_id:
            cands.append(f"{BASE}/market/{m.id}?tid={m.token_id}")
        if m.condition_id and m.token_id:
            cands.append(f"{BASE}/market/{m.condition_id}?tid={m.token_id}")

        # Dedup
        seen = set()
        out: List[str] = []
        for u in cands:
            if u not in seen:
                out.append(u)
                seen.add(u)
        return out

    def resolve(self, m: Market) -> Optional[str]:
        tried: List[str] = []
        for url in self._candidates(m):
            tried.append(url)
            if self._probe(url):
                if self.verbose:
                    print(f"[URL] RESOLVED for '{m.question[:60]}…' -> {url}")
                return url
        if self.verbose:
            print(f"[URL] FAILED for '{m.question[:60]}…'\n       Tried:")
            for u in tried:
                print(f"         - {u}")
        return None
