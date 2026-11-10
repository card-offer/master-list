"""The crawler hand-in gate and the ingest step. All offers in this file are synthetic test data."""
import copy
import json
import os
import shutil
import tempfile
import unittest

from pipeline.ingest import ingest
from pipeline.lib.calendar import parse_instant
from pipeline.lib.merchants import load_merchant_rules, name_key, name_problems
from tests.test_model import ROOT
from tools.check_observations import check, date_in, number_in
from tools.validate import validate

PAGE = "https://www.cimb.com.sg/en/personal/promotions/latest-promotions/cards/casa-x-vs.html"
LIST = "https://www.cimb.com.sg/en/personal/promotions/dining-deals.html"
TERMS = "https://www.cimb.com.sg/content/dam/cimbsg/personal/document/promotions/example-kopi-tnc.pdf"
NOW = parse_instant("2026-11-12T02:00:00+08:00")


def fetch(url, kind, minute):
    return {"url": url, "final_url": url, "status": 200, "fetched_at": f"2026-11-12T01:{minute:02d}:00+08:00", "kind": kind}


def offer(**changes):
    row = {
        "source_url": LIST, "source_key": "example-kopi", "source_key_basis": "merchant_name",
        "title": "Example Kopi: 15% off total bill",
        "merchant": {"kind": "single", "name": "Example Kopi", "names": [], "outlet": "Orchard", "name_source": "listing_tile",
                     "name_quote": "EXAMPLE KOPI<sup>®</sup> (Orchard)", "name_checked": False, "official_domain": None},
        "category": "cafe",
        "benefit": {"type": "discount_pct", "value": 15, "unit": "percent", "up_to": False, "value_text": "15% off", "quote": "15% off total bill"},
        "dates": {"start_date": None, "end_date": "2027-03-31", "end_date_null_reason": None, "quote": "Valid till 31 March 2027.",
                  "source_url": TERMS, "booking_period": None, "usage_period": None, "valid_days": ["sat", "sun"]},
        "min_spend": {"amount": 50, "currency": "SGD", "quote": "with a minimum spend of S$50"},
        "limits": [{"kind": "reward_cap", "amount": 20, "currency": "SGD", "per": ["transaction"], "scope": None, "weekdays": None,
                    "quote": "Discount is capped at S$20 per transaction."}],
        "eligibility": {"scope": "card", "confidence": "stated", "network_ids": [], "card_names": ["CIMB Visa Signature"],
                        "card_types": ["credit"], "tiers": [], "quote": "Valid for CIMB Visa Signature cardmembers."},
        "terms": {"url": TERMS, "scope": "deal_document", "sha256": "a" * 64, "fetched_at": "2026-11-12T01:03:00+08:00", "null_reason": None},
        "redeem": {"countries": ["SG"], "basis": "no_foreign_signal"},
        "flags": [],
    }
    for path, value in changes.items():
        target = row
        parts = path.split("__")
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = value
    return row


CARD_PAGE = "https://www.cimb.com.sg/en/personal/banking-with-us/cards/credit-cards/example-travel.html"


def card(**changes):
    row = {
        "official_url": CARD_PAGE, "name": "CIMB Example Travel Card", "name_quote": "CIMB Example Travel Card",
        "networks": ["mastercard"], "network_quote": "World Mastercard benefits", "tier": "world", "card_type": "credit",
        "islamic": False, "status": "active",
        "annual_fee": {"amount": 196.2, "supplementary_amount": None, "quote": "Annual fee: S$196.20, waived for the first year.",
                       "waivers": [{"kind": "first_year", "min_spend": None, "min_transactions": None, "quote": "Annual fee: S$196.20, waived for the first year."}]},
        "min_income": {"amount": 30000, "period": "year", "quote": "Minimum annual income of S$30,000"},
        "earn_rates": [{"kind": "cashback_pct", "category": "overseas", "rate": 2, "up_to": False, "quote": "2% cashback on overseas spend"}],
        "benefits": [
            {"type": "lounge_access", "quote": "6 complimentary lounge visits each year", "limits": [],
             "lounge": {"programmes": ["dragonpass"], "visits": 6, "unlimited": False, "guest_policy_quote": None, "supplementary_share_visits": None}},
            {"type": "lounge_access", "quote": "Unlimited access to the Example Lounge", "limits": [],
             "lounge": {"programmes": [], "visits": None, "unlimited": True, "guest_policy_quote": None, "supplementary_share_visits": None}},
        ],
        "flags": [],
    }
    for path, value in changes.items():
        target = row
        parts = path.split("__")
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = value
    return row


def hand_in(offers):
    return {
        "contract": "observation/1",
        "run": {"run_id": "test-run-0001", "crawler": "test", "country": "SG", "issuer_id": "sg-cimb",
                "started_at": "2026-11-12T01:00:00+08:00", "finished_at": "2026-11-12T02:00:00+08:00",
                "listing_urls": [LIST], "listing_complete": False, "robots_checked": True, "blocked": []},
        "fetches": [fetch(LIST, "issuer_promotion_listing", 1), fetch(PAGE, "issuer_promotion_page", 2), fetch(TERMS, "issuer_terms_document", 3),
                    fetch(CARD_PAGE, "issuer_product_page", 4)],
        "offers": offers,
    }


def bundle():
    """The published single-page CIMB offer, seen again with a new title."""
    return offer(
        source_url=PAGE, source_key="casa-x-vs", source_key_basis="single_offer_page", title="A new title for the same page",
        merchant={"kind": "issuer_own", "name": None, "names": [], "outlet": None, "name_source": None, "name_quote": None,
                  "name_checked": False, "official_domain": None},
        category="sign_up", min_spend=None, limits=[],
        benefit={"type": "other", "value": None, "unit": None, "up_to": False, "value_text": None, "quote": None},
        dates={"start_date": None, "end_date": "2026-12-31", "end_date_null_reason": None, "quote": "Promotion ends 31 December 2026.",
               "source_url": PAGE, "booking_period": None, "usage_period": None, "valid_days": None},
        eligibility={"scope": "issuer", "confidence": "inferred", "network_ids": [], "card_names": [], "card_types": [], "tiers": [], "quote": None},
        terms={"url": PAGE, "scope": "deal_page_section", "sha256": "b" * 64, "fetched_at": "2026-11-12T01:02:00+08:00", "null_reason": None},
    )


class GateTests(unittest.TestCase):
    def errors(self, *offers):
        return check(hand_in(list(offers)), ROOT, now=NOW)[0]

    def assert_error(self, text, *offers):
        errors = self.errors(*offers)
        self.assertTrue(any(text in line for line in errors), errors)

    def test_good_hand_in_passes(self):
        self.assertEqual(self.errors(offer(), bundle()), [])

    def test_merchant_name_must_be_in_quote(self):
        self.assert_error("is not inside name_quote", offer(merchant__name="Sample Kopi", source_key="sample-kopi"))

    def test_offer_wording_is_not_a_merchant(self):
        bad = offer(merchant__name="15% off every Tue", merchant__name_quote="15% off every Tue", source_key="x", source_key_basis="page_anchor")
        self.assert_error("looks like offer wording", bad)

    def test_name_checked_accepts_a_real_name_with_offer_words(self):
        row = offer(merchant__name="Free Fire", merchant__name_quote="Free Fire", merchant__name_checked=True, merchant__outlet=None, source_key="free-fire")
        errors, warnings, _ = check(hand_in([row]), ROOT, now=NOW)
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)

    def test_issuer_is_not_a_merchant(self):
        self.assert_error("card issuer", offer(merchant__name="CIMB", merchant__name_quote="CIMB", source_key="cimb"))

    def test_unknown_merchant_needs_flag(self):
        row = offer(source_key="tile-7", source_key_basis="page_anchor")
        row["merchant"].update({"kind": "unknown", "name": None, "name_source": None, "name_quote": None, "outlet": None})
        self.assert_error("needs the flag merchant_not_stated", row)

    def test_amount_must_be_in_quote(self):
        self.assert_error("benefit value 20 is not inside its quote", offer(benefit__value=20))
        self.assert_error("min_spend amount 500", offer(min_spend__amount=500))

    def test_date_must_be_in_quote(self):
        self.assert_error("end_date 2027-04-30 is not inside dates.quote", offer(dates__end_date="2027-04-30"))

    def test_expired_offer_is_refused(self):
        self.assert_error("before the run date", offer(dates__end_date="2026-10-31", dates__quote="Valid till 31 October 2026."))

    def test_far_end_date_needs_flag(self):
        self.assert_error("months ahead", offer(dates__end_date="2029-03-31", dates__quote="Valid till 31 March 2029."))

    def test_host_must_be_official(self):
        row = hand_in([offer()])
        row["fetches"].append(fetch("https://deals.example.com/cimb", "issuer_promotion_page", 5))
        self.assertTrue(any("official_domains" in line for line in check(row, ROOT, now=NOW)[0]))

    def test_source_key_must_not_come_from_title(self):
        self.assert_error("made from the title", offer(source_key="example-kopi-15-off-total-bill", source_key_basis="page_anchor"))

    def test_fragment_in_source_url_is_refused(self):
        self.assert_error("must not have a fragment", offer(source_url=LIST + "#kopi"))

    def test_inferred_eligibility_carries_no_cards(self):
        self.assert_error("inferred eligibility", offer(eligibility__confidence="inferred"))

    def test_number_and_date_proof(self):
        self.assertTrue(number_in("capped at RM5,000", 5000))
        self.assertFalse(number_in("RM500 cap", 5000))
        self.assertFalse(number_in("115%", 15))
        self.assertTrue(date_in("until 31 Dec 26", "2026-12-31"))
        self.assertFalse(date_in("effective from 1st May 2028", "2028-04-30"))


class CardGateTests(unittest.TestCase):
    def errors(self, row):
        data = hand_in([])
        data["cards"] = [row]
        return check(data, ROOT, now=NOW)[0]

    def assert_error(self, text, row):
        errors = self.errors(row)
        self.assertTrue(any(text in line for line in errors), errors)

    def test_good_card_passes(self):
        self.assertEqual(self.errors(card()), [])

    def test_network_needs_proof(self):
        self.assert_error("network visa is not inside", card(networks=["visa"]))

    def test_no_network_needs_flag(self):
        self.assert_error("set the flag network_not_stated", card(networks=[], network_quote=None))

    def test_fee_and_income_and_rate_need_proof(self):
        self.assert_error("annual_fee amount 200", card(annual_fee__amount=200))
        self.assert_error("min_income amount 24000", card(min_income__amount=24000))
        row = card()
        row["earn_rates"][0]["rate"] = 5
        self.assert_error("rate 5 is not inside", row)

    def test_lifetime_waiver_stands_alone(self):
        row = card()
        row["annual_fee"]["waivers"].append({"kind": "lifetime", "min_spend": None, "min_transactions": None, "quote": "No annual fee for life"})
        self.assert_error("lifetime waiver cannot stand with other waivers", row)

    def test_lounge_count_and_unlimited_are_separate(self):
        row = card()
        row["benefits"][0]["lounge"]["unlimited"] = True
        self.assert_error("gives a visit count and unlimited", row)

    def test_card_name_must_be_in_quote(self):
        self.assert_error("card name is not inside name_quote", card(name="CIMB Sample Card"))


class MerchantNameTests(unittest.TestCase):
    def test_one_brand_one_key(self):
        rules = load_merchant_rules(ROOT)
        keys = {name_key(text, rules) for text in ("Shopee Singapore", "SHOPEE", "Shopee Pte Ltd", "Shopee<sup>®</sup>")}
        self.assertEqual(keys, {"shopee"})
        self.assertEqual(name_key("Singapore Airlines", rules), "singapore airlines")

    def test_published_single_merchants_pass_the_name_test(self):
        rules = load_merchant_rules(ROOT)
        with open(os.path.join(ROOT, "merchants", "registry.json"), encoding="utf-8") as fh:
            names = [row["name"] for row in json.load(fh)["items"] if not row["verified"]]
        self.assertEqual([n for n in names if name_problems(n, rules)], [])


class IngestTests(unittest.TestCase):
    def setUp(self):
        parent = tempfile.mkdtemp(prefix="card-offer-ingest-")
        self.tree = os.path.join(parent, "tree")
        shutil.copytree(ROOT, self.tree, ignore=shutil.ignore_patterns(".git", "dist", "__pycache__", "raw"))

    def items(self, *parts):
        with open(os.path.join(self.tree, *parts), encoding="utf-8") as fh:
            return json.load(fh)["items"]

    def test_ingest_keeps_ids_links_merchant_and_validates(self):
        before = {row["id"]: row for row in self.items("sg", "offers", "cimb.json")}
        report = ingest(hand_in([offer(), bundle()]), root=self.tree, now=NOW)
        after = {row["id"]: row for row in self.items("sg", "offers", "cimb.json")}
        self.assertEqual(report["exact"], 1)
        self.assertEqual(report["new"], 1)
        self.assertTrue(set(before) <= set(after))
        kept = after["sg-cimb-6037fd74b9"]
        self.assertEqual(kept["title"], "A new title for the same page")
        self.assertEqual(kept["first_seen"], before["sg-cimb-6037fd74b9"]["first_seen"])
        self.assertEqual(kept["merchant_kind"], "issuer_own")
        new = [row for key, row in after.items() if key not in before][0]
        self.assertEqual((new["merchant_name"], new["merchant_id"], new["merchant_outlet"]), ("Example Kopi", "example-kopi", "Orchard"))
        self.assertEqual(new["eligibility"]["card_ids"], ["sg-cimb-visa-signature"])
        self.assertEqual(new["cap"], {"amount": 20, "currency": "SGD", "per": "transaction"})
        text = json.dumps(new)
        for private in ("Valid till 31 March 2027", "minimum spend of S$50", "EXAMPLE KOPI"):
            self.assertNotIn(private, text)
        registry = {row["id"]: row for row in self.items("merchants", "registry.json")}
        self.assertEqual(registry["example-kopi"]["offer_ids"], [new["id"]])
        self.assertFalse(registry["example-kopi"]["verified"])
        errors, _warnings, _stats = validate(self.tree)
        self.assertEqual(errors, [])

    def test_title_change_on_a_shared_page_keeps_the_id(self):
        ingest(hand_in([offer()]), root=self.tree, now=NOW)
        first = [row for row in self.items("sg", "offers", "cimb.json") if row["merchant_name"] == "Example Kopi"][0]
        again = offer(title="Example Kopi: weekend treat", source_key="tile-12", source_key_basis="page_anchor")
        report = ingest(hand_in([again]), root=self.tree, now=NOW)
        second = [row for row in self.items("sg", "offers", "cimb.json") if row["merchant_name"] == "Example Kopi"]
        self.assertEqual(report["page_and_merchant"], 1)
        self.assertEqual([row["id"] for row in second], [first["id"]])

    def test_ingest_adds_a_card_and_an_offer_can_name_it(self):
        data = hand_in([offer(eligibility__card_names=["CIMB Example Travel Card"], eligibility__quote="Valid for CIMB Example Travel Card.")])
        data["cards"] = [card()]
        report = ingest(data, root=self.tree, now=NOW)
        self.assertEqual(report["cards"]["new"], 1)
        cards = {row["id"]: row for row in self.items("sg", "cards", "cimb.json")}
        new = cards["sg-cimb-example-travel-card"]
        self.assertEqual((new["networks"], new["network_source"], new["status"]), (["mastercard"], "crawler_quote", "active"))
        self.assertEqual(new["annual_fee"]["amount"], 196.2)
        self.assertEqual(len(new["annual_fee"]["waiver_rules"]), 1)
        self.assertEqual([b["details"]["visits_values"] for b in new["benefits"]], [[6], ["unlimited"]])
        linked = [row for row in self.items("sg", "offers", "cimb.json") if row["merchant_name"] == "Example Kopi"][0]
        self.assertEqual(linked["eligibility"]["card_ids"], ["sg-cimb-example-travel-card"])
        self.assertEqual(report["unmatched_card_names"], [])
        again = ingest(data, root=self.tree, now=NOW)
        self.assertEqual((again["cards"]["new"], again["cards"]["kept"]), (0, 1))
        errors, _warnings, _stats = validate(self.tree)
        self.assertEqual(errors, [])

    def test_card_with_no_network_goes_to_review(self):
        data = hand_in([])
        data["cards"] = [card(networks=[], network_quote=None, flags=["network_not_stated"])]
        report = ingest(data, root=self.tree, now=NOW)
        self.assertEqual(len(report["cards"]["needs_review"]), 1)
        errors, _warnings, _stats = validate(self.tree)
        self.assertEqual(errors, [])

    def test_bad_hand_in_changes_nothing(self):
        before = self.items("sg", "offers", "cimb.json")
        with self.assertRaises(SystemExit):
            ingest(hand_in([offer(benefit__value=99)]), root=self.tree, now=NOW)
        self.assertEqual(self.items("sg", "offers", "cimb.json"), before)


if __name__ == "__main__":
    unittest.main()
