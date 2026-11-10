#!/usr/bin/env python3
"""Turn one checked crawler hand-in into published records.

    python pipeline/ingest.py raw/observations/sg/dbs/<run_id>.json

The crawler states facts with quotes. This step does the bookkeeping that must not be left
to a language model: ids, merchant registry, lifecycle dates, archive and the fetch log.
Quotes are not published, except the eligibility quote, which becomes evidence_text.
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.lib.calendar import add_months, local_date, parse_instant, stamp
from pipeline.lib.layout import write_collection, write_json
from pipeline.lib.merchants import Registry, clean_name, load_merchant_rules, name_key
from pipeline.lib.rules import load_rules, repo_root
from pipeline.lib.transform import cap_view, new_card_id, new_offer_id, placement
from tools.check_observations import check

RULE_NAMES = {
    ("card", "stated"): "card_names_matched_on_official_page",
    ("issuer_network", "stated"): "issuer_cards_on_named_network(s)",
    ("issuer", "stated"): "all_issuer_cards_stated_on_official_page",
    ("issuer", "inferred"): "issuer_wide_no_card_restriction_found",
}
SOURCE_KIND = {"single": "page"}


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_items(path):
    return load_json(path)["items"] if os.path.exists(path) else []


def base_url(url):
    return url.split("#", 1)[0]


def match_existing(obs_offer, merchant_key, existing, taken):
    """Find the published offer that is the same deal. Order: exact url and key, then same page and merchant."""
    full = f"{obs_offer['source_url']}#{obs_offer['source_key']}"
    for offer in existing:
        if offer["id"] not in taken and offer["source_url"] in (full, obs_offer["source_url"] if obs_offer["source_key_basis"] == "single_offer_page" else full):
            return offer, "exact"
    if merchant_key:
        same = [offer for offer in existing if offer["id"] not in taken
                and base_url(offer["source_url"]) == obs_offer["source_url"] and offer.get("_merchant_key") == merchant_key]
        if len(same) == 1:
            return same[0], "page_and_merchant"
        moved = [offer for offer in existing if offer["id"] not in taken and offer.get("_merchant_key") == merchant_key
                 and offer.get("end_date") == obs_offer["dates"]["end_date"] and base_url(offer["source_url"]) != obs_offer["source_url"]]
        if len(moved) == 1:
            return moved[0], "moved_url"
    return None, "new"


def ingest_cards(obs, cards, issuer_id, country, zone, mrules, report):
    """Update the issuer's card list from the hand-in. Cards that the run did not see stay as they are."""
    cc, slug = country.lower(), issuer_id.split("-", 1)[1]
    fetch_by = {}
    for row in obs["fetches"]:
        fetch_by[row["url"]] = row
        fetch_by.setdefault(row["final_url"], row)
    by_key = {name_key(card["name"], mrules): card for card in cards}
    by_url = {}
    for card in cards:
        by_url.setdefault(card["official_url"], []).append(card)
    observed_urls = [item["official_url"] for item in obs.get("cards") or []]
    used = {card["id"] for card in cards}
    for card in cards:
        used.update(card.get("aliases") or [])
    report["cards"] = {"new": 0, "kept": 0, "needs_review": []}
    for item in obs.get("cards") or []:
        page = item["official_url"]
        old = by_key.get(name_key(item["name"], mrules))
        if old is None and len(by_url.get(page, [])) == 1 and observed_urls.count(page) == 1:
            old = by_url[page][0]
        source = fetch_by[page]
        seen_day = local_date(parse_instant(source["fetched_at"]), zone["timezone"]).isoformat()
        if old:
            card_id = old["id"]
            report["cards"]["kept"] += 1
        else:
            card_id = new_card_id(cc, slug, item["name"], item["name"], used)
            report["cards"]["new"] += 1
        reasons = [f"crawler flag: {flag}" for flag in item["flags"] if flag != "shared_product_page"]
        fee, income = item["annual_fee"], item["min_income"]
        benefits = []
        for benefit in item["benefits"]:
            details = None
            limits = [{key: value for key, value in limit.items() if key != "quote"} for limit in benefit["limits"]]
            lounge = benefit["lounge"]
            if lounge or limits:
                details = {}
            if lounge:
                details.update({
                    "programmes": lounge["programmes"], "visits": lounge["visits"],
                    "visits_values": ["unlimited"] if lounge["unlimited"] else ([lounge["visits"]] if lounge["visits"] is not None else []),
                    "guest_policy_text": lounge["guest_policy_quote"], "supplementary_share_visits": lounge["supplementary_share_visits"],
                })
            if limits:
                cap, cap_reason = cap_view(limits, None)
                details.update({"limits": limits, "cap": cap, "cap_null_reason": cap_reason})
            benefits.append({"type": benefit["type"], "text": benefit["quote"], "texts": [benefit["quote"]], "source_url": page, "details": details})
        record = {
            "id": card_id, "aliases": list(old.get("aliases") or []) if old else [], "name": clean_name(item["name"]),
            "issuer_id": issuer_id, "country": country, "currency": zone["currency"],
            "networks": item["networks"], "network_source": "crawler_quote" if item["networks"] else None,
            "tier": item["tier"], "card_type": item["card_type"], "islamic": item["islamic"],
            "status": "needs_review" if reasons else item["status"], "review_reason": "; ".join(reasons) if reasons else None,
            "annual_fee": {
                "text": fee["quote"], "source_url": page, "amount": fee["amount"], "principal_amount": fee["amount"],
                "supplementary_amount": fee["supplementary_amount"],
                "waiver_rules": [{"text": w["quote"], "kind": w["kind"], "min_spend": w["min_spend"], "min_transactions": w["min_transactions"]} for w in fee["waivers"]],
            } if fee else None,
            "min_income": {
                "text": income["quote"], "source_url": page, "amount": income["amount"], "period": income["period"],
                "annual_amount": income["amount"] * 12 if income["period"] == "month" else income["amount"],
            } if income else None,
            "benefits": benefits, "benefit_types": sorted({benefit["type"] for benefit in benefits}),
            "benefits_scope": "shared_product_page" if "shared_product_page" in item["flags"] else "card",
            "earn_rates": [{"kind": r["kind"], "category": r["category"], "rate": r["rate"], "up_to": r["up_to"], "text": r["quote"], "source_url": page} for r in item["earn_rates"]],
            "official_url": page, "sources": [{"url": page, "kind": source["kind"], "fetched_at": source["fetched_at"]}],
            "name_verified_on_source": True,
            "checked_at": source["fetched_at"], "checked_fetch_url": source["url"], "checked_at_null_reason": None,
            "first_seen": (old.get("first_seen") if old else None) or seen_day, "last_seen": seen_day,
        }
        if reasons:
            report["cards"]["needs_review"].append({"card": card_id, "reasons": reasons})
        if old:
            cards[cards.index(old)] = record
        else:
            cards.append(record)
        by_key[name_key(item["name"], mrules)] = record
    return cards


def ingest(obs, root=None, now=None):
    root = root or repo_root()
    now = now or datetime.datetime.now(datetime.timezone.utc)
    errors, warnings, _stats = check(obs, root, now=now)
    if errors:
        raise SystemExit("hand-in failed the gate:\n" + "\n".join(errors))
    rules, mrules = load_rules(), load_merchant_rules(root)
    run = obs["run"]
    country, issuer_id = run["country"], run["issuer_id"]
    cc, slug = country.lower(), issuer_id.split("-", 1)[1]
    zone = {row["code"]: row for row in load_json(os.path.join(root, "countries.json"))["items"]}[country]
    today = local_date(now, zone["timezone"])
    offers_path = os.path.join(root, cc, "offers", f"{slug}.json")
    archive_path = os.path.join(root, cc, "archive", "offers", f"{slug}.json")
    reg_path = os.path.join(root, "merchants", "registry.json")
    existing, archived = load_items(offers_path), load_items(archive_path)
    for offer in existing:
        offer["_merchant_key"] = name_key(offer.get("merchant_name") or "", mrules)
    registry = Registry(load_items(reg_path), mrules)
    cards_path = os.path.join(root, cc, "cards", f"{slug}.json")
    cards = load_items(cards_path)
    cards_before = json.dumps(cards, sort_keys=True)
    card_by_key = {}
    for card in cards:
        for text in [card["name"]] + [a for a in card.get("aliases") or [] if " " in a]:
            card_by_key.setdefault(name_key(text, mrules), card["id"])
    fetch_by = {}
    for row in obs["fetches"]:
        fetch_by[row["url"]] = row
        fetch_by.setdefault(row["final_url"], row)
    used = {offer["id"] for offer in existing} | {offer["id"] for offer in archived}
    for offer in existing + archived:
        used.update(offer.get("aliases") or [])
    report = {}
    cards = ingest_cards(obs, cards, issuer_id, country, zone, mrules, report)
    card_by_key = {}
    for card in cards:
        for text in [card["name"]] + [a for a in card.get("aliases") or [] if " " in a]:
            card_by_key.setdefault(name_key(text, mrules), card["id"])
    taken, out = set(), []
    report.update({"new": 0, "exact": 0, "page_and_merchant": 0, "moved_url": 0, "needs_review": [], "unmatched_card_names": []})
    for item in obs["offers"]:
        merchant = item["merchant"]
        mkey = name_key(merchant["name"] or "", mrules) if merchant["kind"] == "single" else ""
        old, how = match_existing(item, mkey, existing, taken)
        report[how] += 1
        source = fetch_by[item["source_url"]]
        seen_day = local_date(parse_instant(source["fetched_at"]), zone["timezone"]).isoformat()
        published_url = item["source_url"] if item["source_key_basis"] == "single_offer_page" else f"{item['source_url']}#{item['source_key']}"
        aliases = []
        if old and how != "moved_url":
            taken.add(old["id"])
            offer_id, published_url, aliases = old["id"], old["source_url"], list(old.get("aliases") or [])
        else:
            offer_id = new_offer_id(cc, slug, published_url, rules["id_hash_hex_chars"], used)
            if old:
                taken.add(old["id"])
                aliases = sorted(set(old.get("aliases") or []) | {old["id"]})
        merchant_id = None
        if merchant["kind"] == "single":
            merchant_id = registry.resolve(merchant["name"], country, item["category"], merchant["official_domain"])
        rule, dates, terms = item["eligibility"], item["dates"], item["terms"]
        card_ids, reasons = [], []
        for name in rule["card_names"]:
            card_id = card_by_key.get(name_key(name, mrules))
            if card_id:
                card_ids.append(card_id)
            else:
                report["unmatched_card_names"].append({"offer": offer_id, "card_name": name})
                reasons.append(f"card name not in the card list: {name}")
        for flag in item["flags"]:
            reasons.append(f"crawler flag: {flag}")
        limits = [{key: value for key, value in limit.items() if key != "quote"} for limit in item["limits"]]
        cap, cap_reason = cap_view(limits, None)
        end = dates["end_date"]
        if reasons:
            status, review_by = "needs_review", end or add_months(today, rules["evergreen_review_months"]).isoformat()
            report["needs_review"].append({"offer": offer_id, "reasons": reasons})
        elif end is None:
            status, review_by = "evergreen", add_months(today, rules["evergreen_review_months"]).isoformat()
        else:
            status, review_by = "active", end
        publish_end = end if status != "needs_review" or "end_date_past_horizon" not in item["flags"] else None
        sources = [{"url": item["source_url"], "kind": source["kind"], "fetched_at": source["fetched_at"]}]
        latest = source
        for url in (terms["url"], dates["source_url"]):
            row = fetch_by.get(url or "")
            if row and all(entry["url"] != url for entry in sources):
                sources.append({"url": url, "kind": row["kind"], "fetched_at": row["fetched_at"]})
            if row and parse_instant(row["fetched_at"]) > parse_instant(latest["fetched_at"]):
                latest = row
        benefit = {key: value for key, value in item["benefit"].items() if key != "quote"}
        benefit["source"] = "offer_text" if benefit["value"] is not None else None
        countries = item["redeem"]["countries"]
        out.append({
            "id": offer_id, "aliases": aliases, "country": country, "currency": zone["currency"],
            "title": item["title"], "description": None,
            "provider": {"type": "issuer", "id": issuer_id},
            "merchant_kind": merchant["kind"],
            "merchant_name": clean_name(merchant["name"]) if merchant["kind"] == "single" else None,
            "merchant_names": [clean_name(name) for name in merchant["names"]],
            "merchant_outlet": merchant["outlet"], "merchant_id": merchant_id,
            "merchant_name_source": merchant["name_source"] if merchant["kind"] == "single" else None,
            "category": item["category"], "benefit": benefit,
            "min_spend": {"amount": item["min_spend"]["amount"], "currency": item["min_spend"]["currency"]} if item["min_spend"] else None,
            "min_spend_source_url": (terms["url"] or item["source_url"]) if item["min_spend"] else None,
            "cap": cap, "cap_null_reason": cap_reason, "limits": limits,
            "cap_source_url": (terms["url"] or item["source_url"]) if limits else None,
            "eligibility": {
                "scope": rule["scope"], "rule": RULE_NAMES[(rule["scope"], rule["confidence"])], "confidence": rule["confidence"],
                "issuer_ids": [issuer_id], "network_ids": rule["network_ids"], "card_ids": sorted(card_ids),
                "card_types": rule["card_types"], "tiers": rule["tiers"], "evidence_text": rule["quote"],
            },
            "cross_border": {
                "is_cross_border": any(code not in (country, "*") for code in countries) or "*" in countries,
                "card_issuing_country": country, "redeem_countries": countries, "basis": item["redeem"]["basis"],
            },
            "status": status, "first_seen": old["first_seen"] if old else seen_day, "last_seen": seen_day,
            "review_by": review_by, "review_reason": "; ".join(reasons) if reasons else None,
            "end_date_reviewer_accepted": False, "stated_end_date": end if publish_end is None and end else None,
            "start_date": dates["start_date"], "start_date_null_reason": None if dates["start_date"] else "not_stated_in_terms_or_page",
            "end_date": publish_end, "dates_source_url": dates["source_url"] or item["source_url"],
            "booking_period": dates["booking_period"],
            "usage_period": dates["usage_period"] or {"start": dates["start_date"], "end": publish_end},
            "valid_days": dates["valid_days"],
            "terms_url": terms["url"], "terms_url_null_reason": None if terms["url"] else (terms["null_reason"] or "terms_are_a_popup_on_the_listing"),
            "terms_scope": terms["scope"], "terms_hash": terms["sha256"],
            "terms_hash_null_reason": None if terms["sha256"] else "no_terms_on_page",
            "terms_fetched_at": terms["fetched_at"],
            "source_url": published_url, "source_verified": True, "sources": sources, "detail_level": "structured",
            "checked_at": latest["fetched_at"], "checked_fetch_url": latest["url"], "checked_at_null_reason": None,
        })
    # Published offers that this run did not see.
    not_seen = []
    for offer in existing:
        offer.pop("_merchant_key", None)
        if offer["id"] in taken:
            continue
        age = (today - datetime.date.fromisoformat(offer["last_seen"])).days
        if run["listing_complete"] and offer["status"] in {"active", "evergreen"} and age >= mrules["withdraw_after_days"]:
            offer["status"] = "withdrawn"
            offer["review_reason"] = f"not on the issuer listing since {offer['last_seen']}"
        not_seen.append(offer["id"])
        out.append(offer)
    live, to_archive, dropped = [], list(archived), 0
    for offer in out:
        place = placement(offer["status"], offer.get("end_date"), today, rules["archive_retention_days"])
        if place == "live":
            live.append(offer)
        elif place == "archive":
            offer["status"] = "expired"
            to_archive.append(offer)
        else:
            dropped += 1
    to_archive = [o for o in to_archive if placement("expired", o.get("end_date"), today, rules["archive_retention_days"]) == "archive"]
    generated = stamp(now)
    header = {"schema_version": "0.3.0", "country": country, "issuer_id": issuer_id, "generated_at": generated}
    write_collection(offers_path, header, live)
    if json.dumps(cards, sort_keys=True) != cards_before:
        write_collection(cards_path, header, cards)
    if to_archive:
        write_collection(archive_path, dict(header, archive=True), to_archive)
    # Registry counts need every live and archived offer in every country.
    all_offers = []
    for name in sorted(os.listdir(root)):
        if len(name) == 2 and name.isalpha() and os.path.isdir(os.path.join(root, name)):
            for folder in (os.path.join(root, name, "offers"), os.path.join(root, name, "archive", "offers")):
                if os.path.isdir(folder):
                    for file_name in sorted(os.listdir(folder)):
                        all_offers += load_items(os.path.join(folder, file_name))
    merchants = registry.finish(all_offers, rules["merchant_min_offers"])
    write_collection(reg_path, {"schema_version": "0.3.0", "generated_at": generated}, merchants)
    log_path = os.path.join(root, "pipeline", "fetch_metadata.json")
    log = load_json(log_path)
    known = {(row["url"], row["fetched_at"]) for row in log}
    for row in obs["fetches"]:
        if (row["url"], row["fetched_at"]) not in known:
            log.append({"url": row["url"], "status": row["status"], "final_url": row["final_url"], "fetched_at": row["fetched_at"]})
    with open(log_path, "w", encoding="utf-8") as fh:
        json.dump(log, fh, ensure_ascii=False, indent=0)
        fh.write("\n")
    index_path = os.path.join(root, "index.json")
    index = load_json(index_path)
    index["merchants"] = len(merchants)
    index["generated_at"] = generated
    index["countries"][country]["offers"] = sum(len(load_items(os.path.join(root, cc, "offers", f))) for f in os.listdir(os.path.join(root, cc, "offers")))
    index["countries"][country]["cards"] = sum(len(load_items(os.path.join(root, cc, "cards", f))) for f in os.listdir(os.path.join(root, cc, "cards")))
    write_json(index_path, index)
    issuers_path = os.path.join(root, cc, "issuers.json")
    issuers = load_json(issuers_path)
    for row in issuers["items"]:
        if row["id"] == issuer_id:
            row["offer_count"] = len(live)
            row["card_ids"] = sorted(card["id"] for card in cards)
    header = {key: value for key, value in issuers.items() if key not in ("items", "count")}
    write_collection(issuers_path, header, issuers["items"])
    report.update({"issuer": issuer_id, "live": len(live), "archived": len(to_archive), "dropped_after_retention": dropped,
                   "not_seen_in_this_run": len(not_seen), "warnings": warnings})
    return report


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    print(json.dumps(ingest(load_json(sys.argv[1])), indent=1))
