"""Rules that must stay true after the schema 0.3 migration."""
import datetime
import json
import os
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
os.chdir(ROOT)
import sys
sys.path.insert(0, str(ROOT))

from pipeline.lib.calendar import add_months
from pipeline.lib.rules import load_rules
from pipeline.lib.transform import apply_date_policy, cap_view, cross_border, limits_from_text, parse_limits, parse_money, placement
from tools.validate import check_constant_checked_at, check_horizon


class RulesTests(unittest.TestCase):
    def test_thresholds_come_from_config(self):
        rules = load_rules()
        self.assertIn("end_date_max_months", rules)
        self.assertIn("evergreen_review_months", rules)
        self.assertIn("archive_retention_days", rules)
        self.assertIn("merchant_min_offers", rules)
        text = (ROOT / "tools" / "validate.py").read_text(encoding="utf-8")
        self.assertNotIn("end_date_max_months =", text)
        joined = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "pipeline").rglob("*.py") if "lib" not in path.parts or path.name == "transform.py")
        self.assertNotIn("TODAY", "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "pipeline").rglob("*.py")))

    def test_pipeline_has_no_clock_constant(self):
        forbidden = ("TODAY", "datetime.date(2026", "2028-12-31", "[:400]", " or 36", "<=1100", ">1100")
        for path in (ROOT / "pipeline").rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for token in forbidden:
                self.assertNotIn(token, text, f"{path} contains {token}")
        transform = (ROOT / "pipeline" / "lib" / "transform.py").read_text(encoding="utf-8")
        self.assertNotIn("sg-ocbc", transform)

    def test_prefixed_dollar_is_not_the_home_currency(self):
        hong_kong = parse_limits("maximum discount at HK$240 in a single transaction", "SGD")[0]
        self.assertEqual(hong_kong[0]["currency"], "HKD")
        self.assertEqual(hong_kong[0]["kind"], "per_transaction_limit")
        self.assertEqual(hong_kong[0]["per"], ["transaction"])
        united = parse_limits("maximum discount value is US$100", "SGD")[0]
        self.assertEqual(united[0]["currency"], "USD")
        bare = parse_limits("capped at $20 per month", "SGD")[0]
        self.assertEqual(bare[0]["currency"], "SGD")

    def test_second_cap_and_hotel_scope_are_kept(self):
        limits, _reason = parse_limits(
            "maximum Cash Back of RM80 per Participating Month and RM240 throughout the Campaign Period",
            "MYR",
        )
        amounts = {item["amount"]: item["per"] for item in limits}
        self.assertEqual(amounts[80], ["month"])
        self.assertEqual(amounts[240], ["campaign"])
        hotel, _reason = parse_limits(
            "capped at RM100 with a minimum spend of RM600. Hotels: 8% off (capped at RM50)",
            "MYR",
        )
        scoped = [item for item in hotel if item["amount"] == 50]
        self.assertEqual(scoped[0]["scope"], "hotel")

    def test_redemption_and_pool_limits_keep_the_count(self):
        limits, reason = parse_limits("limited to 1 redemption per customer and capped at a maximum of 2000 redemptions", "MYR")
        self.assertIsNone(reason)
        kinds = {(item["kind"], item["amount"]) for item in limits}
        self.assertIn(("redemption_limit", 1), kinds)
        self.assertIn(("pool_limit", 2000), kinds)

    def test_spend_cap_is_not_a_reward_cap(self):
        limits, _reason = parse_limits("capped at S$1,000 spend on online spend per calendar month", "SGD")
        self.assertEqual(limits[0]["kind"], "qualifying_spend_cap")
        self.assertEqual(limits[0]["per"], ["month"])
        cap, reason = cap_view(limits, None)
        self.assertIsNone(cap)
        self.assertEqual(reason, "not_a_reward_cap")

    def test_campaign_budget_is_not_a_cardholder_limit(self):
        limits, reason = parse_limits("capped at RM100,000 monthly budget allocation", "MYR")
        self.assertEqual(limits, [])
        self.assertEqual(reason, "campaign_budget_is_not_a_cardholder_limit")

    def test_parser_window_comes_from_config(self):
        rules = load_rules()
        self.assertIsInstance(rules["amount_context_chars"], int)
        self.assertIsInstance(rules["per_context_words"], int)
        source = (ROOT / "pipeline" / "lib" / "transform.py").read_text(encoding="utf-8")
        self.assertNotIn(" - 80", source)
        self.assertNotIn("{0,4}", source)
        self.assertNotIn("// 2", source)
        self.assertIsInstance(rules["minimum_phrase_chars"], int)

    def test_count_between_per_and_the_noun_still_matches(self):
        limits, _reason = parse_limits(
            "Limited to 1 redemption per 1 card per 1 passport number throughout the program",
            "SGD",
        )
        self.assertEqual(limits[0]["kind"], "redemption_limit")
        self.assertIn("card", limits[0]["per"])

    def test_same_amount_twice_is_one_limit(self):
        limits, reason = parse_limits(
            "capped at RM100 a year. capped at RM100 per calendar year, per Principal card",
            "MYR",
        )
        self.assertIsNone(reason)
        self.assertEqual(len(limits), 1)
        self.assertEqual(limits[0]["amount"], 100)
        cap, cap_reason = cap_view(limits, reason)
        self.assertIsNone(cap_reason)
        self.assertEqual(cap["per"], "year")

    def test_cap_period_prefers_the_time_dimension(self):
        limits, reason = parse_limits("capped at RM80 rebate per card per month", "MYR")
        cap, cap_reason = cap_view(limits, reason)
        self.assertIsNone(cap_reason)
        self.assertEqual(cap["per"], "month")
        self.assertIn("card", limits[0]["per"])
        self.assertIn("month", limits[0]["per"])

    def test_plain_amounts_are_not_cut_at_three_digits(self):
        spend = parse_money("minimum spend of RM5000", "MYR")
        self.assertEqual(spend["amount"], 5000)
        limits, _reason = parse_limits("capped at RM1000", "MYR")
        self.assertEqual(limits[0]["amount"], 1000)

    def test_period_labels_are_not_campaign_periods(self):
        limits, _reason = parse_limits("capped at S$100 Promotion Period: Every Tuesday, from 6 Jan 2026", "SGD")
        self.assertNotIn("campaign", limits[0]["per"])
        self.assertEqual(limits[0]["weekdays"], ["tue"])
        labelled, _reason = parse_limits("capped at RM150 Offer period: 1 November 2026 to 30 November 2026", "MYR")
        self.assertNotIn("campaign", labelled[0]["per"])

    def test_table_bill_is_a_redemption_and_quarter_is_kept(self):
        limits, _reason = parse_limits("Limited to 1 redemption per table per bill", "SGD")
        self.assertEqual(limits[0]["kind"], "redemption_limit")
        self.assertIn("table", limits[0]["per"])
        quarter, _reason = parse_limits("capped at 2 redemptions per calendar quarter", "SGD")
        self.assertEqual(quarter[0]["kind"], "pool_limit")
        self.assertEqual(quarter[0]["per"], ["quarter"])
        pool, _reason = parse_limits("Capped at 880 redemptions per month Limited to one (1) redemption per user per month", "SGD")
        kinds = {(item["kind"], item["amount"]) for item in pool}
        self.assertIn(("pool_limit", 880), kinds)

    def test_charges_and_balance_transfers_are_not_caps(self):
        limits, reason = parse_limits("up to a maximum of RM100 shall be imposed to the card", "MYR")
        self.assertEqual(limits, [])
        self.assertEqual(reason, "not_a_cap")
        discount, reason = parse_limits("capped at 50 redemptions) Promo code: X RM210 off with a min", "MYR")
        self.assertFalse(any(item["amount"] == 210 for item in discount))
        facility, reason = parse_limits("up to a maximum of RM30000 subject to 80% of available credit", "MYR")
        self.assertEqual(facility, [])

    def test_large_payout_and_winners_pool(self):
        payout, reason = parse_limits(
            "maximum Cash Back payment of RM30000 each Campaign month during the Campaign Period",
            "MYR",
        )
        self.assertEqual(payout, [])
        self.assertEqual(reason, "campaign_budget_is_not_a_cardholder_limit")
        phrase_only, reason = parse_limits(
            "maximum Cash Back payment of RM500 each Campaign month",
            "MYR",
        )
        self.assertEqual(phrase_only, [])
        self.assertEqual(reason, "campaign_budget_is_not_a_cardholder_limit")
        kept, _reason = parse_limits(
            "capped at RM50 per month per Eligible Cardmember, on a first-come, first-served basis",
            "MYR",
        )
        self.assertEqual(kept[0]["kind"], "reward_cap")
        self.assertEqual(cap_view(kept, None)[0]["per"], "month")
        large, reason = parse_limits("capped at RM10000 per month", "MYR")
        self.assertEqual(large, [])
        self.assertEqual(reason, "campaign_budget_is_not_a_cardholder_limit")
        below, _reason = parse_limits("capped at S$2500", "SGD")
        self.assertEqual(below[0]["amount"], 2500)
        winners, _reason = parse_limits(
            "capped at RM70 per Eligible Participant and limited to a maximum of 200 winners per Campaign Month",
            "MYR",
        )
        pool = [item for item in winners if item["amount"] == 200]
        self.assertEqual(pool[0]["kind"], "pool_limit")
        self.assertIn("month", pool[0]["per"])
        bonus, _reason = parse_limits(
            "capped at S$2,000 eligible retail spend (i.e. maximum monthly Bonus Cash Back is S$8)",
            "SGD",
        )
        kinds = {(item["kind"], item["amount"]) for item in bonus}
        self.assertIn(("qualifying_spend_cap", 2000), kinds)
        self.assertIn(("reward_cap", 8), kinds)

    def test_fee_waiver_date_is_not_kept(self):
        offer = {
            "_old_id": "sample",
            "title": "Monthly reward day",
            "dates_text": "The Annual Fee Waiver Campaign will run from 1 January 2026 until 31 December 2028.",
            "end_date": "2028-12-31",
            "start_date": "2026-01-01",
        }
        apply_date_policy(offer, "", datetime.date(2026, 11, 10), 24)
        self.assertEqual(offer["status"], "needs_review")
        self.assertIsNone(offer["end_date"])
        self.assertIn("annual fee waiver", offer["review_reason"])

    def test_illustration_date_is_not_kept(self):
        offer = {
            "_old_id": "sample",
            "title": "Example card",
            "dates_text": "To illustrate: Rewards Category From 30 Jan to 30 April 2028.",
            "end_date": "2028-04-30",
            "start_date": "2028-01-30",
        }
        apply_date_policy(offer, "", datetime.date(2026, 11, 10), 24)
        self.assertEqual(offer["status"], "needs_review")
        self.assertIsNone(offer["end_date"])

    def test_conflicting_period_is_not_kept(self):
        offer = {
            "_old_id": "sample",
            "title": "Fuel card",
            "dates_text": "This Promotion is valid till 26 March 2029.",
            "end_date": "2029-03-26",
            "start_date": None,
        }
        clauses = "This Promotion is valid for thirty-six (36) months from 27 March 2023."
        apply_date_policy(offer, clauses, datetime.date(2026, 11, 10), 24)
        self.assertEqual(offer["status"], "needs_review")
        self.assertIsNone(offer["end_date"])
        self.assertIn("conflict", offer["review_reason"])

    def test_horizon_uses_config_months(self):
        months = load_rules()["end_date_max_months"]
        today = datetime.date(2026, 11, 10)
        offer = {
            "_old_id": "sample",
            "title": "Far offer",
            "dates_text": "Offer valid until 31 December 2028.",
            "end_date": "2028-12-31",
            "start_date": None,
        }
        apply_date_policy(offer, "", today, months)
        self.assertEqual(offer["status"], "needs_review")
        self.assertIsNone(offer["end_date"])
        self.assertEqual(offer["stated_end_date"], "2028-12-31")

    def test_cross_border_uses_place_not_a_constant(self):
        places = [{"phrase": "bangkok", "country": "TH"}, {"phrase": "kuala lumpur", "country": "MY"}]
        foreign = cross_border(
            {"country": "MY", "title": "Up to 20% discount at MOCA Bangkok", "cross_border": {"merchant_country": "MY"}},
            "MOCA Bangkok",
            places,
            {},
        )
        local = cross_border(
            {"country": "MY", "title": "Dining in Kuala Lumpur", "cross_border": {"merchant_country": "MY"}},
            "Pavilion Kuala Lumpur",
            places,
            {},
        )
        self.assertTrue(foreign["is_cross_border"])
        self.assertEqual(foreign["redeem_countries"], ["TH"])
        self.assertFalse(local["is_cross_border"])

    def test_archive_retention_comes_from_the_caller(self):
        today = datetime.date(2026, 11, 10)
        self.assertEqual(placement("active", "2026-12-01", today, 180), "live")
        self.assertEqual(placement("expired", "2026-10-01", today, 180), "archive")
        self.assertEqual(placement("expired", "2020-01-01", today, 180), "drop")
        self.assertEqual(placement("evergreen", None, today, 180), "live")

    def test_constant_checked_at_rejected_for_different_fetches(self):
        errors = []
        rows = [
            {"id": "a", "checked_at": "2026-11-09T10:00:00+08:00", "checked_fetch_url": "https://bank.example/a"},
            {"id": "b", "checked_at": "2026-11-09T10:00:00+08:00", "checked_fetch_url": "https://bank.example/b"},
        ]
        check_constant_checked_at(rows, "sample.json", errors)
        self.assertTrue(errors)
        errors.clear()
        shared = [
            {"id": "a", "checked_at": "2026-11-09T10:00:00+08:00", "checked_fetch_url": "https://bank.example/list"},
            {"id": "b", "checked_at": "2026-11-09T10:00:00+08:00", "checked_fetch_url": "https://bank.example/list"},
        ]
        check_constant_checked_at(shared, "sample.json", errors)
        self.assertFalse(errors)

    def test_horizon_validator_needs_reviewer_flag(self):
        errors = []
        generated = "2026-11-10T00:00:00+00:00"
        far = add_months(datetime.date(2026, 11, 10), load_rules()["end_date_max_months"] + 2).isoformat()
        check_horizon({"id": "x", "end_date": far, "end_date_reviewer_accepted": False}, generated, load_rules()["end_date_max_months"], errors)
        self.assertTrue(errors)
        errors.clear()
        check_horizon({"id": "x", "end_date": far, "end_date_reviewer_accepted": True}, generated, load_rules()["end_date_max_months"], errors)
        self.assertFalse(errors)


class PublishedTests(unittest.TestCase):
    def test_every_old_id_resolves(self):
        fixture_path = ROOT / "tests" / "fixtures" / "ids_0_2_0.json"
        if not fixture_path.exists():
            self.skipTest("fixture is written by the migration")
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        cards, offers = [], []
        for country in ("my", "sg"):
            for folder, bucket in (("cards", cards), ("offers", offers)):
                path = ROOT / country / folder
                if not path.is_dir():
                    continue
                for file in path.glob("*.json"):
                    bucket.extend(json.loads(file.read_text(encoding="utf-8"))["items"])
            archive = ROOT / country / "archive" / "offers"
            if archive.is_dir():
                for file in archive.glob("*.json"):
                    offers.extend(json.loads(file.read_text(encoding="utf-8"))["items"])
        for kind, rows, old_ids in (("card", cards, fixture["cards"]), ("offer", offers, fixture["offers"])):
            index = {}
            for row in rows:
                index.setdefault(row["id"], row["id"])
                for alias in row.get("aliases") or []:
                    index[alias] = row["id"]
            missing = [old for old in old_ids if old not in index]
            self.assertEqual(missing, [], kind)

    def _offers(self):
        offers = {}
        for country in ("my", "sg"):
            folder = ROOT / country / "offers"
            for file in folder.glob("*.json"):
                for offer in json.loads(file.read_text(encoding="utf-8"))["items"]:
                    offers[offer["id"]] = offer
        return offers

    def test_named_amount_fixes(self):
        offers = self._offers()
        hong_kong = offers["sg-standard-chartered-d28d6e9ba9"]
        self.assertEqual(hong_kong["cap"]["currency"], "HKD")
        self.assertEqual(hong_kong["cap"]["per"], "transaction")
        self.assertEqual(hong_kong["limits"][0]["kind"], "per_transaction_limit")
        united = offers["sg-ocbc-5b9e79af32"]
        self.assertEqual(united["limits"][0]["currency"], "USD")
        budget = offers["my-hsbc-0dcfbab5d3"]
        self.assertIsNone(budget["cap"])
        self.assertEqual(budget["limits"], [])
        self.assertEqual(budget["cap_null_reason"], "campaign_budget_is_not_a_cardholder_limit")
        for offer_id in ("my-hsbc-cfc584cbaa", "my-hong-leong-02f7f7226b"):
            hotel = [item for item in offers[offer_id]["limits"] if item["amount"] == 50]
            self.assertEqual(hotel[0]["scope"], "hotel", offer_id)
        dbs = offers["sg-dbs-05312cf75e"]
        self.assertEqual(dbs["limits"][0]["kind"], "qualifying_spend_cap")
        self.assertIsNone(dbs["cap"])
        self.assertEqual(offers["my-hsbc-b1fc0473a7"]["min_spend"]["amount"], 5000)
        self.assertEqual(offers["my-standard-chartered-74ca506a6d"]["limits"][0]["amount"], 1000)
        for offer_id in ("sg-dbs-157c8ce3e1", "sg-posb-64e190b407"):
            self.assertEqual(offers[offer_id]["limits"][0]["weekdays"], ["tue"])
            self.assertNotIn("campaign", offers[offer_id]["limits"][0]["per"])
        self.assertNotIn("campaign", offers["my-uob-ad87b6b148"]["limits"][0]["per"])

    def test_card_cashback_caps_keep_the_stated_period(self):
        missing = []
        for country in ("my", "sg"):
            folder = ROOT / country / "cards"
            for file in folder.glob("*.json"):
                for card in json.loads(file.read_text(encoding="utf-8"))["items"]:
                    for benefit in card.get("benefits") or []:
                        details = benefit.get("details") or {}
                        if benefit.get("type") != "cashback" or not details.get("limits"):
                            continue
                        for item in details["limits"]:
                            if item["kind"] == "qualifying_spend_cap":
                                self.assertIn("month", item["per"], card["id"])
                                continue
                            if item.get("scope") == "category":
                                continue
                            if card["id"] == "sg-uob-singtel-uob-card":
                                continue
                            if not item["per"]:
                                missing.append(card["id"])
        self.assertEqual(missing, [])

    def test_every_cap_text_amount_is_a_limit_or_a_reason(self):
        fixture = json.loads((ROOT / "tests" / "fixtures" / "cap_text_amounts.json").read_text(encoding="utf-8"))
        offers = self._offers()
        missing = []
        for row in fixture:
            offer = offers[row["id"]]
            if row["reason"]:
                self.assertTrue(offer.get("cap_null_reason"), row["id"])
                continue
            found = {(item["amount"], item["currency"]) for item in offer.get("limits") or []}
            for amount in row["amounts"]:
                key = (amount["amount"], amount["currency"])
                if key not in found:
                    missing.append((row["id"], key))
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
