# Next crawls (work order of 20 Nov 2026)

This file is the work order for Card Crawler after PR 66. It lists the crawls that are still open, in the order to do them. `crawler/RULES.md` is the rule for each fact. `crawler/COMPLETE_INSTRUCTION.md` is the method for each track. `crawler/HARD_SITES.md` is the method for a site that blocks or needs JavaScript. If this file disagrees with `crawler/RULES.md`, `crawler/RULES.md` is correct.

Copy all the text below the line and give it to Card Crawler.

---

You are the crawler for https://github.com/card-offer/master-list. Do the tasks below in order. One run is one issuer, or one network and one location. Each run gives one pull request. Do not merge a pull request.

## 0. Before each run

1. Pull `main`. Read `crawler/RULES.md`, `crawler/HARD_SITES.md` and this file again. They change.
2. The user agent is desktop Chrome. `pipeline/fetcher.py` sends it by default. Do not set `CRAWLER_USER_AGENT` unless the maintainer gives you a value.
3. Real-Chrome mode is permitted only for the hosts in `config/real_chrome_hosts.json`. On 20 Nov 2026 these are `specials.priceless.com`, `www.maybank2u.com.my` and the 15 census bank homepages in section 7. For every other host, use plain and headless-browser mode only. Use real Chrome only after plain and browser mode fail, one attempt per host, with `--min-gap 30`.
4. Use only hosts in the issuer's or the network's `official_domains`. If an official page links to a host that is not on that list, report the host. Do not crawl it.
5. After each run: `python tools/check_observations.py <file>` until exit 0, then `python pipeline/ingest.py <file>`, then `python tools/validate.py .`, then the pull request. Give the report in section 11 of `crawler/COMPLETE_INSTRUCTION.md`.
6. Use the scripted crawl of `crawler/SCRIPTED_CRAWL.md` for every listing. Write the recipe at the first run of a listing and commit it with the run. From the second run on, read only the items that `diff` and `carry` give you.
7. A run that only finds what was already published is still a run. Hand it in, so `last_seen` and `checked_at` move forward.

## 1. Maybank Malaysia (`my-maybank`)

Follow `crawler/HARD_SITES.md` section 5. The 13 Nov run read the promotions pages and published 62 offers. The conventional card listing was not read, so `crawl.status` is `partial`.

1. Probe the conventional card listing `https://www.maybank2u.com.my/maybank2u/malaysia/en/personal/cards/credit_cards_listing.page` with a plain request, then with the browser, then one real-Chrome probe if both fail.
2. If a probe reads the listing, do a full card run and a full offer run for `my-maybank`. Match the 62 published offers to the cards.
3. If all probes fail, record `network_unreachable` with the error text of each mode, and report.

## 2. Cards that are missing from a card list

These offers are `needs_review` because the offer names a card that is not in the issuer's card file. Do a card run for the issuer and find each card on its official domains. Then do an offer run, so the ingest matches the offers again. Do not change the eligibility quote of an offer to make it match.

| Issuer | Card names in the offers | Offers in review |
|---|---|---|
| `my-standard-chartered` | Priority Banking Visa Infinite credit card; Priority Worldmiles Mastercard | 43 |
| `my-aeon-credit` | AEON Platinum Visa Card; AEON Platinum Mastercard; AEON Member Plus Visa Card; AEON Member Plus Credit Card | 4 |
| `my-hong-leong` | HLB Infinite P Credit Card; HLB Infinite Credit Card; HLB Infinite Doctor's Edition Credit Card | 1 |

A card can be for Priority or private banking clients only. It is still a card. Hand it in with the eligibility that the page states. If the issuer has no page for the card, or the page says that the card is no longer offered, report the card name and the page you checked. Do not make a card record without a page.

## 3. Offers with crawler flags

Re-read the terms of these offers. The most frequent flags:

| Issuer | Flag | Offers |
|---|---|---|
| `my-ocbc` | `date_conflict` | 68 |
| `my-hong-leong` | `amount_unclear` | 29 |
| `sg-maybank` | `end_date_past_horizon` | 18 |

1. `date_conflict`: the listing and the terms state different dates. Take the dates from the offer's own terms document. If the terms state a booking period and a stay or usage period, give both (`booking_period` and `usage_period`). Keep the flag only when the terms themselves state two different end dates for one offer, and quote both.
2. `end_date_past_horizon`: an end date more than 24 months ahead. Check that the date is the end of the offer and not a card fee date, a programme date or a rate change date. Quote the sentence that gives the end date.
3. `amount_unclear`: give the amount and the currency only when the quote states them. Otherwise give null with the reason.
4. `merchant_not_stated`: find the merchant in the terms or on the offer page. If no page states a merchant, keep the flag.

Do these as part of the next full run of each issuer. Do not make a run for one flag.

## 4. Merchant names from the old data

These offers still have `merchant_name_source: legacy_title_parse`. The name came from an old title parse and was not read on a page. In the next run of each issuer, read the name from the page heading, the listing tile or the terms document, as `crawler/RULES.md` section 3 says.

| Issuer | Offers |
|---|---|
| `sg-ocbc` | 77 |
| `my-rhb` | 22 |
| `my-uob` | 20 |
| `my-hong-leong` | 5 |
| `sg-icbc` | 3 |
| `sg-amex` | 1 |
| `my-standard-chartered` | 1 |

If the offer is no longer on the listing, do not hand it in. The ingest withdraws it after 14 days.

## 5. Issuers that are not covered or partly covered

| Issuer | Status | What to do |
|---|---|---|
| `my-bank-rakyat` | not_covered | The compare-cards URL is a 404. The card menu needs JavaScript. Use the ladder of `crawler/HARD_SITES.md` section 2, step 3: find the data source in the page source or sitemap first, then render. The reCAPTCHA is on a contact form only. Do not submit any form. |
| `my-icbc` | not_covered | The census read the product page on `icbcmy.com`: ICBC UnionPay Dual Currency Credit Card and ICBC Visa Credit Card, each as Classic, Gold and Platinum. Do a card run and an offer run. |
| `my-hsbc` | partial | Do a card run on the Amanah catalogue on `hsbcamanah.com.my`. That host is in `official_domains`. |
| `sg-boc` | partial | Cards are in. The listings had no current card offers. Read the Treats, Rewards and Promotions listings again. If they still have no offer, report it, and the run is complete. |
| `sg-trust` | partial | Partner coupons are images or CMS data on hosts that are not official. Do not crawl those hosts. Report the hosts with the official page that links to them. |

## 6. Network offer sites (track C)

Follow section 7 of `crawler/COMPLETE_INSTRUCTION.md` and the Track C table in `crawler/FULL_CRAWL.md`.

1. C1 and C2, Mastercard Priceless for Malaysia and Singapore. `specials.priceless.com` is approved for real-Chrome mode. Use plain, then browser, then real Chrome with `--min-gap 30` if the site refuses the first two. Do the Malaysia run first. Stop after it, and continue to Singapore when the maintainer accepts it.
2. C3 and C4, JCB Malaysia and Singapore: run them again. Many published JCB offers have the eligibility quote "All members object". That text looks like a page label or script value, not a sentence of the offer. Quote the eligibility sentence of each offer exactly as the page shows it. If the page states no eligibility sentence, give null with the reason. Leave out offers for JCB cards issued in another country, and count them in the report.
3. C5 to C12: Visa, UnionPay, American Express and Diners Club for Malaysia and Singapore. Do one run for each row. A country offer host that is not in `official_domains` must be reported first, not crawled.

## 7. Census rechecks

The rechecks of 20 Nov 2026 are done (PRs 69, 70 and 71). They found three new issuers: `th-bangkok-bank`, `ph-pnb` and `id-permata`. These are now in `crawler/FULL_CRAWL.md` as 79, 80 and 81. One task is left:

1. Krung Thai Bank: probe `https://www.ktb.co.th/` with `--url --country TH`. The maintainer accepted `krungthai.com` on 20 Nov 2026, after the recheck ran. The probe follows the redirect, and `www.krungthai.com` is on the real-Chrome list.

The other banks stay `not_reached` after real Chrome: BDO (Akamai challenge), Chinabank, Security Bank, Citibank PH, Standard Chartered PH, UnionBank, Kasikornbank, SCB, BRI, BNI and Maybank Indonesia. Do not try them again until the maintainer says so.

## 8. Cards and offers for Hong Kong, Thailand, Indonesia and the Philippines

These issuers are in the repository from the census, with no cards and no offers. The maintainer accepted all of them and their `official_domains` on 20 Nov 2026. Do the issuers in the order of `crawler/FULL_CRAWL.md`, after tasks 1 to 6: Hong Kong 35 to 51, Thailand 52 to 62, Indonesia 63 to 72, Philippines 73 to 78, then 79 to 81. Pages that are not in English follow section 4 of `crawler/COMPLETE_INSTRUCTION.md`.

## 9. When to stop and ask

Stop and ask the maintainer when a task needs a host that is not official, a real-Chrome attempt on a host that is not on the approved list, a sign-in, a form, or a captcha. Record it in `run.blocked`, set the run aside, and continue with the next task.
