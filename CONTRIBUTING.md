# Contributing

Thank you for helping keep this list correct. Three rules apply to every change.

## 1. Every claim needs an official source

- Each added or changed value must cite an official source URL: the issuing bank's site, the card network's site, or the merchant's own site, including their T&C documents.
- Offers must include the deal's own T&C link (`terms_url`) when one exists, and an `end_date` written in that T&C or on the deal page. Offers without a stated end date are not published.
- Never estimate or fill in a value that the source does not state. Use `null` instead.
- Update `last_checked` on every record you touch.

## 2. No data from aggregator sites

Do not copy, use or cite data from third-party comparison, review, deal or aggregator sites, blogs or forums, even when they quote a bank. Go to the official page and cite that.

## 3. The maintainer reviews every change

- All changes go through a pull request and are reviewed by the maintainer before merge. Nobody merges their own change.
- Changes to fees, income requirements or earn rates get an extra check against the source.
- The `validate` check must pass: `python tools/validate.py` from the repository root.

## How to contribute

- Found an error or a missing offer? Open an issue with the matching form. That is usually enough.
- Sending a pull request? Fill in the checklist in the pull request template and link the issue.
- Banks and networks: use the issuer submission form to share an official offer feed or page.

Text you write in this repository (JSON, Markdown, YAML) must not contain em dashes.
