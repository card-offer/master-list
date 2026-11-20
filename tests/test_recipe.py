import json
import os
import tempfile
import unittest

from pipeline import recipe as R
from pipeline.fetcher import _domains_for_url, load_real_chrome_hosts

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LIST_1 = """<html><body><div class="deals">
<div class="tile"><a class="go" href="/deals/kopi-10"><h3>Kopi House</h3></a><p class="v">10% off total bill</p>
<span class="end">Valid till 31 Dec 2026</span></div>
<div class="tile"><a class="go" href="/deals/spa-20#t"><h3>Calm Spa</h3></a><p class="v">20% off</p></div>
</div><a class="next" href="?page=2">Next</a></body></html>"""
LIST_2 = """<html><body><div class="deals">
<div class="tile"><a class="go" href="/deals/books-5"><h3>Book Nook</h3></a><p class="v">5% off</p></div>
</div></body></html>"""
DETAIL = """<html><body><h1>{name}</h1><main><p>{benefit}</p><div class="tnc">Terms: valid till 31 Dec 2026 with Bank cards.</div></main></body></html>"""


def recipe(**over):
    base = {
        "recipe": "recipe/1", "id": "sg-bank-offers", "owner": {"type": "issuer", "id": "sg-dbs"}, "country": "SG",
        "purpose": "offers", "mode": "plain", "start_urls": ["https://www.dbs.com.sg/deals"],
        "pagination": {"next": "a.next@href", "max_pages": 5},
        "list": {"item": "div.tile", "fields": {"merchant": "h3", "url": "a.go@href", "benefit": "p.v",
                                                "end": {"selector": "span.end", "regex": r"till (.+)$"}}},
        "detail": {"fields": {"heading": "h1", "terms": "div.tnc"}, "text_selector": "main"},
    }
    base.update(over)
    return base


class FakeFetch:
    def __init__(self, pages):
        self.pages, self.calls = pages, []

    def __call__(self, url):
        self.calls.append(url)
        body = self.pages.get(url)
        if body is None:
            return {"url": url, "status": None, "not_fetched": "not_found"}
        return {"url": url, "final_url": url, "status": 200, "body": body.encode("utf-8"), "text": body,
                "fetched_at": "2026-11-20T09:00:00+08:00"}


def site(benefit_spa="20% off"):
    return FakeFetch({
        "https://www.dbs.com.sg/deals": LIST_1.replace("20% off", benefit_spa),
        "https://www.dbs.com.sg/deals?page=2": LIST_2,
        "https://www.dbs.com.sg/deals/kopi-10": DETAIL.format(name="Kopi House", benefit="10% off total bill"),
        "https://www.dbs.com.sg/deals/spa-20#t": DETAIL.format(name="Calm Spa", benefit=benefit_spa),
        "https://www.dbs.com.sg/deals/books-5": DETAIL.format(name="Book Nook", benefit="5% off"),
    })


class ExtractTests(unittest.TestCase):
    def test_fields_text_attribute_and_regex(self):
        items = R.extract_items(LIST_1, recipe(), "https://www.dbs.com.sg/deals")
        self.assertEqual(len(items), 2)
        first = items[0]["fields"]
        self.assertEqual(first["merchant"], "Kopi House")
        self.assertEqual(first["url"], "https://www.dbs.com.sg/deals/kopi-10")
        self.assertEqual(first["end"], "31 Dec 2026")
        self.assertIsNone(items[1]["fields"]["end"])

    def test_all_and_join(self):
        rule = {"selector": "h3", "all": True, "join": " | "}
        soup = R._parse(LIST_1)
        self.assertEqual(R.html_field(soup, rule, "https://x.example/"), "Kopi House | Calm Spa")
        self.assertEqual(R.html_field(soup, {"selector": "h3", "all": True}, "https://x.example/"), ["Kopi House", "Calm Spa"])

    def test_json_source(self):
        data = {"data": {"items": [{"title": {"en": "Kopi House"}, "link": "/d/1", "img": [{"alt": "logo"}]}]}}
        rec = recipe(source="json", list={"item": "data.items", "fields": {"merchant": "title.en", "url": "link", "logo": "img[0].alt"}})
        items = R.extract_items(json.dumps(data), rec, "https://www.dbs.com.sg/api/deals")
        self.assertEqual(items[0]["fields"], {"merchant": "Kopi House", "url": "https://www.dbs.com.sg/d/1", "logo": "logo"})

    def test_key_from_url_path_and_fragment(self):
        rec = recipe()
        self.assertEqual(R.item_key({"url": "https://www.dbs.com.sg/deals/spa-20#t"}, rec, 0), "spa-20-t")
        self.assertEqual(R.item_key({}, rec, 3), "item-3")


class RecipeCheckTests(unittest.TestCase):
    def test_good_recipe(self):
        self.assertEqual(R.recipe_problems(recipe()), [])

    def test_unknown_key_and_missing_parts(self):
        bad = recipe(proxy="residential", list={"fields": {}})
        problems = R.recipe_problems(bad)
        self.assertIn("unknown key proxy", problems)
        self.assertIn("list.item is missing", problems)

    def test_real_chrome_needs_an_approved_host(self):
        problems = R.recipe_problems(recipe(mode="real_chrome"))
        self.assertTrue(any("real_chrome is not approved" in p for p in problems))
        ok = recipe(mode="real_chrome", start_urls=["https://specials.priceless.com/en-my/"])
        self.assertEqual(R.recipe_problems(ok), [])


class RunDiffCarryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.recipe_path = os.path.join(self.root, "r.json")
        R.write_json(self.recipe_path, recipe())

    def tearDown(self):
        self.tmp.cleanup()

    def run_once(self, fetch, minute):
        import datetime
        now = datetime.datetime(2026, 11, 20, 9, minute, tzinfo=datetime.timezone.utc)
        return R.cmd_run(self.recipe_path, fetch=fetch, now=now, root=self.root)

    def test_run_follows_next_page_and_details(self):
        fetch = site()
        path, out = self.run_once(fetch, 0)
        self.assertEqual([i["key"] for i in out["items"]], ["kopi-10", "spa-20-t", "books-5"])
        self.assertTrue(out["listing_complete"])
        self.assertEqual(len(out["listing_urls"]), 2)
        kopi = out["items"][0]
        self.assertEqual(kopi["detail"]["heading"], "Kopi House")
        self.assertEqual(kopi["terms_sha256"], R.sha("Terms: valid till 31 Dec 2026 with Bank cards."))
        self.assertTrue(os.path.exists(path))
        self.assertTrue(all(os.path.exists(p) for p in out["page_texts"].values()))

    def test_max_pages_marks_the_listing_incomplete(self):
        R.write_json(self.recipe_path, recipe(pagination={"next": "a.next@href", "max_pages": 1}))
        _path, out = self.run_once(site(), 0)
        self.assertFalse(out["listing_complete"])
        self.assertEqual(out["problems"][-1]["reason"], "max_pages")

    def test_diff_sends_only_changed_and_new_items_to_the_model(self):
        first, _ = self.run_once(site(), 0)
        second, _ = self.run_once(site(benefit_spa="30% off"), 5)
        work_path, work = R.cmd_diff(second, root=self.root)
        self.assertEqual(work["buckets"]["same"], ["kopi-10", "books-5"])
        self.assertEqual(work["buckets"]["changed"], ["spa-20-t"])
        self.assertEqual([i["key"] for i in work["items"]], ["spa-20-t"])
        self.assertTrue(work_path.endswith(".work.json"))

    def test_diff_warns_when_the_item_count_falls(self):
        self.run_once(site(), 0)
        broken = site()
        broken.pages["https://www.dbs.com.sg/deals"] = "<html><body>new layout</body></html>"
        second, _ = self.run_once(broken, 5)
        _work_path, work = R.cmd_diff(second, root=self.root)
        self.assertTrue(work["warnings"][0].startswith("recipe_may_be_broken"))

    def test_carry_keeps_unchanged_offers_whose_quotes_are_still_on_the_page(self):
        self.run_once(site(), 0)
        second, _ = self.run_once(site(benefit_spa="30% off"), 5)
        obs_dir = os.path.join(self.root, "raw", "observations", "sg", "dbs")
        os.makedirs(obs_dir)
        previous = {
            "contract": "observation/1",
            "run": {"run_id": "20261113-1000-sg-dbs", "crawler": "grok", "country": "SG", "issuer_id": "sg-dbs",
                    "started_at": "2026-11-13T10:00:00+08:00", "finished_at": "2026-11-13T11:00:00+08:00",
                    "listing_urls": ["https://www.dbs.com.sg/deals"], "listing_complete": True, "robots_checked": True,
                    "blocked": []},
            "fetches": [{"url": "https://www.dbs.com.sg/deals", "final_url": "https://www.dbs.com.sg/deals", "status": 200,
                         "fetched_at": "2026-11-13T10:00:00+08:00", "kind": "issuer_promotion_listing"}],
            "offers": [
                {"source_url": "https://www.dbs.com.sg/deals/kopi-10", "source_key": "kopi-10",
                 "merchant": {"name": "Kopi House", "name_quote": "Kopi House"},
                 "benefit": {"quote": "10% off total bill"}, "terms": {"fetched_at": "2026-11-13T10:00:00+08:00"}},
                {"source_url": "https://www.dbs.com.sg/deals/books-5", "source_key": "books-5",
                 "merchant": {"name": "Book Nook", "name_quote": "Book Nook"},
                 "benefit": {"quote": "15% off"}, "terms": {"fetched_at": None}},
                {"source_url": "https://www.dbs.com.sg/deals/spa-20", "source_key": "spa-20-t",
                 "merchant": {"name": "Calm Spa", "name_quote": "Calm Spa"}, "benefit": {"quote": "20% off"}, "terms": {}},
            ],
            "cards": [],
        }
        prev_path = os.path.join(obs_dir, "20261113-1000-sg-dbs.json")
        R.write_json(prev_path, previous)
        draft_path, todo = R.cmd_carry(second, prev_path, root=self.root)
        draft = R.load_json(draft_path)
        self.assertEqual([o["source_key"] for o in draft["offers"]], ["kopi-10"])
        self.assertEqual(draft["offers"][0]["terms"]["fetched_at"], "2026-11-20T09:00:00+08:00")
        self.assertEqual(todo["recheck"][0]["key"], "books-5")  # "15% off" is not on the page now
        self.assertEqual(todo["for_the_model"], ["spa-20-t"])
        self.assertEqual(draft["run"]["run_id"], R.load_json(second)["run_id"])
        self.assertTrue(draft["run"]["listing_complete"])


class SchemaTests(unittest.TestCase):
    def test_test_recipe_and_committed_recipes_match_the_schema(self):
        import glob
        from jsonschema import Draft202012Validator
        schema = R.load_json(os.path.join(ROOT, "schema", "recipe.schema.json"))
        validator = Draft202012Validator(schema)
        self.assertEqual([e.message for e in validator.iter_errors(recipe())], [])
        for path in glob.glob(os.path.join(ROOT, "config", "recipes", "*.json")):
            data = R.load_json(path)
            self.assertEqual([e.message for e in validator.iter_errors(data)], [], path)
            self.assertEqual(R.recipe_problems(data), [], path)
            self.assertEqual(os.path.basename(path), data["id"] + ".json")


class CensusHostTests(unittest.TestCase):
    def test_census_bank_host_is_accepted_for_a_probe(self):
        domains, label = _domains_for_url(ROOT, "https://www.ktb.co.th/", "th")
        self.assertEqual(label, "census-th")
        self.assertIn("krungthai.com", domains)

    def test_census_hosts_with_real_chrome_are_on_the_list(self):
        hosts = load_real_chrome_hosts(ROOT)
        census = R.load_json(os.path.join(ROOT, "config", "census_hosts.json"))["items"]
        for row in census:
            if row["name"] == "Krung Thai Bank":
                continue
            self.assertTrue(any(d in hosts for d in row["official_domains"]), row["name"])


if __name__ == "__main__":
    unittest.main()
