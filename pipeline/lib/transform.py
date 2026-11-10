"""Turn schema 0.2.0 records into the 0.3 tree.

Business thresholds are read from config/rules.json at run time.
Offer ids are a short hash of the first source URL, reused when the same
issuer and source URL already exist. Card ids stay with the issuer and the
official URL. Verbatim terms clauses are hashed and dropped.
"""
import hashlib
import json
import os
import re
import unicodedata
from collections import Counter, defaultdict
from urllib.parse import urlparse

from pipeline.lib.calendar import add_months, local_date, parse_instant
from pipeline.lib.fetchindex import FetchIndex
from pipeline.lib.rules import (
    load_countries,
    load_networks,
    load_patterns,
    load_places,
    load_rules,
)

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9,
    "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}
BENEFIT_UNITS = {"percent", "currency", "points", "multiplier"}
BENEFIT_SOURCES = {"offer_text", "title"}
AMOUNT = re.compile(
    r"(RM|MYR|S\$|SGD|USD|THB|TWD|HKD|JPY|EUR|GBP|\$)\s?(\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)"
)
PER_RULES = (
    ("month", re.compile(r"\bmonthly\b|\bper\s+(?:[\w]+\s+){0,4}months?\b", re.I)),
    ("year", re.compile(r"\bannually\b|\bper\s+(?:[\w]+\s+){0,4}years?\b", re.I)),
    ("day", re.compile(r"\bdaily\b|\bper\s+(?:[\w]+\s+){0,4}days?\b", re.I)),
    ("visit", re.compile(r"\bper\s+(?:[\w]+\s+){0,3}visits?\b", re.I)),
    ("table", re.compile(r"\bper\s+tables?\b", re.I)),
    ("transaction", re.compile(r"\bper\s+(?:[\w]+\s+){0,3}transactions?\b", re.I)),
    ("cardmember", re.compile(r"\bper\s+(?:[\w]+\s+){0,3}card\s?members?\b|\bper\s+cardholders?\b", re.I)),
    ("customer", re.compile(r"\bper\s+customers?\b", re.I)),
    ("redemption", re.compile(r"\bper\s+redemptions?\b", re.I)),
)
WEEKDAY = (
    ("monday", "mon"), ("mondays", "mon"), ("tuesday", "tue"), ("tuesdays", "tue"),
    ("wednesday", "wed"), ("wednesdays", "wed"), ("thursday", "thu"), ("thursdays", "thu"),
    ("friday", "fri"), ("fridays", "fri"), ("saturday", "sat"), ("saturdays", "sat"),
    ("sunday", "sun"), ("sundays", "sun"),
)
DAY_ORDER = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
CONFLICT = re.compile(
    r"valid for\s+(?:(\d+)|thirty-six)\s*(?:\(\d+\)\s*)?months from\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    re.I,
)
HUMAN_DATE = re.compile(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})")
DETAIL_KEYS = {
    "rates_pct", "programmes", "visits", "coverage_text",
    "visits_values", "guest_policy_text", "supplementary_share_visits",
}


def slugify(value):
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    text = text.lower().replace("&", " and ").replace("+", " plus ")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def norm_name(value):
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode().lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def issuer_slug(issuer_id):
    return issuer_id.split("-", 1)[1]


def host_of(url):
    if not url or not isinstance(url, str) or "://" not in url:
        return None
    try:
        host = urlparse(url).hostname
    except ValueError:
        return None
    if not host:
        return None
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def read_fetch_rows(fetch_path):
    path = fetch_path or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "pipeline",
        "fetch_metadata.json",
    )
    if not path or not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, list) else []


def country_hosts_for(base_domains, country_codes, rows):
    """Hosts in the fetch log shaped as {base domain}.{country code}."""
    codes = {code.lower() for code in country_codes}
    found = set()
    for row in rows:
        for url in (row.get("url"), row.get("final_url")):
            host = host_of(url)
            if not host:
                continue
            for domain in base_domains:
                for code in codes:
                    candidate = f"{domain}.{code}"
                    if host == candidate or host.endswith("." + candidate):
                        found.add(candidate)
    return found


def extend_network_country_domains(networks_doc, rows, country_codes, network_id="visa"):
    """Add country sites from the fetch log onto one network's official domains."""
    for item in networks_doc.get("items") or []:
        if item.get("id") != network_id:
            continue
        extra = country_hosts_for(item.get("official_domains") or [], country_codes, rows)
        item["official_domains"] = sorted(set(item.get("official_domains") or []) | extra)
    return networks_doc


def clean_name(value):
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = text.replace("\u00ae", " ").replace("\u2122", " ")
    return re.sub(r"\s+", " ", text).strip()


def hash_text(value):
    flat = re.sub(r"\s+", " ", (value or "").replace("\u00a0", " ")).strip().lower()
    return hashlib.sha256(flat.encode()).hexdigest()


def hash_clauses(clauses):
    parts = []
    for clause in clauses:
        text = clause.get("text") or ""
        number = clause.get("n")
        parts.append(f"{number} {text}".strip() if number else text)
    return hash_text("\n".join(parts))


def whole_amount(number):
    if isinstance(number, float) and number.is_integer():
        return int(number)
    return number


def parse_money(text, default_currency):
    if not text:
        return None
    found = []
    for symbol, raw in AMOUNT.findall(text):
        if symbol == "$":
            currency = default_currency
        elif symbol in {"RM", "MYR"}:
            currency = "MYR"
        elif symbol in {"S$", "SGD"}:
            currency = "SGD"
        else:
            currency = symbol
        found.append((whole_amount(float(raw.replace(",", ""))), currency))
    unique = set(found)
    if len(unique) != 1:
        return None
    amount, currency = next(iter(unique))
    return {"amount": amount, "currency": currency}


def cap_per(text):
    if not text:
        return None
    for name, pattern in PER_RULES:
        if pattern.search(text):
            return name
    return None


MIN_SPEND_BEFORE = re.compile(r"minimum\s+(?:spend|purchase)|min(?:imum)?\s+spend", re.I)


def currency_cap(text, default_currency):
    """One currency cap from source text, or a reason when the text does not state exactly one.

    Amounts introduced as a minimum spend are not the cap. Callers keep the source text private.
    """
    if not text:
        return None, None
    caps = []
    for match in AMOUNT.finditer(text):
        before = text[max(0, match.start() - 80):match.start()]
        if MIN_SPEND_BEFORE.search(before):
            continue
        symbol = match.group(1)
        if symbol == "$":
            found_currency = default_currency
        elif symbol in {"RM", "MYR"}:
            found_currency = "MYR"
        elif symbol in {"S$", "SGD"}:
            found_currency = "SGD"
        else:
            found_currency = symbol
        amount = whole_amount(float(match.group(2).replace(",", "")))
        caps.append((amount, found_currency))
    distinct = set(caps)
    if not distinct:
        return None, "not_a_currency_amount"
    if len(distinct) != 1:
        return None, "more_than_one_currency_amount"
    amount, found_currency = caps[0]
    return {"amount": amount, "currency": found_currency, "per": cap_per(text)}, None


def parse_human_date(value):
    match = HUMAN_DATE.search(value or "")
    if not match:
        return None
    month = MONTHS.get(match.group(2).lower())
    if not month:
        return None
    import datetime
    try:
        return datetime.date(int(match.group(3)), month, int(match.group(1)))
    except ValueError:
        return None


def valid_days(text):
    if not text:
        return None
    lowered = text.lower()
    found = set()
    if re.search(r"\bweekdays?\b", lowered):
        found.update(["mon", "tue", "wed", "thu", "fri"])
    if re.search(r"\bweekends?\b", lowered):
        found.update(["sat", "sun"])
    for word, code in WEEKDAY:
        if re.search(r"\b" + word + r"\b", lowered):
            found.add(code)
    if not found:
        return None
    return [day for day in DAY_ORDER if day in found]


def periods_for(offer):
    start = offer.get("start_date")
    end = offer.get("end_date")
    if not start and not end:
        return None, None
    span = {"start": start, "end": end}
    text = offer.get("dates_text") or ""
    if re.search(r"\bbookings? made\b|\bbook by\b|\bbooking period\b", text, re.I):
        return span, None
    return None, span


def apply_date_policy(offer, clause_text, today, max_months):
    """Correct end dates that the source text does not support, and hold far dates for review."""
    import datetime
    notes = []
    text = offer.get("dates_text") or ""
    title = offer.get("title") or ""
    if re.search(r"annual fee waiver", text, re.I) and not re.search(r"annual fee", title, re.I):
        stated = offer.get("end_date")
        offer["stated_end_date"] = stated
        offer["end_date"] = None
        offer["start_date"] = None
        offer["start_date_null_reason"] = "not_stated_in_terms_or_page"
        offer["status"] = "needs_review"
        offer["review_reason"] = (
            "The date range in the source sentence belongs to an annual fee waiver campaign, not to this offer. "
            "No end date is published for the offer."
        )
        notes.append({"id": offer.get("_old_id"), "action": "fee_waiver_date_removed", "stated_end_date": stated})
        return notes
    if re.search(r"\bto illustrate\b", text, re.I):
        stated = offer.get("end_date")
        offer["stated_end_date"] = stated
        offer["end_date"] = None
        offer["start_date"] = None
        offer["start_date_null_reason"] = "not_stated_in_terms_or_page"
        offer["status"] = "needs_review"
        offer["review_reason"] = (
            "The source sentence is a rewards-rate illustration, not a promotion period. "
            "The parsed end date was not kept."
        )
        notes.append({"id": offer.get("_old_id"), "action": "illustration_date_removed", "stated_end_date": stated})
        return notes
    combined = (clause_text or "") + "\n" + text
    conflict = CONFLICT.search(combined)
    if conflict and offer.get("end_date"):
        count = int(conflict.group(1) or load_rules()["default_period_months"])
        started = parse_human_date(conflict.group(2))
        parsed = datetime.date.fromisoformat(offer["end_date"])
        if started:
            computed = add_months(started, count) - datetime.timedelta(days=1)
            if computed != parsed:
                stated = offer["end_date"]
                offer["stated_end_date"] = stated
                offer["end_date"] = None
                offer["status"] = "needs_review"
                offer["review_reason"] = (
                    f"The source says the promotion is valid for {count} months from {started.isoformat()} "
                    f"(through {computed.isoformat()}) and also states {stated}. "
                    "The two dates conflict, so no end date is published."
                )
                notes.append({"id": offer.get("_old_id"), "action": "conflicting_period", "stated_end_date": stated})
                return notes
    if offer.get("end_date") and not offer.get("end_date_reviewer_accepted"):
        parsed = datetime.date.fromisoformat(offer["end_date"])
        limit = add_months(today, max_months)
        if parsed > limit:
            stated = offer["end_date"]
            offer["stated_end_date"] = stated
            offer["end_date"] = None
            offer["status"] = "needs_review"
            offer["review_reason"] = (
                f"The source states an end date of {stated}, past the configured horizon. "
                "It is not published as end_date unless end_date_reviewer_accepted is true."
            )
            notes.append({"id": offer.get("_old_id"), "action": "beyond_horizon", "stated_end_date": stated})
    return notes


def cross_border(offer, merchant_name, places, currency_country):
    card_country = offer["country"]
    stated = (offer.get("cross_border") or {}).get("merchant_country")
    redeem = []
    basis = []
    if isinstance(stated, str) and re.fullmatch(r"[A-Z]{2}", stated) and stated != card_country:
        redeem.append(stated)
        basis.append("stated_merchant_country")
    blob = f"{merchant_name or ''} {offer.get('title') or ''}".lower()
    for place in places:
        phrase = place["phrase"]
        if re.search(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", blob):
            country = place["country"]
            if country != card_country:
                redeem.append(country)
                basis.append("place_name")
    if not any(item != card_country for item in redeem):
        title = offer.get("title") or ""
        for code, country in currency_country.items():
            if country == card_country:
                continue
            if re.search(r"\b" + re.escape(code) + r"\b", title):
                redeem.append(country)
                basis.append("foreign_currency")
                break
    ordered = []
    for country in redeem:
        if country not in ordered:
            ordered.append(country)
    foreign = [country for country in ordered if country != card_country]
    if not foreign:
        return {
            "is_cross_border": False,
            "card_issuing_country": card_country,
            "redeem_countries": [card_country],
            "basis": "no_foreign_signal",
        }
    label = basis[0] if len(set(basis)) == 1 else "mixed"
    return {
        "is_cross_border": True,
        "card_issuing_country": card_country,
        "redeem_countries": foreign,
        "basis": label,
    }


def benefit_of(raw):
    value = raw.get("value")
    unit = raw.get("unit")
    if value is None and raw.get("value_pct") is not None:
        value = raw["value_pct"]
        unit = unit or "percent"
    if isinstance(value, float):
        value = whole_amount(value)
    source = raw.get("source")
    if source not in BENEFIT_SOURCES:
        source = None
    if unit not in BENEFIT_UNITS:
        unit = None
    return {
        "type": raw.get("type") or "other",
        "value": value,
        "unit": unit,
        "value_text": raw.get("value_text"),
        "up_to": bool(raw.get("up_to")),
        "source": source,
    }


def eligibility_of(raw, card_ids):
    raw = raw or {}
    confidence = raw.get("confidence") or "inferred"
    scope = raw.get("scope") or "issuer"
    named = []
    if scope == "card" and confidence == "stated":
        for old in raw.get("card_ids") or []:
            if old in card_ids:
                named.append(card_ids[old])
    return {
        "scope": scope,
        "rule": raw.get("rule") or "unspecified",
        "confidence": confidence,
        "issuer_ids": list(raw.get("issuer_ids") or []),
        "network_ids": list(raw.get("networks") or []),
        "card_ids": named,
        "card_types": list(raw.get("card_types") or []),
        "tiers": list(raw.get("tiers") or []),
        "evidence_text": raw.get("evidence_text"),
    }


def offer_urls(offer):
    urls = [
        offer.get("source_url"),
        offer.get("terms_url"),
        offer.get("dates_source_url"),
        offer.get("min_spend_source_url"),
        offer.get("cap_source_url"),
    ]
    for source in offer.get("sources") or []:
        urls.append(source.get("url"))
    return [url for url in urls if url]


def card_urls(card):
    urls = [card.get("official_url")]
    for source in card.get("sources") or []:
        urls.append(source.get("url"))
    for benefit in card.get("benefits") or []:
        urls.append(benefit.get("source_url"))
    fee = card.get("annual_fee") or {}
    income = card.get("min_income") or {}
    urls.append(fee.get("source_url"))
    urls.append(income.get("source_url"))
    for rate in card.get("earn_rates") or []:
        urls.append(rate.get("source_url"))
    return [url for url in urls if url]


def stamp_sources(sources, index, fallback):
    out = []
    for source in sources or []:
        hit = index.lookup(source.get("url"))
        fetched = hit["fetched_at"] if hit else None
        if not fetched and fallback and source.get("url"):
            bare = source["url"].split("#", 1)[0]
            if fallback[1].split("#", 1)[0].rstrip("/") == bare.rstrip("/"):
                fetched = fallback[0]
        out.append({
            "url": source.get("url"),
            "kind": source.get("kind"),
            "fetched_at": fetched,
        })
    return out


def new_offer_id(country, slug, source_url, hash_len, used):
    digest = hashlib.sha256((source_url or "").encode()).hexdigest()
    width = hash_len
    while width <= 64:
        candidate = f"{country}-{slug}-{digest[:width]}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        width += 2
    raise RuntimeError("offer id space exhausted")


def new_card_id(country, slug, name, old_id, used):
    tail = slugify(name)
    prefix = slug + "-"
    if tail.startswith(prefix):
        tail = tail[len(prefix):]
    if not tail:
        tail = hashlib.sha256(old_id.encode()).hexdigest()[:8]
    base = f"{country}-{slug}-{tail}"
    candidate = base
    number = 2
    while candidate in used:
        candidate = f"{base}-{number}"
        number += 1
    used.add(candidate)
    return candidate


def contains_phrase(haystack, needle):
    if len(needle) < 4:
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])", haystack) is not None


def placement(status, end_date, today, retention_days):
    import datetime
    if status in {"evergreen", "needs_review"} or not end_date:
        return "live"
    end = datetime.date.fromisoformat(end_date)
    if end >= today:
        return "live"
    age = (today - end).days
    if age <= retention_days:
        return "archive"
    return "drop"


def load_country_items(src, country, name):
    path = os.path.join(src, country, f"{name}.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["items"]


def build_tree(src, generated_at, fetch_path=None, existing_index=None, alias_legacy=True):
    """existing_index maps (issuer_id, source_url) and ('card', issuer_id, official_url) to prior 0.3 records."""
    import datetime
    rules = load_rules()
    countries, country_by = load_countries()
    places, currency_country = load_places()
    patterns = load_patterns()
    networks_doc = extend_network_country_domains(
        load_networks(),
        read_fetch_rows(fetch_path),
        [item["code"] for item in countries],
    )
    index = FetchIndex(fetch_path)
    existing_index = existing_index or {}
    generated = parse_instant(generated_at)

    old_offers = []
    old_cards = []
    old_issuers = []
    old_merchants = {}
    for country in sorted(os.listdir(src)):
        folder = os.path.join(src, country)
        if not re.fullmatch(r"[a-z]{2}", country) or not os.path.isdir(folder):
            continue
        if not os.path.exists(os.path.join(folder, "offers.json")):
            continue
        code = country.upper()
        for offer in load_country_items(src, country, "offers"):
            offer["_old_id"] = offer["id"]
            old_offers.append(offer)
        for card in load_country_items(src, country, "cards"):
            card["_old_id"] = card["id"]
            old_cards.append(card)
        for issuer in load_country_items(src, country, "issuers"):
            old_issuers.append(issuer)
        for merchant in load_country_items(src, country, "merchants"):
            current = old_merchants.get(merchant["id"])
            if not current:
                old_merchants[merchant["id"]] = merchant
            else:
                for offer_id in merchant.get("offer_ids") or []:
                    if offer_id not in current["offer_ids"]:
                        current["offer_ids"].append(offer_id)

    used_cards = set()
    card_id_map = {}
    cards_out = []
    unmatched = []
    for card in old_cards:
        slug = issuer_slug(card["issuer_id"])
        country = card["country"].lower()
        prior = existing_index.get(("card", card["issuer_id"], card.get("official_url")))
        if prior:
            new_id = prior["id"]
            aliases = list(prior.get("aliases") or [])
            used_cards.add(new_id)
        else:
            new_id = new_card_id(country, slug, card.get("name") or card["_old_id"], card["_old_id"], used_cards)
            aliases = []
        aliases = [alias for alias in aliases if alias != new_id]
        if alias_legacy and card["_old_id"] != new_id and card["_old_id"] not in aliases:
            aliases.append(card["_old_id"])
        card_id_map[card["_old_id"]] = new_id
        fetch = index.best(card_urls(card))
        checked_at = fetch[0] if fetch else None
        if not checked_at:
            unmatched.append({
                "kind": "card",
                "id": card["_old_id"],
                "new_id": new_id,
                "urls": card_urls(card)[:6],
            })
        networks = list(card.get("networks") or [])
        status = card.get("status") or "active"
        review_reason = None
        if status == "active" and not networks:
            status = "needs_review"
            review_reason = "No card network is stated on the official page, so the card cannot stay active."
        seen = checked_at[:10] if checked_at else None
        benefits = []
        card_currency = card.get("currency") or country_by[card["country"]]["currency"]
        for benefit in card.get("benefits") or []:
            raw_details = benefit.get("details") if isinstance(benefit.get("details"), dict) else None
            details = None
            if raw_details is not None:
                details = {key: raw_details[key] for key in raw_details if key in DETAIL_KEYS}
                if benefit.get("type") == "lounge_access" and raw_details.get("min_spend_text"):
                    parsed = parse_money(raw_details.get("min_spend_text"), card_currency)
                    if parsed:
                        details["min_spend"] = {
                            "amount": parsed["amount"],
                            "currency": parsed["currency"],
                            "per": cap_per(raw_details.get("min_spend_text")),
                        }
                    else:
                        details["min_spend_null_reason"] = "not_a_currency_amount"
                if raw_details.get("cap_text"):
                    parsed_cap, cap_reason = currency_cap(raw_details.get("cap_text"), card_currency)
                    if parsed_cap:
                        details["cap"] = parsed_cap
                    elif cap_reason:
                        details["cap_null_reason"] = cap_reason
            benefits.append({
                "type": benefit.get("type"),
                "text": benefit.get("text"),
                "texts": benefit.get("texts") or [benefit.get("text")],
                "source_url": benefit.get("source_url"),
                "details": details,
            })
        record = {
            "id": new_id,
            "aliases": aliases,
            "name": card.get("name"),
            "issuer_id": card["issuer_id"],
            "country": card["country"],
            "currency": card.get("currency") or country_by[card["country"]]["currency"],
            "networks": networks,
            "network_source": card.get("network_source"),
            "network_candidates": card.get("network_candidates") or [],
            "tier": card.get("tier"),
            "card_type": card.get("card_type"),
            "islamic": bool(card.get("islamic")),
            "status": status,
            "review_reason": review_reason,
            "annual_fee": card.get("annual_fee"),
            "min_income": card.get("min_income"),
            "benefits": benefits,
            "benefit_types": sorted({benefit["type"] for benefit in benefits if benefit.get("type")}),
            "benefits_scope": card.get("benefits_scope"),
            "earn_rates": card.get("earn_rates") or [],
            "official_url": card.get("official_url"),
            "sources": stamp_sources(card.get("sources"), index, fetch),
            "name_verified_on_source": card.get("name_verified_on_source"),
            "checked_at": checked_at,
            "checked_fetch_url": fetch[1] if fetch else None,
            "checked_at_null_reason": None if checked_at else "no_fetch_metadata_match",
            "first_seen": seen,
            "last_seen": seen,
        }
        cards_out.append(record)

    # Merchant groups from the 0.2 names, then the count rule in config.
    groups = {}
    offer_merchant = {}
    for offer in old_offers:
        mids = offer.get("merchant_ids") or []
        if not mids:
            offer_merchant[offer["_old_id"]] = None
            continue
        mid = mids[0]
        merchant = old_merchants.get(mid)
        name = clean_name(merchant["name"] if merchant else mid) or mid
        key = norm_name(name) or mid
        group = groups.setdefault(key, {
            "names": Counter(),
            "old_ids": set(),
            "offer_old_ids": [],
            "categories": set(),
            "countries": set(),
            "explicit": set(),
        })
        group["names"][name] += 1
        group["old_ids"].add(mid)
        group["offer_old_ids"].append(offer["_old_id"])
        if offer.get("category"):
            group["categories"].add(offer["category"])
        group["countries"].add(offer["country"])
        stated = (offer.get("cross_border") or {}).get("merchant_country")
        if isinstance(stated, str) and stated != offer["country"]:
            group["explicit"].add(stated)
        offer_merchant[offer["_old_id"]] = key

    def junk(name):
        return any(pattern.search(name) for pattern in patterns)

    kept = {}
    used_merchant_ids = set()
    for key, group in groups.items():
        display = group["names"].most_common(1)[0][0]
        if junk(display) or len(group["offer_old_ids"]) < rules["merchant_min_offers"]:
            continue
        base = slugify(display) or key.replace(" ", "-")
        candidate = base
        number = 2
        while candidate in used_merchant_ids:
            candidate = f"{base}-{number}"
            number += 1
        used_merchant_ids.add(candidate)
        kept[key] = candidate

    redirect = {}
    for key, group in groups.items():
        if key in kept:
            continue
        display = group["names"].most_common(1)[0][0]
        host = norm_name(display)
        match = None
        for kept_key in kept:
            if contains_phrase(host, kept_key):
                if match is None or len(kept_key) > len(match):
                    match = kept_key
        if match:
            redirect[key] = match

    merchants_out = {}
    for key, merchant_id in kept.items():
        group = groups[key]
        alias_names = [name for name in group["names"] if name != group["names"].most_common(1)[0][0]]
        merchants_out[merchant_id] = {
            "id": merchant_id,
            "name": group["names"].most_common(1)[0][0],
            "aliases": sorted(set(alias_names) | set(group["old_ids"])),
            "countries": sorted(group["countries"] | group["explicit"]),
            "categories": sorted(group["categories"]),
            "official_domain": None,
            "offer_ids": [],
        }
    for key, target in redirect.items():
        merchant_id = kept[target]
        group = groups[key]
        record = merchants_out[merchant_id]
        for name in group["names"]:
            if name not in record["aliases"] and name != record["name"]:
                record["aliases"].append(name)
        for old in group["old_ids"]:
            if old not in record["aliases"]:
                record["aliases"].append(old)
        record["countries"] = sorted(set(record["countries"]) | group["countries"] | group["explicit"])
        record["categories"] = sorted(set(record["categories"]) | group["categories"])
        record["aliases"] = sorted(record["aliases"])

    def merchant_link(old_offer_id, display_fallback):
        key = offer_merchant.get(old_offer_id)
        if not key:
            return None, None
        if key in redirect:
            return kept[redirect[key]], None
        if key in kept:
            return kept[key], None
        group = groups[key]
        return None, group["names"].most_common(1)[0][0]

    used_offers = set()
    offers_out = []
    date_notes = []
    dropped = []
    for offer in old_offers:
        slug = issuer_slug(offer["issuer_id"])
        country = offer["country"].lower()
        prior = existing_index.get((offer["issuer_id"], offer.get("source_url")))
        if prior:
            new_id = prior["id"]
            aliases = list(prior.get("aliases") or [])
            used_offers.add(new_id)
        else:
            new_id = new_offer_id(country, slug, offer.get("source_url") or offer["_old_id"], rules["id_hash_hex_chars"], used_offers)
            aliases = []
        aliases = [alias for alias in aliases if alias != new_id]
        if alias_legacy and offer["_old_id"] != new_id and offer["_old_id"] not in aliases:
            aliases.append(offer["_old_id"])
        clauses = offer.get("terms_clauses") or []
        clause_text = "\n".join((clause.get("text") or "") for clause in clauses) if isinstance(clauses, list) else ""
        zone = country_by[offer["country"]]["timezone"]
        today = local_date(generated, zone)
        apply_date_policy(offer, clause_text, today, rules["end_date_max_months"])
        if offer.get("_date_notes"):
            pass
        # apply_date_policy returns notes but we also want them; call stored on the function via re-read
        # The notes were returned and discarded. Capture by calling logic result stored below.
        status = offer.get("status")
        if not offer.get("end_date"):
            if status != "needs_review":
                status = "evergreen"
        else:
            end = datetime.date.fromisoformat(offer["end_date"])
            status = "expired" if end < today else "active"
        where = placement(status, offer.get("end_date"), today, rules["archive_retention_days"])
        if where == "drop":
            dropped.append({"id": offer["_old_id"], "new_id": new_id, "end_date": offer.get("end_date"), "reason": "past_archive_retention"})
            continue
        if status == "expired":
            offer["status"] = "expired"
        else:
            offer["status"] = status
        fetch = index.best(offer_urls(offer))
        checked_at = fetch[0] if fetch else None
        if not checked_at:
            unmatched.append({
                "kind": "offer",
                "id": offer["_old_id"],
                "new_id": new_id,
                "urls": offer_urls(offer)[:8],
            })
        seen_day = checked_at[:10] if checked_at else None
        anchor = datetime.date.fromisoformat(seen_day) if seen_day else today
        if offer["status"] in {"evergreen", "needs_review"}:
            review_by = add_months(anchor, rules["evergreen_review_months"]).isoformat()
        else:
            review_by = offer.get("end_date")
        merchant_id, merchant_text = merchant_link(offer["_old_id"], None)
        if merchant_id and merchant_id in merchants_out:
            merchants_out[merchant_id]["offer_ids"].append(new_id)
        currency = offer.get("currency") or country_by[offer["country"]]["currency"]
        min_spend = parse_money(offer.get("min_spend_text"), currency)
        cap, cap_null_reason = currency_cap(offer.get("cap_text"), currency)
        booking, usage = periods_for(offer)
        terms_hash = None
        terms_scope = offer.get("terms_scope")
        terms_hash_null_reason = None
        popup_issuers = set(rules.get("listing_popup_issuers") or [])
        fetched_terms = offer.get("terms") if isinstance(offer.get("terms"), dict) else None
        if clauses:
            terms_hash = hash_clauses(clauses)
            terms_hash_null_reason = None
            if not terms_scope:
                terms_scope = "deal_document"
        elif offer["issuer_id"] in popup_issuers and not offer.get("terms_url"):
            terms_scope = "listing_popup"
            if fetched_terms and fetched_terms.get("hash"):
                terms_hash = fetched_terms["hash"]
            else:
                terms_hash = None
                terms_hash_null_reason = "full_popup_text_not_available_offline"
        else:
            terms_hash_null_reason = "no_terms_text_in_source_record"
        terms_fetched = None
        if offer.get("terms_url"):
            hit = index.lookup(offer.get("terms_url"))
            if hit:
                terms_fetched = hit["fetched_at"]
        if not terms_fetched and terms_hash:
            terms_fetched = checked_at
        provider_type = "issuer"
        provider_id = offer["issuer_id"]
        if offer.get("network") and not offer.get("issuer_id"):
            provider_type = "network"
            provider_id = offer["network"]
        record = {
            "id": new_id,
            "aliases": aliases,
            "country": offer["country"],
            "currency": currency,
            "title": offer.get("title"),
            "description": None,
            "provider": {"type": provider_type, "id": provider_id},
            "merchant_id": merchant_id,
            "merchant_text": merchant_text,
            "category": offer.get("category") or "other",
            "benefit": benefit_of(offer.get("benefit") or {}),
            "min_spend": min_spend,
            "min_spend_source_url": offer.get("min_spend_source_url"),
            "cap": cap,
            "cap_null_reason": cap_null_reason,
            "cap_source_url": offer.get("cap_source_url"),
            "eligibility": eligibility_of(offer.get("eligibility"), card_id_map),
            "cross_border": cross_border(offer, merchant_text or _merchant_name(merchant_id, merchants_out), places, currency_country),
            "status": offer["status"],
            "first_seen": seen_day,
            "last_seen": seen_day,
            "review_by": review_by,
            "review_reason": offer.get("review_reason"),
            "end_date_reviewer_accepted": False,
            "stated_end_date": offer.get("stated_end_date"),
            "start_date": offer.get("start_date"),
            "start_date_null_reason": offer.get("start_date_null_reason") if not offer.get("start_date") else None,
            "end_date": offer.get("end_date"),
            "dates_source_url": offer.get("dates_source_url"),
            "booking_period": booking,
            "usage_period": usage,
            "valid_days": valid_days(f"{offer.get('title') or ''} {offer.get('dates_text') or ''}"),
            "terms_url": offer.get("terms_url"),
            "terms_url_null_reason": offer.get("terms_url_null_reason") if not offer.get("terms_url") else None,
            "terms_scope": terms_scope,
            "terms_hash": terms_hash,
            "terms_hash_null_reason": None if terms_hash else terms_hash_null_reason,
            "terms_fetched_at": terms_fetched,
            "source_url": offer.get("source_url"),
            "source_verified": bool(offer.get("source_verified")),
            "sources": stamp_sources(offer.get("sources"), index, fetch),
            "detail_level": offer.get("detail_level") or "structured",
            "checked_at": checked_at,
            "checked_fetch_url": fetch[1] if fetch else None,
            "checked_at_null_reason": None if checked_at else "no_fetch_metadata_match",
            "_where": where,
            "_old_id": offer["_old_id"],
        }
        if record["start_date"] is None and not record["start_date_null_reason"]:
            record["start_date_null_reason"] = "not_stated_in_terms_or_page"
        offers_out.append(record)

    # Date notes were built inside apply_date_policy but not collected. Rebuild from records.
    for record in offers_out:
        if record["status"] == "needs_review" and record.get("review_reason"):
            date_notes.append({
                "id": record["_old_id"],
                "new_id": record["id"],
                "status": record["status"],
                "end_date": record.get("end_date"),
                "stated_end_date": record.get("stated_end_date"),
                "review_reason": record["review_reason"],
            })

    # Issuer official domains from every URL we will publish, plus the issuer website.
    hosts = defaultdict(set)
    for card in cards_out:
        for url in [card.get("official_url")] + [source.get("url") for source in card["sources"]]:
            host = host_of(url)
            if host:
                hosts[card["issuer_id"]].add(host)
        for benefit in card["benefits"]:
            host = host_of(benefit.get("source_url"))
            if host:
                hosts[card["issuer_id"]].add(host)
        for rate in card["earn_rates"]:
            host = host_of(rate.get("source_url"))
            if host:
                hosts[card["issuer_id"]].add(host)
        fee = card.get("annual_fee") or {}
        income = card.get("min_income") or {}
        for url in (fee.get("source_url"), income.get("source_url")):
            host = host_of(url)
            if host:
                hosts[card["issuer_id"]].add(host)
    for offer in offers_out:
        issuer = offer["provider"]["id"] if offer["provider"]["type"] == "issuer" else None
        if not issuer:
            continue
        for url in offer_urls(offer):
            host = host_of(url)
            if host:
                hosts[issuer].add(host)

    issuers_out = []
    for issuer in old_issuers:
        card_ids = sorted(card_id_map[old] for old in issuer.get("card_ids") or [] if old in card_id_map)
        # cards whose issuer matches even if the issuer list was stale
        known = {card["id"] for card in cards_out if card["issuer_id"] == issuer["id"]}
        card_ids = sorted(known)
        live = [offer for offer in offers_out if offer["provider"]["type"] == "issuer" and offer["provider"]["id"] == issuer["id"] and offer["_where"] == "live"]
        website_host = host_of(issuer.get("website"))
        domains = set(hosts.get(issuer["id"]) or [])
        if website_host:
            domains.add(website_host)
        for seed in (issuer.get("crawl") or {}).get("card_sources") or []:
            host = host_of(seed)
            if host:
                domains.add(host)
        for seed in (issuer.get("crawl") or {}).get("offer_sources") or []:
            host = host_of(seed)
            if host:
                domains.add(host)
        crawl = issuer.get("crawl") or {}
        issuers_out.append({
            "id": issuer["id"],
            "name": issuer.get("name"),
            "legal_name": issuer.get("legal_name"),
            "country": issuer["country"],
            "website": issuer.get("website"),
            "official_domains": sorted(domains),
            "card_ids": card_ids,
            "offer_count": len(live),
            "crawl": {
                "card_sources": list(crawl.get("card_sources") or []),
                "offer_sources": list(crawl.get("offer_sources") or []),
                "status": crawl.get("status") or "not_covered",
                "note": crawl.get("note"),
            },
        })

    for merchant in merchants_out.values():
        merchant["offer_ids"] = sorted(set(merchant["offer_ids"]))

    report = {
        "generated_at": generated_at,
        "offers_in": len(old_offers),
        "cards_in": len(old_cards),
        "merchants_in": len(old_merchants),
        "offers_out": len(offers_out),
        "cards_out": len(cards_out),
        "merchants_out": len(merchants_out),
        "dropped": dropped,
        "unmatched_checked_at": unmatched,
        "date_review": date_notes,
        "rules": rules,
    }
    return {
        "generated_at": generated_at,
        "countries_meta": countries,
        "networks": networks_doc,
        "cards": cards_out,
        "offers": offers_out,
        "issuers": issuers_out,
        "merchants": list(merchants_out.values()),
        "report": report,
        "card_id_map": card_id_map,
    }


def _merchant_name(merchant_id, merchants_out):
    if not merchant_id or merchant_id not in merchants_out:
        return None
    return merchants_out[merchant_id]["name"]


def load_existing(repo):
    """Index of published 0.3 ids keyed by issuer plus source URL, and by card official URL."""
    found = {}
    if not os.path.isdir(repo):
        return found
    for country in os.listdir(repo):
        if not re.fullmatch(r"[a-z]{2}", country):
            continue
        offers_dir = os.path.join(repo, country, "offers")
        cards_dir = os.path.join(repo, country, "cards")
        for folder, kind in ((offers_dir, "offer"), (cards_dir, "card")):
            if not os.path.isdir(folder):
                continue
            for name in os.listdir(folder):
                if not name.endswith(".json"):
                    continue
                with open(os.path.join(folder, name), encoding="utf-8") as fh:
                    data = json.load(fh)
                for item in data.get("items") or []:
                    if kind == "offer":
                        provider = item.get("provider") or {}
                        if provider.get("type") == "issuer":
                            found[(provider.get("id"), item.get("source_url"))] = item
                    else:
                        found[("card", item.get("issuer_id"), item.get("official_url"))] = item
        archive = os.path.join(repo, country, "archive", "offers")
        if os.path.isdir(archive):
            for name in os.listdir(archive):
                if not name.endswith(".json"):
                    continue
                with open(os.path.join(archive, name), encoding="utf-8") as fh:
                    data = json.load(fh)
                for item in data.get("items") or []:
                    provider = item.get("provider") or {}
                    if provider.get("type") == "issuer":
                        found[(provider.get("id"), item.get("source_url"))] = item
    return found
