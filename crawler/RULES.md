# Crawler rule for Grok Bot

Version 2. Contract: `observation/1`. Schema: `schema/observation.schema.json`.

You crawl. The pipeline publishes. You do not write the public files, you do not make IDs, and you do not edit the merchant registry. You give one hand-in file for each issuer and each run. The gate checks it. The ingest step publishes it.

## 1. The work cycle

1. Read `{cc}/issuers.json`. Take the issuer and its `official_domains`.
2. Crawl the issuer's offer listings and each offer page and terms document.
3. Write `raw/observations/{cc}/{issuer_id}/{run_id}.json`. The `raw/` folder is private. Do not commit it.
4. Run `python tools/check_observations.py <file>`. Correct each `error` line. Run it again until it gives exit 0.
5. Run `python pipeline/ingest.py <file>`, then `python tools/validate.py .`.
6. Open a pull request with the changed public files. Do not merge it.

If the gate refuses a fact and the page does not support a correction, remove the fact (use null) or set a flag. Do not change a quote to make the gate pass.

## 2. Crawl limits

1. Use only hosts in the issuer's `official_domains`. A merchant's own site is permitted only as fetch kind `merchant_page`, and only when the issuer page links to it.
2. Do not use aggregator, comparison, deal, review, blog or forum sites. Do not use search engine snippets as a source.
3. Read `robots.txt` for each host before the first page of that host, over https. Do not fetch a disallowed path. Record it in `run.blocked` with reason `robots_disallow`. What the answer means:
   - Status 200: obey the rules for your user agent.
   - Status 404 or 410: the host has no rules. You can crawl it.
   - Status 401, 403 or 429, a server error (500 and higher), a timeout, a TLS or connection error, more than 5 redirects, a redirect loop, or a redirect to a host that is not in `official_domains`: `robots.txt` is not readable. Do not fetch a page of that host in this run. Record the host in `run.blocked` with reason `robots_unreachable`.
   - A redirect of `robots.txt` to a host that is in the same `official_domains` list is permitted. Log each hop.
   - A fact from a page that was fetched after `robots.txt` was not readable is not evidence. Fetch the page again in a run where `robots.txt` is readable, or leave the fact out.
4. Public pages only. No sign-in, no sign-up, no form, no contact, no captcha bypass.
5. One request at a time for each host, with a minimum of 1.5 seconds between the starts of two requests. Measure the gap with a monotonic clock, and log each request with its time to the millisecond. A log with whole seconds does not prove the gap.
   - A redirect hop and a `robots.txt` request are requests.
   - A headless browser has the same rules. Each request that the browser makes to the host (document, script, data) is a request: check `robots.txt` for it, space it and log it. Stop requests to hosts that are not in `official_domains`, apart from the files that the page needs to show its text.
   - In a browser, the only permitted actions are a scroll and a click on a control that shows more of the same public content: load more, next page, a tab, an accordion, a category or country filter, a cookie notice. Log each action. Do not type in a field, do not submit a form, and do not sign in. If a page needs this, record it in `run.blocked` with reason `login_required`.
   - Use `pipeline/fetcher.py` for each request. It applies this section in code. `crawler/HARD_SITES.md` says what to do when a site does not answer, needs JavaScript or blocks the crawler.
   - Status 429 or 503 on a page: stop requests to that host for the remainder of the run.
   - Do not fetch a URL whose path is a sign-in, registration or application form.
   - Keep session IDs out of the hand-in file. If a site puts a session ID in a URL (for example `jsessionid`), record the URL without it.
6. Record each fetch in `fetches` with its real time and time zone offset. Do not write a time that you did not measure.
7. Set `run.listing_complete` to true only if you read every page and every tile of every listing. If you are not sure, set false.
8. If you cannot reach a page, record it in `run.blocked`. Do not fill the gap from memory.
9. If an official URL sends you to a host that is not in `official_domains`, do not read that host. Do not record the fetch. Record the official URL in `run.blocked` with reason `off_domain_redirect` and the target in `redirect_to`, and keep `listing_complete` false. The maintainer decides if the host is official.

## 3. The merchant name

This is the most important field. A cardholder looks for offers by merchant.

### 3.1 Find the name in this order

1. The heading of the offer page (`page_heading`).
2. The tile on the listing (`listing_tile`).
3. The terms document, where it names the participating merchant (`terms_document`).
4. The alt text of the merchant logo (`logo_alt_text`).
5. The merchant's own page that the issuer page links to (`merchant_page`).

Do not take the name from the URL, from your memory or from a guess.

### 3.2 Write the name correctly

1. Write the trading name as the page writes it. Keep the page's spelling and capitals: `Trip.com`, `7-Eleven`, `B/SKIN`.
2. Remove markup and trademark signs: `Baa Baa Sheepz<sup>®</sup>` becomes `Baa Baa Sheepz`.
3. Give the brand only. Do not add offer words, prices, dates, card names or campaign names.
4. Put a branch, outlet or in-hotel restaurant in `outlet`, not in `name`.
5. Do not translate the name. Do not expand or shorten it.
6. Copy the text that contains the name into `name_quote`. The gate fails if the name is not inside the quote. The name must be in one part of the quote: the gate cuts the quote at each comma, semicolon and line end. An address line is not proof of a name. Quote the heading or the tile that names the merchant.

| The page says | name | outlet | kind |
|---|---|---|---|
| Fairmont Singapore, The Eight: 20% off total food bill | Fairmont Singapore | The Eight | single |
| Complimentary Yakitori platter at Toji Yakitori Bar | Toji Yakitori Bar | null | single |
| Agoda x Mastercard: up to 12% off | Agoda | null | single |
| 15% off at Ogawa (KLSCM) | Ogawa | KLSCM | single |
| 10% off at Hertz, Avis and Budget | null (use `names`) | null | multiple |
| 5% cashback on all petrol spend | null | null | category |
| 0% instalment plan, balance transfer, sign-up gift | null | null | issuer_own |
| 50% off flights capped at S$100 every Tue | null | null | category |

### 3.3 Choose the kind

- `single`: one merchant. `name`, `name_source` and `name_quote` are mandatory.
- `multiple`: the offer names two or more merchants. Put each in `names`. Each name gets its own record in the merchant registry, so write each one with the same care as a single name. If the page gives each merchant its own terms or dates, hand in one offer for each merchant.
- `category`: the offer applies to a type of spend, not a named merchant.
- `issuer_own`: the issuer's own product or campaign. The issuer and the card networks are never merchants.
- `unknown`: permitted only after you read the page, the tile and the terms and none states a merchant. Set the flag `merchant_not_stated`. The gate fails a run of 20 or more offers when more than 5 percent are `unknown`.

### 3.4 Names with offer words

The gate refuses a name that contains words such as off, free, sale, deal, rewards, or an amount. If that is the real trading name (for example `Free Fire`), set `name_checked` to true. Use it only when the page shows it as the brand.

### 3.5 Official domain

Set `official_domain` only when the issuer page links to the merchant's own site. Write the host only, for example `trip.com`. If there is no link, use null.

## 4. One offer, one record

1. One record for each deal that has its own merchant, benefit or dates.
2. `source_url` is the official page that shows the offer. Do not add a fragment.
3. `source_key` tells the offer apart from other offers on the same page. Choose the first that exists:
   1. `single_offer_page`: the page has one offer. Use the last part of the URL path.
   2. `page_anchor`: the page's own element id or anchor for the tile.
   3. `deal_code`: the promo code or deal id that the page prints.
   4. `terms_file_name`: the file name of the deal's terms document.
   5. `merchant_name`: the merchant name key that the gate prints.
4. Do not make `source_key` from the title. Titles change. The key must stay the same in the next crawl.
5. Do not hand in an offer whose end date is before the run date.

## 5. Facts and quotes

Each fact that will be published needs a quote: the one sentence on the official page or in the terms that states it. A quote has a maximum of 300 characters. Quotes are private and are not published, except the eligibility quote and the card quotes. An em dash in a published quote is written as a hyphen.

| Fact | Rule |
|---|---|
| `benefit.value` | What the cardholder gets: the discount, cashback, voucher or gift value. The number must be in `benefit.quote`. A fee, an interest rate or a minimum spend is not a benefit value: use null. If the page gives no number, use null and a `benefit.type` that fits. |
| `dates.end_date` | Day, month and year must be in `dates.quote`. If the page states no end date, use null with `end_date_null_reason: not_stated`. The offer is then published as evergreen. |
| `dates.start_date` | Only if the page states it. If not, use null. Do not use the fetch date. |
| `booking_period`, `usage_period` | Use them when the page gives a booking window and a stay or travel window. |
| `min_spend` | Amount and ISO 4217 currency. The amount must be in its quote. |
| `limits` | One entry for each stated limit. Do not put a campaign budget or a prize pool as a `reward_cap`. A total for all customers is a `pool_limit`. |
| `eligibility` | `stated` needs a quote. Use `card` with `card_names` as the page writes them, or `issuer_network` with `network_ids`, or `issuer` when the page says all cards. If the page states no restriction, use `issuer` with `inferred` and no card names. `tiers` holds card tiers only (gold, platinum, signature and so on). A customer segment, for example a priority banking programme, is not a tier. The eligibility quote is published as `evidence_text`, so give one sentence only, from the page or from the terms. |
| `terms` | `deal_document`: the deal's own document. `deal_page_section`: the terms section on the offer page. `listing_popup`: a popup on the listing. Hash the full terms text (lower case, white space collapsed to one space, sha256). Never use the bank's general terms. |
| `redeem.countries` | Where the cardholder can use the offer. Use the card country unless the page states a different place. Use `*` for worldwide. |

Rules for all facts:

1. If the page does not state it, the value is null. Do not estimate, do not calculate and do not copy from a different offer.
2. If two sentences on the page conflict, set the flag `date_conflict` or `amount_unclear`. The offer then goes to review.
3. If an end date is more than 24 months ahead, read it again. If it is correct, set the flag `end_date_past_horizon`.
4. Use the currency that the page writes. Do not convert.
5. Do not use an em dash in a title.

## 6. Cards

Hand in the issuer's cards in the `cards` list of the same file. Do the cards before the offers, so each card name in an offer finds its card.

1. `official_url` is the issuer's own product page for the card. Fetch kind is `issuer_product_page`.
2. `name` is the product name as the page heading writes it. Copy the heading into `name_quote`.
3. `networks`: the network must be in `network_quote` or in the card name. Look in this order: the card name, the page text, the alt text of the card image, the product disclosure sheet. If none states it, give an empty list and set the flag `network_not_stated`. Do not guess from the card design or from your memory. The quote must state the network of the card itself. The name of a network service, for example a lounge or travel programme, is not proof.
4. `annual_fee.amount` is the principal card fee for one year, as the page writes it. Use 0 only when the page says there is no annual fee. The amount must be in the quote.
5. `waivers`: one entry for each kind. `lifetime` stands alone. If the page gives conflicting waiver sentences, set the flag `fee_unclear`.
6. `min_income`: amount and period (`year` or `month`) as stated. Do not convert a month to a year.
7. `earn_rates`: one entry for each stated rate. The rate must be in its quote.
8. `benefits`: one entry for each stated benefit, with the one sentence that states it. Do not merge two sentences. For lounge access, give one entry for each rule: "6 visits each year" and "unlimited access to lounge X" are two entries.
9. If one page describes two or more cards and you cannot tell which benefit belongs to which card, set the flag `shared_product_page`.
10. Card texts are published. Keep each quote to the one sentence that states the fact.

## 7. Network runs and other languages

`crawler/COMPLETE_INSTRUCTION.md` has the steps. The rules for the facts are:

1. A run of a card network's own offer site has `run.network_id` and no `run.issuer_id`. It has no `cards` list. Eligibility is scope `network`, with `network_ids` equal to the network of the run.
2. Card tiers that the page names go in `tiers`. Issuers that the page names go in `issuer_names`, as the page writes them.
3. The country of a network run is the location where the card was issued, as the site lists it. The country must be in `countries.json`.
4. Keep the title, the merchant name and each quote in the language and the script of the page. If the page shows the merchant name in two scripts, put the Latin form in `name` and the second form in `alt_names`.
5. The gate reads amounts with the separators of the country and with number words (juta, triệu, 万, lakh), and dates with Indonesian and Thai month names and the Thai Buddhist year. The word lists are in `config/merchant_rules.json`.

## 8. What the pipeline does with your file

- It keeps the published ID when the page and key are the same, or when the page and the merchant are the same. A new title does not make a new ID.
- It links each `single` merchant to one global record in `merchants/registry.json`. `Shopee Singapore`, `SHOPEE` and `Shopee Pte Ltd` become one brand. A brand with one offer and no official domain is published with `verified: false`.
- It keeps a card ID when the card name is the same. A card with no network goes to review.
- It maps `card_names` to card IDs. Write each card name as the page writes it. The pipeline ignores the issuer name, the country and the words credit card when it matches. A name that is not in the card list sends the offer to review. Report these names. Do not change them to fit.
- It sets `first_seen`, `last_seen`, `status` and `review_by`.
- After a complete listing run, an offer that was not seen for 14 days becomes `withdrawn`.
- Expired offers move to the archive.

## 9. Report after each run

Give these numbers and nothing else, unless something failed:

1. Cards and offers handed in, and the count for each merchant kind.
2. New, kept and withdrawn offers from the ingest report.
3. Offers in `needs_review`, with the reason.
4. Card names that were not matched.
5. Blocked URLs, with the reason.
