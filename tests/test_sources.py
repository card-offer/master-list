"""The crawl sources list must cover official issuer and network hosts, and nothing else unofficial."""
import json
import unittest
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "crawler" / "sources.json"
SOURCES_MD = ROOT / "crawler" / "SOURCES.md"

ALLOWED_STATUS = {"ok", "js_shell", "bot_wall", "network_unreachable", "untested"}
ALLOWED_TYPES = {"issuer", "network", "regulator", "merchant"}
ALLOWED_PURPOSES = {"cards", "offers", "census"}
REGULATOR_HOSTS = {("MY", "bnm.gov.my"), ("SG", "eservices.mas.gov.sg"), ("TH", "bot.or.th")}


def host_of(value):
    if "://" in value:
        host = (urlsplit(value).hostname or "").lower()
    else:
        host = value.lower()
    return host[4:] if host.startswith("www.") else host


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_builder():
    # tools/ is not a package. Load the builder by path so the test uses the same code.
    import importlib.util
    module_path = ROOT / "tools" / "build_sources.py"
    spec = importlib.util.spec_from_file_location("build_sources", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SourcesListTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_json(SOURCES)
        cls.items = cls.data["items"]
        cls.issuers = []
        for path in sorted(ROOT.glob("*/issuers.json")):
            country = path.parent.name
            if len(country) == 2 and country.isalpha() and country.islower():
                cls.issuers.extend(load_json(path)["items"])
        cls.networks = load_json(ROOT / "config" / "networks.json")["items"]

    def test_committed_list_matches_the_builder(self):
        builder = load_builder()
        built = builder.build_sources(ROOT)
        self.assertEqual(self.data, built)
        self.assertEqual(SOURCES_MD.read_text(encoding="utf-8"), builder.render_sources_md(built))

    def test_ids_are_unique_and_rows_are_complete(self):
        ids = [row["id"] for row in self.items]
        self.assertEqual(len(ids), len(set(ids)))
        for row in self.items:
            for key in ("id", "site", "host", "country", "type", "purpose", "entry_urls", "status", "full_crawl_order", "suggested_by"):
                self.assertIn(key, row, row.get("id"))
            self.assertIn(row["status"], ALLOWED_STATUS, row["id"])
            self.assertIn(row["type"], ALLOWED_TYPES, row["id"])
            self.assertIn(row["purpose"], ALLOWED_PURPOSES, row["id"])
            self.assertIn(row["country"], {"MY", "SG", "TH"}, row["id"])
            self.assertIsInstance(row["entry_urls"], list)
            self.assertTrue(row["host"] and "." in row["host"], row["id"])
            self.assertFalse(row["host"].startswith("www."), row["id"])
            self.assertTrue(row["suggested_by"] is None or isinstance(row["suggested_by"], str), row["id"])
            for url in row["entry_urls"]:
                self.assertEqual(host_of(url), row["host"], f"{row['id']} entry URL host {url}")

    def test_every_issuer_official_domain_is_listed(self):
        missing = []
        for issuer in self.issuers:
            for domain in issuer["official_domains"]:
                host = host_of(domain)
                if not any(
                    row["type"] == "issuer"
                    and row.get("issuer_id") == issuer["id"]
                    and row["host"] == host
                    for row in self.items
                ):
                    missing.append(f"{issuer['id']} {host}")
        self.assertEqual(missing, [])

    def test_every_network_official_domain_is_listed(self):
        missing = []
        for network in self.networks:
            for domain in network["official_domains"]:
                host = host_of(domain)
                if not any(
                    row["type"] == "network"
                    and row.get("network_id") == network["id"]
                    and row["host"] == host
                    for row in self.items
                ):
                    missing.append(f"{network['id']} {host}")
        self.assertEqual(missing, [])

    def test_listed_hosts_are_official_or_regulator(self):
        official = set()
        for issuer in self.issuers:
            for domain in issuer["official_domains"]:
                official.add(("issuer", issuer["id"], host_of(domain)))
        for network in self.networks:
            for domain in network["official_domains"]:
                official.add(("network", network["id"], host_of(domain)))
        unexpected = []
        for row in self.items:
            if row["type"] == "regulator":
                if (row["country"], row["host"]) not in REGULATOR_HOSTS:
                    unexpected.append(row["id"])
                continue
            if row["type"] == "issuer":
                key = ("issuer", row.get("issuer_id"), row["host"])
            elif row["type"] == "network":
                key = ("network", row.get("network_id"), row["host"])
            else:
                continue
            if key not in official:
                unexpected.append(row["id"])
        self.assertEqual(unexpected, [])

    def test_guide_stays_in_sync_with_the_list(self):
        text = SOURCES_MD.read_text(encoding="utf-8")
        self.assertIn("crawler/sources.json", text)
        self.assertIn("suggested_by", text)
        for row in self.items:
            self.assertIn(f"`{row['host']}`", text, row["id"])
        self.assertIn(str(len(self.items)), text)
