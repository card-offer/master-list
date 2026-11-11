# Full crawl: Malaysia and Singapore

This file is the instruction for the crawler for the first full crawl. `crawler/RULES.md` is the rule for each fact. If the two files disagree, `crawler/RULES.md` is correct.

Copy all the text below the line and give it to Grok Bot.

---

You are the crawler for https://github.com/card-offer/master-list. This task is the first full crawl of Malaysia (MY) and Singapore (SG). The goal is: each credit card issuer, each of its cards, each of its offers, and each offer matched to the cards that can use it.

Do the four phases in order. Do not start a phase before the phase before it is accepted.

## Before you start

1. Pull the main branch. The head must be commit 7a090e9 or later.
2. Read `crawler/RULES.md` from the start to the end. Read `schema/observation.schema.json`.
3. Work on one branch for each pull request. Make each branch from the newest main.

## Rules for all phases

1. Use official sources only: the issuer's own hosts in `official_domains`, and in phase 1 the two regulator sites. Do not use aggregator, comparison, deal, review, blog or forum sites. Do not use search engine snippets as a source.
2. Read `robots.txt` on each host first. Do not fetch a disallowed path.
3. Public pages only. No sign-in, no sign-up, no form, no captcha bypass.
4. One request at a time for each host, with a minimum of 1.5 seconds between requests.
5. If the page does not state a value, write null. Do not estimate, and do not use your memory.
6. Do not make IDs. Do not edit files in the country folders or `merchants/registry.json` by hand. Only `pipeline/ingest.py` writes them. The one exception is `{cc}/issuers.json` in phase 1.
7. Do not commit anything under `raw/`. Do not merge a pull request.
8. If a rule is not clear, stop and ask. Do not guess.

## Phase 1: find all the issuers

The repository has 34 issuers now. They are in the table at the end of this file. The purpose of this phase is to make sure that no issuer is missing.

1. Read the regulator lists. These two sites are permitted in this phase only:
   1. Malaysia, Bank Negara Malaysia: the list "Credit Card Issuers" (banks and non-banks) and the list of charge card issuers, on bnm.gov.my.
   2. Singapore, Monetary Authority of Singapore: the Financial Institutions Directory on eservices.mas.gov.sg. Read the categories Local Bank, Qualifying Full Bank, Full Bank, Digital Full Bank, Wholesale Bank, and Credit and Charge Card Licensee.
2. For each entry on a regulator list, open the institution's own official site and find out if it issues a credit card or a charge card to consumers in that country.
3. Give each entry one result:
   - `in_repository`: it is one of the 34. Give the issuer ID.
   - `same_group`: its cards are sold on the site of an issuer in the repository (for example the Islamic bank of a group). Give the issuer ID. Its cards go under that issuer, with `islamic: true` where the page says so.
   - `new_issuer`: it issues consumer credit or charge cards and is not in the repository.
   - `no_consumer_card`: it has no consumer credit or charge card (for example debit cards only, or corporate cards only). Give the official URL that shows this.
   - `not_reached`: you could not read its site. Give the reason.
4. Check these names with special care. They are not in the repository, and earlier work did not settle them:
   - Malaysia: Paydee, Agrobank, MBSB Bank, Kuwait Finance House, Co-opbank Pertama, GXBank, AEON Bank, Boost Bank, Ryt Bank, KAF Digital Bank, Diners Club, American Express, Citibank, Bank of China, ICBC.
   - Singapore: Diners Club, Optal, WEX Finance, RHB, State Bank of India, ICICI Bank, Bank of East Asia, Trust Bank.
5. Write the result as a table in a new file `crawler/ISSUER_CENSUS.md`, one section for each country. Columns: regulator entry, regulator list, result, issuer ID, official URL that proves the result, date checked.
6. For each `new_issuer`, add a record to `{cc}/issuers.json` with `id` (`{cc}-{short-name}`), `name`, `legal_name` as the regulator writes it, `website`, `official_domains` (the hosts of its card and offer pages), empty `card_ids`, and `crawl.status` `not_covered`.
7. Run `python tools/validate.py .`, then open one pull request for phase 1. Stop. The maintainer decides each new issuer and each official domain.

Report for phase 1: the count of regulator entries for each country, the count for each result, and the list of `new_issuer` and `not_reached` entries.

## Phase 2: cards, one issuer at a time

Do this for each issuer in the order of the table, after phase 1 is merged. Phase 2 and phase 3 for one issuer go in the same hand-in file.

1. Find the issuer's complete list of credit and charge cards for consumers. Use the issuer's own card listing page. Check it against the site menu and the sitemap, so that a card that is not on the listing is not missed.
2. Include cards that are closed to new applications but are still shown, with status `no_new_applications`. Do not include debit cards, prepaid cards or corporate cards.
3. Hand in one record for each card in the `cards` list. Follow section 6 of `crawler/RULES.md`.
4. One card product is one record. If the page sells one product on two networks, hand in one card with two networks. If the issuer gives two product names, hand in two cards.
5. Count the cards on the listing page and count your records. Put both numbers in your report. If they are not equal, explain each difference.

## Phase 3: offers, and the cards that can use each offer

1. Find every place where the issuer shows offers: the promotions listing, each category listing, the merchant deals site, and offers that are only on a card's product page. Put each listing URL in `run.listing_urls`.
2. Read every page of each listing and every tile. Set `listing_complete` to true only if you did this. If you stopped early, keep it false and report how many offers you did not read.
3. Hand in one record for each offer. Follow sections 3, 4 and 5 of `crawler/RULES.md`. The merchant name is the most important field.
4. Match each offer to cards. Read the offer page and its terms, and choose one:
   - The page names cards: use scope `card`, and write each card name in `card_names` as the page writes it. Give the sentence in `quote`.
   - The page names a network (for example "all Visa cards of the bank"): use scope `issuer_network` with `network_ids`. Give the sentence in `quote`.
   - The page says all credit cards of the issuer: use scope `issuer`, confidence `stated`. Give the sentence in `quote`.
   - The page names no card and no network: use scope `issuer`, confidence `inferred`, with no card names. Do not guess which cards qualify.
5. If the page excludes cards (for example "not valid for corporate cards" or "excluding the X card"), keep the sentence in the eligibility quote and set the flag `eligibility_unclear`.
6. The ingest report lists each card name that did not match a card. For each one, look again:
   - If the card is real and you missed it in phase 2, add the card and run the ingest again.
   - If the page uses a short or old name for a card that you have, report it. Do not change the name to make it fit.
7. Do not hand in an offer whose end date is before the day of the run. Count the offers that you left out for this reason.

## Phase 4: gate, ingest and pull request, for each issuer

1. Write the file `raw/observations/{cc}/{issuer_id}/{run_id}.json`.
2. Run `python tools/check_observations.py <file>`. Correct each error line. Run it again until it gives exit code 0. Do not change a quote to make the gate pass.
3. Run `python pipeline/ingest.py <file>`.
4. Run `python tools/validate.py .` and `python -m unittest discover -s tests`.
5. Open one pull request for each issuer. Title: `data: {issuer_id} run {run_id} ({n} cards, {n} offers)`.
6. Send the hand-in file to the maintainer directly. It is private.
7. Do the next issuer on a new branch from main. Do not wait for the merge, but do not put two issuers in one pull request.

## When to stop and ask

1. A site blocks you, needs a sign-in, or shows a captcha: record it in `run.blocked`, set the issuer aside, and continue with the next issuer.
2. An official URL sends you to a host that is not in `official_domains`: record it as `off_domain_redirect` and report the host. Do not crawl it.
3. An issuer has more than 300 offers: do the cards and the first 300 offers, keep `listing_complete` false, and report the number that remains.
4. The gate refuses a fact that you think is correct: keep the fact out of the file and report the page and the sentence.
5. Three issuers in sequence fail for the same reason: stop and report.

## Report for each issuer

Give only these items:

1. Issuer ID, run ID and pull request URL.
2. Cards on the issuer's listing, and cards handed in.
3. Offers found, offers handed in, offers left out as expired, and offers not read.
4. The count for each merchant kind, and the count for each eligibility choice (cards named, network named, all cards stated, inferred).
5. Card names in offers that did not match a card.
6. Records in `needs_review`, with the reason.
7. Blocked URLs, with the reason.
8. The last line of the gate, of the validator and of the tests.

After the last issuer, give one table for all issuers with items 2, 3 and 4, and the list of issuers that are not complete.

## The issuers in the repository now

Do them in this order. The small ones are first, so that a problem shows early. The numbers are the records published before this crawl. They came from older scripts, so do not use them as a target.

### Singapore

| Order | Issuer ID | Name | Official domains | Cards now | Offers now | Note |
|---|---|---|---|---|---|---|
| 1 | `sg-cimb` | CIMB Singapore | cimb.com.sg, deals.cimb.com | 5 | 3 | Run 2 is in PR 7. Finish the deals site. |
| 2 | `sg-gxs` | GXS Bank | gxs.com.sg, cdn.prod.website-files.com | 1 | 4 | |
| 3 | `sg-maribank` | MariBank | maribank.sg, banking-aka-storage.maribank.com.sg | 1 | 3 | |
| 4 | `sg-trust` | Trust Bank | trust.com.sg | 0 | 0 | Not covered before. The site did not answer. |
| 5 | `sg-icbc` | ICBC Singapore | icbc.com.sg | 8 | 5 | |
| 6 | `sg-boc` | Bank of China Singapore | bankofchina.com | 9 | 0 | No offers were found before. |
| 7 | `sg-amex` | American Express Singapore | americanexpress.com | 7 | 4 | Singapore pages only. |
| 8 | `sg-citi` | Citibank Singapore | citibank.com.sg | 8 | 3 | Some offers are in the app only. Record them as blocked. |
| 9 | `sg-hsbc` | HSBC Singapore | hsbc.com.sg, cardpromotions.hsbc.com.sg | 7 | 19 | |
| 10 | `sg-dcs` | DCS Card Centre | dcscc.com, cards.dcscc.com, static.dcscc.com | 11 | 46 | |
| 11 | `sg-uob` | UOB | uob.com.sg | 15 | 4 | Coverage was thin before. |
| 12 | `sg-posb` | POSB | posb.com.sg, dbs.com.sg | 1 | 56 | POSB cards only. DBS cards go under `sg-dbs`. |
| 13 | `sg-dbs` | DBS Bank | dbs.com.sg | 8 | 68 | |
| 14 | `sg-maybank` | Maybank Singapore | maybank2u.com.sg, cardspromo.maybank2u.com.sg | 11 | 88 | |
| 15 | `sg-standard-chartered` | Standard Chartered Singapore | sc.com | 11 | 240 | Singapore pages only (sc.com/sg). |
| 16 | `sg-ocbc` | OCBC | ocbc.com | 11 | 450 | Terms are in popups on the listing. Use terms scope `listing_popup` and hash the full popup text. |

### Malaysia

| Order | Issuer ID | Name | Official domains | Cards now | Offers now | Note |
|---|---|---|---|---|---|---|
| 17 | `my-al-rajhi` | Al Rajhi Bank Malaysia | alrajhibank.com.my | 2 | 2 | |
| 18 | `my-bsn` | BSN | bsn.com.my | 4 | 6 | |
| 19 | `my-bank-rakyat` | Bank Rakyat | bankrakyat.com.my | 0 | 0 | Not covered before. The card menu needs JavaScript. |
| 20 | `my-ocbc` | OCBC Malaysia | ocbc.com.my | 6 | 8 | |
| 21 | `my-aeon-credit` | AEON Credit Service | myaeoncredit.com.my | 9 | 5 | |
| 22 | `my-alliance` | Alliance Bank | alliancebank.com.my | 6 | 13 | |
| 23 | `my-bank-islam` | Bank Islam | bankislam.com | 9 | 12 | |
| 24 | `my-muamalat` | Bank Muamalat | muamalat.com.my | 8 | 18 | |
| 25 | `my-hong-leong` | Hong Leong Bank | hlb.com.my | 9 | 14 | |
| 26 | `my-affin` | Affin Bank | affinalways.com | 4 | 30 | |
| 27 | `my-cimb` | CIMB Bank | cimb.com.my | 17 | 15 | If the deals are on deals.cimb.com, report it. The host is not in this issuer's domains. |
| 28 | `my-public-bank` | Public Bank | pbebank.com | 16 | 18 | |
| 29 | `my-uob` | UOB Malaysia | uob.com.my | 7 | 57 | |
| 30 | `my-hsbc` | HSBC Malaysia | hsbc.com.my, sp.hsbc.com.my | 6 | 69 | |
| 31 | `my-ambank` | AmBank | ambank.com.my | 35 | 8 | 35 cards is high. Check for the same card under two names. |
| 32 | `my-standard-chartered` | Standard Chartered Malaysia | sc.com, av.sc.com | 3 | 101 | Malaysia pages only (sc.com/my). |
| 33 | `my-rhb` | RHB Bank | rhbgroup.com | 12 | 166 | |
| 34 | `my-maybank` | Maybank | maybank2u.com.my | 33 | 0 | The site did not answer before. If it fails, record it and continue. |

New issuers from phase 1 go after number 34, after the maintainer accepts them.
