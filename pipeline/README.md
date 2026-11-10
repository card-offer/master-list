# Pipeline

These scripts crawl official issuer, network and merchant pages and publish schema 0.3.

Run them from the repository root. They read `config/rules.json` for the end-date horizon, the evergreen `review_by` interval, archive retention, and the merchant minimum. They do not embed those numbers, and they do not use a fixed "today" date. `generated_at` is the clock at build time. `checked_at` comes from `pipeline/fetch_metadata.json` or from the fetch that just ran.

`python pipeline/publish.py` writes `{cc}/offers/{issuer}.json` and `{cc}/cards/{issuer}.json` when `raw/offers_built.json` and `raw/cards_built.json` exist. It keeps an offer id when the issuer and `source_url` already match a published offer. Offers with no end date stay, with status `evergreen`. Expired offers move to `{cc}/archive/offers/`.

`python pipeline/migrate_0_3.py` is the one-time offline migration from schema 0.2.0. It does not fetch any page.

Derived indexes are built by `python tools/build_indexes.py` and are not committed.
