# Scripted crawl: recipes

This file is the method that makes a weekly crawl cost fewer model tokens. A script does the fetch, the extraction and the change check. The crawler model writes a recipe one time for each listing. After that, it reads only the offers that are new or changed. `crawler/RULES.md` is still the rule for each fact, and the gate and the ingest are the same.

## 1. The idea

Hosted scraping APIs work in the same way: the client sends extraction rules (CSS selectors that map to named fields), browser steps (click, scroll, wait), and a choice of plain or rendered fetch. The client then gets compact JSON back, not the page. The tool here copies those parts and keeps our own crawl limits.

| Part | In this repository |
|---|---|
| Extraction rules (selector to field, text or attribute, list of items) | `list.fields` and `detail.fields` in a recipe |
| Browser steps (click a "load more" control, scroll, wait) | `mode: browser`, `actions.expand_selector`, `actions.scroll_times`, `settle_ms` |
| Read the JSON that the page loads | `source: json` with a dotted path, for the public JSON file of a listing |
| Next pages | `pagination.next` (a selector) or `pagination.url_template` with `{n}` |
| Do not fetch the same thing again for nothing | `diff` and `carry`: an unchanged offer is copied from the last hand-in after a script check |

What is not copied, because `crawler/HARD_SITES.md` section 3 forbids it: rotating or residential proxies, a change of IP or country, stealth browser plugins, captcha solving, and parallel requests to one host. Every request of a recipe goes through `pipeline/fetcher.py`, so `robots.txt`, the 1.5 second gap, the official hosts, the real-Chrome list and the private log all apply.

## 2. The weekly cycle for one listing

```bash
python pipeline/recipe.py run config/recipes/<id>.json
```

```bash
python pipeline/recipe.py diff raw/extract/<id>/<run_id>.json
```

```bash
python pipeline/recipe.py carry raw/extract/<id>/<run_id>.json raw/observations/<cc>/<issuer>/<last_run>.json
```

1. `run` fetches the listing, the next pages and the detail pages, and writes `raw/extract/<id>/<run_id>.json`. It keeps the text of each page under `raw/pages/`.
2. `diff` compares the run with the last run of the same recipe and with the published offers. It writes `<run_id>.work.json` with only the items that are `new` or `changed`, and prints the counts. An item is `same` when its listing text and its detail text did not change.
3. `carry` copies each `same` offer from your last hand-in file into `raw/observations/<cc>/<issuer>/<run_id>.draft.json`. It copies an offer only when every quote of that offer is still in the text that was fetched today. An offer that fails this check goes to the `recheck` list in `<run_id>.todo.json`.
4. You read only the items in `for_the_model` and `recheck` of the todo file. Add each one to the draft file under `crawler/RULES.md`, as in a hand-in by hand. Use the extracted fields as a start, and take each quote from the page text.
5. Save the draft as the hand-in file, without `.draft` in the name. Then run the gate, the ingest and the validator, and open the pull request, as in `crawler/COMPLETE_INSTRUCTION.md` section 8.

Items in `gone` were in the last run and are not on the listing now. Do not hand them in. The ingest withdraws an offer after 14 days off a complete listing.

## 3. Write a recipe

Write the recipe at the first run of a listing, and commit it under `config/recipes/<id>.json` in the same pull request. Use the id `<owner id>-<purpose>`, for example `sg-dbs-offers` or `network-mastercard-my-offers`. The file must match `schema/recipe.schema.json`.

1. Probe the listing with `pipeline/fetcher.py probe` (see `crawler/HARD_SITES.md`). Keep the page that the probe saves under `raw/probes/`.
2. In that saved page, find the element that holds one offer tile. That is `list.item`.
3. Inside the tile, find the merchant name, the link to the offer page, the benefit text and the date text. Each is a field rule.
4. If the listing has more pages, give `pagination`. If it has a "load more" control, use `mode: browser` and `actions.expand_selector`.
5. If the listing loads a public JSON file on an official host, use that file as the start URL with `source: json`. This is the best source.
6. If each offer has its own page, give `detail.fields`. Name the terms element `terms`; the script then gives `terms_sha256`, with the same rule as `terms.sha256` in the hand-in.
7. Test the recipe on the saved page. No fetch is made:

```bash
python pipeline/recipe.py check config/recipes/<id>.json raw/probes/<saved page>.html
```

The check prints the item count and the first items, and warns about a field that is empty on every item. Correct the selectors until the count is the same as the number of tiles you see on the page.

A small recipe:

```json
{
  "recipe": "recipe/1",
  "id": "sg-dbs-offers",
  "owner": {"type": "issuer", "id": "sg-dbs"},
  "country": "SG",
  "purpose": "offers",
  "mode": "plain",
  "start_urls": ["https://www.dbs.com.sg/personal/promotion/default.page"],
  "pagination": {"next": "a.next@href", "max_pages": 20},
  "list": {
    "item": "div.promo-tile",
    "fields": {
      "merchant": "h3",
      "url": "a@href",
      "benefit": "p.offer",
      "end": {"selector": "span.validity", "regex": "till (.+)$"}
    }
  },
  "detail": {"fields": {"heading": "h1", "terms": "div.tnc"}, "text_selector": "main"}
}
```

The selectors in this example show the form only. They were not taken from the DBS site.

## 4. When the script and the page disagree

1. `diff` prints `recipe_may_be_broken` when the item count is less than half of the last run. The site layout probably changed. Test the recipe on a new saved page and correct it. Do not hand in a run with this warning, because the missing items would look withdrawn.
2. `empty_fields` names a field that is empty on every item. Correct its selector.
3. A `max_pages` problem means that the listing has more pages than the recipe allows. The run is not complete. Raise `max_pages` and run again.
4. If a site cannot be read with a recipe, crawl it by hand under `crawler/HARD_SITES.md`. Write in the report why the recipe did not work.

## 5. Token rules

1. Do not read a full page when a recipe exists for it. Read the work file and the todo file.
2. For a new or changed item, read the detail page text from `raw/pages/`, not the HTML.
3. Do not read the items in `same`. The script checked them.
4. Report the counts of `run`, `diff` and `carry` in the run report: items, same, new, changed, gone, carried and recheck.
