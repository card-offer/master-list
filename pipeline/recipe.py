#!/usr/bin/env python3
"""Scripted crawl: a saved recipe of selectors does the fetch and the extraction, so the crawler
model reads only the offers that are new or changed.

    python pipeline/recipe.py check config/recipes/<id>.json [saved_page.html]
    python pipeline/recipe.py run config/recipes/<id>.json
    python pipeline/recipe.py diff raw/extract/<id>/<run_id>.json
    python pipeline/recipe.py carry raw/extract/<id>/<run_id>.json <previous observation file>

check  Validate a recipe. With a saved page, print what the recipe extracts from it. No fetch.
run    Fetch the start pages, the next pages and the detail pages with pipeline/fetcher.py (robots,
       per-host gap, official hosts and the private log all apply), extract the fields and write
       raw/extract/<id>/<run_id>.json. Page texts go to raw/pages/. Nothing under raw/ is committed.
diff   Compare a run with the last run of the same recipe and with the published offers. Write
       <run_id>.work.json with the items that are new or changed. Print the counts.
carry  Copy each unchanged offer from the last hand-in file when every quote of that offer is still
       in the text of the page that was just fetched. Write a draft hand-in file and list what the
       crawler model must still do. The gate and the ingest are the same as for a hand-in by hand.

A recipe is JSON (schema/recipe.schema.json). A field rule is one of:
  "css selector"              text of the first match
  "css selector@attr"         attribute of the first match (an href or src becomes an absolute URL)
  {"selector": "...", "output": "text" | "html" | "@attr", "all": true, "regex": "...", "join": " "}
For a JSON source, a rule is a dotted path such as "data.items" or "title.en" or "images[0].url".
"""
import datetime
import glob
import hashlib
import json
import os
import re
import sys
from urllib.parse import urljoin, urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

CONTRACT = "recipe/1"
SPACE = re.compile(r"\s+")
BLOCK_REASONS = {"robots_disallow", "http_error", "timeout", "login_required", "captcha", "app_only", "not_found",
                 "off_domain_redirect", "robots_unreachable", "bot_wall", "network_unreachable"}


def norm(text):
    """White space collapsed to one space, lower case. The same rule as terms.sha256."""
    return SPACE.sub(" ", text or "").strip().lower()


def sha(text):
    return hashlib.sha256(norm(text).encode("utf-8")).hexdigest()


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


# Recipe checks

RECIPE_KEYS = {"recipe", "id", "owner", "country", "purpose", "mode", "source", "start_urls", "settle_ms",
               "actions", "pagination", "list", "detail", "listing_kind", "detail_kind", "note"}


def recipe_problems(recipe):
    out = []
    for key in sorted(set(recipe) - RECIPE_KEYS):
        out.append(f"unknown key {key}")
    if recipe.get("recipe") != CONTRACT:
        out.append(f"recipe must be {CONTRACT}")
    if not re.fullmatch(r"[a-z0-9-]{3,64}", recipe.get("id") or ""):
        out.append("id must be lower case letters, digits and hyphens")
    owner = recipe.get("owner") or {}
    if owner.get("type") not in ("issuer", "network") or not owner.get("id"):
        out.append("owner needs type issuer or network, and id")
    if not re.fullmatch(r"[A-Z]{2}", recipe.get("country") or ""):
        out.append("country must be two upper case letters")
    if recipe.get("purpose") not in ("offers", "cards"):
        out.append("purpose must be offers or cards")
    if recipe.get("mode", "plain") not in ("plain", "browser", "real_chrome"):
        out.append("mode must be plain, browser or real_chrome")
    if recipe.get("source", "html") not in ("html", "json"):
        out.append("source must be html or json")
    if not recipe.get("start_urls"):
        out.append("start_urls is empty")
    lst = recipe.get("list") or {}
    if not lst.get("item"):
        out.append("list.item is missing")
    if recipe.get("detail") and not (lst.get("fields") or {}).get("url"):
        out.append("list.fields.url is needed to follow detail pages")
    if lst.get("key") and lst["key"] not in (lst.get("fields") or {}):
        out.append("list.key must name one of list.fields")
    if recipe.get("mode") == "real_chrome":
        from pipeline.fetcher import load_real_chrome_hosts, real_chrome_host_allowed
        approved = load_real_chrome_hosts(ROOT)
        for url in recipe.get("start_urls") or []:
            if not real_chrome_host_allowed(url, approved):
                out.append(f"real_chrome is not approved for {url}")
    return out


# Extraction

def _parse(html):
    from bs4 import BeautifulSoup
    return BeautifulSoup(html or "", "html.parser")


def _rule(rule):
    if isinstance(rule, str):
        selector, _, attr = rule.rpartition("@") if "@" in rule.split()[-1] else (rule, "", "")
        return {"selector": selector or rule, "output": f"@{attr}" if attr else "text"}
    return dict(rule)


def _value(node, output, base_url):
    if output == "html":
        return str(node)
    if output.startswith("@"):
        value = node.get(output[1:])
        if isinstance(value, list):
            value = " ".join(value)
        if value and output[1:] in ("href", "src", "data-href", "data-src"):
            value = urljoin(base_url, value)
        return value
    return SPACE.sub(" ", node.get_text(" ")).strip()


def html_field(scope, rule, base_url):
    rule = _rule(rule)
    selector, output = rule.get("selector"), rule.get("output", "text")
    nodes = [scope] if selector in (":scope", ".", "") else scope.select(selector)
    values = [v for v in (_value(n, output, base_url) for n in nodes) if v not in (None, "")]
    if rule.get("regex"):
        found = []
        for v in values:
            m = re.search(rule["regex"], v)
            if m:
                found.append(m.group(1) if m.groups() else m.group(0))
        values = found
    if rule.get("all"):
        return rule["join"].join(values) if "join" in rule else values
    return values[0] if values else None


def json_path(data, path):
    if path in ("", "."):
        return data
    for part in re.findall(r"[^.\[\]]+|\[\d+\]", path):
        if part.startswith("["):
            index = int(part[1:-1])
            data = data[index] if isinstance(data, list) and len(data) > index else None
        else:
            data = data.get(part) if isinstance(data, dict) else None
        if data is None:
            return None
    return data


def extract_items(body, recipe, base_url):
    """The list items of one page: [{fields, text}]. text is the item's own text, for the change check."""
    lst = recipe["list"]
    out = []
    if recipe.get("source", "html") == "json":
        data = json.loads(body) if isinstance(body, str) else json.loads(body.decode("utf-8"))
        rows = json_path(data, lst["item"]) or []
        for row in rows:
            fields = {name: json_path(row, path) for name, path in lst["fields"].items()}
            if fields.get("url"):
                fields["url"] = urljoin(base_url, str(fields["url"]))
            out.append({"fields": fields, "text": json.dumps(row, ensure_ascii=False, sort_keys=True)})
        return out
    soup = _parse(body)
    for node in soup.select(lst["item"]):
        fields = {name: html_field(node, rule, base_url) for name, rule in lst["fields"].items()}
        out.append({"fields": fields, "text": SPACE.sub(" ", node.get_text(" ")).strip()})
    return out


def extract_detail(body, recipe, base_url):
    detail = recipe["detail"]
    soup = _parse(body)
    fields = {name: html_field(soup, rule, base_url) for name, rule in (detail.get("fields") or {}).items()}
    scope = soup.select_one(detail["text_selector"]) if detail.get("text_selector") else soup
    text = SPACE.sub(" ", (scope or soup).get_text(" ")).strip()
    return fields, text


def next_page(body, recipe, base_url, number):
    pag = recipe.get("pagination") or {}
    if pag.get("url_template"):
        return pag["url_template"].replace("{n}", str(number))
    if pag.get("next") and recipe.get("source", "html") == "html":
        return html_field(_parse(body), pag["next"], base_url)
    return None


def item_key(fields, recipe, index):
    """source_key for the hand-in: the recipe key field, else the detail URL path, else the position."""
    lst = recipe["list"]
    raw = fields.get(lst["key"]) if lst.get("key") else None
    if not raw and fields.get("url"):
        parts = urlsplit(str(fields["url"]))
        raw = (parts.path.rstrip("/").split("/")[-1] or "") + ("-" + parts.fragment if parts.fragment else "")
    raw = raw or f"item-{index}"
    key = re.sub(r"[^a-z0-9]+", "-", str(raw).lower()).strip("-")[:60].strip("-")
    return key or f"item-{index}"


# Run

class Runner:
    """Fetches pages for a recipe through PoliteFetcher or BrowserFetcher. fetch(url) -> result dict."""

    def __init__(self, recipe, fetch, pages_dir):
        self.recipe, self.fetch, self.pages_dir = recipe, fetch, pages_dir
        self.texts = {}

    def _keep(self, url, result):
        text = result.get("text") or ""
        path = os.path.join(self.pages_dir, hashlib.sha256(text.encode("utf-8")).hexdigest() + ".txt")
        os.makedirs(self.pages_dir, exist_ok=True)
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
        self.texts[url] = path

    def run(self):
        recipe = self.recipe
        pag = recipe.get("pagination") or {}
        max_pages = int(pag.get("max_pages", 1 if not pag else 20))
        items, listing_urls, problems, complete = [], [], [], True
        seen_keys = set()
        for start in recipe["start_urls"]:
            url, number = start, int(pag.get("start", 1))
            for page_no in range(max_pages):
                last_allowed = page_no == max_pages - 1
                result = self.fetch(url)
                if result.get("not_fetched") or not result.get("status") or result["status"] >= 400:
                    problems.append({"url": url, "reason": result.get("not_fetched") or f"http_{result.get('status')}"})
                    complete = False
                    break
                listing_urls.append(result["final_url"])
                self._keep(result["final_url"], result)
                body = result.get("body") or b""
                found = extract_items(body if recipe.get("source") == "json" else body.decode("utf-8", "replace"),
                                      recipe, result["final_url"])
                if not found and page_no:
                    break
                for index, row in enumerate(found):
                    key = item_key(row["fields"], recipe, len(items) + index)
                    while key in seen_keys:
                        key = (key[:56] + "-" + hashlib.sha256((key + str(index)).encode()).hexdigest()[:3])
                    seen_keys.add(key)
                    items.append({"key": key, "page_url": result["final_url"], "fields": row["fields"],
                                  "item_sha256": sha(row["text"]), "fetched_at": result["fetched_at"]})
                number += 1
                nxt = next_page(body.decode("utf-8", "replace") if isinstance(body, bytes) else body, recipe,
                                result["final_url"], number)
                if not nxt or nxt in listing_urls:
                    break
                if last_allowed:
                    complete = False  # a next page exists, but max_pages stops the run
                    problems.append({"url": nxt, "reason": "max_pages"})
                    break
                url = nxt
        if recipe.get("detail"):
            for item in items:
                url = item["fields"].get("url")
                if not url:
                    continue
                result = self.fetch(url)
                if result.get("not_fetched") or not result.get("status") or result["status"] >= 400:
                    item["detail_problem"] = result.get("not_fetched") or f"http_{result.get('status')}"
                    problems.append({"url": url, "reason": item["detail_problem"]})
                    continue
                fields, text = extract_detail(result["body"].decode("utf-8", "replace"), recipe, result["final_url"])
                self._keep(result["final_url"], result)
                item.update(detail_url=result["final_url"], detail=fields, detail_sha256=sha(text),
                            detail_fetched_at=result["fetched_at"])
                if fields.get("terms"):
                    item["terms_sha256"] = sha(fields["terms"] if isinstance(fields["terms"], str) else " ".join(fields["terms"]))
        return {"listing_urls": listing_urls, "listing_complete": complete and not problems, "items": items,
                "problems": problems, "page_texts": self.texts}


def make_fetch(recipe, log_path):
    from pipeline.fetcher import (CHROME_USER_AGENT, BrowserFetcher, PoliteFetcher, load_real_chrome_hosts,
                                  resolve_probe)
    owner = recipe["owner"]
    if owner["type"] == "issuer":
        _label, _url, domains = resolve_probe(ROOT, ["fetcher.py", "probe", owner["id"], recipe["start_urls"][0]])
    else:
        _label, _url, domains = resolve_probe(ROOT, ["fetcher.py", "probe", "--url", recipe["start_urls"][0],
                                                     "--country", recipe["country"]])
    agent = os.environ.get("CRAWLER_USER_AGENT") or CHROME_USER_AGENT
    gap = float(os.environ.get("CRAWLER_MIN_GAP") or 1.5)
    fetcher = PoliteFetcher(log_path, domains, agent, min_gap=gap)
    mode = recipe.get("mode", "plain")
    if mode == "plain":
        return fetcher, fetcher.get
    browser = BrowserFetcher(fetcher, real_chrome=mode == "real_chrome",
                             approved_hosts=load_real_chrome_hosts(ROOT) if mode == "real_chrome" else None)
    actions = recipe.get("actions") or {}

    def fetch(url):
        return browser.render(url, settle_ms=int(recipe.get("settle_ms", 3000)),
                              expand_selector=actions.get("expand_selector"),
                              max_clicks=int(actions.get("max_clicks", 20)),
                              scroll_times=int(actions.get("scroll_times", 0)))
    return fetcher, fetch


def run_id_for(recipe, now):
    return f"{now.strftime('%Y%m%d-%H%M')}-{recipe['id']}"[:64]


def cmd_run(recipe_path, fetch=None, now=None, root=ROOT):
    recipe = load_json(recipe_path)
    problems = recipe_problems(recipe)
    if problems:
        raise ValueError("; ".join(problems))
    now = now or datetime.datetime.now(datetime.timezone.utc).astimezone()
    run_id = run_id_for(recipe, now)
    log = os.path.join(root, "raw", "logs", f"recipe-{run_id}.jsonl")
    fetcher = None
    if fetch is None:
        fetcher, fetch = make_fetch(recipe, log)
    out = Runner(recipe, fetch, os.path.join(root, "raw", "pages")).run()
    out.update(contract=CONTRACT, recipe_id=recipe["id"], recipe_sha256=sha(json.dumps(recipe, sort_keys=True)),
               owner=recipe["owner"], country=recipe["country"], purpose=recipe["purpose"], run_id=run_id,
               started_at=now.isoformat(timespec="seconds"),
               finished_at=datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(timespec="seconds"))
    if fetcher is not None:
        out["fetches"] = list(fetcher.fetches)
        out["blocked"] = list(fetcher.blocked)
    path = os.path.join(root, "raw", "extract", recipe["id"], f"{run_id}.json")
    write_json(path, out)
    return path, out


# Diff

def published_offers(root, owner, country):
    cc = country.lower()
    name = owner["id"][3:] if owner["type"] == "issuer" else f"network-{owner['id']}"
    path = os.path.join(root, cc, "offers", f"{name}.json")
    return load_json(path)["items"] if os.path.exists(path) else []


def previous_run(path):
    folder = os.path.dirname(path)
    runs = sorted(p for p in glob.glob(os.path.join(folder, "*.json"))
                  if not p.endswith((".work.json", ".draft.json")) and os.path.basename(p) < os.path.basename(path))
    return runs[-1] if runs else None


def diff(run, previous, published):
    """Bucket each item: same (unchanged since the last run), new, or changed. gone: keys of the last run not seen now."""
    before = {item["key"]: item for item in (previous or {}).get("items", [])}
    by_terms = {o.get("terms_hash") for o in published if o.get("terms_hash")}
    by_url = {o.get("source_url") for o in published}
    buckets = {"same": [], "changed": [], "new": []}
    for item in run["items"]:
        old = before.get(item["key"])
        if old and old.get("item_sha256") == item.get("item_sha256") and old.get("detail_sha256") == item.get("detail_sha256"):
            buckets["same"].append(item["key"])
        elif not old and item.get("terms_sha256") and item["terms_sha256"] in by_terms:
            buckets["same"].append(item["key"])
        elif old or (item["fields"].get("url") in by_url):
            buckets["changed"].append(item["key"])
        else:
            buckets["new"].append(item["key"])
    seen = {item["key"] for item in run["items"]}
    buckets["gone"] = sorted(k for k in before if k not in seen)
    return buckets


def cmd_diff(path, root=ROOT):
    run = load_json(path)
    prev_path = previous_run(path)
    previous = load_json(prev_path) if prev_path else None
    buckets = diff(run, previous, published_offers(root, run["owner"], run["country"]))
    todo = set(buckets["changed"]) | set(buckets["new"])
    warnings = []
    if previous and len(run["items"]) < 0.5 * len(previous["items"]):
        warnings.append(f"recipe_may_be_broken: {len(run['items'])} items now, {len(previous['items'])} in the last run. "
                        "Check the recipe on a saved page before a hand-in. Do not hand in withdrawals from this run.")
    empty = [name for name in (run["items"][0]["fields"] if run["items"] else {})
             if all(not item["fields"].get(name) for item in run["items"])]
    if empty:
        warnings.append("empty_fields: " + ", ".join(empty))
    work = {"warnings": warnings, "run_id": run["run_id"], "recipe_id": run["recipe_id"], "previous_run": prev_path and os.path.basename(prev_path),
            "counts": {k: len(v) for k, v in buckets.items()}, "buckets": buckets,
            "listing_complete": run["listing_complete"], "problems": run["problems"],
            "items": [i for i in run["items"] if i["key"] in todo]}
    out = path[:-5] + ".work.json"
    write_json(out, work)
    return out, work


# Carry

def quotes_of(node):
    """Every quote string in an offer: values of keys that end in quote or are named quote."""
    out = []
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, str) and (key == "quote" or key.endswith("_quote")):
                out.append(value)
            else:
                out.extend(quotes_of(value))
    elif isinstance(node, list):
        for value in node:
            out.extend(quotes_of(value))
    return out


def carry(run, work, previous_obs, read_text):
    """Unchanged offers from the last hand-in whose quotes are all still on today's pages."""
    same = set(work["buckets"]["same"])
    items = {i["key"]: i for i in run["items"]}
    texts = {url: norm(read_text(url)) for url in run["page_texts"]}
    kept, recheck = [], []
    for offer in previous_obs.get("offers", []):
        key = offer.get("source_key")
        item = items.get(key)
        if key not in same or item is None:
            continue
        urls = {item["page_url"], item.get("detail_url"), offer.get("source_url"), (offer.get("terms") or {}).get("url")}
        pool = " ".join(texts.get(u, "") for u in urls if u)
        missing = [q for q in quotes_of(offer) if norm(q) not in pool]
        if missing:
            recheck.append({"key": key, "missing_quotes": missing[:3]})
            continue
        offer = json.loads(json.dumps(offer))
        if offer.get("terms", {}).get("fetched_at"):
            offer["terms"]["fetched_at"] = item.get("detail_fetched_at") or item["fetched_at"]
        kept.append(offer)
    return kept, recheck


def cmd_carry(run_path, previous_obs_path, root=ROOT, crawler="recipe"):
    run = load_json(run_path)
    work_path = run_path[:-5] + ".work.json"
    work = load_json(work_path) if os.path.exists(work_path) else cmd_diff(run_path, root)[1]
    previous = load_json(previous_obs_path)

    def read_text(url):
        path = run["page_texts"].get(url)
        if not path or not os.path.exists(path):
            return ""
        with open(path, encoding="utf-8") as fh:
            return fh.read()

    kept, recheck = carry(run, work, previous, read_text)
    owner = run["owner"]
    kind_listing = "network_offer_listing" if owner["type"] == "network" else "issuer_promotion_listing"
    kind_page = "network_offer_page" if owner["type"] == "network" else "issuer_promotion_page"
    listing = set(run["listing_urls"])
    fetches = [{"url": f["url"], "final_url": f["final_url"], "status": f["status"], "fetched_at": f["fetched_at"],
                "kind": kind_listing if f["final_url"] in listing else kind_page}
               for f in run.get("fetches", []) if f.get("status")]
    draft_run = dict(previous["run"])
    draft_run.update(run_id=run["run_id"], crawler=crawler, started_at=run["started_at"], finished_at=run["finished_at"],
                     listing_urls=run["listing_urls"] or draft_run["listing_urls"],
                     listing_complete=run["listing_complete"], robots_checked=True,
                     blocked=[{"url": b["url"], "reason": b["reason"] if b["reason"] in BLOCK_REASONS else "http_error"}
                              for b in run.get("blocked", []) if b.get("reason")])
    draft = {"contract": previous["contract"], "run": draft_run, "fetches": fetches or previous["fetches"],
             "offers": kept, "cards": previous.get("cards", []) if run["purpose"] == "offers" else []}
    folder = os.path.dirname(previous_obs_path)
    out = os.path.join(folder, f"{run['run_id']}.draft.json")
    write_json(out, draft)
    todo = {"draft": out, "carried": len(kept), "recheck": recheck,
            "for_the_model": [k for k in work["buckets"]["new"] + work["buckets"]["changed"]],
            "gone": work["buckets"]["gone"]}
    write_json(run_path[:-5] + ".todo.json", todo)
    return out, todo


# Check

def cmd_check(recipe_path, page_path=None):
    recipe = load_json(recipe_path)
    problems = recipe_problems(recipe)
    for line in problems:
        print("error:", line)
    if page_path:
        with open(page_path, encoding="utf-8") as fh:
            body = fh.read()
        base = recipe["start_urls"][0]
        items = extract_items(body, recipe, base)
        print(f"{len(items)} items")
        for row in items[:5]:
            print(json.dumps(row["fields"], ensure_ascii=False)[:300])
        empty = [name for name in recipe["list"]["fields"] if items and all(not r["fields"].get(name) for r in items)]
        for name in empty:
            print(f"warning: field {name} is empty on every item")
        if not items:
            print("error: list.item matched nothing")
            problems.append("no items")
    return 1 if problems else 0


def main(argv):
    if len(argv) < 3 or argv[1] not in ("check", "run", "diff", "carry"):
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "check":
        return cmd_check(argv[2], argv[3] if len(argv) > 3 else None)
    if cmd == "run":
        path, out = cmd_run(argv[2])
        print(f"{path}: {len(out['items'])} items, listing_complete {out['listing_complete']}, problems {len(out['problems'])}")
        return 0
    if cmd == "diff":
        path, work = cmd_diff(argv[2])
        print(f"{path}: " + ", ".join(f"{k} {v}" for k, v in work["counts"].items()))
        for line in work["warnings"]:
            print("warning:", line)
        return 0
    if len(argv) < 4:
        print("carry needs the previous observation file")
        return 2
    path, todo = cmd_carry(argv[2], argv[3])
    print(f"{path}: carried {todo['carried']}, recheck {len(todo['recheck'])}, for the model {len(todo['for_the_model'])}, gone {len(todo['gone'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
