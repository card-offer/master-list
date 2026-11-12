# Contributing

Thank you for helping keep this list correct. These rules apply to every change.

## 1. Every claim needs an official source

- Each added or changed value must cite an official source URL: the issuer's site, the card network's site, or the merchant's own site.
- `terms_url` is the deal's own terms link when one exists. Do not paste verbatim terms. Publish `terms_url`, `terms_hash`, `terms_fetched_at` and the structured facts.
- An offer with a stated end date must include that `end_date`. An offer with no stated end date is published as `status: evergreen` with a `review_by` date. Do not delete it.
- Never estimate a value the source does not state. Use null.
- `checked_at` is a full ISO date-time with offset from the fetch, not a single date stamped on a whole file.

## 2. Official sources only

Use official issuer, card network and merchant pages only. Do not bring in material from anywhere else, even when that page quotes a bank.

## 3. Thresholds live in config

Do not hard-code the end-date horizon, the evergreen review interval, the archive retention, or the merchant minimum in code. Those values are in `config/rules.json` and the tools read them at run time.

## 4. The maintainer reviews every change

- All changes go through a pull request. Nobody merges their own change.
- The `validate` check must pass: `python tools/validate.py` from the repository root.
- Text in this repository (JSON, Markdown, YAML, and comments) must not contain an em dash.

## Identifiers

Keep an existing offer id when the issuer and `source_url` are unchanged. Put a replaced id in `aliases`. Card ids are `{cc}-{issuer}-{slug}`. Offer ids are `{cc}-{issuer}-{short hash of the first source URL}`.

## 5. Suggesting a site

To propose a new official site for the crawl list, open a GitHub issue with the "Suggest a site to crawl" form. Give the URL, the country, the site type (issuer, network, merchant or regulator), whether the page lists cards or offers, and why the page is official.

A maintainer then triages the issue:

1. Confirm that the host is the organisation's own official domain, and that the page is not an aggregator or comparison site. Suggestions that are not official are declined.
2. Probe the page with `pipeline/fetcher.py`, following `crawler/RULES.md` v3 and `crawler/HARD_SITES.md`.
3. If the site belongs on the list, open a pull request that adds it to `crawler/sources.json` (see `crawler/SOURCES.md`). The new row uses status `untested`, or the probe class (`ok`, `js_shell`, `bot_wall`, or `network_unreachable`) when the probe recorded one. Link the issue in the `suggested_by` field.
4. The change needs a review from the CODEOWNERS maintainer before it is merged.

Do not add a host to `official_domains` or start a crawl from a suggestion until that pull request is merged.
