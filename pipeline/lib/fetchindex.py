"""Match a record URL to pipeline/fetch_metadata.json."""
import json
import os
from urllib.parse import urlparse, urlunparse

from pipeline.lib.rules import repo_root


class FetchIndex:
    def __init__(self, path=None):
        path = path or os.path.join(repo_root(), "pipeline", "fetch_metadata.json")
        with open(path, encoding="utf-8") as fh:
            rows = json.load(fh)
        self.by = {}
        for row in rows:
            self.by.setdefault(row["url"], row)
            final = row.get("final_url")
            if final:
                self.by.setdefault(final, row)

    def lookup(self, url):
        if not url or not isinstance(url, str):
            return None
        raw = url.strip()
        candidates = [raw]
        parts = urlparse(raw)
        no_fragment = urlunparse(parts._replace(fragment=""))
        candidates.append(no_fragment)
        expanded = []
        for cand in candidates:
            expanded.append(cand)
            if cand.endswith("/"):
                expanded.append(cand[:-1])
            else:
                expanded.append(cand + "/")
        seen = set()
        for cand in expanded:
            if cand in seen:
                continue
            seen.add(cand)
            hit = self.by.get(cand)
            if hit:
                return hit
        return None

    def best(self, urls):
        """Latest fetch among the record's own URLs. Returns (fetched_at, metadata url) or None."""
        winner = None
        for url in urls:
            hit = self.lookup(url)
            if not hit:
                continue
            if winner is None or hit["fetched_at"] > winner[0]:
                winner = (hit["fetched_at"], hit["url"])
        return winner
