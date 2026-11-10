"""Publish raw build files into the schema 0.3 tree.

Run from the repository root after the crawl has written raw/cards_built.json and
raw/offers_built.json. A rerun keeps an existing offer id when issuer and source_url
match. Fetch times come from the fetch record or pipeline/fetch_metadata.json.
Offers with no stated end date are kept. Expired offers are archived.
This module has no clock constant: generated_at is the build clock.
"""
import datetime
import json
import os
import sys
import tempfile

sys.path.insert(0, "pipeline")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from card_finish import finish as card_finish
from pipeline.lib.calendar import stamp
from pipeline.lib.rules import repo_root
from pipeline.lib.transform import build_tree, load_existing
from pipeline.migrate_0_3 import write_tree


def noem(value):
    if isinstance(value, str):
        return value.replace("\u2014", " - ").replace("  ", " ")
    if isinstance(value, list):
        return [noem(item) for item in value]
    if isinstance(value, dict):
        return {key: noem(item) for key, item in value.items()}
    return value


def enrich(offers):
    """Attach dates and terms metadata already extracted into raw/terms_enriched.json."""
    import re
    enriched = {}
    if os.path.exists("raw/terms_enriched.json"):
        enriched = json.load(open("raw/terms_enriched.json", encoding="utf-8"))
    kept = []
    for offer in offers:
        record = enriched.get(offer["source_url"]) if offer["sources"][0]["kind"] == "issuer_promotion_page" else None
        period = (record or {}).get("period")
        terms = (record or {}).get("terms")
        offer["start_date"] = period["valid_from"] if period else None
        offer["start_date_null_reason"] = None if (period and period["valid_from"]) else "not_stated_in_terms_or_page"
        offer["end_date"] = period["valid_until"] if period else None
        if period:
            offer["dates_text"] = period["text"]
            offer["dates_source_url"] = period["source_url"]
        spend = (record or {}).get("min_spend")
        cap = (record or {}).get("cap")
        if spend:
            offer["min_spend_text"] = spend["text"]
            offer["min_spend_source_url"] = spend["source_url"]
        else:
            offer["min_spend_source_url"] = offer["source_url"] if offer.get("min_spend_text") else None
        offer["cap_text"] = cap["text"] if cap else None
        offer["cap_source_url"] = cap["source_url"] if cap else None
        if terms:
            offer["terms_url"] = terms["url"]
            offer["terms_url_null_reason"] = None
            offer["terms_scope"] = "deal_page_section" if terms["kind"] == "page_section" else "deal_document"
            offer["terms_clauses"] = terms["clauses"]
            offer["terms_hash"] = terms["hash"]
            offer["terms_fetched_at"] = terms["fetched_at"]
            if terms["url"] != offer["source_url"]:
                offer["sources"] = offer["sources"] + [{
                    "url": terms["url"],
                    "kind": "issuer_terms_document",
                    "fetched_at": terms["fetched_at"],
                }]
        else:
            offer["terms_url"] = None
            if record and record.get("error"):
                offer["terms_url_null_reason"] = "deal_page_not_readable"
            elif not record:
                offer["terms_url_null_reason"] = "listing_only_no_deal_page"
            elif record.get("hub"):
                offer["terms_url_null_reason"] = "multi_deal_hub_page"
            else:
                offer["terms_url_null_reason"] = "no_deal_specific_terms_link_on_page"
            offer["terms_scope"] = None
            offer["terms_clauses"] = None
            offer["terms_hash"] = None
            offer["terms_fetched_at"] = None
        offer.pop("validity", None)
        offer.pop("last_checked", None)
        kept.append(offer)
    return noem(kept)


def write_snapshot(directory, cards, offers):
    import collections
    by_country = collections.defaultdict(lambda: {"cards": [], "offers": [], "issuers": []})
    cfg = json.load(open("pipeline/issuers_config.json", encoding="utf-8"))
    issuers = []
    for row in cfg:
        issuers.append({
            "id": row["id"],
            "name": row["name"],
            "legal_name": row.get("legal_name"),
            "country": row["country"],
            "website": row["website"],
            "card_ids": [card["id"] for card in cards if card["issuer_id"] == row["id"]],
            "offer_count": 0,
            "crawl": {
                "card_sources": row.get("seeds") or [],
                "offer_sources": [],
                "status": "ok",
                "note": None,
            },
        })
    merchants = []
    for country in {card["country"] for card in cards} | {offer["country"] for offer in offers}:
        cc = country.lower()
        os.makedirs(os.path.join(directory, cc), exist_ok=True)
        def dump(name, items, cc=cc, country=country):
            json.dump(
                {"schema_version": "0.2.0", "country": country, "generated_at": stamp(), "count": len(items), "items": items},
                open(os.path.join(directory, cc, name), "w", encoding="utf-8"),
            )
        dump("cards.json", [card for card in cards if card["country"] == country])
        dump("offers.json", [offer for offer in offers if offer["country"] == country])
        dump("issuers.json", [issuer for issuer in issuers if issuer["country"] == country])
        dump("merchants.json", merchants)


def main():
    if not os.path.exists("raw/offers_built.json") or not os.path.exists("raw/cards_built.json"):
        print("no raw build files; published tree left unchanged")
        return 0
    cards = noem(json.load(open("raw/cards_built.json", encoding="utf-8")))
    offers = noem(json.load(open("raw/offers_built.json", encoding="utf-8")))
    for card in cards:
        if card.get("network_source") == "page_text":
            card["network_candidates"] = card["networks"]
            card["networks"] = []
            card["network"] = None
            card["network_source"] = None
        card_finish(card)
        card["benefit_types"] = sorted({benefit["type"] for benefit in card["benefits"]})
    offers = enrich(offers)
    for offer in offers:
        # Merchant country is computed later from the record. Do not copy the card country in.
        offer["cross_border"] = {"merchant_country": None, "card_issuing_countries": [offer["country"]]}
        fetched = None
        for source in offer.get("sources") or []:
            if source.get("fetched_at") and "T" in str(source.get("fetched_at")):
                fetched = source["fetched_at"]
        if fetched:
            for source in offer["sources"]:
                if source.get("fetched_at") and "T" not in str(source["fetched_at"]):
                    source["fetched_at"] = fetched
    root = repo_root()
    existing = load_existing(root)
    with tempfile.TemporaryDirectory() as tmp:
        write_snapshot(tmp, cards, offers)
        generated = stamp(datetime.datetime.now(datetime.timezone.utc))
        tree = build_tree(tmp, generated, existing_index=existing, alias_legacy=False)
    write_tree(root, tree)
    print("published", len(tree["offers"]), "offers", len(tree["cards"]), "cards")
    return 0


if __name__ == "__main__":
    sys.exit(main())
