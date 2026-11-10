"""Load run-time thresholds. Numbers live in config JSON, not in code."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REQUIRED = (
    "end_date_max_months",
    "evergreen_review_months",
    "archive_retention_days",
    "merchant_min_offers",
    "id_hash_hex_chars",
)


def repo_root():
    return ROOT


def _load(name):
    path = os.path.join(ROOT, "config", name)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_rules():
    data = _load("rules.json")
    missing = [key for key in REQUIRED if key not in data]
    if missing:
        raise SystemExit("config/rules.json is missing: " + ", ".join(missing))
    for key in REQUIRED:
        if not isinstance(data[key], int) or isinstance(data[key], bool):
            raise SystemExit(f"config/rules.json {key} must be an integer")
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
