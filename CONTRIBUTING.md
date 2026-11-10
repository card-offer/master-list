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
