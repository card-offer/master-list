#!/usr/bin/env python3
"""Validate the schema 0.3 tree.

    python tools/validate.py .

Countries come from the folder list. Thresholds come from config/rules.json.
A constant checked_at is rejected when the records do not share one fetched document.
An end date past the configured horizon is rejected unless end_date_reviewer_accepted is true.
"""
import datetime
import hashlib
import json
import os
import re
import sys
import tempfile
from urllib.parse import urlparse

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.lib.merchants import load_merchant_rules, name_key
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


def parse_instant_or_error(value):
    try:
        return parse_instant(value), None
    except (ValueError, TypeError) as exc:
        return None, str(exc)


def parse_date_or_error(value):
    try:
        return datetime.date.fromisoformat(value), None
    except (ValueError, TypeError) as exc:
        return None, str(exc)


def check_horizon(offer, generated_at, max_months, errors):
    end = offer.get("end_date")
    if not end or offer.get("end_date_reviewer_accepted"):
        return
    generated, generated_error = parse_instant_or_error(generated_at)
    if generated_error:
        errors.append(f"{offer['id']}: generated_at is not a valid date-time ({generated_error})")
        return
    parsed, date_error = parse_date_or_error(end)
    if date_error:
        errors.append(f"{offer['id']}: end_date is not a valid date ({date_error})")
        return
    limit = add_months(generated.date(), max_months)
    if parsed > limit:
        errors.append(f"{offer['id']}: end_date {end} is past the configured horizon")


def network_id_for_host(host, networks):
    if not host:
        return None
    for network_id, row in networks.items():
        for domain in row.get("official_domains") or []:
            domain = domain.lower()
            if host == domain or host.endswith("." + domain):
                return network_id
    return None


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
    return allowed


def load_fetch_pairs(root):
    path = os.path.join(root, "pipeline", "fetch_metadata.json")
    pairs = set()
    if not os.path.exists(path):
        return pairs
    for row in load_json(path):
        fetched = row.get("fetched_at")
        for url in (row.get("url"), row.get("final_url")):
            if url and fetched:
                pairs.add((url, fetched))
    return pairs


def expected_offer_id(offer, hash_len):
    provider = offer.get("provider") or {}
    source = offer.get("source_url")
    country = offer.get("country")
    if provider.get("type") != "issuer" or not source or not country or "-" not in provider.get("id", ""):
        return None
    slug = provider["id"].split("-", 1)[1]
    digest = hashlib.sha256(source.encode()).hexdigest()[:hash_len]
    return f"{country.lower()}-{slug}-{digest}"


VERBATIM_KEYS = {"dates_text", "cap_text", "min_spend_text", "quote", "name_quote"}


def reject_verbatim_keys(value, where, errors):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in VERBATIM_KEYS:
                errors.append(f"{where}: {key} is not published")
            else:
                reject_verbatim_keys(item, where, errors)
    elif isinstance(value, list):
        for item in value:
            reject_verbatim_keys(item, where, errors)


def check_fetch_log(record, pairs, errors):
    checked = record.get("checked_at")
    if checked in (None, ""):
        return
    url = record.get("checked_fetch_url")
    if not url or (url, checked) not in pairs:
        errors.append(f"{record.get('id')}: checked_at or checked_fetch_url is not in the fetch log")


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
                if checked == "":
                    errors.append(f"{item.get('id')}: checked_at is empty")
                if checked and generated_at:
                    checked_at, checked_error = parse_instant_or_error(checked)
                    generated, generated_error = parse_instant_or_error(generated_at)
                    if checked_error:
                        errors.append(f"{item.get('id')}: checked_at is not a valid date-time ({checked_error})")
                    elif generated_error:
                        errors.append(f"{item.get('id')}: generated_at is not a valid date-time ({generated_error})")
                    elif checked_at > generated:
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
    live_ids = {offer["id"] for offer in offers} | card_ids
    for record in list(offers) + list(cards):
        for alias in record.get("aliases") or []:
            if alias in live_ids and alias != record["id"]:
                errors.append(f"{record['id']}: alias {alias} equals another record's live id")
    seen_offer_ids = set()
    session_id = re.compile(r"(?i)(?:;jsessionid=|[?&;](?:jsessionid|phpsessid|sessionid|sid|aspsessionid\w*)=)")
    log_path = os.path.join(root, "pipeline", "fetch_metadata.json")
    if os.path.exists(log_path):
        for row in load_json(log_path):
            for url in (row.get("url"), row.get("final_url")):
                if url and session_id.search(url):
                    errors.append(f"pipeline/fetch_metadata.json: url with a session id: {url[:80]}")
    merchant_rules = load_merchant_rules(root)
    for brand in merchants:
        expected = bool(brand.get("official_domain")) or len(brand.get("offer_ids") or []) >= rules["merchant_min_offers"]
        if brand.get("verified") != expected:
            errors.append(f"merchant {brand['id']}: verified must be {str(expected).lower()} (official domain or {rules['merchant_min_offers']} offers)")
        if not brand.get("offer_ids"):
            errors.append(f"merchant {brand['id']}: no offer links to this merchant")
    hash_len = rules["id_hash_hex_chars"]
    clause_patterns = [re.compile(pat, re.I) for pat in rules["description_clause_patterns"]]
    fetch_pairs = load_fetch_pairs(root)
    for offer in offers:
        if offer["id"] in seen_offer_ids:
            errors.append(f"{offer['id']}: duplicate offer id")
        seen_offer_ids.add(offer["id"])
        reject_verbatim_keys(offer, offer["id"], errors)
        expected = expected_offer_id(offer, hash_len)
        if expected and offer["id"] != expected:
            errors.append(f"{offer['id']}: offer id is not the hash of source_url (expected {expected})")
        eligibility = offer.get("eligibility") or {}
        if eligibility.get("confidence") == "inferred" and eligibility.get("card_ids"):
            errors.append(f"{offer['id']}: inferred offer must not carry card ids")
        description = offer.get("description") or ""
        if len(description) > rules["description_max_chars"]:
            errors.append(f"{offer['id']}: description is longer than the configured maximum")
        if any(pattern.search(description) for pattern in clause_patterns):
            errors.append(f"{offer['id']}: description contains clause text")
        check_fetch_log(offer, fetch_pairs, errors)
        allowed = domains_for(offer, issuer_by, networks, merchant_by)
        for url in offer_url_list(offer):
            host = host_of(url)
            if not host:
                continue
            network_id = network_id_for_host(host, networks)
            provider = offer["provider"]
            issuer_domains = set()
            if provider.get("type") == "issuer":
                issuer_domains = set((issuer_by.get(provider.get("id")) or {}).get("official_domains") or [])
            network_is_provider = provider.get("type") == "network" and provider.get("id") == network_id
            if network_id and not network_is_provider and host not in issuer_domains:
                errors.append(f"{offer['id']}: host {host} is a {network_id} domain but that network is not the provider")
                continue
            if host not in allowed:
                errors.append(f"{offer['id']}: host {host} is not an official domain of the provider or merchant")
        for card_id in eligibility.get("card_ids") or []:
            if card_id not in card_ids:
                errors.append(f"{offer['id']}: unknown card id {card_id}")
        if offer.get("merchant_id") and offer["merchant_id"] not in merchant_by:
            errors.append(f"{offer['id']}: unknown merchant id {offer['merchant_id']}")
        ids = offer.get("merchant_ids") or []
        kind = offer.get("merchant_kind")
        if kind == "single" and ids != [offer.get("merchant_id")]:
            errors.append(f"{offer['id']}: merchant_ids must hold the one merchant_id when merchant_kind is single")
        if kind == "multiple" and len(ids) < 2:
            errors.append(f"{offer['id']}: merchant_kind multiple needs two or more merchant_ids")
        if kind in {"category", "issuer_own", "unknown"} and ids:
            errors.append(f"{offer['id']}: merchant_ids must be empty when merchant_kind is {kind}")
        for merchant_id in ids:
            if merchant_id not in merchant_by:
                errors.append(f"{offer['id']}: unknown merchant id {merchant_id}")
            elif offer["id"] not in merchant_by[merchant_id].get("offer_ids") or []:
                errors.append(f"{offer['id']}: merchant {merchant_id} does not list this offer")
        if offer.get("merchant_kind") == "single" and offer.get("merchant_id") in merchant_by:
            brand = merchant_by[offer["merchant_id"]]
            keys = {name_key(text, merchant_rules) for text in [brand["name"]] + list(brand.get("aliases") or [])}
            if name_key(offer.get("merchant_name") or "", merchant_rules) not in keys:
                errors.append(f"{offer['id']}: merchant_name {offer.get('merchant_name')} is not a name or alias of merchant {brand['id']}")
            if offer["id"] not in brand.get("offer_ids") or []:
                errors.append(f"{offer['id']}: merchant {brand['id']} does not list this offer")
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
        reject_verbatim_keys(card, card["id"], errors)
        if card.get("status") == "active" and not card.get("networks"):
            errors.append(f"{card['id']}: active card has an empty networks list")
        check_fetch_log(card, fetch_pairs, errors)
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
        dirnames[:] = [name for name in dirnames if name not in {".git", "dist", "__pycache__", ".venv", "venv", "node_modules"}]
        for name in files:
            if name.endswith((".json", ".md", ".yml", ".yaml")):
                with open(os.path.join(dirpath, name), encoding="utf-8") as fh:
                    text = fh.read()
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
