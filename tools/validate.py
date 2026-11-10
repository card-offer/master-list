#!/usr/bin/env python3
"""Validate the schema 0.3 tree.

    python tools/validate.py .

Countries come from the folder list. Thresholds come from config/rules.json.
A constant checked_at is rejected when the records do not share one fetched document.
An end date past the configured horizon is rejected unless end_date_reviewer_accepted is true.
"""
import datetime
import json
import os
import sys
import tempfile
from urllib.parse import urlparse

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.lib.calendar import add_months, parse_instant
from pipeline.lib.rules import load_rules
from pipeline.lib.transform import host_of
from tools.build_indexes import load_tree, write_indexes

SKIP_DIRS = {".git", "schema", "tools", "pipeline", "tests", "config", "merchants", "reports", "dist", ".github"}


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def registry_for(root):
    reg = Registry()
    schema_dir = os.path.join(root, "schema")
    for name in os.listdir(schema_dir):
        if not name.endswith(".json"):
            continue
        schema = load_json(os.path.join(schema_dir, name))
        reg = reg.with_resource(schema["$id"], Resource.from_contents(schema))
    return reg


def validator(root, reg, name):
    schema = load_json(os.path.join(root, "schema", name))
    return Draft202012Validator(schema, registry=reg, format_checker=FormatChecker())


def countries_of(root):
    found = []
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name)
        if os.path.isdir(path) and len(name) == 2 and name.isalpha() and name not in SKIP_DIRS:
            found.append(name)
    return found


def iter_data_files(root):
    for country in countries_of(root):
        issuer_file = os.path.join(root, country, "issuers.json")
        if os.path.exists(issuer_file):
            yield issuer_file, "issuers-file.schema.json"
        for kind, schema in (("cards", "cards-file.schema.json"), ("offers", "offers-file.schema.json")):
            folder = os.path.join(root, country, kind)
            if not os.path.isdir(folder):
                continue
            for name in sorted(os.listdir(folder)):
                if name.endswith(".json"):
                    yield os.path.join(folder, name), schema
        archive = os.path.join(root, country, "archive", "offers")
        if os.path.isdir(archive):
            for name in sorted(os.listdir(archive)):
                if name.endswith(".json"):
                    yield os.path.join(archive, name), "offers-file.schema.json"
    merchants = os.path.join(root, "merchants", "registry.json")
    if os.path.exists(merchants):
        yield merchants, "merchants-file.schema.json"
    for name, schema in (("networks.json", "networks-file.schema.json"), ("countries.json", "countries-file.schema.json")):
        path = os.path.join(root, name)
        if os.path.exists(path):
            yield path, schema


def check_constant_checked_at(records, where, errors):
    stamped = [row for row in records if row.get("checked_at")]
    if len(stamped) < 2:
        return
    times = {row["checked_at"] for row in stamped}
    if len(times) != 1:
        return
    fetches = {row.get("checked_fetch_url") for row in stamped}
    if len(fetches) == 1 and None not in fetches:
        return
    errors.append(f"{where}: constant checked_at across records that do not share one checked_fetch_url")


def check_horizon(offer, generated_at, max_months, errors):
    end = offer.get("end_date")
    if not end or offer.get("end_date_reviewer_accepted"):
        return
    limit = add_months(parse_instant(generated_at).date(), max_months)
    if datetime.date.fromisoformat(end) > limit:
        errors.append(f"{offer['id']}: end_date {end} is past the configured horizon")


def domains_for(offer, issuers, networks, merchants):
    provider = offer["provider"]
    allowed = set()
    if provider["type"] == "issuer":
        allowed.update((issuers.get(provider["id"]) or {}).get("official_domains") or [])
    elif provider["type"] == "network":
        allowed.update((networks.get(provider["id"]) or {}).get("official_domains") or [])
    elif provider["type"] == "merchant":
        domain = (merchants.get(provider["id"]) or {}).get("official_domain")
        if domain:
            allowed.add(domain)
    merchant = merchants.get(offer.get("merchant_id") or "")
    if merchant and merchant.get("official_domain"):
        allowed.add(merchant["official_domain"])
    for network in networks.values():
        allowed.update(network.get("official_domains") or [])
    return allowed


def offer_url_list(offer):
    urls = [
        offer.get("source_url"), offer.get("terms_url"), offer.get("dates_source_url"),
        offer.get("min_spend_source_url"), offer.get("cap_source_url"), offer.get("checked_fetch_url"),
    ]
    for source in offer.get("sources") or []:
        urls.append(source.get("url"))
    return [url for url in urls if isinstance(url, str) and url.startswith("http")]


def validate(root, index_dir=None):
    root = os.path.abspath(root)
    rules = load_rules()
    reg = registry_for(root)
    errors = []
    warnings = []
    countries = countries_of(root)
    if not countries:
        errors.append("no country folders")
    if os.path.isdir(os.path.join(root, "global")):
        errors.append("global/: derived indexes are built in CI and are not stored on main")
    for country in countries:
        if os.path.isdir(os.path.join(root, country, "index")):
            errors.append(f"{country}/index: derived indexes are built in CI and are not stored on main")
    for path, schema_name in iter_data_files(root):
        data = load_json(path)
        rel = os.path.relpath(path, root)
        for err in validator(root, reg, schema_name).iter_errors(data):
            errors.append(f"{rel} {err.json_path}: {err.message[:240]}")
        items = data.get("items") or []
        if schema_name in {"offers-file.schema.json", "cards-file.schema.json"}:
            check_constant_checked_at(items, rel, errors)
            generated_at = data.get("generated_at")
            for item in items:
                checked = item.get("checked_at")
                if checked and generated_at:
                    if parse_instant(checked) > parse_instant(generated_at):
                        errors.append(f"{item.get('id')}: checked_at {checked} is later than generated_at {generated_at}")
                if schema_name == "offers-file.schema.json":
                    check_horizon(item, generated_at, rules["end_date_max_months"], errors)
                    if "archive" in rel.replace("\\", "/") and item.get("status") != "expired":
                        errors.append(f"{item.get('id')}: archive offer status must be expired")
    cards, offers, issuers, merchants = load_tree(root)
    issuer_by = {row["id"]: row for row in issuers}
    merchant_by = {row["id"]: row for row in merchants}
    networks = {}
    network_path = os.path.join(root, "networks.json")
    if os.path.exists(network_path):
        for row in load_json(network_path)["items"]:
            networks[row["id"]] = row
    card_ids = {card["id"] for card in cards}
    for offer in offers:
        allowed = domains_for(offer, issuer_by, networks, merchant_by)
        for url in offer_url_list(offer):
            host = host_of(url)
            if host and host not in allowed:
                errors.append(f"{offer['id']}: host {host} is not an official domain of the provider, merchant or network")
        for card_id in offer["eligibility"].get("card_ids") or []:
            if card_id not in card_ids:
                errors.append(f"{offer['id']}: unknown card id {card_id}")
        if offer.get("merchant_id") and offer["merchant_id"] not in merchant_by:
            errors.append(f"{offer['id']}: unknown merchant id {offer['merchant_id']}")
        if offer["status"] == "active" and not offer.get("end_date"):
            errors.append(f"{offer['id']}: active offer is missing end_date")
        if offer["status"] == "evergreen" and offer.get("end_date"):
            errors.append(f"{offer['id']}: evergreen offer must not have an end date")
    for card in cards:
        allowed = set((issuer_by.get(card["issuer_id"]) or {}).get("official_domains") or [])
        urls = [card.get("official_url")]
        for source in card.get("sources") or []:
            urls.append(source.get("url"))
        for benefit in card.get("benefits") or []:
            urls.append(benefit.get("source_url"))
        for url in urls:
            if isinstance(url, str) and url.startswith("http"):
                host = host_of(url)
                if host and host not in allowed:
                    errors.append(f"{card['id']}: host {host} is not on issuer {card['issuer_id']} official_domains")
        if card.get("status") == "active" and not card.get("networks"):
            errors.append(f"{card['id']}: active card has an empty networks list")
    if index_dir is None:
        index_dir = tempfile.mkdtemp(prefix="card-offer-indexes-")
        write_indexes(root, index_dir)
    index_validator = validator(root, reg, "index.schema.json")
    for dirpath, _dirs, files in os.walk(index_dir):
        for name in files:
            if not name.endswith(".json"):
                continue
            path = os.path.join(dirpath, name)
            data = load_json(path)
            for err in index_validator.iter_errors(data):
                errors.append(f"{os.path.relpath(path, index_dir)} {err.json_path}: {err.message[:200]}")
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in {".git", "dist", "__pycache__"}]
        for name in files:
            if name.endswith((".json", ".md", ".yml", ".yaml")):
                text = open(os.path.join(dirpath, name), encoding="utf-8").read()
                if "\u2014" in text:
                    errors.append(f"{os.path.relpath(os.path.join(dirpath, name), root)}: contains an em dash")
    return errors, warnings, {
        "offers": len(offers),
        "cards": len(cards),
        "merchants": len(merchants),
        "countries": countries,
    }


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    errors, warnings, stats = validate(root)
    for warning in warnings[:50]:
        print("warning", warning)
    for error in errors[:80]:
        print(error)
    print(f"offers {stats['offers']}, cards {stats['cards']}, merchants {stats['merchants']}, countries {','.join(stats['countries'])}, errors {len(errors)}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
