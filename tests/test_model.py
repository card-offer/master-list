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
from pipeline.lib.transform import apply_date_policy, cross_border, currency_cap, placement
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

    def test_currency_cap_ignores_the_minimum_spend(self):
        text = "capped at RM200 with a minimum spend of RM800 in a single receipt"
        cap, reason = currency_cap(text, "MYR")
        self.assertIsNone(reason)
        self.assertEqual(cap["currency"], "MYR")
        self.assertEqual(cap["per"], None)
        self.assertEqual(cap["amount"], currency_cap("capped at RM200", "MYR")[0]["amount"])

    def test_currency_cap_keeps_a_stated_period(self):
        cap, reason = currency_cap("capped at S$150 per calendar month", "SGD")
        self.assertIsNone(reason)
        self.assertEqual(cap["currency"], "SGD")
        self.assertEqual(cap["per"], "month")

    def test_currency_cap_states_why_a_number_is_not_published(self):
        cap, reason = currency_cap("limited to 1 redemption per customer", "MYR")
        self.assertIsNone(cap)
        self.assertEqual(reason, "not_a_currency_amount")
        cap, reason = currency_cap("capped at RM80 per month and RM240 throughout the period", "MYR")
        self.assertIsNone(cap)
        self.assertEqual(reason, "more_than_one_currency_amount")

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

    def test_offers_that_had_cap_text_keep_a_number_or_a_reason(self):
        fixture_path = ROOT / "tests" / "fixtures" / "cap_text_offer_ids.json"
        offer_ids = json.loads(fixture_path.read_text(encoding="utf-8"))
        offers = {}
        for country in ("my", "sg"):
            folder = ROOT / country / "offers"
            for file in folder.glob("*.json"):
                for offer in json.loads(file.read_text(encoding="utf-8"))["items"]:
                    offers[offer["id"]] = offer
        missing = []
        for offer_id in offer_ids:
            offer = offers[offer_id]
            if offer.get("cap") or offer.get("cap_null_reason"):
                continue
            missing.append(offer_id)
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
