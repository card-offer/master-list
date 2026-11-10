#!/usr/bin/env python3
"""Build derived indexes from the published tree. Writes them outside the main branch payload.

    python tools/build_indexes.py . dist/indexes
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.lib.calendar import stamp
from pipeline.lib.layout import write_json


def load_items(folder):
    rows = []
    if not os.path.isdir(folder):
        return rows
    for name in sorted(os.listdir(folder)):
        if name.endswith(".json"):
            with open(os.path.join(folder, name), encoding="utf-8") as fh:
                rows.extend(json.load(fh)["items"])
    return rows


def load_tree(root):
    cards, offers, issuers, merchants = [], [], [], []
    for country in sorted(os.listdir(root)):
        folder = os.path.join(root, country)
        if not (len(country) == 2 and country.isalpha() and os.path.isdir(folder)):
            continue
        cards.extend(load_items(os.path.join(folder, "cards")))
        offers.extend(load_items(os.path.join(folder, "offers")))
        offers.extend(load_items(os.path.join(folder, "archive", "offers")))
        issuer_path = os.path.join(folder, "issuers.json")
        if os.path.exists(issuer_path):
            with open(issuer_path, encoding="utf-8") as fh:
                issuers.extend(json.load(fh)["items"])
    registry = os.path.join(root, "merchants", "registry.json")
    if os.path.exists(registry):
        with open(registry, encoding="utf-8") as fh:
            merchants = json.load(fh)["items"]
    return cards, offers, issuers, merchants


def expand(offer, cards_by_issuer, cards_by_id):
    """Return (resolved card ids, excluded card ids, confirmed). Inferred rules are not expanded."""
    rule = offer["eligibility"]
    confirmed = rule.get("confidence") == "stated" and bool(rule.get("evidence_text"))
    if not confirmed:
        return [], [], False
    scope = rule.get("scope")
    if scope == "card":
        return list(rule.get("card_ids") or []), [], True
    issuers = list(rule.get("issuer_ids") or [])
    if not issuers and offer["provider"]["type"] == "issuer":
        issuers = [offer["provider"]["id"]]
    pool = []
    if scope == "network" and not issuers:
        pool = list(cards_by_id.values())
    else:
        for issuer_id in issuers:
            pool.extend(cards_by_issuer.get(issuer_id, []))
    if scope == "issuer":
        return sorted({card["id"] for card in pool}), [], True
    networks = set(rule.get("network_ids") or [])
    resolved, excluded = [], []
    for card in pool:
        if card.get("status") == "needs_review" or not card.get("networks"):
            excluded.append(card["id"])
        elif networks & set(card.get("networks") or []):
            resolved.append(card["id"])
    return sorted(set(resolved)), sorted(set(excluded)), True


def _bucket():
    return {}


def add(entries, key, field, value):
    row = entries.setdefault(key, {})
    row.setdefault(field, [])
    if value not in row[field]:
        row[field].append(value)


def build(root, generated_at=None):
    generated_at = generated_at or stamp(datetime.datetime.now(datetime.timezone.utc))
    cards, offers, issuers, merchants = load_tree(root)
    cards_by_id = {card["id"]: card for card in cards}
    cards_by_issuer = {}
    for card in cards:
        cards_by_issuer.setdefault(card["issuer_id"], []).append(card)
    resolved_of = {}
    excluded_of = {}
    confirmed_of = {}
    for offer in offers:
        resolved, excluded, confirmed = expand(offer, cards_by_issuer, cards_by_id)
        resolved_of[offer["id"]] = resolved
        excluded_of[offer["id"]] = excluded
        confirmed_of[offer["id"]] = confirmed

    by_country = {}
    for card in cards:
        country = card["country"]
        pack = by_country.setdefault(country, {name: {} for name in (
            "by_merchant", "by_card", "by_issuer", "by_network", "by_category",
            "by_country", "by_benefit_type", "by_tier",
        )})
        add(pack["by_issuer"], card["issuer_id"], "card_ids", card["id"])
        add(pack["by_country"], country, "card_ids", card["id"])
        add(pack["by_tier"], card.get("tier") or "unknown", "card_ids", card["id"])
        for network in card.get("networks") or ["unknown"]:
            add(pack["by_network"], network, "card_ids", card["id"])
        for benefit_type in card.get("benefit_types") or []:
            add(pack["by_benefit_type"], benefit_type, "card_ids", card["id"])
        pack["by_card"].setdefault(card["id"], {})
    for offer in offers:
        country = offer["country"]
        pack = by_country.setdefault(country, {name: {} for name in (
            "by_merchant", "by_card", "by_issuer", "by_network", "by_category",
            "by_country", "by_benefit_type", "by_tier",
        )})
        provider = offer["provider"]
        if provider["type"] == "issuer":
            add(pack["by_issuer"], provider["id"], "offer_ids", offer["id"])
            if not confirmed_of[offer["id"]]:
                add(pack["by_issuer"], provider["id"], "unconfirmed_offer_ids", offer["id"])
        add(pack["by_category"], offer["category"], "offer_ids", offer["id"])
        add(pack["by_country"], country, "offer_ids", offer["id"])
        add(pack["by_benefit_type"], offer["benefit"]["type"], "offer_ids", offer["id"])
        if offer.get("merchant_id"):
            add(pack["by_merchant"], offer["merchant_id"], "offer_ids", offer["id"])
            for card_id in resolved_of[offer["id"]]:
                add(pack["by_merchant"], offer["merchant_id"], "card_ids", card_id)
        for card_id in resolved_of[offer["id"]]:
            add(pack["by_card"], card_id, "offer_ids", offer["id"])
            if offer.get("merchant_id"):
                add(pack["by_card"], card_id, "merchant_ids", offer["merchant_id"])
        networks = set(offer["eligibility"].get("network_ids") or [])
        for card_id in resolved_of[offer["id"]]:
            networks.update(cards_by_id[card_id].get("networks") or [])
        for network in networks:
            add(pack["by_network"], network, "offer_ids", offer["id"])
        for card_id in excluded_of[offer["id"]]:
            add(pack["by_network"], "needs_review", "excluded_card_ids", card_id)
    for key in by_country:
        for index_name, entries in by_country[key].items():
            for entry in entries.values():
                for field, values in entry.items():
                    entry[field] = sorted(set(values))
    return {
        "generated_at": generated_at,
        "by_country": by_country,
        "cards": cards,
        "offers": offers,
        "merchants": merchants,
        "resolved": resolved_of,
        "confirmed": confirmed_of,
    }


def write_indexes(root, dest, generated_at=None):
    built = build(root, generated_at)
    os.makedirs(dest, exist_ok=True)
    global_entries = {}
    for country, indexes in built["by_country"].items():
        country_dir = os.path.join(dest, country.lower())
        os.makedirs(country_dir, exist_ok=True)
        for name, entries in indexes.items():
            write_json(os.path.join(country_dir, name + ".json"), {
                "schema_version": "0.3.0",
                "key": name,
                "country": country,
                "generated_at": built["generated_at"],
                "entries": entries,
            })
            if name == "by_country":
                continue
            bucket = global_entries.setdefault(name, {})
            for key, entry in entries.items():
                target = bucket.setdefault(key, {})
                for field, values in entry.items():
                    target.setdefault(field, [])
                    target[field].extend(values)
    global_dir = os.path.join(dest, "global")
    os.makedirs(global_dir, exist_ok=True)
    for name, entries in global_entries.items():
        for entry in entries.values():
            for field, values in entry.items():
                entry[field] = sorted(set(values))
        write_json(os.path.join(global_dir, name + ".json"), {
            "schema_version": "0.3.0",
            "key": name,
            "country": None,
            "generated_at": built["generated_at"],
            "entries": entries,
        })
    return built


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    dest = sys.argv[2] if len(sys.argv) > 2 else "dist/indexes"
    built = write_indexes(root, dest)
    print(f"indexes written to {dest} offers {len(built['offers'])} cards {len(built['cards'])}")


if __name__ == "__main__":
    main()
