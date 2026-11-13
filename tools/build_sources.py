#!/usr/bin/env python3
"""Build the issuer rows of crawler/sources.json from the issuers.json files.

    python3 tools/build_sources.py           write crawler/sources.json and crawler/SOURCES.md
    python3 tools/build_sources.py --check   exit 1 if the committed files differ

Issuer rows come from my/issuers.json and sg/issuers.json: one cards row and one
offers row for each official domain. Card entry URLs come from crawl.card_sources.
Offer entry URLs come from crawl.offer_sources, then from pipeline/offers_config.json
seeds for that issuer, when the URL host matches the row. full_crawl_order comes
from the issuer table in crawler/FULL_CRAWL.md. An issuer that is in issuers.json
but not yet in that table is marked after-34, as the file says.

Network and regulator rows are kept as they are in crawler/sources.json. Status
and suggested_by on an issuer row are kept when the same issuer, host and purpose
already have a row; a new row is untested with suggested_by null.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "crawler" / "sources.json"
SOURCES_MD = ROOT / "crawler" / "SOURCES.md"
FULL_CRAWL = ROOT / "crawler" / "FULL_CRAWL.md"
OFFERS_CONFIG = ROOT / "pipeline" / "offers_config.json"

ISSUER_ORDER_RE = re.compile(r"^\|\s*(\d+)\s*\|\s*`([^`]+)`\s*\|", re.M)
AFTER_34 = "after-34"

ROW_KEYS = (
    "id", "site", "host", "country", "type", "purpose", "entry_urls",
    "status", "full_crawl_order", "suggested_by",
)


def host_of(value):
    if "://" in value:
        host = (urlsplit(value).hostname or "").lower()
    else:
        host = value.lower()
    return host[4:] if host.startswith("www.") else host


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def dump_json(data):
    return json.dumps(data, indent=1, ensure_ascii=False) + "\n"


def load_issuers(root):
    items = []
    for country in ("my", "sg"):
        items.extend(load_json(root / country / "issuers.json")["items"])
    return items


def issuer_orders(root):
    """Map issuer id to the integer order in crawler/FULL_CRAWL.md."""
    text = (root / "crawler" / "FULL_CRAWL.md").read_text(encoding="utf-8")
    found = {}
    for match in ISSUER_ORDER_RE.finditer(text):
        order, issuer_id = int(match.group(1)), match.group(2)
        if issuer_id in found and found[issuer_id] != order:
            raise ValueError(f"issuer {issuer_id} has two orders in FULL_CRAWL.md")
        found[issuer_id] = order
    return found


def urls_for_host(urls, host):
    seen = set()
    matched = []
    for url in urls or []:
        if host_of(url) != host or url in seen:
            continue
        seen.add(url)
        matched.append(url)
    return matched


def offer_entry_urls(issuer, host, offers_config):
    crawl = issuer.get("crawl") or {}
    urls = urls_for_host(crawl.get("offer_sources") or [], host)
    seen = set(urls)
    seeds = (offers_config.get(issuer["id"]) or {}).get("seeds") or []
    for url in seeds:
        if host_of(url) != host or url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def existing_issuer_index(items):
    index = {}
    for row in items:
        if row.get("type") != "issuer":
            continue
        index[(row.get("issuer_id"), row["host"], row["purpose"])] = row
    return index


def row_dict(base, extra=None):
    row = {key: base[key] for key in ROW_KEYS}
    if extra:
        row.update(extra)
    return row


def build_issuer_rows(root, existing_items, issuers, offers_config, orders):
    previous = existing_issuer_index(existing_items)
    rows = []
    for issuer in issuers:
        order = orders.get(issuer["id"], AFTER_34)
        hosts = sorted({host_of(domain) for domain in issuer["official_domains"]})
        crawl = issuer.get("crawl") or {}
        for host in hosts:
            for purpose in ("cards", "offers"):
                if purpose == "cards":
                    entry_urls = urls_for_host(crawl.get("card_sources") or [], host)
                else:
                    entry_urls = offer_entry_urls(issuer, host, offers_config)
                prior = previous.get((issuer["id"], host, purpose), {})
                status = prior.get("status", "untested")
                suggested = prior["suggested_by"] if "suggested_by" in prior else None
                rows.append(row_dict({
                    "id": f"{issuer['id']}-{host}-{purpose}",
                    "site": issuer["name"],
                    "host": host,
                    "country": issuer["country"],
                    "type": "issuer",
                    "purpose": purpose,
                    "entry_urls": entry_urls,
                    "status": status,
                    "full_crawl_order": order,
                    "suggested_by": suggested,
                }, {"issuer_id": issuer["id"]}))
    return rows


def order_sort_key(value):
    if value == "phase-1":
        return (0, 0, "")
    if isinstance(value, int):
        return (1, value, "")
    if value == AFTER_34:
        return (2, 0, "")
    text = str(value)
    if text.startswith("C"):
        try:
            return (3, int(text[1:]), "")
        except ValueError:
            return (3, 0, text)
    return (4, 0, text)


def sort_items(items):
    type_rank = {"regulator": 0, "issuer": 1, "network": 2, "merchant": 3}
    purpose_rank = {"census": 0, "cards": 1, "offers": 2}

    def key(row):
        return (
            type_rank.get(row["type"], 9),
            order_sort_key(row["full_crawl_order"]),
            row["country"],
            row["host"],
            purpose_rank.get(row["purpose"], 9),
            row["id"],
        )

    return sorted(items, key=key)


def build_sources(root=None):
    """Return the sources.json object built from the repository files."""
    root = Path(root) if root is not None else ROOT
    current = load_json(root / "crawler" / "sources.json")
    kept = [row for row in current["items"] if row.get("type") != "issuer"]
    issuers = load_issuers(root)
    offers_config = load_json(root / "pipeline" / "offers_config.json")
    orders = issuer_orders(root)
    issuer_rows = build_issuer_rows(root, current["items"], issuers, offers_config, orders)
    items = sort_items(kept + issuer_rows)
    return {
        "description": current.get("description") or (
            "Canonical list of sites to crawl for Malaysia and Singapore. "
            "Every official issuer or network host, and the phase 1 regulator hosts, "
            "must appear here before a crawl. See crawler/SOURCES.md."
        ),
        "items": items,
    }


GUIDE_HEAD = """# Crawl sources

This file describes the canonical list of sites to crawl for Malaysia (MY) and Singapore (SG). The list itself is [`crawler/sources.json`](sources.json). Do not crawl a host that is not on the list.

Issuer rows are built by `tools/build_sources.py` from `{cc}/issuers.json` official domains and entry URLs, and from `pipeline/offers_config.json` seeds. Network and regulator rows are kept as they are in `crawler/sources.json`. A host also has to be in the issuer's or the network's `official_domains`, except for the two regulator sites used in the phase 1 census.

## How to read a row

| Field | Meaning |
|---|---|
| `site` | The issuer, network or regulator name. |
| `host` | The official host, without a leading `www.` |
| `country` | `MY` or `SG`. |
| `type` | `issuer`, `network` or `regulator`. |
| `purpose` | `cards` or `offers` for crawl pages, and `census` for the regulator lists. |
| `entry_urls` | Known listing or start URLs from the repository. An empty list means the host is official but no start URL is recorded yet. |
| `status` | Fetcher class from repository evidence only: `ok`, `js_shell`, `bot_wall`, `network_unreachable`, or `untested` when the repository has no such evidence. Do not invent a status. |
| `full_crawl_order` | The order in `crawler/FULL_CRAWL.md`: `1` to `34` for issuers in that table, `after-34` for a phase 1 issuer not yet given a number, `C1` to `C12` for network offer sites, and `phase-1` for regulators. |
| `suggested_by` | The GitHub issue that proposed the site, or `null` when the row came from the repository itself. |

## Suggesting a site

Contributors can propose a site with the "Suggest a site to crawl" issue form. The triage is in `CONTRIBUTING.md`. A maintainer checks that the site is official, probes it with `pipeline/fetcher.py`, and opens a pull request that adds a row here. Suggestions that are not official bank, network, merchant or regulator pages are declined.

## The list

"""


def render_sources_md(data):
    items = data["items"]
    by_country = Counter(row["country"] for row in items)
    by_type = Counter(row["type"] for row in items)
    counts = (
        f"There are {len(items)} rows in `crawler/sources.json`. "
        f"Counts by country: MY {by_country.get('MY', 0)}, SG {by_country.get('SG', 0)}. "
        f"Counts by type: issuer {by_type.get('issuer', 0)}, "
        f"network {by_type.get('network', 0)}, regulator {by_type.get('regulator', 0)}.\n"
    )
    lines = [
        counts,
        "| Order | Country | Type | Purpose | Site | Host | Status | Entry URLs |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in items:
        urls = ", ".join(row["entry_urls"])
        lines.append(
            f"| {row['full_crawl_order']} | {row['country']} | {row['type']} | "
            f"{row['purpose']} | {row['site']} | `{row['host']}` | {row['status']} | {urls} |"
        )
    return GUIDE_HEAD + "\n".join(lines) + "\n"


def write_sources(root=None):
    root = Path(root) if root is not None else ROOT
    data = build_sources(root)
    (root / "crawler" / "sources.json").write_text(dump_json(data), encoding="utf-8")
    (root / "crawler" / "SOURCES.md").write_text(render_sources_md(data), encoding="utf-8")
    return data


def check_sources(root=None):
    root = Path(root) if root is not None else ROOT
    data = build_sources(root)
    json_ok = (root / "crawler" / "sources.json").read_text(encoding="utf-8") == dump_json(data)
    md_ok = (root / "crawler" / "SOURCES.md").read_text(encoding="utf-8") == render_sources_md(data)
    return json_ok, md_ok, data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="do not write; exit 1 if the committed files differ")
    parser.add_argument("--root", default=str(ROOT), help="repository root")
    args = parser.parse_args(argv)
    root = Path(args.root)
    if args.check:
        json_ok, md_ok, data = check_sources(root)
        if json_ok and md_ok:
            print(f"crawler/sources.json and crawler/SOURCES.md match the builder ({len(data['items'])} rows).")
            return 0
        if not json_ok:
            print("crawler/sources.json differs from tools/build_sources.py. Run python3 tools/build_sources.py.")
        if not md_ok:
            print("crawler/SOURCES.md differs from tools/build_sources.py. Run python3 tools/build_sources.py.")
        return 1
    data = write_sources(root)
    print(f"Wrote crawler/sources.json and crawler/SOURCES.md ({len(data['items'])} rows).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
