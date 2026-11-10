# card-offer master-list: build report (MY + SG)

Built 9 Nov 2026 (MYT); offers rebuilt 10 Nov 2026 00:05 MYT with the end-date rule and own-T&C capture (schema 0.2.0). Output: `/workspace/cc-master/master-list/` (publish-ready tree). Nothing was created on GitHub, pushed or deployed. No one was contacted.

## 0. Source sweep, 10 Nov 2026 (supersedes the counts in sections 2 and 3)

- Worksheet: worksheet/sources.csv (156 rows: 126 done, 30 blocked, 0 to do). Summary and blocked list: worksheet/sources.md.
- Credit card issuers: MY 18 (AEON Credit, Affin, Al Rajhi, Alliance, AmBank, BSN, Bank Islam, Bank Rakyat, CIMB, HSBC, Hong Leong, Maybank, Muamalat, OCBC, Public Bank, RHB, Standard Chartered, UOB). SG 16 (Amex, BOC, CIMB, Citi, DBS, DCS, GXS, HSBC, ICBC, MariBank, Maybank, OCBC, POSB, Standard Chartered, Trust, UOB).
- Not issuers (debit only on official site): MBSB, GXBank, AEON Bank, KFH MY. Unconfirmed (site unreachable or no MY catalogue): Agrobank, Amex MY, Citibank MY, Co-opbank Pertama, Diners Club MY.
- Published after the sweep and the hub T&C fix: 1535 offers (MY 542, SG 993), 300 cards (MY 186, SG 114), 1065 merchants; validate.py 0 errors.
- Sweep added 21 cards and 1460 offers; 78 sweep offers held back (no end date). publish.py totals: 110 held back (no end date), 16 dropped as expired. Held-back list: raw/held_back.json.
- Network portals: Visa MY/SG (15 each) and JCB MY (9) / SG (4) offer links saved in raw/network_offers/ only; the schema has no slot for network-level offers. Mastercard (403), Priceless and UnionPay (JavaScript search UI) blocked.
- Sweep code: scripts/sources/ (adapters.py, offerlib.py, merge_extra.py, write_md.py). publish.py, schema/ and validate.py unchanged.
- Note: publish.py was run once outside .build.lock (a mistaken --help check); every later run used the lock.

| issuer | before | after |
|---|---|---|
| my-aeon-credit | 2 | 5 |
| my-affin | 0 | 30 |
| my-al-rajhi | 2 | 2 |
| my-alliance | 12 | 13 |
| my-ambank | 10 | 8 |
| my-bank-islam | 0 | 12 |
| my-bsn | 0 | 6 |
| my-cimb | 8 | 15 |
| my-hong-leong | 15 | 14 |
| my-hsbc | 0 | 69 |
| my-maybank | 56 | 0 |
| my-muamalat | 0 | 18 |
| my-ocbc | 0 | 8 |
| my-public-bank | 25 | 18 |
| my-rhb | 0 | 166 |
| my-standard-chartered | 5 | 101 |
| my-uob | 49 | 57 |
| sg-amex | 0 | 4 |
| sg-cimb | 2 | 3 |
| sg-citi | 7 | 3 |
| sg-dbs | 11 | 68 |
| sg-dcs | 0 | 46 |
| sg-gxs | 0 | 4 |
| sg-hsbc | 1 | 19 |
| sg-icbc | 0 | 5 |
| sg-maribank | 0 | 3 |
| sg-maybank | 0 | 88 |
| sg-ocbc | 0 | 450 |
| sg-posb | 0 | 56 |
| sg-standard-chartered | 10 | 240 |
| sg-uob | 2 | 4 |

Maybank MY 56 to 0: the main pipeline holds all 56 back for no end date (section 2). The correct listing (promotions/maybank_cards.page) cannot be reached from the crawl box.

Blockers needing Wilson: Maybank MY unreachable from the box; Trust SG connection closed; Bank Rakyat card menu is JavaScript-only; Mastercard 403; Priceless and UnionPay JavaScript only; Citi SG World Privileges app-only; Agrobank, Citibank MY, Diners MY, Co-opbank unreachable; a schema slot is needed for network-level offers.

### Hub T&C fix (10 Nov 2026)

Offers whose terms_url pointed at a promotions hub instead of the deal's own T&C were re-checked deal by deal (scripts/sources/fix_hub_terms.py, log raw/hubfix/report.json, summary raw/hubfix/summary.json).

- RHB MY (139 offers on https://www.rhbgroup.com/cards/promotions-privileges/index.html): each tile popup links its own T&C PDF. 135 now carry that PDF as terms_url with clauses, hash and fetched_at; dates come from the PDF's PROMOTION PERIOD clause (all 135 end dates matched the tile; 119 start dates now stated from the PDF). 4 tiles (Yen @ W, Nobu, Graze @ Hilton, Experian) have no T&C link: terms_url null (no_deal_specific_terms_link_on_page), dates from the popup text. 12 multi-promotion tiles got their merchant name back in the title. None dropped.
- OCBC SG (466 offers on https://www.ocbc.com/personal-banking/cards/card-promotion): deals have no page or T&C document of their own; the T&C exists only as a popup on the hub. terms_url is null (no_deal_specific_terms_link_on_page) and the hub stays as source_url. End dates are read only from each deal's own "Valid from / Valid till" sentence; the listing JSON display window is no longer used. 450 kept, 4 end dates corrected (Four Seasons festive takeaway 25 Dec to 30 Nov 2026, Sofitel Racines 26 Dec to 31 Dec 2026, Sofitel festive goodies 25 Dec to 22 Dec 2026, Agoda flights 30 Sep 2027 to 31 Dec 2026), 16 held back because the deal text states no end date (Sinopec, VOYAGE benefits, Global Blue, Marina Bay Sands, SeniorCare and medical partners, Westin festive buffets).
- The 2026-12-31 (145) and 2026-12-30 (120) OCBC end dates are each stated in that deal's own popup text; they are not a blanket hub date.


## 1. Sourcing

- Sources are official issuer pages only, plus issuer promotion pages.
- Each card and offer records `sources[].url`, `fetched_at` and `last_checked`.
- No third-party aggregator data is used.
- Fetching:
  - Direct fetches use a polite crawler: one host at a time, with a 1.5 s delay between requests, and responses cached under `raw/cache/`.
  - Maybank MY and Maybank SG time out from this network. Their listing and promotion pages were read with a web fetcher and transcribed into `raw/manual/`, with the source URL recorded.
- Em dashes in quoted page text are replaced with " - ".
- Offer dates, minimum spend, cap and T&C clauses come only from the deal's own T&C or deal page; the bank's general terms are never used.

## 2. Counts

| | MY | SG | Total |
|---|---|---|---|
| Issuers | 18 | 12 | 30 |
| Cards | 186 | 93 | 279 |
| Offers published | 80 | 11 | 91 |
| Offers held back (no end date) | 92 | 18 | 110 |
| Offers dropped (expired per own T&C) | 12 | 4 | 16 |
| Merchants | 36 | 1 | 37 |

Before this run 217 offers were published (184 MY, 33 SG), 143 of them with no end date.

### Cards per issuer

**MY**

| Issuer | Cards |
|---|---|
| AmBank | 35 |
| Maybank | 33 |
| CIMB | 17 |
| Public Bank | 16 |
| RHB | 12 |
| Hong Leong | 9 |
| AEON Credit | 9 |
| Bank Islam | 9 |
| Muamalat | 8 |
| UOB | 7 |
| OCBC | 6 |
| HSBC | 6 |
| Alliance | 6 |
| Affin | 4 |
| BSN | 4 |
| Standard Chartered | 3 |
| Al Rajhi | 2 |
| Bank Rakyat | 0 |

**SG**

| Issuer | Cards |
|---|---|
| UOB | 15 |
| OCBC | 11 |
| Standard Chartered | 11 |
| Maybank | 11 |
| BOC | 9 |
| DBS | 8 |
| Citi | 8 |
| HSBC | 7 |
| Amex | 7 |
| CIMB | 5 |
| POSB | 1 |
| Trust | 0 |

### Cards per network

A card on two networks counts in both.

| Network | MY | SG |
|---|---|---|
| Visa | 92 | 19 |
| Mastercard | 55 | 9 |
| Amex | 6 | 8 |
| UnionPay | 1 | 1 |
| Unconfirmed | 32 | 56 |

### Other card counts

- **Islamic cards:** 53 (MY).
- **Income requirement found:** MY 114, SG 34.
- **Annual fee found:** MY 84, SG 42.

### Card structure (schema 0.2.0)

- Benefits are merged to one entry per benefit type (`texts[]` keeps every distinct verbatim line). Heading-only lines such as "Lounge Access" are dropped. 2,079 raw lines became 642 entries.
- Fill rates over 279 cards:

| Field | Filled |
|---|---|
| annual_fee.amount (number; 0 when the page says no annual fee) | 123 (44%) |
| annual_fee.waiver_rules | 142 (50%) |
| min_income.amount and period | 148 (53%) |
| earn_rates (numeric rate per spend category) | 178 (63%); 131 with a named category |
| lounge entries | 90 cards: programmes 75, visits 43, guest_policy_text 13, supplementary_share_visits stated 5 (null on the rest, as the pages do not say) |

### Card benefit types (both countries)

| Benefit type | Cards |
|---|---|
| Annual fee waiver | 137 |
| Points | 113 |
| Cashback | 105 |
| Travel insurance | 92 |
| Lounge access | 91 |
| Fuel | 37 |
| Miles | 37 |
| Golf | 36 |
| Instalment | 19 |
| Dining | 12 |

- Lounge entries carry programme (Priority Pass, LoungeKey, DragonPass, Plaza Premium, Mastercard Travel Pass), visit count, guest mention and minimum spend text when stated.

### Offers

Every published offer has an `end_date` read from the deal's own T&C document or deal page, with `dates_text` (verbatim) and `dates_source_url`. Offers with no stated end date are held back (see "Offers held back: no end date").

**Field fill rates (91 published offers)**

| Field | Filled |
|---|---|
| end_date | 91 (100%) |
| start_date | 77 (84%); the other 14 have `start_date_null_reason: not_stated_in_terms_or_page` (for example "from now until 31 December 2026") |
| dates_source_url | 91 (100%): 34 from a T&C document, 57 from the deal page (including its printed T&C section) |
| terms_url, terms_clauses, terms_hash, terms_fetched_at | 60 (66%): 35 deal T&C documents, 25 T&C sections printed on the deal page |
| terms_url null with reason | 31 (`no_deal_specific_terms_link_on_page`) |
| min_spend_text | 53 (58%) |
| cap_text | 21 (23%) |

**MY offers per issuer (published)**

| Issuer | Offers |
|---|---|
| UOB | 34 |
| Public Bank | 16 |
| CIMB | 8 |
| Alliance | 7 |
| AmBank | 6 |
| Hong Leong | 4 |
| AEON | 2 |
| Al Rajhi | 2 |
| Standard Chartered | 1 |
| Maybank | 0 (56 held back) |

**SG offers per issuer (published)**

| Issuer | Before | Now |
|---|---|---|
| Citi | 7 | 3 |
| DBS | 11 | 3 |
| CIMB | 2 | 2 |
| UOB | 2 | 1 |
| Standard Chartered | 10 | 1 |
| HSBC | 1 | 1 |
| OCBC, POSB, Maybank, Amex, BOC | 0 | 0 |

### Offer eligibility rule

1. **card:** the official page names specific cards (confidence: stated).
2. **issuer_network:** the page restricts the offer to the issuer's cards on a named network (confidence: stated or inferred).
3. **issuer:** no restriction was found, so the offer is assumed to apply to all of the issuer's credit cards (confidence: assumed).

`eligible_card_ids` holds the expanded list.

## 3. Gaps

### Issuers not covered or partial

- **Not covered:**
  - Bank Rakyat MY: card pages and the product disclosure sheet return 404.
  - Trust SG: the site times out or returns 500.
- **Partial cards:**
  - Affin and BSN: the listing pages are JavaScript-only, so only known pages are used.
  - RHB: Islamic variants come from the listing page only.
  - HLB Opus: the page is blocked, so the name is unverified.
  - POSB: 1 card.
  - Amex SG: card pages only.
- **No offers captured:**
  - MY: RHB, OCBC, HSBC, Affin, BSN, Bank Islam, Muamalat.
  - SG: OCBC, POSB, Maybank, Amex, BOC.
  - Causes: JavaScript-rendered promotion hubs, 0 candidates found, or 404.

### Network offer portals

Not captured:

- Visa: the offers site is a JavaScript single-page app with no static data.
- Mastercard Priceless: returns 403.
- Amex SG offers: returns 404.
- UnionPay and JCB: not crawled.

### Field gaps

- **Unconfirmed network:** 88 cards (32 MY, 56 SG).
  - Fix: one curated override per card, from the product disclosure sheet.
- **Tier:** null where the card name has no tier word (about 100 cards).
- **Offers:**
  - 110 offers held back for no end date. Causes:
    - Maybank MY (56): maybank2u.com.my refuses this network (curl timeout, Playwright `ERR_HTTP2_PROTOCOL_ERROR`). The listing was read once with a web fetcher, but it carries no per-deal links, so no T&C or dates can be read.
    - Multi-deal hub pages (15: UOB MY region and category pages, HLB card offers, DBS Vantage deals): the dates belong to the individual deals. The single-deal pages are captured separately where the crawler found them.
    - No deal-specific T&C link and no end date on the page (34): Public Bank merchant privileges whose only T&C link is the general online banking terms, SC MY privilege hubs (only the consumer banking T&C is linked), DBS SG pages whose T&C is behind a JavaScript drawer, Citi rewards redemption programmes (ongoing).
    - Deal T&C found but it states no end date (5): ongoing programmes such as 0% instalment plans and wallet T&Cs.
  - 16 offers dropped because their own T&C dates have passed (mostly HLB 2024 and 2025 campaigns and SC SG 2018 to 2020 pages that are still online; also one AmBank, one Alliance and one HLB campaign that ended in 2026).
  - Merchant is missing for most SG offers.
  - Benefit value is only partly parsed (the 'other' benefit type).
- **SG offer coverage is thin:** 11 published offers. OCBC, POSB, Maybank SG, Amex SG and BOC hubs still have no adapter in this run (a parallel worker owns new issuer adapters).
- **Known extraction noise:** a few offer categories come from keywords. Treat `category` as a hint. One UOB MY item ("UOB Credit Cards") comes from the card listing page's campaign tile.

<!-- held-back:start -->
## Offers held back: no end date

110 offers are not published because no end date is written in the deal's own T&C or on its page. They stay in `raw/offers_built.json` and are re-checked on every run.

By cause:

- 56: listing only, no per-deal page or T&C reachable
- 34: no deal-specific T&C link and no end date on the deal page
- 15: multi-deal hub page: dates belong to individual deals, not to this listing
- 5: no end date stated in the deal T&C or page

| ID | Issuer | Title | T&C URL | Why held |
|---|---|---|---|---|
| `my-alliance-discover-korea-in-style-exclusive-offers-on-iconic-attractions` | my-alliance | Discover Korea in Style, Exclusive Offers On Iconic Attractions | none on page | no deal-specific T&C link and no end date on the deal page |
| `my-alliance-enjoy-0-instalment-payment-plans` | my-alliance | Enjoy 0% Instalment Payment plans! | https://www.alliancebank.com.my/Alliance/media/documents/Promotion/pine-labs-instant-discount-campaign-tc.pdf | no end date stated in the deal T&C or page |
| `my-alliance-enjoy-15-off-travel-privileges-and-up-to-rm15-off-dining-and-shopping-o` | my-alliance | Enjoy 15% OFF* Travel Privileges & Up to RM15 OFF* Dining and Shopping Offers | none on page | no deal-specific T&C link and no end date on the deal page |
| `my-alliance-link-spend-and-win-plaza-premium-lounge-access-and-smart-traveller-poin` | my-alliance | Link, Spend & Win Plaza Premium Lounge Access and Smart Traveller Points Campaign | none on page | no deal-specific T&C link and no end date on the deal page |
| `my-ambank-ambank-and-ambank-islamic-visa-golf-privileges` | my-ambank | AmBank and AmBank Islamic Visa Golf Privileges | https://www.ambank.com.my/docs/ambankretaillibraries/terms-and-conditions/ambankvisagolfprivilegestnc_till-31dec26-eng.pdf?sfvrsn=f8753764_5 | no end date stated in the deal T&C or page |
| `my-ambank-elevate-your-wellness-journey-with-ambank-cards-i` | my-ambank | Elevate Your Wellness Journey with AmBank Cards/-i! | none on page | no deal-specific T&C link and no end date on the deal page |
| `my-ambank-promotion-amonlinetravelinsurance` | my-ambank | Promotion: AmOnlineTravelInsurance | none on page | no deal-specific T&C link and no end date on the deal page |
| `my-hong-leong-treat-yourself-to-our-exclusive-hlb-partners` | my-hong-leong | Treat yourself to our exclusive HLB Partners | none on page | multi-deal hub page: dates belong to individual deals, not to this listing |
| `my-maybank-0-ezypay-on-aura-diamonds-and-gemstones-sms-deen-jewellers` | my-maybank | 0% EzyPay on Aura Diamonds & Gemstones, SMS Deen Jewellers | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-10-off-at-berjaya-times-square-theme-park` | my-maybank | 10% OFF at Berjaya Times Square Theme Park | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-10-off-at-kedai-kopitiam-lepak-sama-nanyang-cafe` | my-maybank | 10% OFF at Kedai Kopitiam Lepak Sama Nanyang Cafe | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-10-off-at-nikusutei-japanese-muslim-restaurant` | my-maybank | 10% OFF at Nikusutei Japanese Muslim Restaurant | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-10-off-food-and-beverages-at-avi-pangkor-beach-resort` | my-maybank | 10% OFF food and beverages at AVI Pangkor Beach Resort | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-10-off-food-and-beverages-at-avillion-admiral-cove` | my-maybank | 10% OFF food and beverages at Avillion Admiral Cove | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-10-off-food-and-beverages-at-avillion-cameron-highlands` | my-maybank | 10% OFF food and beverages at Avillion Cameron Highlands | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-10-off-food-and-beverages-at-avillion-port-dickson` | my-maybank | 10% OFF food and beverages at Avillion Port Dickson | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-15-off-at-five-senses-experience-suites` | my-maybank | 15% OFF at Five Senses Experience Suites | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-15-off-at-the-emperor-at-dorsett-grand-subang` | my-maybank | 15% OFF at The Emperor at Dorsett Grand Subang | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-25-off-at-arabian-oud-malaysia` | my-maybank | 25% OFF at Arabian Oud Malaysia | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-buy-two-get-one-complimentary-item-at-sibling-s-gelato` | my-maybank | Buy Two, get One Complimentary Item at Sibling's Gelato | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-complimentary-1-set-handmade-pork-ball-at-two-pesos` | my-maybank | Complimentary 1 set Handmade Pork Ball at Two Pesos | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-complimentary-2-scrunchies-at-emma-fashion-wardrobe` | my-maybank | Complimentary 2 Scrunchies at Emma Fashion Wardrobe | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-complimentary-2x-blue-mountain-coffee-at-rich-kopitiam` | my-maybank | Complimentary 2x Blue Mountain Coffee at Rich Kopitiam | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-complimentary-coffee-at-twenty-two-bakery` | my-maybank | Complimentary coffee at Twenty-Two Bakery | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-complimentary-dessert-at-cili-kampung` | my-maybank | Complimentary Dessert at Cili Kampung | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-complimentary-drinks-at-shanghai-food-centre` | my-maybank | Complimentary Drinks at Shanghai Food Centre | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-complimentary-gift-and-special-offers-at-sk-jewellery` | my-maybank | Complimentary Gift & Special Offers at SK Jewellery | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-complimentary-hair-treatment-at-rambutkl` | my-maybank | Complimentary Hair Treatment at RAMBUTKL | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-complimentary-ice-cream-at-jm-bariani-house` | my-maybank | Complimentary Ice Cream at JM Bariani House | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-complimentary-shopping-vouchers-at-mitsui-outlet-park-klia-sepang-and-mi` | my-maybank | Complimentary Shopping Vouchers at Mitsui Outlet Park KLIA Sepang & Mitsui Shopping Park LaLaport BBCC | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-complimentary-signature-potato-salad-at-agrain` | my-maybank | Complimentary Signature Potato Salad at Agrain | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-complimentary-twg-tea-macarons-in-singapore` | my-maybank | Complimentary TWG Tea Macarons in Singapore | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-complimentary-wax-and-coating-at-auto-colourlab` | my-maybank | Complimentary Wax & Coating at Auto Colourlab | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-face-gym-massage-at-verthys-the-beauty-aesthetic` | my-maybank | Face Gym Massage at Verthys The Beauty Aesthetic | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-lunch-deals-from-rm15-with-maybank-mastercard` | my-maybank | Lunch Deals from RM15 with Maybank Mastercard | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-maybank-card-exclusives-at-mandai-rainforest-resort` | my-maybank | Maybank Card Exclusives at Mandai Rainforest Resort | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-maybank-cards-dining-deals-at-ting-shan-cuisine-tuah-1895` | my-maybank | Maybank Cards Dining Deals at Ting Shan Cuisine TUAH 1895 | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-medical-benefits-at-top-medical-centres-in-malaysia` | my-maybank | Medical Benefits at top Medical Centres in Malaysia | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-rebate-rm20-at-rock-road-seafood-restaurant` | my-maybank | Rebate RM20 at Rock Road Seafood Restaurant | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-rm10-off-at-jom-burger` | my-maybank | RM10 OFF at Jom Burger | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-rm15-lunch-deals-at-pezzo-pizza` | my-maybank | RM15 Lunch Deals at Pezzo Pizza | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-rm15-lunch-deals-at-sugarbun` | my-maybank | RM15 Lunch Deals at SugarBun | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-rm199-off-at-iconic-lab` | my-maybank | RM199 OFF at Iconic Lab | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-rm2-off-at-miyakori-coffee` | my-maybank | RM2 OFF at Miyakori Coffee | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-rm20-off-at-a-and-co-hair-salon` | my-maybank | RM20 OFF at A&CO Hair Salon | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-rm20-off-at-colour-room-by-apt` | my-maybank | RM20 OFF at Colour Room by APT | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-rm25-instant-rebate-at-sukka-perfumes` | my-maybank | RM25 Instant Rebate at Sukka Perfumes | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-rm3-for-waffle-at-coolblog` | my-maybank | RM3 for Waffle at CoolBlog | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-rm30-off-at-servauto` | my-maybank | RM30 OFF at ServAuto | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-rm5-off-selected-treatments-at-klinik-ourcare` | my-maybank | RM5 OFF selected treatments at Klinik Ourcare | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-special-deals-at-furama-bukit-bintang` | my-maybank | Special Deals at Furama Bukit Bintang | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-special-deals-at-harvey-norman` | my-maybank | Special Deals at Harvey Norman | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-special-deals-at-ipoh-specialist-hospital` | my-maybank | Special Deals at Ipoh Specialist Hospital | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-special-deals-at-jom-cuci-kereta` | my-maybank | Special Deals at Jom Cuci Kereta | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-special-deals-at-klinik-pergigian-dental-republik` | my-maybank | Special Deals at Klinik Pergigian Dental Republik | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-special-deals-at-love-and-co` | my-maybank | Special Deals at Love & Co | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-special-deals-at-naz-iphone` | my-maybank | Special Deals at Naz iPhone | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-special-deals-at-ohana-bar-ipoh` | my-maybank | Special Deals at Ohana Bar Ipoh | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-special-deals-at-shin-shiki` | my-maybank | Special Deals at Shin Shiki | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-special-deals-at-tenaga-solar-jaya-borneo` | my-maybank | Special Deals at Tenaga Solar Jaya Borneo | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-special-deals-at-tenaga-solar-jaya-maju` | my-maybank | Special Deals at Tenaga Solar Jaya Maju | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-special-offers-at-world-of-feng-shui` | my-maybank | Special Offers at World of Feng Shui | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-spend-globally-and-stand-to-win-travel-rewards-worth-up-to-rm20-000` | my-maybank | Spend Globally & Stand to Win Travel Rewards Worth Up to RM20,000 | none on page | listing only, no per-deal page or T&C reachable |
| `my-maybank-up-to-rm200-rebate-on-vivo-smartphones` | my-maybank | Up to RM200 Rebate on vivo Smartphones | none on page | listing only, no per-deal page or T&C reachable |
| `my-public-bank-0-balance-transfer-with-pb-visa-credit-cards` | my-public-bank | 0% Balance Transfer with PB Visa Credit Cards | none on page | no deal-specific T&C link and no end date on the deal page |
| `my-public-bank-pb-mastercard-privileges-agoda-s-year-round-offer` | my-public-bank | PB Mastercard Privileges: Agoda's Year Round Offer | none on page | no deal-specific T&C link and no end date on the deal page |
| `my-public-bank-pb-mastercard-privileges-alipay` | my-public-bank | PB Mastercard Privileges @ Alipay | https://www.pbebank.com/media/ixjfbidg/tc_alipay-rmb30.pdf | no end date stated in the deal T&C or page |
| `my-public-bank-pb-mastercard-privileges-priceless-specials-with-all-pb-and-pib-plat` | my-public-bank | PB Mastercard Privileges: Priceless Specials with all PB & PIB Platinum Mastercard Credit Cards/-i and Debit Cards | none on page | no deal-specific T&C link and no end date on the deal page |
| `my-public-bank-pb-mastercard-privileges-southeast-asia-golf-programme` | my-public-bank | PB Mastercard Privileges: Southeast Asia Golf Programme | none on page | no deal-specific T&C link and no end date on the deal page |
| `my-public-bank-pb-privileges-rm100-off-on-mhflypass-purchase-with-journify` | my-public-bank | PB Privileges: RM100 OFF on MHflypass purchase with Journify | none on page | no deal-specific T&C link and no end date on the deal page |
| `my-public-bank-pb-visa-infinite-privileges-infinite-tastes-beyond-the-menu` | my-public-bank | PB Visa Infinite Privileges: Infinite Tastes Beyond The Menu | none on page | no deal-specific T&C link and no end date on the deal page |
| `my-public-bank-pb-visa-privileges-relaxing-getaway-with-agoda` | my-public-bank | PB Visa Privileges: Relaxing Getaway with Agoda | none on page | no deal-specific T&C link and no end date on the deal page |
| `my-public-bank-zero-interest-instalment-plan-ziip-zero-profit-instalment-plan-zpip-` | my-public-bank | Zero Interest Instalment Plan (ZIIP)/Zero Profit Instalment Plan (ZPIP) Programme | https://www.pbebank.com/media/4ejp40mo/tc_ziip-zmfip.pdf | no end date stated in the deal T&C or page |
| `my-standard-chartered-0-easy-payment-scheme` | my-standard-chartered | 0% Easy Payment Scheme | none on page | no deal-specific T&C link and no end date on the deal page |
| `my-standard-chartered-health-and-wellness` | my-standard-chartered | Health & Wellness | none on page | no deal-specific T&C link and no end date on the deal page |
| `my-standard-chartered-the-good-life-privileges` | my-standard-chartered | The Good Life Privileges | none on page | no deal-specific T&C link and no end date on the deal page |
| `my-standard-chartered-travel-perks` | my-standard-chartered | Travel Perks | none on page | no deal-specific T&C link and no end date on the deal page |
| `my-uob-15-off-on-selected-treatments-at-bangkok-life-hub` | my-uob | 15% off on selected treatments at Bangkok LIFE Hub | none on page | no deal-specific T&C link and no end date on the deal page |
| `my-uob-complimentary-items-and-instant-rebate-deals` | my-uob | Complimentary Items & Instant Rebate Deals | none on page | multi-deal hub page: dates belong to individual deals, not to this listing |
| `my-uob-deals-you-will-love-in-east-malaysia-and-other-states` | my-uob | Deals you will love in East Malaysia and other states | none on page | multi-deal hub page: dates belong to individual deals, not to this listing |
| `my-uob-deals-you-will-love-in-johor-bahru` | my-uob | Deals you will love in Johor Bahru | none on page | multi-deal hub page: dates belong to individual deals, not to this listing |
| `my-uob-deals-you-will-love-in-kuala-lumpur` | my-uob | Deals you will love in Kuala Lumpur | none on page | multi-deal hub page: dates belong to individual deals, not to this listing |
| `my-uob-deals-you-will-love-in-penang` | my-uob | Deals you will love in Penang | none on page | multi-deal hub page: dates belong to individual deals, not to this listing |
| `my-uob-deals-you-will-love-worldwide` | my-uob | Deals you will love Worldwide | none on page | multi-deal hub page: dates belong to individual deals, not to this listing |
| `my-uob-exclusive-deals-on-home-improvement-and-car-services` | my-uob | Exclusive Deals on Home Improvement & Car Services | none on page | multi-deal hub page: dates belong to individual deals, not to this listing |
| `my-uob-exclusive-promotions-on-fashion-gadgets-and-lifestyle-items` | my-uob | Exclusive Promotions on Fashion, Gadgets & Lifestyle Items | none on page | multi-deal hub page: dates belong to individual deals, not to this listing |
| `my-uob-exclusive-travel-offers-hotels-flights-and-more` | my-uob | Exclusive Travel Offers: Hotels, Flights & More | none on page | multi-deal hub page: dates belong to individual deals, not to this listing |
| `my-uob-japanese-dining-deals` | my-uob | Japanese Dining Deals | none on page | no deal-specific T&C link and no end date on the deal page |
| `my-uob-under-10-and-above-deals` | my-uob | Under 10% and above deals | none on page | multi-deal hub page: dates belong to individual deals, not to this listing |
| `my-uob-uob-cards-deals-and-offers` | my-uob | UOB Cards Deals and Offers | none on page | no deal-specific T&C link and no end date on the deal page |
| `my-uob-up-to-50-off-dining-offers` | my-uob | Up to 50% off Dining Offers | none on page | multi-deal hub page: dates belong to individual deals, not to this listing |
| `my-uob-wellness-within-reach-exclusive-lifestyle-offers` | my-uob | Wellness Within Reach: Exclusive Lifestyle Offers | none on page | multi-deal hub page: dates belong to individual deals, not to this listing |
| `sg-citi-big-rewards` | sg-citi | BIG Rewards | none on page | no deal-specific T&C link and no end date on the deal page |
| `sg-citi-cash-rebate` | sg-citi | Cash Rebate | none on page | no deal-specific T&C link and no end date on the deal page |
| `sg-citi-citi-credit-card-petrol-savings-deals-for-you` | sg-citi | Citi Credit Card Petrol Savings Deals for You | none on page | no deal-specific T&C link and no end date on the deal page |
| `sg-citi-redeem-your-apple-products-with-your-points-miles` | sg-citi | Redeem your Apple Products with your Points / Miles | none on page | no deal-specific T&C link and no end date on the deal page |
| `sg-dbs-dbs-half-priced-holidays` | sg-dbs | DBS Half-priced Holidays | none on page | no deal-specific T&C link and no end date on the deal page |
| `sg-dbs-eat-your-way-to-deals` | sg-dbs | Eat your way to deals | none on page | no deal-specific T&C link and no end date on the deal page |
| `sg-dbs-enjoy-10-off-dine-shop-and-wellness-at-capitol-singapore` | sg-dbs | Enjoy 10% off dine, shop & wellness at Capitol Singapore | none on page | no deal-specific T&C link and no end date on the deal page |
| `sg-dbs-exclusive-offers-for-dbs-altitude-visa-signature-card` | sg-dbs | Exclusive Offers for DBS Altitude Visa Signature Card | none on page | no deal-specific T&C link and no end date on the deal page |
| `sg-dbs-exclusive-offers-for-dbs-vantage-and-dbs-insignia-card` | sg-dbs | Exclusive Offers for DBS Vantage and DBS Insignia Card | none on page | multi-deal hub page: dates belong to individual deals, not to this listing |
| `sg-dbs-healthcare-for-you` | sg-dbs | Healthcare For You | none on page | no deal-specific T&C link and no end date on the deal page |
| `sg-dbs-unlock-s-80-off-and-more-on-your-purchases` | sg-dbs | Unlock S$80 off and more on your purchases | none on page | no deal-specific T&C link and no end date on the deal page |
| `sg-dbs-unlock-up-to-s-100-off-your-shopping-spree` | sg-dbs | Unlock up to S$100 off your shopping spree​ | none on page | no deal-specific T&C link and no end date on the deal page |
| `sg-standard-chartered-credit-card-balance-transfer` | sg-standard-chartered | Credit Card Balance Transfer | https://www.sc.com/content/dam/sc/sg/en/documents/sg-funds-transfer-programme-product-tnc.pdf | no end date stated in the deal T&C or page |
| `sg-standard-chartered-google-pay-lucky-draw-page-new` | sg-standard-chartered | Google Pay Lucky Draw Page - New | none on page | no deal-specific T&C link and no end date on the deal page |
| `sg-standard-chartered-hotels-com` | sg-standard-chartered | Hotels Com | none on page | no deal-specific T&C link and no end date on the deal page |
| `sg-standard-chartered-qoo10-credit-card-promotions` | sg-standard-chartered | Qoo10 Credit Card Promotions | none on page | no deal-specific T&C link and no end date on the deal page |
| `sg-standard-chartered-the-good-life-privileges` | sg-standard-chartered | The Good Life Privileges | none on page | no deal-specific T&C link and no end date on the deal page |
| `sg-uob-uob-cards-jb-deals` | sg-uob | UOB Cards JB Deals | none on page | multi-deal hub page: dates belong to individual deals, not to this listing |

### Dropped as expired by their own T&C date (16)

- `my-hong-leong-win-rm2-000-cashback-or-a-prize-of-your-choice`: end date 2026-08-28
- `my-hong-leong-cards-insure-dine-tap-and-pay-campaign`: end date 2025-07-31
- `my-hong-leong-cc-acqui-raya-up-your-shopping-promotion`: end date 2025-03-31
- `my-hong-leong-hlb-bhumi-pilates-pink-october`: end date 2025-10-02
- `my-hong-leong-hlb-traveloka-11-11-super-sale`: end date 2025-11-14
- `my-hong-leong-unlock-the-latest-huawei-products-with-hlb-cards`: end date 2024-11-30
- `my-hong-leong-hlb-samsung-galaxy-z-pre-sale`: end date 2024-07-30
- `my-hong-leong-hlb-cards-iphone-17-launch-campaign`: end date 2025-10-31
- `my-hong-leong-get-the-iphone-duo-with-hlb-credit-card-and-enjoy-hlb-0-epp`: end date 2026-10-31
- `my-hong-leong-hlb-edu-reward-program-promotion`: end date 2025-03-31
- `my-ambank-earn-up-to-10percent-touch-n-go-cashback-for-insurance-takaful-with-amban`: end date 2026-06-30
- `my-alliance-shop-on-shopee-and-enjoy-exclusive-discounts-plus-birthday-bonus-treats`: end date 2026-06-11
- `sg-standard-chartered-a-million-reasons-to-be-happier`: end date 2026-02-28
- `sg-standard-chartered-paradise-group-credit-card-promotions`: end date 2019-12-31
- `sg-standard-chartered-rebatemango`: end date 2020-10-31
- `sg-standard-chartered-zalora-and-liverpool-fc-top-spenders-promotion`: end date 2018-10-31
<!-- held-back:end -->

## 4. Freshness

- Everything was fetched on 9 Nov 2026 (MYT). `last_checked` is set per record.
- Expired offers were dropped at build (76): a page date before 9 Nov 2026, or a year in the title earlier than 2026. A further 16 were dropped at publish because the end date in their own T&C has passed.

## 5. Update recommendations

1. **Per-issuer adapters:** one adapter per issuer, configured in `scripts/issuers_config.json` and `offers_config.json`. Each adapter defines:
   - seeds
   - product and promotion regexes
   - a fetch mode: static, headless or manual
   - Add headless Playwright for JavaScript hubs: Affin, BSN, OCBC, Visa offers, RHB promotions.
2. **Discovery:**
   - Use sitemaps where they exist (CIMB, PBB, HLB, UOB, SC, HSBC, Citi, DBS, Alliance).
   - Use listing pages elsewhere.
   - No issuer here offers useful RSS.
3. **Change detection:**
   - Store a hash of the normalised main text per URL.
   - Re-extract only pages that changed.
   - Diff the output JSON per record.
4. **Schedule:**
   - Offers: daily.
   - Cards: weekly.
   - Full re-discovery: monthly.
   - Run on GitHub Actions cron or a Cloudflare Cron Trigger.
5. **PR-based review:**
   - The bot opens a pull request with the JSON diff and a summary (added, removed, changed fields), with schema validation and a referential-integrity check in CI.
   - A human approves anything that changes fees, income or rates.
6. **Expiry pruning:**
   - Daily job: move offers past `valid_until` to an `archive/` folder.
   - Flag offers with no validity whose source page has disappeared (404).
7. **Quality:**
   - Track per-issuer field fill rates in CI.
   - Fail the run if a count drops by more than 30%, which signals a site redesign.

## 6. API design

Read-only, versioned, mirroring the file tree:

- `GET /v1/index`
- `GET /v1/{cc}/cards?issuer=&network=&tier=&islamic=&benefit=`
- `GET /v1/{cc}/cards/{id}` (includes eligible offers)
- `GET /v1/{cc}/offers?merchant=&category=&card=&active_on=YYYY-MM-DD`
- `GET /v1/{cc}/merchants/{id}/offers`
- `GET /v1/search?q=` (across countries)
- `GET /v1/schema/{entity}`

Behaviour:

- Responses carry `source_url` and `last_checked`, with ETag and Cache-Control headers.
- Use an `openapi.json` and an MCP wrapper so AI agents can call it as a tool.

### Hosting options

| Option | Pros | Cons |
|---|---|---|
| GitHub raw / Pages | Free, zero ops, versioned by git | No filtering or query, raw rate limits, whole-file downloads |
| Cloudflare Worker + R2 (files) + KV (hot indexes) | Edge-cached, filters in the Worker, cheap, deploy on merge | Small amount of code |
| Worker + D1 | Real SQL filtering and search | Load step per build, D1 limits |
| Supabase (Postgres + PostgREST) | Instant REST, full-text search, row-level security | A server to keep, more than read-only data needs, egress and cold-start limits on the free tier |

**Recommendation:**

1. Keep the GitHub repo as the source of truth, and serve the static JSON on GitHub Pages as a free fallback.
2. Put a Cloudflare Worker in front.
3. On merge, a GitHub Action uploads the build to R2 and writes the indexes to KV.
4. The Worker serves the filtered endpoints with edge caching.
5. Add D1 only if free-text or multi-filter queries get heavy.
6. Use Supabase only if user accounts or write features are added later.

## 7. Files

- **Publish tree:** `master-list/` (index.json, README.md, my/, sg/, global/, schema/).
- **Build scripts:** `scripts/`.
  - Order: crawl_cards.py, build_cards.py, crawl_offers.py, build_offers.py, enrich_terms.py, publish.py, report_heldback.py.
  - enrich_terms.py: for each offer page, finds the deal's own T&C link (PDF via pdftotext, or HTML), rejects general bank terms (by URL and by the document's first lines) and documents that do not mention the deal, then reads the promotion period, minimum spend, cap and clauses. Pages that are JavaScript-only are rendered with Playwright headless (cache: `raw/cache/headless/`, documents: `raw/cache/docs/`). One host at a time, 1.5 s delay.
  - publish.py applies the end-date rule (held-back list in `raw/held_back.json`), card clean-up (`card_finish.py`), writes the tree, copies `scripts/repo_files/` (README, CONTRIBUTING, .github, tools/) into it and runs `master-list/tools/validate.py`. `publish.py --check` runs the validator only.
  - schema_update.py migrates `master-list/schema/` to 0.2.0 (idempotent).
  - Run builds under `flock /workspace/cc-master/.build.lock`.
- **Working data:** `raw/` (cache, sitemaps, manual transcriptions). Not for publishing.
