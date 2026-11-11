# Issuer census (phase 1)

Phase 1 of `crawler/FULL_CRAWL.md`. Every entry on the regulator lists was checked against the institution's own official site on 2026-11-11. Sources are the regulator sites and the institutions' own sites only. `null` means not known or not applicable.

Results: `in_repository`, `same_group`, `new_issuer`, `no_consumer_card`, `not_reached` (see FULL_CRAWL.md, Phase 1, step 3). An `off_domain_redirect` was recorded and not followed.

## Malaysia (MY)

Regulator lists read on bnm.gov.my, FSP directory, tags `credit-card-issuer` (27 entries), `charge-card-issuer` (7 entries) and `limited-purpose-charge-card-issuer` (6 entries): 40 list entries, 35 unique institutions. A bank on two lists has one row for each list.

| regulator entry | regulator list | result | issuer ID | official URL that proves the result | date checked | note |
|---|---|---|---|---|---|---|
| AEON Credit Service (M) Berhad | BNM Credit Card Issuers | in_repository | my-aeon-credit | https://myaeoncredit.com.my/cards/credit-cards/ | 2026-11-11 | BNM gives aeoncredit.com.my; the repository domain myaeoncredit.com.my was used. |
| Affin Bank Berhad | BNM Credit Card Issuers | in_repository | my-affin | https://www.affinalways.com/en/my-cards | 2026-11-11 | Card list is loaded from https://www.affinalways.com/json/card_box/Credit.json |
| Affin Islamic Bank Berhad | BNM Credit Card Issuers | same_group | my-affin | https://www.affinalways.com/json/card_box/Credit.json | 2026-11-11 | Islamic cards (for example AFFIN Mastercard Gold-i) are on the Affin site. |
| Alliance Bank Malaysia Berhad | BNM Credit Card Issuers | in_repository | my-alliance | https://www.alliancebank.com.my/personal/cards/credit-cards | 2026-11-11 |  |
| AmBank (M) Berhad | BNM Credit Card Issuers | in_repository | my-ambank | https://www.ambank.com.my/cards/credit-cards | 2026-11-11 |  |
| AmBank Islamic Berhad | BNM Credit Card Issuers | same_group | my-ambank | https://www.ambank.com.my/cards/credit-cards/ambank-islamic-visa-infinite | 2026-11-11 | ambankislamic.com.my failed the TLS handshake; Islamic cards are on ambank.com.my. |
| Bank Islam Malaysia Berhad | BNM Credit Card Issuers | in_repository | my-bank-islam | https://www.bankislam.com/personal-banking/bank-islam-cards/ | 2026-11-11 |  |
| Bank Kerjasama Rakyat Malaysia Berhad (Bank Rakyat) | BNM Credit Card Issuers | in_repository | my-bank-rakyat | null | 2026-11-11 | Matched by legal name. Site not readable this run: every request, robots.txt included, returned 302 to a 404 image. |
| Bank Muamalat Malaysia Berhad | BNM Credit Card Issuers | in_repository | my-muamalat | https://www.muamalat.com.my/card/personal/credit-card-i/ | 2026-11-11 |  |
| Bank of China (Malaysia) Berhad | BNM Credit Card Issuers | no_consumer_card | null | https://www.bankofchina.com.my/en-my/segment/personal-banking/bank-cards.html | 2026-11-11 | Page shows only the Great Wall International Debit Card. Conflicts with the BNM listing; maintainer to confirm. |
| Bank Simpanan Nasional | BNM Credit Card Issuers | in_repository | my-bsn | https://www.bsn.com.my/PersonalBanking/Cards/cards | 2026-11-11 |  |
| CIMB Bank Berhad | BNM Credit Card Issuers | in_repository | my-cimb | https://www.cimb.com.my/en/personal/day-to-day-banking/cards/credit-card.html | 2026-11-11 |  |
| CIMB Islamic Bank Berhad | BNM Credit Card Issuers | same_group | my-cimb | https://www.cimb.com.my/en/personal/day-to-day-banking/cards/credit-card/cimb-lite-i-credit-card.html | 2026-11-11 |  |
| Hong Leong Bank Berhad | BNM Credit Card Issuers | in_repository | my-hong-leong | https://www.hlb.com.my/en/personal-banking/credit-cards.html | 2026-11-11 |  |
| HSBC Amanah Malaysia Berhad | BNM Credit Card Issuers | same_group | my-hsbc | https://www.hsbc.com.my/credit-cards/ | 2026-11-11 | Amanah cards are listed on hsbc.com.my, but their product pages are on www.hsbcamanah.com.my, which is not in my-hsbc official_domains. Maintainer to decide that host. |
| HSBC Bank Malaysia Berhad | BNM Credit Card Issuers | in_repository | my-hsbc | https://www.hsbc.com.my/credit-cards/ | 2026-11-11 |  |
| Industrial and Commercial Bank of China (Malaysia) Berhad | BNM Credit Card Issuers | new_issuer | my-icbc | https://www.icbcmy.com/en/column/1438058793715253368.html | 2026-11-11 | ICBC UnionPay Dual Currency and ICBC Visa credit cards (Classic, Gold, Platinum). PDS and T&C files are on v.icbc.com.cn. |
| Malayan Banking Berhad | BNM Credit Card Issuers | in_repository | my-maybank | null | 2026-11-11 | Matched by legal name. maybank2u.com.my and maybank.com timed out (HTTP2 protocol error in a browser too) this run. |
| Maybank Islamic Berhad | BNM Credit Card Issuers | not_reached | null | null | 2026-11-11 | www.maybank.com/islamic timed out and www.maybank2u.com.my was unreachable. The repository already holds Maybank Islamic Ikhwan cards under my-maybank; likely same_group once the site is readable. |
| OCBC Bank (Malaysia) Berhad | BNM Credit Card Issuers | in_repository | my-ocbc | https://www.ocbc.com.my/personal-banking/cards/credit-cards | 2026-11-11 |  |
| Paydee Sdn Bhd (formerly known as Synergy Cards Sdn Bhd) | BNM Credit Card Issuers | no_consumer_card | null | https://www.paydee.co/paydee-for-business | 2026-11-11 | Shows a business Paydee Visa card and an enterprise co-brand issuing programme; no named consumer credit card found. Maintainer to confirm. |
| Public Bank Berhad | BNM Credit Card Issuers | in_repository | my-public-bank | https://www.pbebank.com/en/cards/our-cards/?type=Credit | 2026-11-11 |  |
| Public Islamic Bank Berhad | BNM Credit Card Issuers | same_group | my-public-bank | https://www.pbebank.com/en/cards/our-cards/?type=Credit | 2026-11-11 | Lists Public Islamic Bank Visa Platinum Credit Card-i. |
| RHB Bank Berhad | BNM Credit Card Issuers | in_repository | my-rhb | https://www.rhbgroup.com/personal/cards/credit-cards/overview/index.html | 2026-11-11 |  |
| RHB Islamic Bank Berhad | BNM Credit Card Issuers | same_group | my-rhb | https://www.rhbgroup.com/personal/cards/credit-cards/overview/index.html | 2026-11-11 | Islamic tab lists RHB Premier Visa Infinite Credit Card-i (rhbgroup.com/islamic/). |
| Standard Chartered Bank Malaysia Berhad | BNM Credit Card Issuers | in_repository | my-standard-chartered | https://www.sc.com/my/credit-cards/ | 2026-11-11 |  |
| United Overseas Bank (Malaysia) Berhad | BNM Credit Card Issuers | in_repository | my-uob | https://www.uob.com.my/personal/cards/all-cards.page | 2026-11-11 |  |
| Al Rajhi Banking & Investment Corporation (Malaysia) Berhad | BNM Charge Card Issuers (Banks) | in_repository | my-al-rajhi | https://www.alrajhibank.com.my/ | 2026-11-11 | Credit cards are in the site navigation. |
| CIMB Bank Berhad | BNM Charge Card Issuers (Banks) | in_repository | my-cimb | https://www.cimb.com.my/en/personal/day-to-day-banking/cards/credit-card.html | 2026-11-11 |  |
| Citibank Berhad | BNM Charge Card Issuers (Banks) | no_consumer_card | null | https://www.citigroup.com/global/about-us/global-presence/malaysia | 2026-11-11 | States that Citi consumer business in Malaysia transferred to UOB. |
| HSBC Bank Malaysia Berhad | BNM Charge Card Issuers (Banks) | in_repository | my-hsbc | https://www.hsbc.com.my/credit-cards/ | 2026-11-11 |  |
| Malayan Banking Berhad | BNM Charge Card Issuers (Banks) | in_repository | my-maybank | null | 2026-11-11 | Matched by legal name. maybank2u.com.my and maybank.com timed out (HTTP2 protocol error in a browser too) this run. |
| Public Bank Berhad | BNM Charge Card Issuers (Banks) | in_repository | my-public-bank | https://www.pbebank.com/en/cards/our-cards/?type=Credit | 2026-11-11 |  |
| United Overseas Bank (Malaysia) Berhad | BNM Charge Card Issuers (Banks) | in_repository | my-uob | https://www.uob.com.my/personal/cards/all-cards.page | 2026-11-11 |  |
| Boustead Petroleum Marketing Sdn Bhd | BNM Charge Card Issuers (Non-Banks) | no_consumer_card | null | https://www.bhpetrol.com.my/x-fleet-card/ | 2026-11-11 | Fleet card for businesses. |
| Chevron Malaysia Limited | BNM Charge Card Issuers (Non-Banks) | no_consumer_card | null | https://www.caltex.com/my/business/fleet-cards/caltex-starcard.html | 2026-11-11 | Fleet card for businesses. |
| Petron Fuel International Sdn Bhd | BNM Charge Card Issuers (Non-Banks) | no_consumer_card | null | https://www.petron.com.my/cards-loyalty/petron-fleet-card/ | 2026-11-11 | Fleet card For Businesses. The PB-Petron Visa Gold credit card is issued by Public Bank. |
| PETRONAS Dagangan Berhad | BNM Charge Card Issuers (Non-Banks) | no_consumer_card | null | https://www.mymesra.com.my/for-business/petronas-smartpay/ | 2026-11-11 | SmartPay fleet card for businesses. |
| Radius Business Solutions (Malaysia) Sdn Bhd (formerly known as Radius Fuel Cards Sdn Bhd) | BNM Charge Card Issuers (Non-Banks) | no_consumer_card | null | https://www.radius.com/en-my/fuel-cards/ | 2026-11-11 | Business fuel cards. |
| Shell Malaysia Trading Sdn Bhd | BNM Charge Card Issuers (Non-Banks) | no_consumer_card | null | https://www.shell.com.my/business/shell-fuel-card.html | 2026-11-11 | Business fuel card. |

### Malaysia: names to check that are not on the BNM credit or charge card lists

FULL_CRAWL.md Phase 1 step 4 names these. None of them is on the BNM credit card or charge card lists; the BNM entry column shows what bnm.gov.my has for them. They are not counted in the totals above.

| name | BNM entry | result | issuer ID | official URL that proves the result | date checked | note |
|---|---|---|---|---|---|---|
| Kuwait Finance House (Malaysia) Berhad | https://www.bnm.gov.my/-/kuwait-finance-house-malaysia-berhad | no_consumer_card | null | https://www.kfh.com.my/malaysia/personal.html | 2026-11-11 | BNM lists it as a debit card issuer only. Site shows Debit Card-i only. |
| Co-opbank Pertama | none (BNM pages /-/co-opbank-pertama-malaysia-berhad and /-/koperasi-co-opbank-pertama-malaysia-berhad return 404) | no_consumer_card | null | https://www.cbp.com.my/en | 2026-11-11 | Site shows financing, deposits, Ar-Rahnu, takaful and wills; no card. Official URL located by web search, then read on the site. |
| GX Bank Berhad | https://www.bnm.gov.my/-/gx-bank-berhad | no_consumer_card | null | https://gxbank.my/debit-card | 2026-11-11 | Debit card. FlexiCredit is a credit line, not a card. |
| AEON Bank (M) Berhad | https://www.bnm.gov.my/-/aeon-bank-m-berhad | no_consumer_card | null | https://www.aeonbank.com.my | 2026-11-11 | BNM lists it as a debit card issuer only. Site shows debit card only. |
| Boost Bank Berhad | https://www.bnm.gov.my/-/boost-bank-berhad | no_consumer_card | null | https://myboostbank.co | 2026-11-11 | Menu shows Debit Card only. |
| YTL Digital Bank Berhad (Ryt Bank) | https://www.bnm.gov.my/-/ytl-digital-bank-berhad | no_consumer_card | null | https://www.rytbank.my/ryt-card | 2026-11-11 | OPEN QUESTION: the Ryt Card can pay with Ryt Credit (a credit line). Not marketed as a credit card; maintainer to decide whether it counts. |
| KAF Digital Bank Berhad | https://www.bnm.gov.my/-/kaf-digital-bank-berhad | no_consumer_card | null | https://www.kafdigitalbank.com.my/ | 2026-11-11 | Savings only. Official URL located by web search, then read on the site. |
| Bank Pertanian Malaysia Berhad (Agrobank) | https://www.bnm.gov.my/-/bank-pertanian-malaysia-berhad-agrobank | not_reached | null | null | 2026-11-11 | https://www.agrobank.com.my/ TLS certificate authority invalid; not bypassed. |
| MBSB Bank Berhad | https://www.bnm.gov.my/-/mbsb-bank-berhad | not_reached | null | null | 2026-11-11 | off_domain_redirect: www.mbsbbank.com redirects to www.mbsb.com; not followed. |
| Diners Club | none found on BNM | not_reached | null | null | 2026-11-11 | dinersclub.com.my closed the connection. |
| American Express International, Inc. | https://www.bnm.gov.my/-/american-express-international (Approved Payment System Operator only) | not_reached | null | null | 2026-11-11 | off_domain_redirect: www.americanexpress.com/my redirects to go.amex; /en-my/ returns 404. |

The other Malaysia names in step 4 are on the lists above: Paydee, Citibank, Bank of China, ICBC.

## Singapore (SG)

Regulator lists read on eservices.mas.gov.sg, Financial Institutions Directory: Local Bank (6), Qualifying Full Bank (10), Full Bank (20), Wholesale Bank (96), Credit and Charge Card Licensee (4). Total 136. The category Digital Full Bank returns 0 results and is not on the directory home page; GXS Bank and MariBank are listed under Local Bank and Trust Bank under Full Bank.

| regulator entry | regulator list | result | issuer ID | official URL that proves the result | date checked | note |
|---|---|---|---|---|---|---|
| BANK OF SINGAPORE LIMITED | MAS FID: Local Bank | no_consumer_card | null | https://www.bankofsingapore.com/html/en-sg/homepage.html | 2026-11-11 | Private bank; no card products. |
| DBS BANK LTD. | MAS FID: Local Bank | in_repository | sg-dbs | https://www.dbs.com.sg/personal/cards/cards-comparator.page | 2026-11-11 | MAS website is dbs.com; repository uses dbs.com.sg. POSB cards (sg-posb, https://www.posb.com.sg/personal/cards/cards-comparator.page) are a DBS brand with no MAS entry of their own. |
| GXS BANK PTE. LTD. | MAS FID: Local Bank | in_repository | sg-gxs | https://www.gxs.com.sg/flexicard | 2026-11-11 |  |
| MARIBANK SINGAPORE PRIVATE LIMITED | MAS FID: Local Bank | in_repository | sg-maribank | https://www.maribank.sg/product/mari-credit-card | 2026-11-11 |  |
| OVERSEA-CHINESE BANKING CORPORATION LIMITED | MAS FID: Local Bank | in_repository | sg-ocbc | https://www.ocbc.com/personal-banking/cards/credit-card | 2026-11-11 |  |
| UNITED OVERSEAS BANK LIMITED | MAS FID: Local Bank | in_repository | sg-uob | https://www.uob.com.sg/personal/cards/index.page | 2026-11-11 | MAS website is uobgroup.com. |
| BANK OF CHINA LIMITED | MAS FID: Qualifying Full Bank | in_repository | sg-boc | https://www.bankofchina.com/sg/bcservice/bc1/ | 2026-11-11 |  |
| BNP PARIBAS | MAS FID: Qualifying Full Bank | not_reached | null | null | 2026-11-11 | off_domain_redirect: https://www.bnpparibas.com.sg redirects to https://apac.bnpparibas/en/singapore//; not followed. |
| CHINA CONSTRUCTION BANK CORPORATION | MAS FID: Qualifying Full Bank | not_reached | null | null | 2026-11-11 | TLS error on https://www.ccb.com |
| CITIBANK SINGAPORE LIMITED | MAS FID: Qualifying Full Bank | in_repository | sg-citi | https://www.citibank.com.sg/credit-cards/ | 2026-11-11 |  |
| HSBC BANK (SINGAPORE) LIMITED | MAS FID: Qualifying Full Bank | in_repository | sg-hsbc | https://www.hsbc.com.sg/credit-cards/ | 2026-11-11 |  |
| ICICI BANK LIMITED | MAS FID: Qualifying Full Bank | no_consumer_card | null | https://www.icicibank.com.sg/retail-banking | 2026-11-11 | Retail menu: remittances, accounts, deposits; no credit card. MAS website icicibank.com redirects off-domain to icici.bank.in; SG site located by web search, then read on the site. |
| INDUSTRIAL AND COMMERCIAL BANK OF CHINA LIMITED | MAS FID: Qualifying Full Bank | in_repository | sg-icbc | https://www.icbc.com.sg/en/column/1438059017535897814.html | 2026-11-11 |  |
| MAYBANK SINGAPORE LIMITED | MAS FID: Qualifying Full Bank | in_repository | sg-maybank | null | 2026-11-11 | Matched by legal name. www.maybank2u.com.sg timed out this run. |
| STANDARD CHARTERED BANK (SINGAPORE) LIMITED | MAS FID: Qualifying Full Bank | in_repository | sg-standard-chartered | https://www.sc.com/sg/credit-cards/ | 2026-11-11 |  |
| STATE BANK OF INDIA | MAS FID: Qualifying Full Bank | no_consumer_card | null | https://sg.statebank | 2026-11-11 | No card product on the SG site. |
| BANGKOK BANK PUBLIC COMPANY LIMITED | MAS FID: Full Bank | not_reached | null | null | 2026-11-11 | TLS error on https://www.bbl.co.th |
| BANK OF AMERICA,NATIONAL ASSOCIATION | MAS FID: Full Bank | no_consumer_card | null | https://www.bankofamerica.com | 2026-11-11 | No Singapore consumer card on the official site. Card links on this page are for the home market, not Singapore. |
| BANK OF INDIA | MAS FID: Full Bank | not_reached | null | null | 2026-11-11 | HTTP 403 on https://www.boi.com.sg |
| CIMB BANK BERHAD | MAS FID: Full Bank | in_repository | sg-cimb | https://www.cimb.com.sg/en/personal/banking-with-us/cards/credit-cards.html | 2026-11-11 |  |
| CITIBANK N.A. | MAS FID: Full Bank | same_group | sg-citi | https://www.citibank.com.sg/credit-cards/ | 2026-11-11 | MAS lists the same website as Citibank Singapore Limited. The page does not name the issuing entity; maintainer to confirm. |
| CREDIT AGRICOLE CORPORATE AND INVESTMENT BANK | MAS FID: Full Bank | no_consumer_card | null | https://www.ca-cib.com/en | 2026-11-11 | Corporate and investment bank. |
| HL BANK | MAS FID: Full Bank | no_consumer_card | null | https://www.hlbank.com.sg/en/personal-banking/home.html | 2026-11-11 | Its Credit Card menu links to hlb.com.my (Malaysia, my-hong-leong); no Singapore card page. Maintainer to confirm. |
| INDIAN BANK | MAS FID: Full Bank | not_reached | null | null | 2026-11-11 | TLS error on https://www.indian-bank.com |
| INDIAN OVERSEAS BANK | MAS FID: Full Bank | not_reached | null | null | 2026-11-11 | TLS error on https://iob.com |
| JPMORGAN CHASE BANK, N.A. | MAS FID: Full Bank | no_consumer_card | null | https://www.jpmorgan.com/SG/en/about-us | 2026-11-11 | Corporate and investment banking in Singapore. |
| MALAYAN BANKING BERHAD | MAS FID: Full Bank | same_group | sg-maybank | null | 2026-11-11 | Same website as Maybank Singapore Limited (www.maybank2u.com.sg), which timed out this run. |
| MIZUHO BANK, LTD. | MAS FID: Full Bank | no_consumer_card | null | https://www.mizuhogroup.com/asia-pacific/singapore | 2026-11-11 | No Singapore consumer card on the official site. Singapore page of the group site. |
| MUFG BANK, LTD. | MAS FID: Full Bank | no_consumer_card | null | https://www.bk.mufg.jp/global/ | 2026-11-11 | No Singapore consumer card on the official site. |
| P.T. BANK NEGARA INDONESIA (PERSERO) TBK | MAS FID: Full Bank | no_consumer_card | null | https://www.bni.co.id | 2026-11-11 | No Singapore consumer card on the official site. |
| RHB BANK BERHAD | MAS FID: Full Bank | no_consumer_card | null | https://www.rhbgroup.com.sg/rhb/personal | 2026-11-11 | Personal menu: deposits, loans, insurance, investments; no credit card. |
| SUMITOMO MITSUI BANKING CORPORATION | MAS FID: Full Bank | not_reached | null | null | 2026-11-11 | http:// URL returned HTTP 500 from the crawler host; https upgrade on the same host also failed (www.smbc.co.jp) |
| THE BANK OF EAST ASIA LIMITED | MAS FID: Full Bank | no_consumer_card | null | https://www.hkbea.com.sg/html/en/index.html | 2026-11-11 | Deposits, loans and wealth only. |
| THE HONGKONG AND SHANGHAI BANKING CORPORATION LIMITED | MAS FID: Full Bank | same_group | sg-hsbc | https://www.hsbc.com.sg/credit-cards/ | 2026-11-11 | Same website as HSBC Bank (Singapore) Limited; page footer is (c) HSBC Bank (Singapore) Limited. |
| TRUST BANK SINGAPORE LIMITED | MAS FID: Full Bank | in_repository | sg-trust | https://trustbank.sg/ | 2026-11-11 | MAS website trustbank.sg shows the credit card. The repository domain trust.com.sg failed with a TLS error; maintainer to review official_domains. |
| UCO BANK | MAS FID: Full Bank | not_reached | null | null | 2026-11-11 | TLS error on https://www.ucobank.com |
| ABN AMRO CLEARING BANK N.V. | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | read timeout on https://www.abnamro.com |
| AGRICULTURAL BANK OF CHINA LIMITED | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.abchina.com/en/ | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. Card links on this page are for the home market, not Singapore. |
| ANEXT BANK PTE. LTD. | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.anext.com.sg/bank/ | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| ARAB BANK PLC | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.arabbank.com/others/singapore | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. Singapore page of the group site. |
| ARAB BANKING CORPORATION (B.S.C) | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | http:// URL returned HTTP 500 from the crawler host; https upgrade on the same host also failed (www.bank-abc.com) |
| AUSTRALIA AND NEW ZEALAND BANKING GROUP LIMITED | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | off_domain_redirect: https://www.anz.com redirects to https://www.anz.com.au/personal/; not followed. |
| BANCO BILBAO VIZCAYA ARGENTARIA, S.A. | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.bbva.com/en/ | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| BANCO SANTANDER, S.A. | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.santander.com/en/landing-pages/banco-santander-singapore-branch | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. Singapore page of the group site. |
| BANK J. SAFRA SARASIN LTD | MAS FID: Wholesale Bank | no_consumer_card | null | https://jsafrasarasin.com/en/company/locations/country-pages/Singapore.html | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| BANK JULIUS BAER & CO. LTD. | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | HTTP 403 on https://www.juliusbaer.com/ |
| BANK OF BARODA | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | off_domain_redirect: https://www.bankofbaroda.com redirects to https://bankofbaroda.bank.in/; not followed. |
| BANK OF COMMUNICATIONS CO., LTD | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | TLS error on https://www.bankcomm.com |
| BANK OF TAIWAN | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.bot.com.tw/ehtml/homebutton.htm | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| BANQUE PICTET & CIE SA | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.pictet.com/sg/en | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. Singapore page of the group site. |
| BARCLAYS BANK PLC | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.barclays.co.uk/ | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. Card links on this page are for the home market, not Singapore. |
| BDO UNIBANK, INC. | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | HTTP 403 on https://www.bdo.com.ph/singapore |
| CA INDOSUEZ (SWITZERLAND) SA | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | TLS error on https://ca-indosuez.com |
| CANADIAN IMPERIAL BANK OF COMMERCE | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | http:// URL returned HTTP 500 from the crawler host; https upgrade on the same host also failed (www.cibc.com) |
| CATHAY UNITED BANK | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | read timeout on https://www.cathaybk.com.tw |
| CHANG HWA COMMERCIAL BANK LTD | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.chb.com.tw | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| CHINA CITIC BANK INTERNATIONAL LIMITED | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.cncbinternational.com/ | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| CHINA MERCHANTS BANK CO., LTD | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.cmbchina.com/ | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. Card links on this page are for the home market, not Singapore. |
| CLEARSTREAM BANKING S.A. | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.clearstream.com/clearstream-en | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| COMMERZBANK AKTIENGESELLSCHAFT | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | off_domain_redirect: https://www.commerzbank.com redirects to https://www.commerzbank.de/group; not followed. |
| COMMONWEALTH BANK OF AUSTRALIA | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.commbank.com.au/ | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. Card links on this page are for the home market, not Singapore. |
| COOPERATIEVE RABOBANK U.A. | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | HTTP 403 on https://www.rabobank.com/ |
| CREDIT INDUSTRIEL ET COMMERCIAL | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | off_domain_redirect: https://www.cic.com.sg redirects to https://www.cic.asia/; not followed. |
| CTBC BANK CO., LTD. | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | HTTP 202 on https://www.ctbcbank.com/ |
| DEUTSCHE BANK AKTIENGESELLSCHAFT | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.db.com | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| DNB BANK ASA | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.dnb.no | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| DZ BANK AG DEUTSCHE ZENTRAL-GENOSSENSCHAFTSBANK, FRANKFURT AM MAIN | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.dzbank.com/content/dzbank/en/home/international-network/singapore.html | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. Singapore page of the group site. |
| E.SUN COMMERCIAL BANK, LTD. | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.esunbank.com/en/personal | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. Card links on this page are for the home market, not Singapore. |
| EFG BANK AG | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | HTTP 403 on https://www.efginternational.com/ |
| EMIRATES NBD BANK (P.J.S.C) | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | HTTP 403 on https://www.emiratesnbd.com/ |
| EUROCLEAR BANK SA/NV | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | HTTP 403 on https://www.euroclear.com/ |
| FIRST ABU DHABI BANK P.J.S.C. | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.bankfab.com/en-ae/personal | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. Card links on this page are for the home market, not Singapore. |
| FIRST COMMERCIAL BANK, LTD. | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.firstbank.com.tw/sites/fcb/personalhome | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. Card links on this page are for the home market, not Singapore. |
| GOLDMAN SACHS BANK EUROPE SE | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.goldmansachs.com/ | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| GREEN LINK DIGITAL BANK PTE. LTD. | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.glbank.com/ | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| HABIB BANK LIMITED | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.hbl.com/ | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. Card links on this page are for the home market, not Singapore. |
| HACHIJUNI NAGANO BANK, LTD. | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | off_domain_redirect: https://www.82bank.co.jp/ redirects to https://bank.82group.jp/; not followed. |
| HDFC BANK LIMITED | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | off_domain_redirect: https://www.hdfcbank.com/ redirects to https://www.hdfc.bank.in/; not followed. |
| HUA NAN COMMERCIAL BANK, LTD. | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | read timeout on https://www.hncb.com.tw |
| ICBC STANDARD BANK PLC | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.icbcstandard.com/ | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| ING BANK N.V. | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | off_domain_redirect: https://www.ingbank.nl redirects to https://www.ing.nl/particulier/index.html; not followed. |
| INTESA SANPAOLO S.P.A. | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.intesasanpaolo.com | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| KBC BANK N.V. | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.kbc.com/en.html | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| KEB HANA BANK | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | TLS error on https://www.koexbank.co.kr |
| KOOKMIN BANK CO., LTD. | MAS FID: Wholesale Bank | no_consumer_card | null | https://kbglobal.kbstar.com/sg/main | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. Singapore page of the group site. |
| KRUNG THAI BANK PUBLIC COMPANY LIMITED | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | off_domain_redirect: https://www.ktb.co.th redirects to https://krungthai.com/; not followed. |
| LAND BANK OF TAIWAN | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.landbank.com.tw/ | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. Card links on this page are for the home market, not Singapore. |
| LANDESBANK BADEN-WURTTEMBERG | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.lbbw.de/startseite/startseite_6kyjj4koh_d.html | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| MACQUARIE BANK LIMITED | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.macquarie.com/sg/en.html | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. Singapore page of the group site. |
| MEGA INTERNATIONAL COMMERCIAL BANK CO., LTD. | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.megabank.com.tw/personal | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. Card links on this page are for the home market, not Singapore. |
| MITSUBISHI UFJ TRUST AND BANKING CORPORATION | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | TLS error on https://www.mitsubishi-trust.co.jp |
| MORGAN STANLEY BANK ASIA LIMITED | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.morganstanley.com/ | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| NATIONAL AUSTRALIA BANK LIMITED | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | off_domain_redirect: https://www.nationalaustraliabank.com redirects to https://www.nab.com.au/corporate/global-relationships/global-opportunities-and-local-expertise; not followed. |
| NATIONAL BANK OF KUWAIT S.A.K.P. | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.nbk.com/about-nbk-group/our-network/singapore.html | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. Singapore page of the group site. |
| NATIXIS | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | off_domain_redirect: https://www.natixis.com/ redirects to https://natixis.groupebpce.com/; not followed. |
| NATWEST MARKETS PLC | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | TLS error on https://www.natwestmarkets.com |
| PHILIPPINE NATIONAL BANK | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | HTTP 403 on https://www.pnb.com.ph |
| PT BANK MANDIRI (PERSERO) TBK | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | TLS error on https://www.ptbankmandiri.com.sg |
| PT BANK RAKYAT INDONESIA (PERSERO) TBK | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.bri.co.id | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| QATAR NATIONAL BANK (Q.P.S.C.) | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | HTTP 403 on https://www.qnb.com/ |
| RAIFFEISEN BANK INTERNATIONAL AG | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.rbinternational.com/de/home.html | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| ROYAL BANK OF CANADA | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.rbc.com | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| SHANGHAI PUDONG DEVELOPMENT BANK CO., LTD. | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | TLS error on https://www.spdb.com.cn |
| SHINHAN BANK | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.shinhan.com | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| SKANDINAVISKA ENSKILDA BANKEN AB (PUBL) | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | TLS error on https://www.mb.seb.se |
| SOCIETE GENERALE | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | TLS error on https://www.sgcib.com |
| STATE STREET BANK AND TRUST COMPANY | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.statestreet.com/ | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| SUMITOMO MITSUI TRUST BANK, LIMITED | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | off_domain_redirect: https://www.smth.jp/en/index.html redirects to https://www.smtg.jp/en/index.html; not followed. |
| TAIPEI FUBON COMMERCIAL BANK CO., LTD. | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.fubon.com/financialholdings/home/index.html | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| TAISHIN INTERNATIONAL BANK CO., LTD. | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | connection closed by https://www.taishinbank.com.tw |
| THE BANK OF NEW YORK MELLON | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | off_domain_redirect: https://www.bnymellon.com redirects to https://www.bny.com/corporate/global/en.html; not followed. |
| THE BANK OF NOVA SCOTIA | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.scotiabank.ca | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| THE BANK OF YOKOHAMA, LTD. | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.boy.co.jp/ | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. Card links on this page are for the home market, not Singapore. |
| THE CHIBA BANK, LTD | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.chibabank.co.jp/ | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. Card links on this page are for the home market, not Singapore. |
| THE CHUGOKU BANK, LTD. | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.chugin.co.jp/ | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. Card links on this page are for the home market, not Singapore. |
| THE IYO BANK, LTD. | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.iyobank.co.jp/ | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| THE KOREA DEVELOPMENT BANK | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | TLS error on https://www.kol.co.kr |
| THE NORINCHUKIN BANK | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | HTTP 403 on https://www.nochubank.or.jp/ |
| THE NORTHERN TRUST COMPANY | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | read timeout on https://www.ntrs.com |
| THE SAUDI NATIONAL BANK | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | TLS error on https://www.alahli.com |
| THE SHANGHAI COMMERCIAL & SAVINGS BANK, LTD. | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.scsb.com.tw/ | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| THE SHIZUOKA BANK, LTD. | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.shizuokabank.co.jp/ | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| THE SIAM COMMERCIAL BANK PUBLIC COMPANY LIMITED | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | HTTP 403 on https://www.scb.co.th |
| THE TORONTO-DOMINION BANK | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | TLS error on https://www.tdbank.ca |
| UBS AG | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.ubs.com/my/en.html | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. The MAS website redirected to this UBS page for Malaysia; no Singapore page reached. |
| UNICREDIT BANK GMBH | MAS FID: Wholesale Bank | not_reached | null | null | 2026-11-11 | HTTP 403 on https://www.unicreditgroup.eu/en.html |
| UNION BANCAIRE PRIVEE, UBP SA | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.ubp.com/en/contact/our-offices/ubp-singapore | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. Singapore page of the group site. |
| UNION DE BANQUES ARABES ET FRANCAISES | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.ubaf.fr/ | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| VP BANK LTD | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.vpbank.com/en-sg | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. Singapore page of the group site. |
| WELLS FARGO BANK, NATIONAL ASSOCIATION | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.wellsfargo.com/ | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. Card links on this page are for the home market, not Singapore. |
| WESTPAC BANKING CORPORATION | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.westpac.com.au | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. Card links on this page are for the home market, not Singapore. |
| WOORI BANK | MAS FID: Wholesale Bank | no_consumer_card | null | https://www.wooribank.com/ | 2026-11-11 | MAS category Wholesale Bank. No Singapore consumer card on the official site. |
| AMERICAN EXPRESS INTERNATIONAL INC. | MAS FID: Credit and Charge Card Licensee | in_repository | sg-amex | https://www.americanexpress.com/en-sg/credit-cards/ | 2026-11-11 |  |
| DCS CARD CENTRE PTE. LTD. | MAS FID: Credit and Charge Card Licensee | in_repository | sg-dcs | https://cards.dcscc.com/international-credit-card | 2026-11-11 | Issues the DCS Diners Club International Credit Card (covers the Diners Club check). |
| OPTAL SINGAPORE PTE. LTD. | MAS FID: Credit and Charge Card Licensee | not_reached | null | null | 2026-11-11 | off_domain_redirect: www.optal.com redirects to www.wexinc.com/industries/travel/ (WEX group, business travel payments); not followed. |
| WEX Finance Inc. | MAS FID: Credit and Charge Card Licensee | no_consumer_card | null | https://www.wexinc.com/ | 2026-11-11 | Business fleet and payment cards. |

Singapore names in step 4: Diners Club has no MAS entry of its own; Diners Club cards in Singapore are issued by DCS Card Centre (sg-dcs). Optal, WEX Finance, RHB, State Bank of India, ICICI Bank, Bank of East Asia and Trust Bank are rows above.

## Totals

| country | entries | in_repository | same_group | new_issuer | no_consumer_card | not_reached |
|---|---|---|---|---|---|---|
| MY (list entries) | 40 | 23 | 6 | 1 | 9 | 1 |
| MY (unique institutions) | 35 | 18 | 6 | 1 | 9 | 1 |
| SG | 136 | 15 | 3 | 0 | 66 | 52 |
