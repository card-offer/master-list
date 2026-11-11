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

    def test_name_cannot_be_made_from_two_parts_of_an_address(self):
        row = offer(merchant__name="Fairmont Singapore", merchant__outlet=None, source_key="fairmont",
                    merchant__name_quote="80 Bras Basah Rd, Level 1 Fairmont, Singapore 189560")
        self.assert_error("is not inside name_quote", row)
        row["merchant"]["name_quote"] = "Fairmont Singapore 80 Bras Basah Road, Level 8 Singapore 189560"
        self.assertEqual(self.errors(row), [])

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

    def test_fee_is_not_a_benefit_value(self):
        row = offer(benefit={"type": "other", "value": 0.88, "unit": "percent", "up_to": False,
                             "value_text": "processing fee from 0.88%", "quote": "low processing fees from 0.88%"})
        self.assert_error("A fee is not a benefit value", row)

    def test_customer_segment_is_not_a_tier(self):
        self.assert_error("is not one of", offer(eligibility__tiers=["CIMB Preferred"]))

    def test_off_domain_redirect_goes_to_blocked(self):
        data = hand_in([offer()])
        moved = fetch("https://www.cimb.com.sg/en/personal/promotions/elsewhere.html", "issuer_promotion_listing", 5)
        moved["final_url"] = "https://offers.example.com/sg"
        data["fetches"].append(moved)
        errors = check(data, ROOT, now=NOW)[0]
        self.assertTrue(any("reason off_domain_redirect" in line for line in errors), errors)
        data["fetches"].pop()
        data["run"]["blocked"] = [{"url": moved["url"], "reason": "off_domain_redirect", "redirect_to": moved["final_url"]}]
        self.assertEqual(check(data, ROOT, now=NOW)[0], [])
        data["run"]["listing_complete"] = True
        self.assertTrue(any("listing_complete is true" in line for line in check(data, ROOT, now=NOW)[0]))

    def test_session_id_in_a_url_is_refused(self):
        data = hand_in([offer()])
        data["fetches"].append(fetch("https://www.cimb.com.sg/page.html;jsessionid=ABC123", "issuer_promotion_page", 5))
        self.assertTrue(any("session id" in line for line in check(data, ROOT, now=NOW)[0]))

    def test_robots_unreachable_is_a_blocked_reason(self):
        data = hand_in([offer()])
        data["run"]["blocked"] = [{"url": "https://www.cimb.com.sg/robots.txt", "reason": "robots_unreachable"}]
        self.assertEqual(check(data, ROOT, now=NOW)[0], [])

    def test_number_and_date_proof(self):
        self.assertTrue(number_in("capped at RM5,000", 5000))
        self.assertFalse(number_in("RM500 cap", 5000))
        self.assertFalse(number_in("115%", 15))
        self.assertTrue(date_in("until 31 Dec 26", "2026-12-31"))
        self.assertFalse(date_in("effective from 1st May 2028", "2028-04-30"))


NET_LIST = "https://specials.priceless.com/th-th"
NET_PAGE = "https://specials.priceless.com/th-th/offers/example-cafe"


def network_hand_in(*offers, country="TH"):
    return {
        "contract": "observation/1",
        "run": {"run_id": "test-net-0001", "crawler": "test", "country": country, "network_id": "mastercard", "language": "th",
                "started_at": "2026-11-12T01:00:00+08:00", "finished_at": "2026-11-12T02:00:00+08:00",
                "listing_urls": [NET_LIST], "listing_complete": False, "robots_checked": True, "blocked": []},
        "fetches": [fetch(NET_LIST, "network_offer_listing", 1), fetch(NET_PAGE, "network_offer_page", 2)],
        "offers": list(offers),
    }


def network_offer(**changes):
    row = offer(
        source_url=NET_PAGE, source_key="example-cafe", source_key_basis="single_offer_page",
        title="\u0e2a\u0e48\u0e27\u0e19\u0e25\u0e14 15% \u0e17\u0e35\u0e48 Example Cafe",
        merchant={"kind": "single", "name": "Example Cafe", "names": [], "outlet": None, "name_source": "page_heading",
                  "name_quote": "Example Cafe | \u0e40\u0e2d\u0e47\u0e01\u0e0b\u0e4c\u0e41\u0e2d\u0e21\u0e40\u0e1b\u0e34\u0e25 \u0e04\u0e32\u0e40\u0e1f\u0e48", "name_checked": False, "official_domain": None,
                  "alt_names": ["\u0e40\u0e2d\u0e47\u0e01\u0e0b\u0e4c\u0e41\u0e2d\u0e21\u0e40\u0e1b\u0e34\u0e25 \u0e04\u0e32\u0e40\u0e1f\u0e48"]},
        dates={"start_date": None, "end_date": "2026-12-31", "end_date_null_reason": None,
               "quote": "\u0e16\u0e36\u0e07 31 \u0e18.\u0e04. 2569", "source_url": NET_PAGE,
               "booking_period": None, "usage_period": None, "valid_days": None},
        min_spend={"amount": 1500, "currency": "THB", "quote": "\u0e43\u0e0a\u0e49\u0e08\u0e48\u0e32\u0e22\u0e02\u0e31\u0e49\u0e19\u0e15\u0e48\u0e33 1,500 \u0e1a\u0e32\u0e17"},
        limits=[],
        eligibility={"scope": "network", "confidence": "stated", "network_ids": ["mastercard"], "card_names": [], "card_types": ["credit"],
                     "tiers": ["world"], "issuer_names": [], "quote": "World Mastercard cardholders"},
        terms={"url": NET_PAGE, "scope": "deal_page_section", "sha256": "c" * 64, "fetched_at": "2026-11-12T01:02:00+08:00", "null_reason": None},
        redeem={"countries": ["TH"], "basis": "no_foreign_signal"},
    )
    for path, value in changes.items():
        target = row
        parts = path.split("__")
        for part in parts[:-1]:
            target = target[part]
        target[parts[-1]] = value
    return row


class NetworkAndLanguageTests(unittest.TestCase):
    def setUp(self):
        parent = tempfile.mkdtemp(prefix="card-offer-net-")
        self.tree = os.path.join(parent, "tree")
        shutil.copytree(ROOT, self.tree, ignore=shutil.ignore_patterns(".git", "dist", "__pycache__", "raw"))

    def errors(self, data):
        return check(data, ROOT, now=NOW)[0]

    def test_network_hand_in_in_thai_passes(self):
        self.assertEqual(self.errors(network_hand_in(network_offer())), [])

    def test_network_run_needs_network_scope_and_no_cards(self):
        bad = network_offer(eligibility__scope="issuer")
        self.assertTrue(any("scope network" in line for line in self.errors(network_hand_in(bad))))
        data = network_hand_in(network_offer())
        data["cards"] = [card()]
        self.assertTrue(any("has no cards list" in line for line in self.errors(data)))

    def test_run_needs_one_owner_and_a_known_country(self):
        data = network_hand_in(network_offer())
        data["run"]["issuer_id"] = "sg-cimb"
        self.assertTrue(any("not both" in line for line in self.errors(data)))
        self.assertTrue(any("not in countries.json" in line for line in self.errors(network_hand_in(network_offer(), country="ZZ"))))

    def test_network_host_must_be_listed(self):
        data = network_hand_in(network_offer())
        data["fetches"].append(fetch("https://www.priceless-deals.example/th", "network_offer_page", 3))
        self.assertTrue(any("official_domains" in line for line in self.errors(data)))

    def test_alt_name_must_be_in_quote(self):
        bad = network_offer(merchant__alt_names=["\u0e23\u0e49\u0e32\u0e19\u0e2d\u0e37\u0e48\u0e19"])
        self.assertTrue(any("alt name" in line for line in self.errors(network_hand_in(bad))))

    def test_amounts_and_dates_in_other_languages(self):
        self.assertTrue(number_in("minimal transaksi Rp1 juta", 1000000))
        self.assertTrue(number_in("Rp 500.000", 500000))
        self.assertFalse(number_in("Rp 500.000", 500))
        self.assertTrue(number_in("5\u4e07\u5186\u4ee5\u4e0a", 50000))
        self.assertTrue(date_in("berlaku hingga 31 Desember 2026", "2026-12-31"))
        self.assertTrue(date_in("2026\u5e7412\u670831\u65e5\u307e\u3067", "2026-12-31"))
        self.assertTrue(date_in("\u0111\u1ebfn h\u1ebft ng\u00e0y 31/12/2026", "2026-12-31"))

    def test_names_in_other_scripts_keep_a_key_and_get_an_id(self):
        rules = load_merchant_rules(ROOT)
        self.assertEqual(name_key("\u30b9\u30bf\u30fc\u30d0\u30c3\u30af\u30b9", rules), "\u30b9\u30bf\u30fc\u30d0\u30c3\u30af\u30b9")
        self.assertEqual(name_key("Shopee Vi\u1ec7t Nam", rules), "shopee")
        self.assertEqual(name_key("Uniqlo Hong Kong", rules), "uniqlo")

    def test_network_ingest_makes_a_new_country_and_validates(self):
        report = ingest(network_hand_in(network_offer()), root=self.tree, now=NOW)
        self.assertEqual((report["new"], report["provider"]), (1, "mastercard"))
        path = os.path.join(self.tree, "th", "offers", "network-mastercard.json")
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        new = data["items"][0]
        self.assertEqual((data["network_id"], data["issuer_id"]), ("mastercard", None))
        self.assertTrue(new["id"].startswith("th-network-mastercard-"))
        self.assertEqual(new["provider"], {"type": "network", "id": "mastercard"})
        self.assertEqual((new["eligibility"]["scope"], new["eligibility"]["issuer_ids"], new["eligibility"]["tiers"]), ("network", [], ["world"]))
        self.assertEqual((new["currency"], new["end_date"], new["min_spend"]), ("THB", "2026-12-31", {"amount": 1500, "currency": "THB"}))
        with open(os.path.join(self.tree, "merchants", "registry.json"), encoding="utf-8") as fh:
            brand = {row["id"]: row for row in json.load(fh)["items"]}["example-cafe"]
        self.assertEqual(len(brand["aliases"]), 1)
        self.assertEqual(brand["countries"], ["TH"])
        with open(os.path.join(self.tree, "index.json"), encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["countries"]["TH"]["offers"], 1)
        errors, _warnings, _stats = validate(self.tree)
        self.assertEqual(errors, [])

    def test_network_offer_for_named_issuers(self):
        row = network_offer(eligibility__issuer_names=["CIMB Singapore", "Example Bank"], redeem__countries=["SG"],
                            min_spend=None)
        data = network_hand_in(row, country="SG")
        report = ingest(data, root=self.tree, now=NOW)
        with open(os.path.join(self.tree, "sg", "offers", "network-mastercard.json"), encoding="utf-8") as fh:
            new = json.load(fh)["items"][0]
        self.assertEqual(new["eligibility"]["issuer_ids"], ["sg-cimb"])
        self.assertEqual(new["status"], "needs_review")
        self.assertIn("Example Bank", new["review_reason"])
        self.assertEqual(len(report["needs_review"]), 1)
        errors, _warnings, _stats = validate(self.tree)
        self.assertEqual(errors, [])


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

    def test_em_dash_in_a_quote_does_not_stop_the_ingest(self):
        row = offer(eligibility__quote="Valid for CIMB Visa Signature cardmembers \u2014 principal only.")
        ingest(hand_in([row]), root=self.tree, now=NOW)
        new = [item for item in self.items("sg", "offers", "cimb.json") if item["merchant_name"] == "Example Kopi"][0]
        self.assertEqual(new["eligibility"]["evidence_text"], "Valid for CIMB Visa Signature cardmembers - principal only.")
        errors, _warnings, _stats = validate(self.tree)
        self.assertEqual(errors, [])

    def test_ingest_adds_lines_to_the_fetch_log_and_changes_none(self):
        path = os.path.join(self.tree, "pipeline", "fetch_metadata.json")
        with open(path, encoding="utf-8") as fh:
            before = fh.read().splitlines()
        ingest(hand_in([offer()]), root=self.tree, now=NOW)
        with open(path, encoding="utf-8") as fh:
            after = fh.read().splitlines()
        self.assertEqual(len(after) - len(before), 4)
        self.assertEqual(after[:len(before) - 2], before[:-2])

    def test_card_names_match_without_the_issuer_or_country_word(self):
        row = offer(eligibility__card_names=["Visa Infinite", "CIMB Singapore Visa Signature", "CIMB VISA Infinite"],
                    eligibility__quote="Valid for CIMB Singapore Visa Signature and Visa Infinite.")
        report = ingest(hand_in([row]), root=self.tree, now=NOW)
        new = [item for item in self.items("sg", "offers", "cimb.json") if item["merchant_name"] == "Example Kopi"][0]
        self.assertEqual(report["unmatched_card_names"], [])
        self.assertEqual(new["eligibility"]["card_ids"], ["sg-cimb-visa-infinite", "sg-cimb-visa-signature"])
        self.assertEqual(new["status"], "active")

    def test_each_merchant_of_a_multiple_offer_is_in_the_registry(self):
        row = offer(source_key="airport-dining", source_key_basis="page_anchor",
                    merchant={"kind": "multiple", "name": None, "names": ["Example Kopi", "Sample Noodle Bar"], "outlet": None,
                              "name_source": "page_heading", "name_quote": "Example Kopi: T1, Sample Noodle Bar: T3",
                              "name_checked": False, "official_domain": None})
        ingest(hand_in([row]), root=self.tree, now=NOW)
        new = [item for item in self.items("sg", "offers", "cimb.json") if item["merchant_kind"] == "multiple"][0]
        self.assertEqual(new["merchant_ids"], ["example-kopi", "sample-noodle-bar"])
        self.assertIsNone(new["merchant_id"])
        registry = {item["id"]: item for item in self.items("merchants", "registry.json")}
        self.assertEqual(registry["sample-noodle-bar"]["offer_ids"], [new["id"]])
        errors, _warnings, _stats = validate(self.tree)
        self.assertEqual(errors, [])

    def test_a_kept_card_keeps_its_published_name(self):
        data = hand_in([])
        data["cards"] = [card(name="CIMB VISA SIGNATURE", name_quote="CIMB VISA SIGNATURE", networks=["visa"], network_quote="CIMB VISA SIGNATURE",
                              official_url=CARD_PAGE)]
        ingest(data, root=self.tree, now=NOW)
        names = [item["name"] for item in self.items("sg", "cards", "cimb.json")]
        self.assertIn("CIMB Visa Signature", names)
        self.assertNotIn("CIMB VISA SIGNATURE", names)

    def test_bad_hand_in_changes_nothing(self):
        before = self.items("sg", "offers", "cimb.json")
        with self.assertRaises(SystemExit):
            ingest(hand_in([offer(benefit__value=99)]), root=self.tree, now=NOW)
        self.assertEqual(self.items("sg", "offers", "cimb.json"), before)


if __name__ == "__main__":
    unittest.main()
