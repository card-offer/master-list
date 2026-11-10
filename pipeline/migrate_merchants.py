#!/usr/bin/env python3
"""One-time offline step: give every published offer the merchant fields of the crawler rule.

    python pipeline/migrate_merchants.py

It fetches nothing. A name that came from the old title parser is kept only when it passes
the name test in config/merchant_rules.json, and it is marked legacy_title_parse. Every other
offer becomes merchant_kind unknown until the crawler states the merchant with proof.
Safe to run again: offers that already have merchant_kind are not changed.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.lib.calendar import stamp
from pipeline.lib.layout import write_collection, write_json
from pipeline.lib.merchants import Registry, clean_name, load_merchant_rules, name_problems
from pipeline.lib.rules import load_rules, repo_root


def main(root=None):
    root = root or repo_root()
    rules = load_rules()
    mrules = load_merchant_rules(root)
    reg_path = os.path.join(root, "merchants", "registry.json")
    with open(reg_path, encoding="utf-8") as fh:
        reg_file = json.load(fh)
    registry = Registry(reg_file["items"], mrules)
    issuer_names, files = [], []
    for path in sorted(glob.glob(os.path.join(root, "??", "issuers.json"))):
        with open(path, encoding="utf-8") as fh:
            issuer_names += [row["name"] for row in json.load(fh)["items"]]
    with open(os.path.join(root, "networks.json"), encoding="utf-8") as fh:
        network_names = [row["name"] for row in json.load(fh)["items"]]
    for pattern in ("??/offers/*.json", "??/archive/offers/*.json"):
        files += sorted(glob.glob(os.path.join(root, pattern)))
    offers, loaded = [], []
    counts = {"single_registry": 0, "single_legacy_text": 0, "unknown_rejected_text": 0, "unknown_no_text": 0}
    for path in files:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        for offer in data["items"]:
            if "merchant_kind" not in offer:
                text = offer.pop("merchant_text", None)
                name = None
                if offer.get("merchant_id") in registry.items:
                    name = registry.items[offer["merchant_id"]]["name"]
                    counts["single_registry"] += 1
                elif text and not name_problems(clean_name(text), mrules, issuer_names, network_names):
                    name = clean_name(text)
                    offer["merchant_id"] = registry.resolve(name, offer["country"], offer.get("category"))
                    counts["single_legacy_text"] += 1
                else:
                    offer["merchant_id"] = None
                    counts["unknown_rejected_text" if text else "unknown_no_text"] += 1
                offer["merchant_kind"] = "single" if name else "unknown"
                offer["merchant_name"] = name
                offer["merchant_names"] = []
                offer["merchant_outlet"] = None
                offer["merchant_name_source"] = "legacy_title_parse" if name else None
            offers.append(offer)
        loaded.append((path, data))
    generated = stamp()
    for path, data in loaded:
        header = {key: value for key, value in data.items() if key not in ("items", "count")}
        header["generated_at"] = generated
        write_collection(path, header, data["items"])
    items = registry.finish(offers, rules["merchant_min_offers"])
    write_collection(reg_path, {"schema_version": reg_file["schema_version"], "generated_at": generated}, items)
    index_path = os.path.join(root, "index.json")
    with open(index_path, encoding="utf-8") as fh:
        index = json.load(fh)
    index["merchants"] = len(items)
    index["generated_at"] = generated
    write_json(index_path, index)
    counts["registry_records"] = len(items)
    counts["registry_verified"] = sum(1 for row in items if row["verified"])
    print(json.dumps(counts))
    return counts


if __name__ == "__main__":
    main()
