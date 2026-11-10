"""Each bad input must be rejected by tools/validate.py, and a bad date must not crash it."""
import json
import os
import shutil
import tempfile
import unittest

from pipeline.lib.transform import host_of
from tests.test_model import ROOT
from tools.validate import validate


def _ignore(path, names):
    skip = {".git", "dist", "__pycache__", ".pytest_cache"}
    return [name for name in names if name in skip]


class ValidatorGapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = tempfile.mkdtemp(prefix="card-offer-gap-")
        cls.base = os.path.join(parent, "base")
        shutil.copytree(ROOT, cls.base, ignore=_ignore)

    def clone(self):
        parent = tempfile.mkdtemp(prefix="card-offer-case-")
        dest = os.path.join(parent, "tree")
        shutil.copytree(self.base, dest)
        return dest

    def offer_path(self, tmp):
        return os.path.join(tmp, "sg", "offers", "cimb.json")

    def load(self, path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)

    def save(self, path, data):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)

    def errors_after(self, mutator):
        tmp = self.clone()
        mutator(tmp)
        errors, _warnings, _stats = validate(tmp)
        return errors

    def test_clean_copy_passes(self):
        errors, _warnings, _stats = validate(self.base)
        self.assertEqual(errors, [])

    def test_duplicate_offer_record_fails(self):
        def mutate(tmp):
            path = self.offer_path(tmp)
            data = self.load(path)
            data["items"].append(dict(data["items"][0]))
            data["count"] = len(data["items"])
            self.save(path, data)
        errors = self.errors_after(mutate)
        self.assertTrue(any("duplicate offer id" in error for error in errors), errors[:8])

    def test_offer_id_not_hash_of_source_url_fails(self):
        def mutate(tmp):
            path = self.offer_path(tmp)
            data = self.load(path)
            data["items"][0]["id"] = "sg-cimb-0000000000"
            self.save(path, data)
        errors = self.errors_after(mutate)
        self.assertTrue(any("not the hash of source_url" in error for error in errors), errors[:8])

    def test_inferred_offer_with_card_ids_fails(self):
        def mutate(tmp):
            path = self.offer_path(tmp)
            data = self.load(path)
            offer = data["items"][0]
            offer["eligibility"]["confidence"] = "inferred"
            offer["eligibility"]["card_ids"] = ["sg-cimb-a", "sg-cimb-b"]
            self.save(path, data)
        errors = self.errors_after(mutate)
        self.assertTrue(any("inferred offer must not carry card ids" in error for error in errors), errors[:8])

    def test_long_description_fails(self):
        def mutate(tmp):
            path = self.offer_path(tmp)
            data = self.load(path)
            data["items"][0]["description"] = "a" * 500
            self.save(path, data)
        errors = self.errors_after(mutate)
        self.assertTrue(any("longer than the configured maximum" in error for error in errors), errors[:8])

    def test_description_with_clause_text_fails(self):
        def mutate(tmp):
            path = self.offer_path(tmp)
            data = self.load(path)
            data["items"][0]["description"] = "The cardholder shall pay the fee."
            self.save(path, data)
        errors = self.errors_after(mutate)
        self.assertTrue(any("contains clause text" in error for error in errors), errors[:8])

    def test_empty_checked_at_fails(self):
        def mutate(tmp):
            path = self.offer_path(tmp)
            data = self.load(path)
            data["items"][0]["checked_at"] = ""
            self.save(path, data)
        errors = self.errors_after(mutate)
        self.assertTrue(errors)

    def test_checked_at_missing_from_fetch_log_fails(self):
        def mutate(tmp):
            path = self.offer_path(tmp)
            data = self.load(path)
            data["items"][0]["checked_at"] = "2020-01-01T00:00:00+00:00"
            self.save(path, data)
        errors = self.errors_after(mutate)
        self.assertTrue(any("not in the fetch log" in error for error in errors), errors[:8])

    def test_issuer_offer_on_network_domain_fails(self):
        def mutate(tmp):
            path = self.offer_path(tmp)
            data = self.load(path)
            data["items"][0]["terms_url"] = "https://www.visa.com/promotions"
            data["items"][0]["terms_url_null_reason"] = None
            self.save(path, data)
        errors = self.errors_after(mutate)
        self.assertTrue(any("visa domain" in error for error in errors), errors[:8])

    def test_visa_country_offer_host_passes(self):
        url, fetched = self.visa_country_fetch("visa.com.my")
        offer_id = self.load(self.offer_path(self.base))["items"][0]["id"]

        def mutate(tmp):
            path = self.offer_path(tmp)
            data = self.load(path)
            offer = data["items"][0]
            offer["provider"] = {"type": "network", "id": "visa"}
            offer["checked_at"] = fetched
            offer["checked_fetch_url"] = url
            offer["source_url"] = url
            offer["terms_url"] = url
            self.retarget_urls(offer, url)
            self.save(path, data)

        errors = self.errors_after(mutate)
        own = [error for error in errors if offer_id in error]
        self.assertEqual(own, [], own[:8])

    def visa_country_fetch(self, host):
        path = os.path.join(ROOT, "pipeline", "fetch_metadata.json")
        with open(path, encoding="utf-8") as fh:
            rows = json.load(fh)
        for row in rows:
            url = row.get("url")
            if host_of(url) == host:
                return url, row["fetched_at"]
        self.fail(f"fetch log has no {host} url")

    def retarget_urls(self, value, url):
        if isinstance(value, dict):
            for key, item in list(value.items()):
                if isinstance(item, str) and item.startswith("http") and key != "checked_fetch_url":
                    value[key] = url
                else:
                    self.retarget_urls(item, url)
        elif isinstance(value, list):
            for item in value:
                self.retarget_urls(item, url)

    def test_alias_equal_to_another_live_id_fails(self):
        def mutate(tmp):
            path = self.offer_path(tmp)
            data = self.load(path)
            data["items"][0]["aliases"] = [data["items"][1]["id"]]
            self.save(path, data)
        errors = self.errors_after(mutate)
        self.assertTrue(any("equals another record's live id" in error for error in errors), errors[:8])

    def test_verbatim_source_keys_fail(self):
        def mutate(tmp):
            path = self.offer_path(tmp)
            data = self.load(path)
            data["items"][0]["dates_text"] = "Valid till 31 December 2026."
            data["items"][0]["cap_text"] = "capped at RM10"
            data["items"][0]["min_spend_text"] = "minimum spend RM15"
            self.save(path, data)
        errors = self.errors_after(mutate)
        for key in ("dates_text", "cap_text", "min_spend_text"):
            self.assertTrue(any(key in error for error in errors), errors[:8])

    def test_malformed_checked_at_is_a_validation_error(self):
        def mutate(tmp):
            path = self.offer_path(tmp)
            data = self.load(path)
            data["items"][0]["checked_at"] = "2026-13-45T99:99:99+08:00"
            self.save(path, data)
        try:
            errors = self.errors_after(mutate)
        except Exception as exc:  # a crash is a failure of this test
            self.fail(f"validate crashed on a malformed date: {exc}")
        self.assertTrue(any("not a valid date-time" in error for error in errors), errors[:8])


if __name__ == "__main__":
    unittest.main()
