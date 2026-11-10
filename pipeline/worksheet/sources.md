# Credit card source worksheet: Malaysia and Singapore

Generated 2026-11-10 01:38 (Asia/Kuala_Lumpur). Rows: 156; done 126, blocked 30, to do 0, in progress 0.

Official bank, network and merchant pages only. Public pages only; no sign-in, forms or contact. Polite crawl, cached under raw/cache/.

## MY: 18 credit card issuers

Issuers: AEON Credit, Affin, Al Rajhi, Alliance, AmBank, BSN, Bank Islam, Bank Rakyat, CIMB, HSBC, Hong Leong, Maybank, Muamalat, OCBC, Public Bank, RHB, Standard Chartered, UOB.

Checked, not credit card issuers on their official site: AEON Bank, GXBank, Kuwait Finance House, MBSB Bank.

Listed but not confirmed (site unreachable or no issuer catalogue found): Agrobank, American Express MY, Citibank MY, Co-opbank Pertama, Diners Club Malaysia.

| bank | page type | status | cards | offers | url | notes |
|---|---|---|---|---|---|---|
| AEON Bank | issuer_check | blocked | 0 | 0 | https://www.aeonbank.com.my/ | not a credit-card issuer: AEON Bank (digital): debit card only on official site; AEON credit cards are issued by AEON Credit Service, listed separately |
| AEON Credit | catalogue | done | 9 |  | https://myaeoncredit.com.my/cards/credit-cards/ | cards for my-aeon-credit already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| AEON Credit | promotions | done |  | 5 | https://myaeoncredit.com.my/promotions/ | 9 detail pages; 5 offers; skipped {'non_card_title': 4} |
| Affin | catalogue | done | 4 |  | https://www.affinalways.com/en/my-cards | cards for my-affin already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| Affin | promotions | done |  |  | https://www.affinalways.com/en/promotions | hub; card promotions read from the Cards-filtered listing (affin adapter) |
| Affin | promotions | done |  | 33 | https://www.affinalways.com/en/promotions?group=Personal&product_filter=Cards | 64 detail pages; 33 offers; skipped {'weak_card_evidence': 20, 'debit_only': 3, 'non_card_title': 2, 'expired': 6} |
| Affin | promotions | done |  |  | https://www.affinalways.com/flights | not a card promotion listing; card offers read from the Cards-filtered listing |
| Agrobank | issuer_check | blocked |  |  | https://www.agrobank.com.my/ | unreachable again at 2026-11-10 00:41 (curl timeout; fetch gateway 5xx); credit card issuance not confirmed on the official site, so not counted as an issuer |
| Al Rajhi | catalogue | done | 2 |  | https://www.alrajhibank.com.my/ | home page; cards from existing pipeline |
| Al Rajhi | promotions | blocked |  | 0 | https://www.alrajhibank.com.my/promotions | HTTP 404 (also /personal/promotions, /campaigns); no public card promotions listing found; site links only news items |
| Alliance | catalogue | done | 6 |  | https://www.alliancebank.com.my/personal/cards/credit-cards | cards for my-alliance already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| Alliance | promotions | done |  | 19 | https://www.alliancebank.com.my/promotions | 20 detail pages; 19 offers; skipped {'non_card_title': 1} |
| AmBank | catalogue | done | 35 |  | https://www.ambank.com.my/cards/credit-cards | cards for my-ambank already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| AmBank | promotions | done |  | 22 | https://www.ambank.com.my/promotions | 37 detail pages; 22 offers; skipped {'expired': 5, 'non_card_title': 8, 'weak_card_evidence': 2} |
| American Express MY | issuer_check | blocked |  |  | https://www.americanexpress.com/en-my/ | /en-my/ 404; /my/ redirects to /en-my/network/ (Amex network page, 406 words); no Amex-issued MY card catalogue found, so not counted as an issuer |
| BSN | catalogue | done | 4 |  | https://www.bsn.com.my/PersonalBanking/Cards/cards | cards for my-bsn already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| BSN | promotions | done |  |  | https://www.bsn.com.my/page/promotions | hub; credit card promotions read from Cards-i/credit-card-promotions (bsn adapter) |
| BSN | promotions | done |  |  | https://www.bsn.com.my/page/Shopee1111 | covered by bsn adapter (Shopee 11.11 offer, T&C PDF) |
| BSN | promotions | done |  | 7 | https://www.bsn.com.my/IslamicBanking/Cards-i/credit-card-promotions | 7 offer entries read; skipped {} |
| BSN | promotions | done |  | 9 | https://www.bsn.com.my/page/highlights-promotions | 82 detail pages; 9 offers; skipped {'weak_card_evidence': 47, 'non_card_title': 24, 'debit_only': 2} |
| BSN | tnc | done |  |  | https://www.bsn.com.my/cms/upload/pdf/promotion/2026/zus_coffee_apr_tnc_eng.pdf | April ZUS Coffee T&C: promotion period ended; not recorded |
| Bank Islam | catalogue | done | 9 |  | https://www.bankislam.com/personal-banking/bank-islam-cards/ | cards for my-bank-islam already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| Bank Islam | catalogue | done | 9 |  | https://www.bankislam.com/personal-banking/bank-islam-cards/bank-islam-credit-card-i/ | cards for my-bank-islam already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP None |
| Bank Islam | promotions | done |  | 13 | https://www.bankislam.com/promotions/ | 16 detail pages; 13 offers; skipped {'weak_card_evidence': 2, 'expired': 1} |
| Bank Rakyat | catalogue | blocked |  |  | https://www.bankrakyat.com.my/portal-main/compare-cards | retried 2026-11-10 01:26: sitemap.xml and robots.txt 404; rendered home menu confirms Bank Rakyat issues Credit Card-i (PDRM, Cikgu Sejati, Gold, Xclusive Explo |
| Bank Rakyat | promotions | blocked |  |  | https://www.bankrakyat.com.my/portal-main/promotion | retried 2026-11-10 01:26: sitemap.xml and robots.txt 404; rendered home menu confirms Bank Rakyat issues Credit Card-i (PDRM, Cikgu Sejati, Gold, Xclusive Explo |
| Bank Rakyat | tnc | blocked |  |  | https://www.bankrakyat.com.my/assets/documents/PDS%20CREDIT%20CARD-i%20(BM%202026).pdf | HTTP 404; Bank Rakyat credit card-i pages and PDS return 404 to the crawler; no cards or offers read |
| CIMB | catalogue | done | 17 |  | https://www.cimb.com.my/en/personal/day-to-day-banking/cards/credit-card.html | cards for my-cimb already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| CIMB | promotions | done |  | 26 | https://www.cimb.com.my/en/personal/promotions/latest-promotions.html | listing data https://www.cimb.com.my/en/personal/promotions/latest-promotions/_jcr_content/root/responsivegrid_197111812/promo_listing_copy_c.list: 39 items; sk |
| Citibank MY | issuer_check | blocked |  |  | https://www.citibank.com.my/ | unreachable again at 2026-11-10 00:41 (curl timeout; fetch gateway 5xx); credit card issuance not confirmed on the official site, so not counted as an issuer |
| Co-opbank Pertama | issuer_check | blocked |  |  | https://www.coopbank.com.my/ | unreachable again at 2026-11-10 00:41 (curl timeout; fetch gateway 5xx); credit card issuance not confirmed on the official site, so not counted as an issuer |
| Diners Club Malaysia | issuer_check | blocked |  |  | https://www.dinersclub.com.my/ | unreachable again at 2026-11-10 00:41 (curl timeout; fetch gateway 5xx); credit card issuance not confirmed on the official site, so not counted as an issuer |
| GXBank | issuer_check | blocked | 0 | 0 | https://gxbank.my/ | not a credit-card issuer: GXBank: debit card only on official site; no credit card |
| HSBC | app_partner | done |  | 65 | https://sp.hsbc.com.my/ | Smart Privileges offer pages read; site total 69 offers from 69 pages; skipped {} |
| HSBC | catalogue | done | 6 |  | https://www.hsbc.com.my/credit-cards/ | cards for my-hsbc already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| HSBC | merchant_offers | done |  | 0 | https://sp.hsbc.com.my/category/all | Smart Privileges offer pages read; site total 69 offers from 69 pages; skipped {} |
| HSBC | merchant_offers | done |  | 0 | https://sp.hsbc.com.my/category/food-and-beverages | Smart Privileges offer pages read; site total 69 offers from 69 pages; skipped {} |
| HSBC | merchant_offers | done |  | 0 | https://sp.hsbc.com.my/category/health-and-beauty | Smart Privileges offer pages read; site total 69 offers from 69 pages; skipped {} |
| HSBC | merchant_offers | done |  | 0 | https://sp.hsbc.com.my/category/shopping | Smart Privileges offer pages read; site total 69 offers from 69 pages; skipped {} |
| HSBC | merchant_offers | done |  | 4 | https://sp.hsbc.com.my/category/0-card-instalment-plan | Smart Privileges offer pages read; site total 69 offers from 69 pages; skipped {} |
| HSBC | promotions | done |  |  | https://www.hsbc.com.my/offers/ | hub; offers read from Smart Privileges sp.hsbc.com.my (hsbcmy adapter, 69 offers) |
| Hong Leong | catalogue | done | 9 |  | https://www.hlb.com.my/en/personal-banking/credit-cards.html | cards for my-hong-leong already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| Hong Leong | merchant_offers | done |  | 8 | https://www.hlb.com.my/en/personal-banking/promotions/cards-hlb-card-offers.html | 8 inline offer tiles, 8 T&C links; skipped {} |
| Hong Leong | promotions | done |  | 8 | https://www.hlb.com.my/en/personal-banking/promotions.html | 9 detail pages; 8 offers; skipped {'non_card_title': 1} |
| Hong Leong | promotions | blocked |  |  | https://www.hlb.com.my/en/personal-banking/promotions/credit-card.html | guessed URL renders the HLB error page; card promotions read from promotions.html and cards-hlb-card-offers.html instead |
| Kuwait Finance House | issuer_check | blocked | 0 | 0 | https://www.kfh.com.my/ | not a credit-card issuer: headless render of kfh.com.my/malaysia/personal.html (curl gets 406) lists Debit Card-i only; no KFH Malaysia credit card |
| Kuwait Finance House | issuer_check | blocked | 0 | 0 | https://www.kfh.com.my/en/home/Personal/Cards/credit-cards.html | not a credit-card issuer: headless render of kfh.com.my/malaysia/personal.html (curl gets 406) lists Debit Card-i only; no KFH Malaysia credit card |
| MBSB Bank | issuer_check | blocked | 0 | 0 | https://www.mbsbbank.com/ | not a credit-card issuer: MBSB Bank: official site lists debit card-i only; no credit card found |
| Maybank | catalogue | blocked |  |  | https://www.maybank2u.com.my/maybank2u/malaysia/en/personal/cards/credit_cards/index.page | maybank2u.com.my times out for the crawler (retried 2026-11-10 00:41); existing Maybank MY cards/offers come from the earlier pipeline, not re-verified |
| Maybank | promotions | blocked |  |  | https://www.maybank2u.com.my/maybank2u/malaysia/en/personal/promotions/cards/index.page | wrong path (404 via public fetch); real listing is promotions/maybank_cards.page (added as its own row); maybank2u.com.my unreachable from the crawl box |
| Maybank | promotions | blocked |  |  | https://www.maybank2u.com.my/maybank2u/malaysia/en/personal/promotions/maybank_cards.page | correct card promotions listing (found via official search result; public fetch shows about 60 merchant tiles, no dates on the listing); the crawl box cannot re |
| Muamalat | catalogue | done | 8 |  | https://www.muamalat.com.my/card/personal/credit-card-i/ | cards for my-muamalat already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| Muamalat | promotions | done |  | 31 | https://www.muamalat.com.my/promotions/card/ | 33 detail pages; 31 offers; skipped {'no_title': 1, 'non_card_title': 1} |
| OCBC | catalogue | done | 6 |  | https://www.ocbc.com.my/personal-banking/cards/credit-cards | cards for my-ocbc already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| OCBC | promotions | done |  | 7 | https://www.ocbc.com.my/personal-banking/promotion | JS page rendered; 7 inline deal panels with their own T&C; skipped {} |
| Public Bank | catalogue | done | 16 |  | https://www.pbebank.com/en/cards/our-cards/ | cards for my-public-bank already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| Public Bank | promotions | done |  | 23 | https://www.pbebank.com/en/promotions/credit-cards-promotions/ | 23 promo pages (image-based); dates and terms from each deal's own T&C PDF; skipped {} |
| Public Bank | promotions | done |  |  | https://www.pbebank.com/en/promotions/ | hub; credit card promotions read from credit-cards-promotions (pbb adapter) |
| RHB | catalogue | done | 12 |  | https://www.rhbgroup.com/personal/cards/credit-cards/overview/index.html | cards for my-rhb already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| RHB | merchant_offers | done |  | 139 | https://www.rhbgroup.com/cards/promotions-privileges/index.html | static hub; each tile popup links its own T&C PDF: 135 of 139 offers now use that PDF (terms, clauses, hash, dates from its PROMOTION PERIOD clause); 4 tiles ha |
| RHB | merchant_offers | done |  | 25 | https://www.rhbgroup.com/cards/mastercard-offers/index.html | 26 detail pages; skipped {'no_tnc_pdf_matched': 24} |
| RHB | promotions | done |  | 1 | https://www.rhbgroup.com/ApplyandSpendCard/index.html |  |
| RHB | promotions | done |  | 1 | https://www.rhbgroup.com/btcx/index.html |  |
| Standard Chartered | catalogue | done | 3 |  | https://www.sc.com/my/credit-cards/ | cards for my-standard-chartered already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| Standard Chartered | merchant_offers | done |  | 100 | https://www.sc.com/my/promotions/the-good-life-privileges/ | JS page; offers read from its public data file https://www.sc.com/my/data/tgl/offers.json; 100 records; skipped {} |
| Standard Chartered | promotions | done |  |  | https://www.sc.com/my/promotions/ | hub page; card merchant offers read from The Good Life data file (scmy adapter, 100 offers) |
| UOB | catalogue | done | 7 |  | https://www.uob.com.my/personal/cards/all-cards.page | cards for my-uob already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| UOB | merchant_offers | done |  | 5 | https://www.uob.com.my/personal/promotions/dining-deals.page | 6 inline tiles, 0 T&C links; skipped {'expired': 1} |
| UOB | merchant_offers | done |  | 6 | https://www.uob.com.my/personal/promotions/shopping-deals.page | 6 inline tiles, 0 T&C links; skipped {} |
| UOB | merchant_offers | done |  | 4 | https://www.uob.com.my/personal/promotions/travel-deals.page | 6 inline tiles, 0 T&C links; skipped {'no_slug': 2} |
| UOB | merchant_offers | done |  | 6 | https://www.uob.com.my/personal/promotions/lifestyle-deals.page | 6 inline tiles, 0 T&C links; skipped {} |
| UOB | merchant_offers | done |  | 2 | https://www.uob.com.my/personal/promotions/other-deals.page | 3 inline tiles, 0 T&C links; skipped {'no_slug': 1} |
| UOB | promotions | done |  |  | https://www.uob.com.my/personal/promotions/index.page | hub; deals read from the category pages (uobmy adapter) |
| JCB | network_portal | done |  | 9 | https://www.specialoffers.jcb/en/campaign/d/southeast-and-south-asia/malaysia/ | raw only: 9 offer links saved to raw/network_offers/jcb_my_df340925e2a3.json; not merged because the published schema has no network-level (non-issuer) offer sl |
| Mastercard | network_portal | blocked |  |  | https://www.mastercard.com/my/en/personal/offers-and-promotions.html | HTTP 403 to curl and to headless Chromium (retried 2026-11-10 01:26) |
| Mastercard | network_portal | blocked |  | 0 | https://www.priceless.com/m/filter/options/location/1048 | page loads (HTTP 200) but offers only appear through its JS search UI; no offer links in the fetched or rendered page; not crawled further (no internal API use) |
| UnionPay | network_portal | blocked |  | 0 | https://www.unionpayintl.com/my/ | page loads (HTTP 200) but offers only appear through its JS search UI; no offer links in the fetched or rendered page; not crawled further (no internal API use) |
| Visa | network_portal | done |  | 15 | https://www.visa.com.my/en_my/visa-offers-and-perks/ | raw only: 15 offer links saved to raw/network_offers/visa_my_ba8ad587858a.json; not merged because the published schema has no network-level (non-issuer) offer  |
| Visa | network_portal | done |  | 15 | https://www.visa.com.my/en_my/visa-offers-and-perks/ | raw only: 15 offer links saved to raw/network_offers/visa_my_ba8ad587858a.json; not merged because the published schema has no network-level (non-issuer) offer  |

## SG: 16 credit card issuers

Issuers: American Express, BOC, CIMB, Citi, DBS, DCS Card Centre, GXS, HSBC, ICBC, MariBank, Maybank, OCBC, POSB, Standard Chartered, Trust, UOB.

| bank | page type | status | cards | offers | url | notes |
|---|---|---|---|---|---|---|
| American Express | catalogue | done | 7 |  | https://www.americanexpress.com/en-sg/credit-cards/ | cards for sg-amex already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| American Express | merchant_offers | done |  | 1 | https://www.americanexpress.com/en-sg/benefits/the-platinum-card/dining/ | 1 offer entries read; skipped {} |
| American Express | merchant_offers | blocked |  | 0 | https://www.americanexpress.com/en-sg/benefits/the-platinum-card/dining/love-dining-experience/ | HTTP 404 (wrong guessed path); Love Dining is an always-on Platinum benefit with no stated end date on the campaign page, so not recorded as an offer |
| American Express | promotions | done |  | 4 | https://www.americanexpress.com/en-sg/campaigns/the-platinum-card/ | Platinum benefit blocks with a stated end date; skipped {}; undated always-on benefits (Love Dining, Chillax, lounges) not recorded as offers |
| BOC | catalogue | done | 9 |  | https://www.bankofchina.com/sg/bcservice/bc1/ | cards for sg-boc already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| BOC | catalogue | done | 9 |  | https://www.bankofchina.com/sg/bcservice/ | cards for sg-boc already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP None |
| BOC | promotions | done |  | 1 | https://www.bankofchina.com/sg/bcservice/bc3/ | 1 detail pages; 1 offers; skipped {} |
| CIMB | catalogue | done | 5 |  | https://www.cimb.com.sg/en/personal/banking-with-us/cards/credit-cards.html | cards for sg-cimb already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| CIMB | promotions | done |  |  | https://www.cimb.com.sg/en/personal/promotions.html | hub; card promotions read from latest-promotions (cimbsg adapter) |
| CIMB | promotions | done |  | 2 | https://www.cimb.com.sg/en/personal/promotions/latest-promotions.html | 2 offer entries read; skipped {} |
| Citi | app_partner | blocked |  | 0 | https://www.citiworldprivileges.com/sg/ | Citi World Privileges SG renders only an app download page (107 words); merchant offers are app-only |
| Citi | catalogue | done | 8 |  | https://www.citibank.com.sg/credit-cards/ | cards for sg-citi already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| Citi | promotions | done |  | 0 | https://www.citibank.com.sg/static/all-promo | JS page rendered; lists banking/wealth promos and one Mastercard contest; no dated credit card merchant offers beyond those already in the main pipeline |
| DBS | catalogue | done | 8 |  | https://www.dbs.com.sg/personal/cards/default.page | cards for sg-dbs already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| DBS | merchant_offers | done |  | 17 | https://www.dbs.com.sg/personal/cards/offers/default.page | 17 detail pages; 17 offers; skipped {} |
| DBS | promotions | done |  | 25 | https://www.dbs.com.sg/personal/cards/promotions/default.page | 26 detail pages; 25 offers; skipped {'expired': 1} |
| DCS Card Centre | catalogue | done | 11 |  | https://cards.dcscc.com/ | card list read from rendered https://cards.dcscc.com/products (JS); DeCard stablecoin cards left out (credit status unclear) |
| DCS Card Centre | catalogue | done | 11 |  | https://cards.dcscc.com/products | cards for sg-dcs already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP None |
| DCS Card Centre | merchant_offers | done |  | 48 | https://dcscc.com/merchant-deals | 49 detail pages; 48 offers; skipped {'no_title': 1} |
| DCS Card Centre | promotions | done |  | 6 | https://dcscc.com/campaigns | 6 offer entries read; skipped {} |
| DCS Card Centre | promotions | done |  | 2 | https://cards.dcscc.com/dconvertoffer | 2 offer entries read; skipped {} |
| DCS Card Centre | promotions | done |  | 1 | https://cards.dcscc.com/ultimate | Ultimate Platinum cashback campaign; via dcsextra adapter |
| DCS Card Centre | promotions | done |  | 0 | https://dcscc.com/promotions | redirects to cards.dcscc.com home; DCS promotions covered by dconvertoffer, ultimate and merchant-deals rows |
| GXS | catalogue | done | 1 | 2 | https://www.gxs.com.sg/flexicard | 3 offer entries read; skipped {'expired': 1} |
| GXS | promotions | done |  | 4 | https://www.gxs.com.sg/promotions | 6 detail pages; 4 offers; skipped {'no_title': 2} |
| HSBC | catalogue | done | 7 |  | https://www.hsbc.com.sg/credit-cards/ | cards for sg-hsbc already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| HSBC | merchant_offers | done |  | 26 | https://www.hsbc.com.sg/card-promotions | 36 detail pages; 26 offers; skipped {'expired': 3, 'category_hub': 7} |
| HSBC | merchant_offers | done |  | 22 | https://cardpromotions.hsbc.com.sg/ | 35 detail pages; 22 offers; skipped {'http': 1, 'expired': 4, 'category_hub': 7, 'no_title': 1} |
| HSBC | promotions | done |  |  | https://www.hsbc.com.sg/promotions/credit-cards/ | hub; offers read from hsbc.com.sg/card-promotions and cardpromotions.hsbc.com.sg (hsbcsg adapter) |
| ICBC | catalogue | done | 8 |  | https://www.icbc.com.sg/en/column/1438059017535897814.html | 8 cards from the official Credit Cards menu; each card page fetched |
| ICBC | issuer_check | done | 8 |  | https://www.icbc.com.sg/ | issues credit cards (8 card pages); promotions via icbcsg adapter |
| ICBC | promotions | done |  | 6 | https://www.icbc.com.sg/en/column/1438058492253847697.html | 8 offer entries read; skipped {'expired': 2} |
| MariBank | catalogue | done | 1 | 3 | https://www.maribank.sg/product/mari-credit-card | 3 offer entries read; skipped {} |
| MariBank | issuer_check | done | 1 |  | https://www.maribank.sg/ | issues Mari Credit Card (confirmed on official site); offers via maribank adapter |
| Maybank | catalogue | blocked |  |  | https://www.maybank2u.com.sg/en/personal/cards/credit-cards/index.page | timeout / no response from this network (curl) |
| Maybank | merchant_offers | done |  | 9 | https://cardspromo.maybank2u.com.sg/ | 9 detail pages; 9 offers; skipped {} |
| Maybank | merchant_offers | done |  | 16 | https://cardspromo.maybank2u.com.sg/promotions?category=Dining | 17 detail pages; 16 offers; skipped {} |
| Maybank | merchant_offers | done |  | 12 | https://cardspromo.maybank2u.com.sg/promotions?category=Travel | 15 detail pages; 12 offers; skipped {'no_title': 1} |
| Maybank | merchant_offers | done |  | 13 | https://cardspromo.maybank2u.com.sg/promotions?category=Lifestyle | 17 detail pages; 13 offers; skipped {'no_title': 1} |
| Maybank | merchant_offers | done |  | 7 | https://cardspromo.maybank2u.com.sg/promotions?category=Essentials | 10 detail pages; 7 offers; skipped {} |
| Maybank | merchant_offers | done |  | 12 | https://cardspromo.maybank2u.com.sg/promotions?category=Pets | 14 detail pages; 12 offers; skipped {} |
| Maybank | merchant_offers | done |  | 10 | https://cardspromo.maybank2u.com.sg/promotions?category=Malaysia+Deals | 15 detail pages; 10 offers; skipped {} |
| Maybank | merchant_offers | done |  | 10 | https://cardspromo.maybank2u.com.sg/promotions?category=Worldwide+Deals | 13 detail pages; 10 offers; skipped {} |
| Maybank | promotions | blocked |  |  | https://www.maybank2u.com.sg/en/promotions/cards/index.page | maybank2u.com.sg times out for the crawler; SG card offers read from cardspromo.maybank2u.com.sg instead |
| Maybank | tnc | blocked |  |  | https://www.maybank2u.com.sg/iwov-resources/sg/pdf/cards/applynow-tnc.pdf | maybank2u.com.sg times out for the crawler |
| OCBC | catalogue | done | 11 |  | https://www.ocbc.com/personal-banking/cards/credit-card | cards for sg-ocbc already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| OCBC | merchant_offers | done |  | 478 | https://www.ocbc.com/personal-banking/cards/card-promotion | JS hub; listing from public JSON; deals have no page or T&C document of their own (T&C only in hub popups), so terms_url null; end dates read only from each dea |
| POSB | catalogue | done | 1 |  | https://www.posb.com.sg/personal/cards/cards-comparator.page | cards for sg-posb already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| POSB | merchant_offers | done |  | 0 | https://www.posb.com.sg/personal/cards/offers/default.page | 17 detail pages; 0 offers; skipped {} |
| POSB | promotions | done |  | 1 | https://www.posb.com.sg/personal/cards/promotions/default.page | 1 detail pages; 1 offers; skipped {} |
| Standard Chartered | catalogue | done | 11 |  | https://www.sc.com/sg/credit-cards/ | cards for sg-standard-chartered already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| Standard Chartered | merchant_offers | done |  | 242 | https://www.sc.com/sg/promotions/the-good-life-privileges/ | JS page; offers read from its public data file https://www.sc.com/sg/data/tgl/offers.json; 245 records; skipped {'expired': 3} |
| Standard Chartered | promotions | done |  |  | https://www.sc.com/sg/promotions/ | hub page; card merchant offers read from The Good Life data file (scsg adapter) |
| Trust | catalogue | blocked | 0 |  | https://trust.com.sg/ | retried 2026-11-10 01:27 (trust.com.sg and www.trust.com.sg, curl and headless): connection closed, 0 bytes; Trust credit card exists per prior research but not |
| Trust | promotions | blocked |  |  | https://trust.com.sg/rewards | retried 2026-11-10 01:27 (trust.com.sg and www.trust.com.sg, curl and headless): connection closed, 0 bytes; Trust credit card exists per prior research but not |
| UOB | catalogue | done | 15 |  | https://www.uob.com.sg/personal/cards/index.page | cards for sg-uob already built by the existing card pipeline (build_cards / cards_curated.tsv) or this sweep; catalogue probe HTTP 200 |
| UOB | merchant_offers | done |  | 3 | https://www.uob.com.sg/personal/promotions/cards/jbdeals/index.page | JB merchant deal tiles with inline T&C; skipped {}; card-benefit blurbs and UNI$ redemption not recorded as offers |
| UOB | promotions | done |  |  | https://www.uob.com.sg/personal/promotions/index.page | hub; card deals page read (presale/access tiles, mostly no stated discount) |
| JCB | network_portal | done |  | 4 | https://www.specialoffers.jcb/en/campaign/d/southeast-and-south-asia/singapore/ | raw only: 4 offer links saved to raw/network_offers/jcb_sg_a706f484fd5e.json; not merged because the published schema has no network-level (non-issuer) offer sl |
| Mastercard | network_portal | blocked |  | 0 | https://www.priceless.com/m/filter/options/location/1056 | page loads (HTTP 200) but offers only appear through its JS search UI; no offer links in the fetched or rendered page; not crawled further (no internal API use) |
| UnionPay | network_portal | blocked |  | 0 | https://www.unionpayintl.com/sg/ | page loads (HTTP 200) but offers only appear through its JS search UI; no offer links in the fetched or rendered page; not crawled further (no internal API use) |
| Visa | network_portal | done |  | 15 | https://www.visa.com.sg/en_sg/visa-offers-and-perks/ | raw only: 15 offer links saved to raw/network_offers/visa_sg_af4d185bd133.json; not merged because the published schema has no network-level (non-issuer) offer  |

## Published offers per issuer (before this sweep, after)

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

## Blocked rows

- MY Maybank (catalogue): https://www.maybank2u.com.my/maybank2u/malaysia/en/personal/cards/credit_cards/index.page : maybank2u.com.my times out for the crawler (retried 2026-11-10 00:41); existing Maybank MY cards/offers come from the earlier pipeline, not re-verified
- MY Maybank (promotions): https://www.maybank2u.com.my/maybank2u/malaysia/en/personal/promotions/cards/index.page : wrong path (404 via public fetch); real listing is promotions/maybank_cards.page (added as its own row); maybank2u.com.my unreachable from the crawl box
- MY Hong Leong (promotions): https://www.hlb.com.my/en/personal-banking/promotions/credit-card.html : guessed URL renders the HLB error page; card promotions read from promotions.html and cards-hlb-card-offers.html instead
- MY Bank Rakyat (catalogue): https://www.bankrakyat.com.my/portal-main/compare-cards : retried 2026-11-10 01:26: sitemap.xml and robots.txt 404; rendered home menu confirms Bank Rakyat issues Credit Card-i (PDRM, Cikgu Sejati, Gold, Xclusive Explorer) but menu items are JS-only with no URLs and clicking does not navigate; card and promo pages not reachable
- MY Bank Rakyat (promotions): https://www.bankrakyat.com.my/portal-main/promotion : retried 2026-11-10 01:26: sitemap.xml and robots.txt 404; rendered home menu confirms Bank Rakyat issues Credit Card-i (PDRM, Cikgu Sejati, Gold, Xclusive Explorer) but menu items are JS-only with no URLs and clicking does not navigate; card and promo pages not reachable
- MY Agrobank (issuer_check): https://www.agrobank.com.my/ : unreachable again at 2026-11-10 00:41 (curl timeout; fetch gateway 5xx); credit card issuance not confirmed on the official site, so not counted as an issuer
- MY Kuwait Finance House (issuer_check): https://www.kfh.com.my/ : not a credit-card issuer: headless render of kfh.com.my/malaysia/personal.html (curl gets 406) lists Debit Card-i only; no KFH Malaysia credit card
- MY MBSB Bank (issuer_check): https://www.mbsbbank.com/ : not a credit-card issuer: MBSB Bank: official site lists debit card-i only; no credit card found
- MY Diners Club Malaysia (issuer_check): https://www.dinersclub.com.my/ : unreachable again at 2026-11-10 00:41 (curl timeout; fetch gateway 5xx); credit card issuance not confirmed on the official site, so not counted as an issuer
- MY American Express MY (issuer_check): https://www.americanexpress.com/en-my/ : /en-my/ 404; /my/ redirects to /en-my/network/ (Amex network page, 406 words); no Amex-issued MY card catalogue found, so not counted as an issuer
- MY Citibank MY (issuer_check): https://www.citibank.com.my/ : unreachable again at 2026-11-10 00:41 (curl timeout; fetch gateway 5xx); credit card issuance not confirmed on the official site, so not counted as an issuer
- MY GXBank (issuer_check): https://gxbank.my/ : not a credit-card issuer: GXBank: debit card only on official site; no credit card
- MY AEON Bank (issuer_check): https://www.aeonbank.com.my/ : not a credit-card issuer: AEON Bank (digital): debit card only on official site; AEON credit cards are issued by AEON Credit Service, listed separately
- MY Co-opbank Pertama (issuer_check): https://www.coopbank.com.my/ : unreachable again at 2026-11-10 00:41 (curl timeout; fetch gateway 5xx); credit card issuance not confirmed on the official site, so not counted as an issuer
- MY Mastercard (network_portal): https://www.mastercard.com/my/en/personal/offers-and-promotions.html : HTTP 403 to curl and to headless Chromium (retried 2026-11-10 01:26)
- MY Mastercard (network_portal): https://www.priceless.com/m/filter/options/location/1048 : page loads (HTTP 200) but offers only appear through its JS search UI; no offer links in the fetched or rendered page; not crawled further (no internal API use)
- MY UnionPay (network_portal): https://www.unionpayintl.com/my/ : page loads (HTTP 200) but offers only appear through its JS search UI; no offer links in the fetched or rendered page; not crawled further (no internal API use)
- SG Maybank (catalogue): https://www.maybank2u.com.sg/en/personal/cards/credit-cards/index.page : timeout / no response from this network (curl)
- SG Trust (catalogue): https://trust.com.sg/ : retried 2026-11-10 01:27 (trust.com.sg and www.trust.com.sg, curl and headless): connection closed, 0 bytes; Trust credit card exists per prior research but not read
- SG Trust (promotions): https://trust.com.sg/rewards : retried 2026-11-10 01:27 (trust.com.sg and www.trust.com.sg, curl and headless): connection closed, 0 bytes; Trust credit card exists per prior research but not read
- SG Mastercard (network_portal): https://www.priceless.com/m/filter/options/location/1056 : page loads (HTTP 200) but offers only appear through its JS search UI; no offer links in the fetched or rendered page; not crawled further (no internal API use)
- SG UnionPay (network_portal): https://www.unionpayintl.com/sg/ : page loads (HTTP 200) but offers only appear through its JS search UI; no offer links in the fetched or rendered page; not crawled further (no internal API use)
- MY Bank Rakyat (tnc): https://www.bankrakyat.com.my/assets/documents/PDS%20CREDIT%20CARD-i%20(BM%202026).pdf : HTTP 404; Bank Rakyat credit card-i pages and PDS return 404 to the crawler; no cards or offers read
- MY Kuwait Finance House (issuer_check): https://www.kfh.com.my/en/home/Personal/Cards/credit-cards.html : not a credit-card issuer: headless render of kfh.com.my/malaysia/personal.html (curl gets 406) lists Debit Card-i only; no KFH Malaysia credit card
- SG American Express (merchant_offers): https://www.americanexpress.com/en-sg/benefits/the-platinum-card/dining/love-dining-experience/ : HTTP 404 (wrong guessed path); Love Dining is an always-on Platinum benefit with no stated end date on the campaign page, so not recorded as an offer
- SG Maybank (promotions): https://www.maybank2u.com.sg/en/promotions/cards/index.page : maybank2u.com.sg times out for the crawler; SG card offers read from cardspromo.maybank2u.com.sg instead
- SG Maybank (tnc): https://www.maybank2u.com.sg/iwov-resources/sg/pdf/cards/applynow-tnc.pdf : maybank2u.com.sg times out for the crawler
- SG Citi (app_partner): https://www.citiworldprivileges.com/sg/ : Citi World Privileges SG renders only an app download page (107 words); merchant offers are app-only
- MY Al Rajhi (promotions): https://www.alrajhibank.com.my/promotions : HTTP 404 (also /personal/promotions, /campaigns); no public card promotions listing found; site links only news items
- MY Maybank (promotions): https://www.maybank2u.com.my/maybank2u/malaysia/en/personal/promotions/maybank_cards.page : correct card promotions listing (found via official search result; public fetch shows about 60 merchant tiles, no dates on the listing); the crawl box cannot reach maybank2u.com.my (curl timeout, headless 0 bytes), so detail pages, dates and T&C were not read; existing 56 Maybank MY offers come from the earlier pipeline
