#!/usr/bin/env python3
"""Ask robots.txt for each host a file cites and report the answers that leave the rules unreadable.

    python tools/robots_sweep.py crawler/ISSUER_CENSUS.md
    python tools/robots_sweep.py my/issuers.json

One request per host, 1.5 seconds apart, no page fetched. Hosts that answer 401, 403, 429, 5xx or
nothing are the hosts a conclusion in that file rests on blind: RULES.md section 2 step 3 says read
them anyway and flag the pages, and this tool says which ones that costs. Every probe goes through
`pipeline/fetcher.py`, so the log is the same private JSONL a crawl writes.

The host list is every https URL in the file. Pass `--json` to print machine-readable rows.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.fetcher import PoliteFetcher, wall_now  # noqa: E402

UA = os.environ.get("CRAWLER_USER_AGENT") or (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36")
READABLE = ("rules", "allow_all")


def hosts_in(path):
    text = open(path, encoding="utf-8").read()
    hosts = {m.split("/")[0] for m in re.findall(r"https://([^ |)\"']+)", text)}
    return sorted(hosts)


def main(argv):
    paths = [arg for arg in argv[1:] if not arg.startswith("--")]
    if not paths:
        print(__doc__)
        return 2
    hosts = hosts_in(paths[0])
    if not hosts:
        print(f"{paths[0]}: no https urls")
        return 2
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log = os.path.join(root, "raw", "logs", f"robots-sweep-{wall_now().strftime('%Y%m%dT%H%M%S')}.jsonl")
    fetcher = PoliteFetcher(log, hosts, UA, min_gap=1.5, timeout=8.0)

    rows = []
    for host in hosts:
        state, reason = fetcher.robots_for(f"https://{host}/")
        rows.append({"host": host, "state": state, "reason": reason if state == "unreadable" else None})
        if "--json" not in argv:
            print(f"{host}\t{state}\t{reason if state == 'unreadable' else ''}", flush=True)

    bad = [row for row in rows if row["state"] == "unreadable"]
    if "--json" in argv:
        print(json.dumps({"hosts": len(rows), "unreadable": bad, "log": log}, indent=1))
    else:
        print(f"\n{len(rows)} hosts, {len(bad)} unreadable, {sum(1 for r in rows if r['state'] in READABLE)} readable")
        print(f"log {log}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
