# card-offer / master-list

An open, machine-readable list of credit cards and card offers. Malaysia (MY) and Singapore (SG) are the countries published today. The layout is one folder per country, so another country is another folder, not a schema change.

Every value comes from an official issuer, card network or merchant page. If a value is not stated there, it is null. Nothing is estimated.

Schema version: 0.3.0.

## Licence scope

The [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) licence (see `LICENSE`) covers the compiled structured data in this repository only.

Issuer terms and conditions belong to the issuers. This repository does not publish issuer terms and conditions text: no terms documents, no terms clauses, and no descriptions copied from issuer pages. It also does not publish the `dates_text`, `cap_text`, and `min_spend_text` extracts. Those stay in the crawler's private raw cache, which is not part of this repository. Other short fields from official pages are published, including card benefit, fee, income and guest text, and offer `evidence_text` and `value_text`. A record may carry `terms_url`, `terms_hash` and `terms_fetched_at`, plus structured facts. `terms_hash` is the sha256 of the full terms text read at fetch time. When that full text is not available offline, `terms_hash` is null and `terms_hash_null_reason` says why.

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
| `schema/observation.schema.json` | The crawler hand-in file. Private, never committed. `tools/check_observations.py` is its gate and `pipeline/ingest.py` publishes it. |
| `tools/validate.py` | The check that runs on every pull request and on every push to `main`. |

Derived indexes (`by_card`, `by_merchant`, and the rest) are not stored on `main`. CI builds them and the Pages workflow publishes them. Fetching one issuer's file does not download every offer in the country.

## Schema summary

Full definitions are in [`schema/`](schema/).

- **Card** id: `{cc}-{issuer}-{slug}`. `aliases` lists every id the card had under schema 0.2.0. `networks` is required and non-empty while `status` is `active`. A card with no stated network has `status` `needs_review`.
- **Offer** id: `{cc}-{issuer}-{short hash of the first source URL}`. The same issuer and `source_url` keep that id when the pipeline runs again. `aliases` lists the schema 0.2.0 id.
- **Provider**: `{type: issuer|network|merchant, id}`. Network offers have a place in `networks.json`.
- **Merchant**: each offer has `merchant_kind` (`single`, `multiple`, `category`, `issuer_own`, `unknown`). A `single` offer has `merchant_name` as the official page states it, an optional `merchant_outlet`, and a `merchant_id` in the global registry. One brand is one record in all countries. `verified` is true when the brand has an official domain or at least `merchant_min_offers` offers. `merchant_name_source` says where the name was read. `legacy_title_parse` means the name came from the old title parser and the crawler has not confirmed it on the page.
- **Eligibility** is the rule (`scope`, `rule`, `confidence`, issuer, network, card ids, evidence). The expanded card list is an index built in CI. Inferred rules are not expanded.
- **Money**: `min_spend` is `{amount, currency}`. `limits` lists every stated limit (`kind`, `amount`, `currency`, `per`, `scope`, `weekdays`). `per` is an array. It can hold a time period (such as month or year) and a who-dimension (card, customer, visit, or table) together. When both are present, the legacy `cap.per` keeps the time period and `limits` keeps both. `scope` is `hotel`, `online`, `category`, or null.
- **Time**: `checked_at` is a full ISO date-time with offset, taken from the fetch log. `generated_at` is stamped when the file is built. `status` is `active`, `expired`, `withdrawn`, `evergreen` or `needs_review`. `first_seen`, `last_seen` and `review_by` are dates. An offer with no stated end date is `evergreen` and carries `review_by`. Every other live offer has an end date.
- **Periods**: `booking_period` and `usage_period` are separate. `valid_days` lists weekdays when the source states them. Each country has an IANA time zone.
- **cross_border** is computed from a stated merchant country, a place name, or a foreign currency in the title. It is not copied from the card country.

`category`, `benefit.type` and `benefit.unit` are enums. Every object sets `additionalProperties` to false.

## Using the data

```
https://raw.githubusercontent.com/card-offer/master-list/main/index.json
https://raw.githubusercontent.com/card-offer/master-list/main/my/offers/cimb.json
https://raw.githubusercontent.com/card-offer/master-list/main/merchants/registry.json
```

Resolve a schema 0.2.0 id by scanning `id` and `aliases`.

Active offers on a date: `status` is `active`, `start_date` is null or on or before that date, and `end_date` is on or after it. Evergreen offers have no end date; use `review_by`.

Check `terms_url` and the issuer page before relying on an offer. Issuers change terms without notice.

Indexes, once Pages is serving them, live under the site that hosts the schema `$id` URLs (`https://card-offer.github.io/master-list/`).

## Known issues

- 441 offers have `merchant_kind` `unknown`, and 1,094 merchant names are `legacy_title_parse`. The next crawl under `crawler/RULES.md` replaces them.
- The crawler rule covers offers. Cards still use the older scripts in `pipeline/`.
- Short weekday names such as `every Tue` are not parsed. That misses 8 DBS and POSB offers. A full name such as `every Tuesday` is parsed.
- `per stay`, `per receipt` and `per plan` are not parsed.
- `limits.per` can list a time period and a who-dimension together. The legacy `cap.per` keeps the time period.
- Standard Chartered's `per calendar quarter` count is recorded as a `pool_limit`.
- Limit dedupe ignores the period. The same amount, kind and scope become one limit, and the periods are combined.
- The payout phrase rule can drop a per-booking cap that says first-come, first-served. A per-person cap that says the same phrase is kept.

## Report a mistake or suggest an offer

Open an issue with one of the forms: incorrect data, missing card or offer, or issuer submission. See [CONTRIBUTING.md](CONTRIBUTING.md).
