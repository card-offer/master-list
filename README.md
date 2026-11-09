# card-offer / master-list

An open, machine-readable list of credit cards and card offers in Malaysia (MY) and Singapore (SG): cards, offers, merchants and issuers, with an official source URL and a `last_checked` date on every record.

Every value comes from an official bank, card network or merchant page or T&C document. If a value is not stated there, it is `null`. Nothing is estimated.

## Layout

| Path | What it holds |
|---|---|
| `index.json` | Entry point: countries, counts, file paths, schema list. |
| `my/`, `sg/` | One folder per country (lowercase ISO 3166-1 alpha-2). Each has `cards.json`, `offers.json`, `merchants.json`, `issuers.json` and `index/by_*.json` (by merchant, card, issuer, network, category, country, benefit type, tier). |
| `global/` | Cross-country indexes: by network, category, benefit type, tier, country and merchant name. |
| `schema/` | JSON Schema (draft 2020-12) for every entity and file. |
| `tools/validate.py` | The check that runs on every pull request. |

Every data file uses the same wrapper: `{schema_version, country, generated_at, count, items}`.

## Schema summary

Full definitions are in [`schema/`](schema/).

- **Card** (`schema/card.schema.json`): issuer, networks, tier, Islamic flag, `annual_fee` (number, plus `waiver_rules`), `min_income` (number and period), `earn_rates` (numeric rate per spend category), and `benefits` with one entry per benefit type. Lounge entries carry programmes, visits, guest policy text and `supplementary_share_visits` (true, false, or null when the page does not say).
- **Offer** (`schema/offer.schema.json`): title, issuer, merchant, category, benefit, eligibility (`scope`, `rule`, `confidence`, `eligible_card_ids`), `start_date` and `end_date` (ISO dates from the deal's own T&C or page; `start_date` is null with `start_date_null_reason` when not stated), `min_spend_text`, `cap_text`, `terms_url`, and the deal's own T&C as `terms_clauses` with `terms_hash` (sha256 of the normalised text) and `terms_fetched_at`.
- **Merchant** and **Issuer**: names, country, categories, and the card and offer IDs that point to them.

Rules every published offer meets:

- It has an `end_date`. Offers whose end date is not written in an official document are held back until it is.
- It has a `source_url`, and every structured field that came from another document names that document (`dates_source_url`, `min_spend_source_url`, `cap_source_url`, `terms_url`).
- `terms_url` is the deal's own T&C, never a bank's general terms.

## Using the data

The JSON files are the API today. Fetch them directly, for example:

```
https://raw.githubusercontent.com/card-offer/master-list/main/index.json
https://raw.githubusercontent.com/card-offer/master-list/main/my/offers.json
https://raw.githubusercontent.com/card-offer/master-list/main/sg/index/by_merchant.json
```

Typical lookups:

- Offers for a card: `{cc}/index/by_card.json` gives `offer_ids` per card ID; read the offers from `{cc}/offers.json`.
- Offers at a merchant: `{cc}/index/by_merchant.json`, or `global/by_merchant_name.json` across countries.
- Active offers on a date: filter `offers.json` where `start_date` (if set) is on or before the date and `end_date` is on or after it.

Check `terms_url` and the issuer's page before relying on an offer. Issuers change terms without notice.

### Planned read-only API (not live yet)

A versioned, read-only HTTP API mirroring this tree is planned:

- `GET /v1/index`
- `GET /v1/{cc}/cards?issuer=&network=&tier=&islamic=&benefit=`
- `GET /v1/{cc}/cards/{id}` (includes eligible offers)
- `GET /v1/{cc}/offers?merchant=&category=&card=&active_on=YYYY-MM-DD`
- `GET /v1/{cc}/merchants/{id}/offers`
- `GET /v1/search?q=`
- `GET /v1/schema/{entity}`

Responses will carry `source_url` and `last_checked`. Until it ships, use the raw files above.

## Report a mistake or suggest an offer

Open an issue using one of the forms:

- **Incorrect data**: a value on a card or offer is wrong. Give the record ID, the field, the correct value and an official source URL.
- **Missing card or offer**: something is not listed. Give the issuer, the name, an official source URL and its dates.
- **Issuer submission**: for banks that want to point us at their official offer feed or pages.

Blank issues are turned off so every report carries a source. See [CONTRIBUTING.md](CONTRIBUTING.md) for the rules.

## Licence and attribution

Data is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (see `LICENSE`).

Attribution line: `Data: card-offer master-list (https://github.com/card-offer/master-list), CC BY 4.0.`

Card names, trademarks and offer terms belong to their issuers, networks and merchants.
