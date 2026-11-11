"""Merchant names: clean, test, key and match. All word lists come from config/merchant_rules.json."""
import hashlib
import html
import json
import os
import re
import unicodedata

from pipeline.lib.rules import repo_root


def load_merchant_rules(root=None):
    path = os.path.join(root or repo_root(), "config", "merchant_rules.json")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    for key in ("name_max_chars", "quote_max_chars", "unknown_merchant_max_pct", "withdraw_after_days"):
        if not isinstance(data.get(key), int) or isinstance(data.get(key), bool):
            raise SystemExit(f"config/merchant_rules.json {key} must be an integer")
    for key in ("number_words", "month_words"):
        if not isinstance(data.get(key), dict):
            raise SystemExit(f"config/merchant_rules.json {key} must be a map")
    for key in ("legal_suffixes", "country_words", "leading_words", "name_reject_patterns", "name_reject_words"):
        if not isinstance(data.get(key), list):
            raise SystemExit(f"config/merchant_rules.json {key} must be a list")
    data["_reject"] = [re.compile(pattern) for pattern in data["name_reject_patterns"]]
    return data


def clean_name(value):
    """Display form: no markup, no trademark signs, single spaces, no trailing punctuation."""
    text = html.unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    for mark in ("®", "™", "℠"):
        text = text.replace(mark, " ")
    text = text.replace("’", "'").replace("‘", "'")
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip(" :;,-*")


def _fold(char):
    """Lower case. A Latin letter with an accent becomes the plain letter. Letters of other scripts stay."""
    base = unicodedata.normalize("NFKD", char)[0]
    return base if base.isascii() and base.isalpha() else char


def _flat(value):
    """Match form of a text in any script: folded letters, digits and marks, single spaces."""
    text = unicodedata.normalize("NFKC", value or "").casefold().replace("&", " and ").replace("'", "")
    out = []
    for char in text:
        if char.isalnum() or unicodedata.category(char).startswith("M"):
            out.append(_fold(char))
        else:
            out.append(" ")
    return re.sub(r"\s+", " ", "".join(out)).strip()


def _ascii(value):
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.replace("&", " and ").replace("'", ""))).strip()


def name_key(value, rules):
    """Match key. 'Shopee Singapore', 'SHOPEE' and 'Shopee Pte Ltd' give the same key."""
    text = _flat(clean_name(value))
    changed = True
    while changed:
        changed = False
        for suffix in sorted((_flat(s) for s in rules["legal_suffixes"]), key=len, reverse=True):
            if suffix and text.endswith(" " + suffix):
                text = text[: -len(suffix) - 1].strip()
                changed = True
    for country in sorted(rules["country_words"], key=len, reverse=True):
        if text.endswith(" " + country):
            text = text[: -len(country) - 1].strip()
            break
    words = text.split()
    if len(words) > 1 and words[0] in rules["leading_words"]:
        words = words[1:]
    return " ".join(words)


def name_problems(value, rules, issuer_names=(), network_names=()):
    """Reasons why a string is not an acceptable merchant name. Empty list means acceptable."""
    problems = []
    name = value or ""
    if name != clean_name(name):
        problems.append("name is not clean (markup, trademark sign, extra spaces or edge punctuation)")
    if not name_key(name, rules):
        problems.append("name is empty")
        return problems
    if len(name) > rules["name_max_chars"]:
        problems.append(f"name is longer than {rules['name_max_chars']} characters")
    for pattern in rules["_reject"]:
        if pattern.search(name):
            problems.append(f"name looks like offer wording, not a merchant (pattern {pattern.pattern})")
            break
    else:
        for word in rules["name_reject_words"]:
            if word in name.casefold():
                problems.append(f"name looks like offer wording, not a merchant (word {word})")
                break
    key = name_key(name, rules)
    if key in {name_key(n, rules) for n in issuer_names}:
        problems.append("name is the card issuer, use kind issuer_own")
    if key in {name_key(n, rules) for n in network_names}:
        problems.append("name is a card network, not a merchant")
    return problems


def quote_has_name(quote, name):
    """True when the name is inside one part of the quote, ignoring case, markup, accents and punctuation.

    The quote is cut at commas, semicolons, bars and line ends, so a name cannot be made from the
    end of one phrase and the start of the next (an address line such as "Level 1 Fairmont, Singapore").
    A name that has a comma of its own is looked for in the whole quote.
    """
    needle = _flat(clean_name(name))
    if not needle:
        return False
    text = clean_name(quote)
    parts = [text] if re.search(r"[,;|]", clean_name(name)) else re.split(r"[,;|\n\u3001\uff0c\uff1b]", text)
    return any(needle in _flat(part) for part in parts)


def slug(value):
    """ASCII id part. A name with no Latin letter or digit gets a short hash, so the id stays stable."""
    text = _ascii(clean_name(value)).replace(" ", "-")
    if text:
        return text
    flat = _flat(clean_name(value))
    return "m-" + hashlib.sha256(flat.encode()).hexdigest()[:10] if flat else ""


class Registry:
    """Lookup of registry records by name key. New names get an unverified record."""

    def __init__(self, items, rules):
        self.rules = rules
        self.items = {row["id"]: row for row in items}
        self.by_key = {}
        for row in items:
            for text in [row["name"]] + list(row.get("aliases") or []):
                key = name_key(text, rules)
                if key:
                    self.by_key.setdefault(key, row["id"])

    def find(self, name):
        return self.by_key.get(name_key(name, self.rules))

    def resolve(self, name, country, category, official_domain=None, alt_names=()):
        merchant_id = self.find(name)
        if merchant_id is None:
            base = slug(name_key(name, self.rules)) or slug(name)
            merchant_id = base
            number = 2
            while merchant_id in self.items:
                merchant_id = f"{base}-{number}"
                number += 1
            self.items[merchant_id] = {
                "id": merchant_id, "name": clean_name(name), "aliases": [], "countries": [],
                "categories": [], "official_domain": None, "offer_ids": [], "verified": False,
            }
            self.by_key[name_key(name, self.rules)] = merchant_id
        row = self.items[merchant_id]
        shown = clean_name(name)
        if shown != row["name"] and shown not in row["aliases"]:
            row["aliases"] = sorted(set(row["aliases"]) | {shown})
        for other in alt_names:
            other = clean_name(other)
            if other and other != row["name"] and other not in row["aliases"]:
                row["aliases"] = sorted(set(row["aliases"]) | {other})
            self.by_key.setdefault(name_key(other, self.rules), merchant_id)
        if country and country not in row["countries"]:
            row["countries"] = sorted(set(row["countries"]) | {country})
        if category and category != "other" and category not in row["categories"]:
            row["categories"] = sorted(set(row["categories"]) | {category})
        if official_domain and not row.get("official_domain"):
            row["official_domain"] = official_domain
        return merchant_id

    def finish(self, offers, min_offers):
        """Recount offer_ids from the offers and set verified."""
        for row in self.items.values():
            row["offer_ids"] = []
        for offer in offers:
            for merchant_id in offer.get("merchant_ids") or []:
                row = self.items.get(merchant_id)
                if row is not None:
                    row["offer_ids"].append(offer["id"])
        out = []
        for row in self.items.values():
            row["offer_ids"] = sorted(set(row["offer_ids"]))
            if not row["offer_ids"]:
                continue
            row["verified"] = bool(row.get("official_domain")) or len(row["offer_ids"]) >= min_offers
            out.append(row)
        return sorted(out, key=lambda r: r["id"])


def card_core(name, issuer_name, rules):
    """The part of a card name that tells it apart: no issuer name, no country word, no 'credit card'."""
    drop = set(_flat(issuer_name).split()) | set(rules["country_words"]) | {"credit", "card", "cards", "the"}
    return " ".join(word for word in _flat(clean_name(name)).split() if word not in drop)


def match_card(name, cards, issuer_name, rules):
    """Card id for a card name as an offer page writes it, or None. Exact name first, then a unique core."""
    key = name_key(name, rules)
    for card in cards:
        if name_key(card["name"], rules) == key:
            return card["id"]
    core = card_core(name, issuer_name, rules)
    hits = [card["id"] for card in cards if core and card_core(card["name"], issuer_name, rules) == core]
    return hits[0] if len(hits) == 1 else None
