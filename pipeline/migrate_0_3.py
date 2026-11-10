#!/usr/bin/env python3
"""Migrate a schema 0.2.0 tree to schema 0.3. Reads the snapshot, writes the repo.

    python pipeline/migrate_0_3.py

The script does not fetch any page. Timestamps come from pipeline/fetch_metadata.json.
"""
import datetime
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.lib.calendar import stamp
from pipeline.lib.layout import write_collection, write_json
from pipeline.lib.rules import load_countries, load_networks, repo_root
from pipeline.lib.transform import build_tree

SNAP = "/tmp/master-list-0.2.0"
DATA_NAMES = ("offers.json", "cards.json", "merchants.json", "issuers.json")


def snapshot(repo):
    """Keep a 0.2 copy so the migration can be repeated after the repo has changed."""
    marker = os.path.join(repo, "my", "offers.json")
    if os.path.exists(marker):
        if os.path.exists(SNAP):
            shutil.rmtree(SNAP)
        os.makedirs(SNAP)
        for country in ("my", "sg"):
            src = os.path.join(repo, country)
            if not os.path.isdir(src):
                continue
            dst = os.path.join(SNAP, country)
            os.makedirs(dst)
            for name in DATA_NAMES:
                path = os.path.join(src, name)
                if os.path.exists(path):
                    shutil.copy2(path, os.path.join(dst, name))
    if not os.path.exists(os.path.join(SNAP, "my", "offers.json")):
        raise SystemExit("no schema 0.2 offers.json to migrate")
    return SNAP


def _strip(record):
    return {key: value for key, value in record.items() if not key.startswith("_")}


def _by_issuer(records, country):
    grouped = {}
    for record in records:
        if record.get("country") != country:
            continue
        provider = record.get("provider")
        issuer = record.get("issuer_id") or (provider or {}).get("id")
        slug = issuer.split("-", 1)[1]
        grouped.setdefault(slug, []).append(_strip(record))
    return grouped


def write_tree(repo, tree):
    generated = tree["generated_at"]
    for country_code in sorted({card["country"] for card in tree["cards"]} | {offer["country"] for offer in tree["offers"]}):
        cc = country_code.lower()
        for kind, rows in (
            ("cards", [card for card in tree["cards"] if card["country"] == country_code]),
            ("offers", [offer for offer in tree["offers"] if offer["country"] == country_code and offer["_where"] == "live"]),
        ):
            folder = os.path.join(repo, cc, kind)
            if os.path.isdir(folder):
                shutil.rmtree(folder)
            os.makedirs(folder)
            for slug, items in sorted(_by_issuer(rows, country_code).items()):
                issuer_id = items[0].get("issuer_id") or items[0]["provider"]["id"]
                write_collection(
                    os.path.join(folder, slug + ".json"),
                    {
                        "schema_version": "0.3.0",
                        "country": country_code,
                        "issuer_id": issuer_id,
                        "generated_at": generated,
                    },
                    items,
                )
        archived = [offer for offer in tree["offers"] if offer["country"] == country_code and offer["_where"] == "archive"]
        archive_root = os.path.join(repo, cc, "archive", "offers")
        if os.path.isdir(os.path.join(repo, cc, "archive")):
            shutil.rmtree(os.path.join(repo, cc, "archive"))
        if archived:
            os.makedirs(archive_root)
            for slug, items in sorted(_by_issuer(archived, country_code).items()):
                for item in items:
                    item["status"] = "expired"
                write_collection(
                    os.path.join(archive_root, slug + ".json"),
                    {
                        "schema_version": "0.3.0",
                        "country": country_code,
                        "issuer_id": items[0]["provider"]["id"],
                        "generated_at": generated,
                        "archive": True,
                    },
                    items,
                )
        issuers = [issuer for issuer in tree["issuers"] if issuer["country"] == country_code]
        write_collection(
            os.path.join(repo, cc, "issuers.json"),
            {"schema_version": "0.3.0", "country": country_code, "generated_at": generated},
            issuers,
        )
        for obsolete in ("offers.json", "cards.json", "merchants.json"):
            path = os.path.join(repo, cc, obsolete)
            if os.path.exists(path):
                os.remove(path)
        index_dir = os.path.join(repo, cc, "index")
        if os.path.isdir(index_dir):
            shutil.rmtree(index_dir)

    global_dir = os.path.join(repo, "global")
    if os.path.isdir(global_dir):
        shutil.rmtree(global_dir)

    write_collection(
        os.path.join(repo, "merchants", "registry.json"),
        {"schema_version": "0.3.0", "generated_at": generated},
        tree["merchants"],
    )
    networks = dict(tree["networks"])
    networks["generated_at"] = generated
    write_json(os.path.join(repo, "networks.json"), networks)
    countries = {"schema_version": "0.3.0", "generated_at": generated, "items": load_countries()[0]}
    write_json(os.path.join(repo, "countries.json"), countries)

    summary = {}
    for code, meta in {item["code"]: item for item in load_countries()[0]}.items():
        cc = code.lower()
        offers = [offer for offer in tree["offers"] if offer["country"] == code and offer["_where"] == "live"]
        cards = [card for card in tree["cards"] if card["country"] == code]
        issuers = [issuer for issuer in tree["issuers"] if issuer["country"] == code]
        summary[code] = {
            "cards": len(cards),
            "offers": len(offers),
            "issuers": len(issuers),
            "timezone": meta["timezone"],
            "currency": meta["currency"],
            "path": f"/{cc}/",
        }
    manifest = {
        "schema_version": "0.3.0",
        "generated_at": generated,
        "name": "card-offer master list",
        "license": {
            "id": "CC-BY-4.0",
            "name": "Creative Commons Attribution 4.0 International",
            "url": "https://creativecommons.org/licenses/by/4.0/",
            "file": "LICENSE",
            "scope": "Compiled structured data only. Issuer terms belong to the issuers.",
        },
        "countries": summary,
        "merchants": len(tree["merchants"]),
        "networks": len(tree["networks"]["items"]),
        "layout": {
            "offers": "{cc}/offers/{issuer}.json",
            "cards": "{cc}/cards/{issuer}.json",
            "issuers": "{cc}/issuers.json",
            "archive": "{cc}/archive/offers/{issuer}.json",
            "merchants": "merchants/registry.json",
            "networks": "networks.json",
            "countries": "countries.json",
        },
        "indexes": "Built in CI and published to GitHub Pages. Not stored on the main branch.",
        "schemas": sorted(name for name in os.listdir(os.path.join(repo, "schema")) if name.endswith(".json")),
    }
    write_json(os.path.join(repo, "index.json"), manifest)


def before_counts(src):
    counts = {"offers": {}, "cards": {}, "merchants": 0}
    status = {}
    for country in ("my", "sg"):
        offers = load_items(src, country, "offers")
        cards = load_items(src, country, "cards")
        merchants = load_items(src, country, "merchants")
        counts["offers"][country.upper()] = len(offers)
        counts["cards"][country.upper()] = len(cards)
        counts["merchants"] += len(merchants)
        for card in cards:
            status[card.get("status") or "active"] = status.get(card.get("status") or "active", 0) + 1
    counts["offers"]["total"] = sum(counts["offers"].values())
    counts["cards"]["total"] = sum(v for k, v in counts["cards"].items())
    counts["card_status"] = status
    counts["offer_status"] = {"active_implicit": counts["offers"]["total"]}
    return counts


def load_items(src, country, name):
    with open(os.path.join(src, country, f"{name}.json"), encoding="utf-8") as fh:
        return json.load(fh)["items"]


def save_id_fixture(src, repo):
    fixture = {"offers": [], "cards": [], "merchants": []}
    seen_merchants = set()
    for country in ("my", "sg"):
        for offer in load_items(src, country, "offers"):
            fixture["offers"].append(offer["id"])
        for card in load_items(src, country, "cards"):
            fixture["cards"].append(card["id"])
        for merchant in load_items(src, country, "merchants"):
            if merchant["id"] not in seen_merchants:
                seen_merchants.add(merchant["id"])
                fixture["merchants"].append(merchant["id"])
    for key in fixture:
        fixture[key] = sorted(set(fixture[key]))
    path = os.path.join(repo, "tests", "fixtures", "ids_0_2_0.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(fixture, fh, indent=2)
        fh.write("\n")
    return fixture


def main():
    repo = repo_root()
    src = snapshot(repo)
    before = before_counts(src)
    save_id_fixture(src, repo)
    generated = stamp(datetime.datetime.now(datetime.timezone.utc))
    tree = build_tree(src, generated)
    write_tree(repo, tree)
    after = {
        "offers": {},
        "cards": {},
        "offer_status": {},
        "card_status": {},
    }
    for offer in tree["offers"]:
        if offer["_where"] != "live":
            after.setdefault("archive", []).append(offer["id"])
            continue
        after["offers"][offer["country"]] = after["offers"].get(offer["country"], 0) + 1
        after["offer_status"][offer["status"]] = after["offer_status"].get(offer["status"], 0) + 1
    for card in tree["cards"]:
        after["cards"][card["country"]] = after["cards"].get(card["country"], 0) + 1
        after["card_status"][card["status"]] = after["card_status"].get(card["status"], 0) + 1
    after["offers"]["total"] = sum(after["offers"].values())
    after["cards"]["total"] = sum(after["cards"].values())
    after["merchants"] = len(tree["merchants"])
    report = tree["report"]
    report["before"] = before
    report["after"] = after
    report["merchant_text_offers"] = sum(1 for offer in tree["offers"] if offer.get("merchant_text"))
    report["merchant_id_offers"] = sum(1 for offer in tree["offers"] if offer.get("merchant_id"))
    report["no_merchant_offers"] = sum(1 for offer in tree["offers"] if not offer.get("merchant_id") and not offer.get("merchant_text"))
    os.makedirs(os.path.join(repo, "reports"), exist_ok=True)
    with open(os.path.join(repo, "reports", "migration_0_3.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
        fh.write("\n")
    print(json.dumps({
        "before": before,
        "after": after,
        "merchants_out": report["merchants_out"],
        "dropped": report["dropped"],
        "unmatched": len(report["unmatched_checked_at"]),
        "date_review": len(report["date_review"]),
        "generated_at": generated,
    }, indent=2))


if __name__ == "__main__":
    main()
