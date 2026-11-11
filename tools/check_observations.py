#!/usr/bin/env python3
"""Gate for a crawler hand-in file (schema/observation.schema.json).

    python tools/check_observations.py raw/observations/sg/dbs/<run_id>.json

Exit 0: the file can go to pipeline/ingest.py. Exit 1: fix every error line and run again.
The gate does not fetch. It proves each published fact from the quote the crawler gives:
the merchant name, each amount and each date must be inside its quote.
"""
import datetime
import json
import os
import re
import sys

from jsonschema import Draft202012Validator, FormatChecker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.lib.calendar import add_months, parse_instant
from pipeline.lib.merchants import load_merchant_rules, name_key, name_problems, quote_has_name, slug
from pipeline.lib.rules import load_rules
from pipeline.lib.transform import host_of

MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def number_in(quote, amount):
    whole, _, frac = f"{amount:.4f}".rstrip("0").rstrip(".").partition(".")
    grouped = ""
    for index, digit in enumerate(reversed(whole)):
        if index and index % 3 == 0:
            grouped = "[,. ]?" + grouped
        grouped = digit + grouped
    pattern = r"(?<![\d.,])" + grouped + (r"\." + frac + "0*" if frac else r"(?:\.0+)?") + r"(?!\d)"
    return re.search(pattern, quote or "") is not None


def date_in(quote, iso):
    day = datetime.date.fromisoformat(iso)
    text = (quote or "").lower()
    has_day = re.search(rf"(?<!\d)0?{day.day}(?!\d)", text) is not None
    has_year = str(day.year) in text or re.search(rf"(?<!\d){day.year % 100:02d}(?!\d)", text) is not None
    name = MONTHS[day.month - 1]
    has_month = name[:3] in text or re.search(rf"(?<!\d)0?{day.month}(?!\d)", text) is not None
    return has_day and has_month and has_year


def check(obs, root, now=None):
    """Return (errors, warnings, stats). now is the clock for the expiry test (default: run finish)."""
    errors, warnings = [], []
    schema = load_json(os.path.join(root, "schema", "observation.schema.json"))
    for err in Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(obs):
        errors.append(f"schema {err.json_path}: {err.message[:200]}")
    if errors:
        return errors, warnings, {}
    rules, mrules = load_rules(), load_merchant_rules(root)
    run = obs["run"]
    country = run["country"]
    issuer_path = os.path.join(root, country.lower(), "issuers.json")
    issuers = {row["id"]: row for row in load_json(issuer_path)["items"]} if os.path.exists(issuer_path) else {}
    issuer = issuers.get(run["issuer_id"])
    if issuer is None:
        return [f"run: issuer {run['issuer_id']} is not in {country.lower()}/issuers.json. Add the issuer with its official_domains first."], warnings, {}
    networks = load_json(os.path.join(root, "networks.json"))["items"]
    official = set(issuer.get("official_domains") or [])
    currencies = {row["currency"] for row in rules["currency_symbols"]}
    currencies |= {row["currency"] for row in load_json(os.path.join(root, "countries.json"))["items"]}
    if not run["robots_checked"]:
        errors.append("run: robots_checked is false. Read robots.txt for each host before the crawl.")
    started, finished = parse_instant(run["started_at"]), parse_instant(run["finished_at"])
    run_day = (now or finished).date()
    horizon = add_months(run_day, rules["end_date_max_months"])
    fetched = {}
    for row in obs["fetches"]:
        when = parse_instant(row["fetched_at"])
        if not started <= when <= finished:
            errors.append(f"fetch {row['url']}: fetched_at is outside the run start and finish")
        if row["kind"] != "merchant_page":
            first, last = host_of(row["url"]), host_of(row["final_url"])
            if first not in official:
                errors.append(f"fetch {row['url']}: host {first} is not on {run['issuer_id']} official_domains")
            elif last not in official:
                errors.append(f"fetch {row['url']}: it redirects to {last}, which is not on {run['issuer_id']} official_domains. "
                              f"Remove this fetch record and add the url to run.blocked with reason off_domain_redirect and redirect_to.")
        fetched[row["url"]] = row
        fetched.setdefault(row["final_url"], row)
    for row in run["blocked"]:
        if host_of(row["url"]) not in official:
            errors.append(f"run.blocked {row['url']}: host is not on {run['issuer_id']} official_domains. Record only official urls that you could not read.")
        if (row["reason"] == "off_domain_redirect") != ("redirect_to" in row):
            errors.append(f"run.blocked {row['url']}: redirect_to goes with reason off_domain_redirect, and only with it")
    if run["listing_complete"] and any(row["reason"] == "off_domain_redirect" for row in run["blocked"]):
        errors.append("run: listing_complete is true, but an official url redirects to a host that was not crawled")
    for url in run["listing_urls"]:
        if url not in fetched:
            errors.append(f"run: listing url {url} has no fetch record")

    def need_fetch(where, url):
        row = fetched.get(url)
        if row is None:
            errors.append(f"{where}: {url} has no fetch record")
        elif row["status"] != 200:
            errors.append(f"{where}: {url} was fetched with status {row['status']}, not 200")

    def quote_ok(where, quote):
        if quote is not None and len(quote) > mrules["quote_max_chars"]:
            errors.append(f"{where}: quote is longer than {mrules['quote_max_chars']} characters. Give the one sentence that states the fact.")
        if quote and "—" in quote:
            pass

    seen_keys, per_url = set(), {}
    kinds = {}
    for index, offer in enumerate(obs["offers"]):
        where = f"offer[{index}] {offer['source_key']}"
        url = offer["source_url"]
        if "#" in url:
            errors.append(f"{where}: source_url must not have a fragment. Put the anchor in source_key.")
        need_fetch(where, url)
        pair = (url, offer["source_key"])
        if pair in seen_keys:
            errors.append(f"{where}: the same source_url and source_key appear twice")
        seen_keys.add(pair)
        per_url.setdefault(url, []).append(offer)
        if "—" in offer["title"]:
            errors.append(f"{where}: title contains an em dash")
        merchant = offer["merchant"]
        kind = merchant["kind"]
        kinds[kind] = kinds.get(kind, 0) + 1
        quote_ok(where + " merchant", merchant["name_quote"])
        if kind == "single":
            name = merchant["name"]
            if not name or not merchant["name_source"] or not merchant["name_quote"]:
                errors.append(f"{where}: merchant kind single needs name, name_source and name_quote")
            else:
                problems = name_problems(name, mrules, [issuer["name"]], [row["name"] for row in networks])
                for problem in problems:
                    if "offer wording" in problem and merchant["name_checked"]:
                        warnings.append(f"{where}: merchant name '{name}' has offer-like words, accepted because name_checked is true")
                    else:
                        errors.append(f"{where}: merchant name '{name}': {problem}")
                if not quote_has_name(merchant["name_quote"], name):
                    errors.append(f"{where}: merchant name '{name}' is not inside name_quote. Copy the name as the page writes it.")
                if merchant["outlet"] and name_key(merchant["outlet"], mrules) and name_key(merchant["outlet"], mrules) in name_key(name, mrules):
                    errors.append(f"{where}: the outlet is repeated inside the merchant name. Put the brand in name and the outlet in outlet.")
            if merchant["names"]:
                errors.append(f"{where}: merchant kind single must have an empty names list")
        else:
            if merchant["name"] is not None:
                errors.append(f"{where}: merchant name must be null when kind is {kind}")
            if kind == "multiple":
                if len(merchant["names"]) < 2:
                    errors.append(f"{where}: merchant kind multiple needs two or more names")
                if not merchant["name_quote"]:
                    errors.append(f"{where}: merchant kind multiple needs name_quote")
                for name in merchant["names"]:
                    for problem in name_problems(name, mrules, [issuer["name"]], [row["name"] for row in networks]):
                        errors.append(f"{where}: merchant name '{name}': {problem}")
                    if merchant["name_quote"] and not quote_has_name(merchant["name_quote"], name):
                        errors.append(f"{where}: merchant name '{name}' is not inside name_quote")
            elif merchant["names"]:
                errors.append(f"{where}: names must be empty when kind is {kind}")
            if kind == "unknown" and "merchant_not_stated" not in offer["flags"]:
                errors.append(f"{where}: merchant kind unknown needs the flag merchant_not_stated. Use it only after you read the page, the tile and the terms.")
        if kind != "unknown" and "merchant_not_stated" in offer["flags"]:
            errors.append(f"{where}: flag merchant_not_stated is set but merchant kind is {kind}")
        basis = offer["source_key_basis"]
        if basis == "merchant_name":
            if kind != "single" or offer["source_key"] != slug(name_key(merchant["name"] or "", mrules)):
                errors.append(f"{where}: source_key_basis merchant_name needs source_key equal to the merchant name key ({slug(name_key(merchant['name'] or '', mrules))})")
        elif offer["source_key"] == slug(offer["title"])[:60].strip("-"):
            errors.append(f"{where}: source_key is made from the title. Use the page anchor, deal code, terms file name or merchant name.")
        benefit = offer["benefit"]
        quote_ok(where + " benefit", benefit["quote"])
        if benefit["value"] is not None and re.search(r"(?i)\b(?:processing|service|admin(?:istrative)?|annual)\s+fees?\b|\binterest\b|\bp\.?\s?a\.?(?![a-z])|\beir\b", benefit["value_text"] or ""):
            errors.append(f"{where}: benefit value_text describes a fee or an interest rate. A fee is not a benefit value: use value null, or give the amount that the cardholder gets.")
        if benefit["value"] is not None:
            if benefit["unit"] is None or not benefit["quote"]:
                errors.append(f"{where}: benefit value needs unit and quote")
            elif not number_in(benefit["quote"], benefit["value"]):
                errors.append(f"{where}: benefit value {benefit['value']} is not inside its quote")
        dates = offer["dates"]
        quote_ok(where + " dates", dates["quote"])
        end, start = dates["end_date"], dates["start_date"]
        if end is None:
            if dates["end_date_null_reason"] != "not_stated":
                errors.append(f"{where}: end_date is null, so end_date_null_reason must be not_stated")
        else:
            if dates["end_date_null_reason"] is not None:
                errors.append(f"{where}: end_date is set, so end_date_null_reason must be null")
            if not dates["quote"] or not dates["source_url"]:
                errors.append(f"{where}: end_date needs dates.quote and dates.source_url")
            elif not date_in(dates["quote"], end):
                errors.append(f"{where}: end_date {end} is not inside dates.quote (day, month and year)")
            day = datetime.date.fromisoformat(end)
            if day < run_day:
                errors.append(f"{where}: end_date {end} is before the run date. Do not hand in expired offers.")
            if day > horizon and "end_date_past_horizon" not in offer["flags"]:
                errors.append(f"{where}: end_date {end} is more than {rules['end_date_max_months']} months ahead. Read it again. If it is correct, set the flag end_date_past_horizon.")
            if start and start > end:
                errors.append(f"{where}: start_date is after end_date")
        if start and dates["quote"] and not date_in(dates["quote"], start):
            errors.append(f"{where}: start_date {start} is not inside dates.quote. Use null when the page does not state it.")
        if dates["source_url"]:
            need_fetch(where + " dates", dates["source_url"])
        spend = offer["min_spend"]
        if spend:
            quote_ok(where + " min_spend", spend["quote"])
            if not number_in(spend["quote"], spend["amount"]):
                errors.append(f"{where}: min_spend amount {spend['amount']} is not inside its quote")
            if spend["currency"] not in currencies:
                errors.append(f"{where}: min_spend currency {spend['currency']} is not in config")
        for number, limit in enumerate(offer["limits"]):
            quote_ok(f"{where} limits[{number}]", limit["quote"])
            if not number_in(limit["quote"], limit["amount"]):
                errors.append(f"{where}: limits[{number}] amount {limit['amount']} is not inside its quote")
            if limit["currency"] and limit["currency"] not in currencies:
                errors.append(f"{where}: limits[{number}] currency {limit['currency']} is not in config")
            if limit["kind"] in {"reward_cap", "qualifying_spend_cap", "per_transaction_limit"} and not limit["currency"]:
                errors.append(f"{where}: limits[{number}] kind {limit['kind']} needs a currency")
        rule = offer["eligibility"]
        quote_ok(where + " eligibility", rule["quote"])
        if rule["confidence"] == "stated" and not rule["quote"]:
            errors.append(f"{where}: stated eligibility needs a quote")
        if rule["confidence"] == "inferred" and (rule["scope"] != "issuer" or rule["card_names"] or rule["network_ids"]):
            errors.append(f"{where}: inferred eligibility must be scope issuer with no card names and no networks")
        if rule["scope"] == "card" and not rule["card_names"]:
            errors.append(f"{where}: scope card needs card_names")
        if rule["scope"] == "issuer_network" and not rule["network_ids"]:
            errors.append(f"{where}: scope issuer_network needs network_ids")
        terms = offer["terms"]
        if terms["scope"] is None:
            if terms["url"] or terms["sha256"] or terms["null_reason"] is None:
                errors.append(f"{where}: terms.scope is null, so url and sha256 must be null and null_reason must be set")
        else:
            if not terms["sha256"] or not terms["fetched_at"]:
                errors.append(f"{where}: terms need sha256 and fetched_at. Hash the full terms text at fetch time.")
            if terms["scope"] == "deal_document":
                if not terms["url"] or terms["url"] == url:
                    errors.append(f"{where}: terms.scope deal_document needs the document url, not the page url")
            elif terms["scope"] == "deal_page_section" and terms["url"] != url:
                errors.append(f"{where}: terms.scope deal_page_section needs terms.url equal to source_url")
            elif terms["scope"] == "listing_popup" and terms["url"] is not None:
                errors.append(f"{where}: terms.scope listing_popup needs terms.url null")
            if terms["url"]:
                need_fetch(where + " terms", terms["url"])
        redeem = offer["redeem"]
        if redeem["basis"] == "no_foreign_signal" and redeem["countries"] != [country]:
            errors.append(f"{where}: redeem basis no_foreign_signal needs countries [{country}]")
    for url, group in per_url.items():
        if len(group) > 1 and any(offer["source_key_basis"] == "single_offer_page" for offer in group):
            errors.append(f"{url}: source_key_basis single_offer_page is used, but the page has {len(group)} offers")
    network_words = {"visa": ["visa"], "mastercard": ["mastercard", "master card"], "amex": ["american express", "amex"],
                     "unionpay": ["unionpay", "union pay"], "jcb": ["jcb"], "diners": ["diners"]}
    seen_cards = set()
    for index, card in enumerate(obs.get("cards") or []):
        where = f"card[{index}] {card['name']}"
        page = card["official_url"]
        if "#" in page:
            errors.append(f"{where}: official_url must not have a fragment")
        need_fetch(where, page)
        key = name_key(card["name"], mrules)
        if key in seen_cards:
            errors.append(f"{where}: the same card name appears twice")
        seen_cards.add(key)
        quote_ok(where + " name", card["name_quote"])
        if not quote_has_name(card["name_quote"], card["name"]):
            errors.append(f"{where}: card name is not inside name_quote. Copy the name as the page heading writes it.")
        if key == name_key(issuer["name"], mrules):
            errors.append(f"{where}: card name is only the issuer name")
        if card["networks"]:
            proof = ((card["network_quote"] or "") + " " + card["name"]).lower()
            if not card["network_quote"]:
                errors.append(f"{where}: networks need network_quote")
            quote_ok(where + " network", card["network_quote"])
            for network in card["networks"]:
                if not any(word in proof for word in network_words[network]):
                    errors.append(f"{where}: network {network} is not inside network_quote or the card name")
            if "network_not_stated" in card["flags"]:
                errors.append(f"{where}: flag network_not_stated is set but networks are given")
        elif "network_not_stated" not in card["flags"]:
            errors.append(f"{where}: no network. Read the page, the card image alt text and the product disclosure sheet. If none states it, set the flag network_not_stated.")
        fee = card["annual_fee"]
        if fee:
            quote_ok(where + " annual_fee", fee["quote"])
            for label in ("amount", "supplementary_amount"):
                value = fee[label]
                if value not in (None, 0) and not number_in(fee["quote"], value):
                    errors.append(f"{where}: annual_fee {label} {value} is not inside its quote")
            for number, waiver in enumerate(fee["waivers"]):
                quote_ok(f"{where} waivers[{number}]", waiver["quote"])
                if waiver["min_spend"] is not None and not number_in(waiver["quote"], waiver["min_spend"]):
                    errors.append(f"{where}: waivers[{number}] min_spend is not inside its quote")
                if waiver["min_transactions"] is not None and not number_in(waiver["quote"], waiver["min_transactions"]):
                    errors.append(f"{where}: waivers[{number}] min_transactions is not inside its quote")
            kinds_seen = [waiver["kind"] for waiver in fee["waivers"]]
            if len(kinds_seen) != len(set(kinds_seen)):
                errors.append(f"{where}: two waivers have the same kind. Give one waiver for each kind.")
            if "lifetime" in kinds_seen and len(kinds_seen) > 1:
                errors.append(f"{where}: a lifetime waiver cannot stand with other waivers. Read the page again or set the flag fee_unclear.")
        income = card["min_income"]
        if income:
            quote_ok(where + " min_income", income["quote"])
            if not number_in(income["quote"], income["amount"]):
                errors.append(f"{where}: min_income amount {income['amount']} is not inside its quote")
        for number, rate in enumerate(card["earn_rates"]):
            quote_ok(f"{where} earn_rates[{number}]", rate["quote"])
            if not number_in(rate["quote"], rate["rate"]):
                errors.append(f"{where}: earn_rates[{number}] rate {rate['rate']} is not inside its quote")
        for number, benefit in enumerate(card["benefits"]):
            quote_ok(f"{where} benefits[{number}]", benefit["quote"])
            lounge = benefit["lounge"]
            if lounge and benefit["type"] != "lounge_access":
                errors.append(f"{where}: benefits[{number}] has lounge details but type is {benefit['type']}")
            if lounge:
                quote_ok(f"{where} benefits[{number}] guest", lounge["guest_policy_quote"])
                if lounge["visits"] is not None and lounge["unlimited"]:
                    errors.append(f"{where}: benefits[{number}] gives a visit count and unlimited. Use one entry for each lounge rule.")
                if lounge["visits"] is not None and not number_in(benefit["quote"], lounge["visits"]):
                    errors.append(f"{where}: benefits[{number}] lounge visits {lounge['visits']} is not inside its quote")
                if lounge["unlimited"] and "unlimited" not in benefit["quote"].lower():
                    errors.append(f"{where}: benefits[{number}] unlimited is not inside its quote")
            for position, limit in enumerate(benefit["limits"]):
                if not number_in(limit["quote"], limit["amount"]):
                    errors.append(f"{where}: benefits[{number}] limits[{position}] amount is not inside its quote")
    total = len(obs["offers"])
    unknown = kinds.get("unknown", 0)
    if total >= 20 and unknown * 100 > mrules["unknown_merchant_max_pct"] * total:
        errors.append(f"run: {unknown} of {total} offers have merchant kind unknown. The limit is {mrules['unknown_merchant_max_pct']} percent. Read the listing tiles and terms again.")
    stats = {"cards": len(obs.get("cards") or []), "offers": total, "merchant_kinds": kinds, "errors": len(errors), "warnings": len(warnings)}
    return errors, warnings, stats


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    errors, warnings, stats = check(load_json(argv[1]), root)
    for line in warnings:
        print("warning", line)
    for line in errors:
        print("error", line)
    print(json.dumps(stats))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
