# card-offer / master-list

An open, machine-readable list of credit cards and card offers. Malaysia (MY) and Singapore (SG) are the countries published today. The layout is one folder per country, so another country is another folder, not a schema change.

Every value comes from an official issuer, card network or merchant page. If a value is not stated there, it is null. Nothing is estimated.

Schema version: 0.3.0.

## Licence scope

The [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) licence (see `LICENSE`) covers the compiled structured data in this repository only.

Issuer terms and conditions belong to the issuers. This repository does not publish verbatim source text. It does not publish terms documents, terms clauses, copied descriptions, or source sentences for dates and amounts. A record may carry `terms_url`, `terms_hash` and `terms_fetched_at`, plus structured facts. `terms_hash` is the sha256 of the full terms text read at fetch time. When that full text is not available offline, `terms_hash` is null and `terms_hash_null_reason` says why. The source sentences stay in the crawler's private raw cache, which is not part of this repository.

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
| `tools/validate.py` | The check that runs on every pull request and on every push to `main`. |

Derived indexes (`by_card`, `by_merchant`, and the rest) are not stored on `main`. CI builds them and the Pages workflow publishes them. Fetching one issuer's file does not download every offer in the country.

## Schema summary

Full definitions are in [`schema/`](schema/).

- **Card** id: `{cc}-{issuer}-{slug}`. `aliases` lists every id the card had under schema 0.2.0. `networks` is required and non-empty while `status` is `active`. A card with no stated network has `status` `needs_review`.
- **Offer** id: `{cc}-{issuer}-{short hash of the first source URL}`. The same issuer and `source_url` keep that id when the pipeline runs again. `aliases` lists the schema 0.2.0 id.
- **Provider**: `{type: issuer|network|merchant, id}`. Network offers have a place in `networks.json`.
- **Merchant**: a global id. A name becomes a merchant when it has an official domain or at least as many offers as `merchant_min_offers` in `config/rules.json`. Other names stay on the offer as `merchant_text`. Duplicate brands across countries are one record.
- **Eligibility** is the rule (`scope`, `rule`, `confidence`, issuer, network, card ids, evidence). The expanded card list is an index built in CI. Inferred rules are not expanded.
- **Money**: `min_spend` and `cap` are `{amount, currency, per}` beside the source text. `per` is only on `cap`.
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

## Report a mistake or suggest an offer

Open an issue with one of the forms: incorrect data, missing card or offer, or issuer submission. See [CONTRIBUTING.md](CONTRIBUTING.md).
