"""Load run-time thresholds. Numbers live in config JSON, not in code."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INT_KEYS = (
    "end_date_max_months",
    "evergreen_review_months",
    "archive_retention_days",
    "merchant_min_offers",
    "id_hash_hex_chars",
    "max_promotion_days",
    "default_period_months",
    "description_max_chars",
    "amount_context_chars",
    "minimum_phrase_chars",
    "per_context_words",
    "campaign_payout_min_amount",
)
OTHER_KEYS = (
    "listing_end_date_ceiling",
    "listing_popup_issuers",
    "description_clause_patterns",
    "currency_symbols",
    "not_a_cap_patterns",
    "campaign_payout_phrases",
)


def repo_root():
    return ROOT


def _load(name):
    path = os.path.join(ROOT, "config", name)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_rules():
    data = _load("rules.json")
    missing = [key for key in INT_KEYS + OTHER_KEYS if key not in data]
    if missing:
        raise SystemExit("config/rules.json is missing: " + ", ".join(missing))
    for key in INT_KEYS:
        if not isinstance(data[key], int) or isinstance(data[key], bool):
            raise SystemExit(f"config/rules.json {key} must be an integer")
    if not isinstance(data["listing_end_date_ceiling"], str):
        raise SystemExit("config/rules.json listing_end_date_ceiling must be a string")
    if not isinstance(data["listing_popup_issuers"], list):
        raise SystemExit("config/rules.json listing_popup_issuers must be a list")
    if not isinstance(data["description_clause_patterns"], list):
        raise SystemExit("config/rules.json description_clause_patterns must be a list")
    if not isinstance(data["currency_symbols"], list) or not data["currency_symbols"]:
        raise SystemExit("config/rules.json currency_symbols must be a non-empty list")
    for row in data["currency_symbols"]:
        if not isinstance(row, dict) or not row.get("symbol") or not row.get("currency"):
            raise SystemExit("config/rules.json currency_symbols entries need symbol and currency")
    for key in ("not_a_cap_patterns", "campaign_payout_phrases"):
        if not isinstance(data[key], list):
            raise SystemExit(f"config/rules.json {key} must be a list")
    return data


def load_countries():
    data = _load("countries.json")
    items = data["items"]
    by_code = {item["code"]: item for item in items}
    return items, by_code


def load_places():
    data = _load("places.json")
    places = sorted(data["places"], key=lambda row: len(row["phrase"]), reverse=True)
    return places, data.get("currency_country") or {}


def load_patterns():
    import re
    data = _load("non_merchant_patterns.json")
    return [re.compile(pat) for pat in data["patterns"]]


def load_networks():
    return _load("networks.json")
