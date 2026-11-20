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

These offers are `needs_review` because the offer names a card that is not in the issuer's card file. Do a card run for the issuer and find each card on its official domains. Then do an offer run, so the ingest matches the offers again. Do not change the eligibility quote of an offer to make it match. Counts are from 20 Nov 2026.

| Issuer | Card names in the offers | Offers in review |
|---|---|---|
| `my-standard-chartered` | Priority Worldmiles Mastercard | 33 |
| `hk-ccb-asia` | CCB Long Credit Card; CCB (Asia) UnionPay Credit Card | 25 |
| `my-aeon-credit` | AEON Member Plus Visa Card; AEON Platinum Visa Card; AEON Platinum Mastercard | 8 |
| `hk-cmb-wing-lung` | World Card; Affinity Card; RMB Credit Card | 6 |
| `hk-icbc-asia` | ICBC SUP Credit Card; ICBC Wise Gold Credit Card; ICBC Wise Gold Dual Currency Credit Card | 5 |
| `hk-bea` | BEA GOAL Credit Card; Platinum card or above; Supplementary Card of BEA Credit Card | 5 |

A card can be for Priority or private banking clients only. It is still a card. Hand it in with the eligibility that the page states. If the issuer has no page for the card, or the page says that the card is no longer offered, report the card name and the page you checked. Do not make a card record without a page.

A debit card or a corporate card is not in scope. If an offer names only debit or corporate cards, leave it out of the run and count it in the report.

A phrase that names no card, such as `BEA Credit Cards`, means every card of the issuer. Use scope `issuer`. The gate refuses it as a card name.

## 3. Offers with crawler flags

Re-read the terms of these offers in the next full run of each issuer. Do not make a run for one flag.

| Issuer | Flag | Offers |
|---|---|---|
| `hk-dah-sing` | `eligibility_unclear` | 73 |
| `hk-bocom-hk` | `eligibility_unclear` | 32 |
| `sg-ocbc` | `date_conflict` | 29 |
| `my-hong-leong` | `amount_unclear` | 21 |
| `sg-ocbc` | `end_date_past_horizon` | 19 |
| `sg-maybank` | `end_date_past_horizon` | 18 |

1. `eligibility_unclear`: find the sentence in the terms that says which cards can use the offer. If it says all cards of the bank, use scope `issuer`. If it names cards, use scope `card`. Quote the sentence.
2. `date_conflict`: take the dates from the offer's own terms document. If the terms state a booking period and a stay or usage period, give both. Keep the flag only when the terms themselves state two different end dates for one offer, and quote both.
3. `end_date_past_horizon`: an end date more than 24 months ahead. Check that the date is the end of the offer and not a card fee date, a programme date or a rate change date.
4. `amount_unclear`: give the amount and the currency only when the quote states them. Otherwise give null with the reason.

## 4. Merchant names from the old data

These offers still have `merchant_name_source: legacy_title_parse`. In the next run of each issuer, read the name from the page heading, the listing tile or the terms document, as `crawler/RULES.md` section 3 says.

| Issuer | Offers |
|---|---|
| `sg-ocbc` | 74 |
| `my-uob` | 20 |
| `my-rhb` | 17 |
| `my-hong-leong` | 4 |
| `sg-icbc` | 3 |
| `my-standard-chartered` | 1 |

If the offer is no longer on the listing, do not hand it in. The ingest withdraws it after 14 days.

## 5. Issuers that are not covered or partly covered

Malaysia and Singapore: `my-bank-rakyat`, `my-icbc`, `my-hsbc`, `sg-boc` and `sg-trust` were done on 20 Nov 2026 (PRs 84 to 97). `my-icbc` has 2 cards and no offers. `sg-boc` and `sg-trust` stay `partial` with the reasons in their issuer records. `my-aeon-credit` was offline on 20 Nov 2026: run it again when the site answers.

## 6. Network offer sites (track C)

Done on 20 Nov 2026: JCB (C3, C4), UnionPay (C7, C8), American Express (C9, C10) and Diners Club (C11, C12, no Malaysia or Singapore listing). The JCB runs replaced the "All members object" text.

Still to do:

1. C1 and C2, Mastercard Priceless for Malaysia and Singapore. `specials.priceless.com` is approved for real-Chrome mode. Use plain, then browser, then real Chrome with `--min-gap 30` if the site refuses the first two. Do the Malaysia run first.
2. C5 and C6, Visa for Malaysia and Singapore. Start at `https://www.visa.com.my/` and `https://www.visa.com.sg/`. These hosts were in the published `networks.json` and are now in `config/networks.json` too. The runs of 20 Nov 2026 (PRs 76 and 77) stopped at the redirect from visa.com and found 0 offers. They were closed with no merge.

## 7. Census rechecks

The rechecks of 20 Nov 2026 are done (PRs 69, 70 and 71), including the Krung Thai Bank follow-up after the maintainer accepted `krungthai.com`. They found three new issuers: `th-bangkok-bank`, `ph-pnb` and `id-permata`. These are now in `crawler/FULL_CRAWL.md` as 79, 80 and 81. Krung Thai Bank is `same_group` with the existing issuer `th-ktc`: the official `krungthai.com` site presents consumer credit cards as KTC products and links to `ktc.co.th`, which was not crawled.

The other banks stay `not_reached` after real Chrome: BDO (Akamai challenge), Chinabank, Security Bank, Citibank PH, Standard Chartered PH, UnionBank, Kasikornbank, SCB, BRI, BNI and Maybank Indonesia. Do not try them again until the maintainer says so.

## 8. Cards and offers for Hong Kong, Thailand, Indonesia and the Philippines

The maintainer accepted all census issuers and their `official_domains` on 20 Nov 2026. Do the issuers in the order of `crawler/FULL_CRAWL.md`. Pages that are not in English follow section 4 of `crawler/COMPLETE_INSTRUCTION.md`.

Hong Kong: 10 issuers were done on 20 Nov 2026 (PRs 102 to 111). Still to do: `hk-citi`, `hk-cncbi`, `hk-standard-chartered`, `hk-hang-seng`, `hk-dbs`, `hk-hsbc` and `hk-bochk` (orders 45 to 51). Then Thailand 52 to 62, Indonesia 63 to 72, the Philippines 73 to 78, then 79 to 81.

## 9. When to stop and ask

Stop and ask the maintainer when a task needs a host that is not official, a real-Chrome attempt on a host that is not on the approved list, a sign-in, a form, or a captcha. Record it in `run.blocked`, set the run aside, and continue with the next task.
