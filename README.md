# card-offer / master-list

An open, machine-readable list of credit cards and card offers. Malaysia (MY) and Singapore (SG) are the countries published today. The layout is one folder per country, so another country is another folder, not a schema change.

Every value comes from an official issuer, card network or merchant page. If a value is not stated there, it is null. Nothing is estimated.

Schema version: 0.3.0.

## Quick start: use the data in your app

This repository publishes static JSON for developers building card comparisons, offer searches and other tools. Reading it requires no account, API key, package installation or crawler run. Browse a linked JSON file to inspect it, or fetch it from your application. This repository does not include a consumer card-search website or a query API; your application provides the search and display.

1. Open the [entry point](https://raw.githubusercontent.com/card-offer/master-list/main/index.json) to see the countries, schema version and file layout.
2. Choose a country and read its issuers: [Malaysia](https://raw.githubusercontent.com/card-offer/master-list/main/my/issuers.json) or [Singapore](https://raw.githubusercontent.com/card-offer/master-list/main/sg/issuers.json). Records are in `items`.
3. Choose an issuer ID, for example `my-cimb`. Remove the country prefix to get the filename: `my/cards/cimb.json` and `my/offers/cimb.json`. For `sg-dbs`, use `sg/cards/dbs.json` and `sg/offers/dbs.json`.
4. Read the records from each file's `items` array. Check coverage, dates and eligibility before displaying an offer as usable.

| What you need | Example |
|---|---|
| Issuer coverage and card IDs | [MY issuers](https://raw.githubusercontent.com/card-offer/master-list/main/my/issuers.json) |
| A bank's card products | [CIMB Malaysia cards](https://raw.githubusercontent.com/card-offer/master-list/main/my/cards/cimb.json) |
| A bank's offers | [CIMB Malaysia offers](https://raw.githubusercontent.com/card-offer/master-list/main/my/offers/cimb.json) |
| Merchant names and aliases | [Merchant registry](https://raw.githubusercontent.com/card-offer/master-list/main/merchants/registry.json) |
| Country currencies and time zones | [Countries](https://raw.githubusercontent.com/card-offer/master-list/main/countries.json) |

### JavaScript example

Run this in a modern browser console or save it as `example.mjs` and run `node example.mjs` with a Node.js version that provides `fetch`. The public files support cross-origin requests.

```js
const base = "https://raw.githubusercontent.com/card-offer/master-list/main";

async function readJSON(path) {
  const response = await fetch(`${base}/${path}`);
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  return response.json();
}

const [issuerFile, cardFile, offerFile] = await Promise.all([
  readJSON("my/issuers.json"),
  readJSON("my/cards/cimb.json"),
  readJSON("my/offers/cimb.json"),
]);
const issuer = issuerFile.items.find(row => row.id === "my-cimb");
console.log(issuer.name, issuer.crawl.status);
console.log(`${cardFile.items.length} cards, ${offerFile.items.length} offers`);

// Use the card country's calendar day, independent of the device's time zone.
const parts = Object.fromEntries(new Intl.DateTimeFormat("en", {
  timeZone: "Asia/Kuala_Lumpur", year: "numeric", month: "2-digit", day: "2-digit",
}).formatToParts(new Date()).map(part => [part.type, part.value]));
const today = `${parts.year}-${parts.month}-${parts.day}`;

const currentOffers = offerFile.items.filter(offer => {
  if (offer.start_date && offer.start_date > today) return false;
  if (offer.status === "active") return Boolean(offer.end_date && offer.end_date >= today);
  if (offer.status === "evergreen") return Boolean(offer.review_by && offer.review_by >= today);
  return false;
});
console.table(currentOffers.map(offer => ({
  title: offer.title,
  merchant: offer.merchant_name ?? (offer.merchant_names?.join(", ") || null),
  eligibility: offer.eligibility.confidence,
  source: offer.source_url,
})));
```

`currentOffers` is a date/status filter. It does not confirm that the user, a particular card, purchase or location meets the offer terms. Check `eligibility`, `valid_days`, booking/usage periods, redemption countries, minimum spend and limits. An `inferred` eligibility rule is not proof that a particular card qualifies. Link to `source_url` and `terms_url` so users can check the issuer's current conditions.

### Coverage, freshness and reuse

- An issuer's `crawl.status` is `ok`, `partial`, `blocked` or `not_covered`; read `crawl.note` too. A registry entry can exist before its card or offer file is available. A missing file, empty list or missing index match does not prove that the issuer has no cards or offers.
- `null` means unknown or not stated, not zero. Keep `needs_review`, expired and withdrawn records out of a default current-offer display. Evergreen records past `review_by` need rechecking before being presented as current.
- `generated_at` is a file-build time; `checked_at` is the source-check time of a record. Coverage is still being verified, and no fixed refresh schedule is promised. See [Known issues](#known-issues).
- Cache a local copy for your application. The URLs above follow `main` and change after merges. To keep a consistent snapshot, replace `main` with the same full commit SHA in every Raw URL, or clone the repository and check out that commit. Pull-request changes are not published through `main` until merged.
- Include this attribution in your app or accompanying credits: `Data: card-offer master-list (https://github.com/card-offer/master-list), CC BY 4.0.` The [licence scope](#licence-scope) below explains what it covers.

### Find offers for one card or merchant

GitHub Pages publishes generated lookup indexes:

- [MY by card](https://card-offer.github.io/master-list/indexes/my/by_card.json)
- [MY by merchant](https://card-offer.github.io/master-list/indexes/my/by_merchant.json)
- [SG by card](https://card-offer.github.io/master-list/indexes/sg/by_card.json)

Look up `entries[cardId].offer_ids` in a `by_card` file, or `entries[merchantId].offer_ids` in `by_merchant`, then join those IDs to the offer records fetched from GitHub Raw. Card indexes omit inferred eligibility rules, so they are not a complete list of offers that might apply. Apply the date/status and terms checks after joining; indexes can also reference archived offers. An absent `offer_ids` array can be treated as empty for that lookup.

Pages currently serves schemas, metadata, the merchant registry and generated indexes. Issuer card/offer files are served from GitHub Raw; a Pages URL such as `/master-list/my/offers/cimb.json` is not a supported endpoint. Pages builds can lag `main`. For indexes matching a pinned repository snapshot, clone that commit and build them locally with Python 3.12 or later:

```sh
git clone https://github.com/card-offer/master-list.git
cd master-list
# For a pinned snapshot, run: git checkout <full-commit-sha>
python3 tools/build_indexes.py . dist/indexes
```

This builds lookups from the checked-out data and does not crawl issuer sites. For example, the card lookup is written to `dist/indexes/my/by_card.json`.

## Licence scope

The [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) licence (see `LICENSE`) covers the compiled structured data in this repository only.

Issuer terms and conditions belong to the issuers. This repository does not publish issuer terms and conditions text: no terms documents, no terms clauses, and no descriptions copied from issuer pages. It also does not publish the `dates_text`, `cap_text`, and `min_spend_text` extracts. Those stay in the crawler's private raw cache, which is not part of this repository. Other short fields from official pages are published, including card benefit, fee, income and guest text, and offer `evidence_text` and `value_text`. `evidence_text` is one sentence that states who can use the offer. It can come from the offer page or from the terms document. A record may carry `terms_url`, `terms_hash` and `terms_fetched_at`, plus structured facts. `terms_hash` is the sha256 of the full terms text read at fetch time. When that full text is not available offline, `terms_hash` is null and `terms_hash_null_reason` says why.

Attribution line: `Data: card-offer master-list (https://github.com/card-offer/master-list), CC BY 4.0.`

Card names and trademarks belong to their issuers, networks and merchants.

## Layout

| Path | What it holds |
|---|---|
| `index.json` | Entry point: countries, counts, layout, schema list. |
| `{cc}/offers/{issuer}.json` | Offers for one issuer, sorted by id, one record per line. |
| `{cc}/cards/{issuer}.json` | Cards for one issuer, same shape. |
| `{cc}/issuers.json` | Issuers, including `official_domains`. |
| `{cc}/archive/offers/{issuer}.json` | Expired offers still inside the configured retention window. |
| `merchants/registry.json` | One global brand record: countries, official domain, aliases. |
| `networks.json` | Visa, Mastercard, American Express, UnionPay, JCB, Diners Club. |
| `countries.json` | Currency and IANA time zone per country. |
| `config/rules.json` | Horizon, review interval, archive retention, merchant rule. Read at run time. |
| `schema/` | JSON Schema (draft 2020-12). `$id` URLs point at GitHub Pages. |
| `pipeline/` | The crawl and publish code. |
| `crawler/RULES.md` | The rule for the crawler: sources, merchant name, facts and quotes. |
| `crawler/COMPLETE_INSTRUCTION.md` | The steps for the crawler: issuer census, cards and offers of each issuer, and the offer sites of the card networks. |
| `crawler/sources.json` | The canonical list of sites to crawl for Malaysia and Singapore. See `crawler/SOURCES.md`. |
| `{cc}/offers/network-{id}.json` | Offers from a card network's own offer site for cards issued in that country. `provider.type` is `network`. |
| `schema/observation.schema.json` | The crawler hand-in file. Private, never committed. `tools/check_observations.py` is its gate and `pipeline/ingest.py` publishes it. |
| `tools/validate.py` | The check that runs on every pull request and on every push to `main`. |

Derived indexes (`by_card`, `by_merchant`, and the rest) are not stored on `main`. CI builds them and the Pages workflow publishes them. Fetching one issuer's file does not download every offer in the country.

## Schema summary

Full definitions are in [`schema/`](schema/).

- **Card** id: `{cc}-{issuer}-{slug}`. `aliases` lists every id the card had under schema 0.2.0. `networks` is required and non-empty while `status` is `active`. A card with no stated network has `status` `needs_review`.
- **Offer** id: `{cc}-{issuer}-{short hash of the first source URL}`. The same issuer and `source_url` keep that id when the pipeline runs again. `aliases` lists the schema 0.2.0 id.
- **Provider**: `{type: issuer|network|merchant, id}`. Network offers have a place in `networks.json`.
- **Merchant**: each offer has `merchant_kind` (`single`, `multiple`, `category`, `issuer_own`, `unknown`). A `single` offer has `merchant_name` as the official page states it, an optional `merchant_outlet`, and a `merchant_id` in the global registry. A `multiple` offer has `merchant_names`. `merchant_ids` lists every registry record of the offer for both kinds, so use it for lookups. One brand is one record in all countries. `verified` is true when the brand has an official domain or at least `merchant_min_offers` offers. `merchant_name_source` says where the name was read. `legacy_title_parse` means the name came from the old title parser and the crawler has not confirmed it on the page.
- **Eligibility** is the rule (`scope`, `rule`, `confidence`, issuer, network, card ids, evidence). The expanded card list is an index built in CI. Inferred rules are not expanded.
- **Money**: `min_spend` is `{amount, currency}`. `limits` lists every stated limit (`kind`, `amount`, `currency`, `per`, `scope`, `weekdays`). `per` is an array. It can hold a time period (such as month or year) and a who-dimension (card, customer, visit, or table) together. When both are present, the legacy `cap.per` keeps the time period and `limits` keeps both. `scope` is `hotel`, `online`, `category`, or null.
- **Time**: `checked_at` is a full ISO date-time with offset, taken from the fetch log. `generated_at` is stamped when the file is built. `status` is `active`, `expired`, `withdrawn`, `evergreen` or `needs_review`. `first_seen`, `last_seen` and `review_by` are dates. An offer with no stated end date is `evergreen` and carries `review_by`. Every other live offer has an end date.
- **Periods**: `booking_period` and `usage_period` are separate. `valid_days` lists weekdays when the source states them. Each country has an IANA time zone.
- **cross_border** is computed from a stated merchant country, a place name, or a foreign currency in the title. It is not copied from the card country.

`category`, `benefit.type` and `benefit.unit` are enums. Every object sets `additionalProperties` to false.

Resolve a schema 0.2.0 id by scanning `id` and `aliases`.

## Known issues

- Offers from a card network's site are stored by country. A network site that lists offers by the place of use (JCB) is stored under that place. A cardholder from a different country who travels there must read that country's network file. No single file lists the offers of one network for all countries.
- 441 offers have `merchant_kind` `unknown`, and 1,094 merchant names are `legacy_title_parse`. The next crawl under `crawler/RULES.md` replaces them.
- The 300 published cards came from the older scripts. The next crawl under `crawler/RULES.md` replaces them, with one benefit entry for each stated sentence.
- Short weekday names such as `every Tue` are not parsed. That misses 8 DBS and POSB offers. A full name such as `every Tuesday` is parsed.
- `per stay`, `per receipt` and `per plan` are not parsed.
- `limits.per` can list a time period and a who-dimension together. The legacy `cap.per` keeps the time period.
- Standard Chartered's `per calendar quarter` count is recorded as a `pool_limit`.
- Limit dedupe ignores the period. The same amount, kind and scope become one limit, and the periods are combined.
- The payout phrase rule can drop a per-booking cap that says first-come, first-served. A per-person cap that says the same phrase is kept.

## Report a mistake or suggest an offer

Open an issue with one of the forms: incorrect data, missing card or offer, issuer submission, or [suggest a site to crawl](https://github.com/card-offer/master-list/issues/new?template=suggest-site.yml). See [CONTRIBUTING.md](CONTRIBUTING.md). The crawl sources list is in [`crawler/sources.json`](crawler/sources.json), with a short guide in [`crawler/SOURCES.md`](crawler/SOURCES.md).
