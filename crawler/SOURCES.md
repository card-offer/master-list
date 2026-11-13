# Crawl sources

This file describes the canonical list of sites to crawl for Malaysia (MY) and Singapore (SG). The list itself is [`crawler/sources.json`](sources.json). Do not crawl a host that is not on the list.

Issuer rows are built by `tools/build_sources.py` from `{cc}/issuers.json` official domains and entry URLs, and from `pipeline/offers_config.json` seeds. Network and regulator rows are kept as they are in `crawler/sources.json`. A host also has to be in the issuer's or the network's `official_domains`, except for the two regulator sites used in the phase 1 census.

## How to read a row

| Field | Meaning |
|---|---|
| `site` | The issuer, network or regulator name. |
| `host` | The official host, without a leading `www.` |
| `country` | `MY` or `SG`. |
| `type` | `issuer`, `network` or `regulator`. |
| `purpose` | `cards` or `offers` for crawl pages, and `census` for the regulator lists. |
| `entry_urls` | Known listing or start URLs from the repository. An empty list means the host is official but no start URL is recorded yet. |
| `status` | Fetcher class from repository evidence only: `ok`, `js_shell`, `bot_wall`, `network_unreachable`, or `untested` when the repository has no such evidence. Do not invent a status. |
| `full_crawl_order` | The order in `crawler/FULL_CRAWL.md`: `1` to `34` for issuers in that table, `after-34` for a phase 1 issuer not yet given a number, `C1` to `C12` for network offer sites, and `phase-1` for regulators. |
| `suggested_by` | The GitHub issue that proposed the site, or `null` when the row came from the repository itself. |

## Suggesting a site

Contributors can propose a site with the "Suggest a site to crawl" issue form. The triage is in `CONTRIBUTING.md`. A maintainer checks that the site is official, probes it with `pipeline/fetcher.py`, and opens a pull request that adds a row here. Suggestions that are not official bank, network, merchant or regulator pages are declined.

## The list

There are 118 rows in `crawler/sources.json`. Counts by country: MY 58, SG 60. Counts by type: issuer 98, network 18, regulator 2.

| Order | Country | Type | Purpose | Site | Host | Status | Entry URLs |
|---|---|---|---|---|---|---|---|
| phase-1 | MY | regulator | census | Bank Negara Malaysia | `bnm.gov.my` | untested |  |
| phase-1 | SG | regulator | census | Monetary Authority of Singapore | `eservices.mas.gov.sg` | untested |  |
| 1 | SG | issuer | cards | CIMB Singapore | `cimb.com.sg` | untested | https://www.cimb.com.sg/en/personal/banking-with-us/cards/credit-cards.html |
| 1 | SG | issuer | offers | CIMB Singapore | `cimb.com.sg` | untested | https://www.cimb.com.sg/en/personal/promotions.html |
| 1 | SG | issuer | cards | CIMB Singapore | `deals.cimb.com` | untested |  |
| 1 | SG | issuer | offers | CIMB Singapore | `deals.cimb.com` | untested |  |
| 2 | SG | issuer | cards | GXS Bank | `cdn.prod.website-files.com` | untested |  |
| 2 | SG | issuer | offers | GXS Bank | `cdn.prod.website-files.com` | untested |  |
| 2 | SG | issuer | cards | GXS Bank | `gxs.com.sg` | untested | https://www.gxs.com.sg/flexicard |
| 2 | SG | issuer | offers | GXS Bank | `gxs.com.sg` | untested |  |
| 3 | SG | issuer | cards | MariBank | `banking-aka-storage.maribank.com.sg` | untested |  |
| 3 | SG | issuer | offers | MariBank | `banking-aka-storage.maribank.com.sg` | untested |  |
| 3 | SG | issuer | cards | MariBank | `maribank.sg` | untested | https://www.maribank.sg/product/mari-credit-card |
| 3 | SG | issuer | offers | MariBank | `maribank.sg` | untested |  |
| 4 | SG | issuer | cards | Trust Bank | `trustbank.sg` | untested | https://trustbank.sg/credit-card/ |
| 4 | SG | issuer | offers | Trust Bank | `trustbank.sg` | untested |  |
| 5 | SG | issuer | cards | ICBC Singapore | `icbc.com.sg` | untested | https://www.icbc.com.sg/en/column/1438059017535897814.html |
| 5 | SG | issuer | offers | ICBC Singapore | `icbc.com.sg` | untested |  |
| 6 | SG | issuer | cards | Bank of China Singapore | `bankofchina.com` | untested | https://www.bankofchina.com/sg/bcservice/bc1/ |
| 6 | SG | issuer | offers | Bank of China Singapore | `bankofchina.com` | untested |  |
| 7 | SG | issuer | cards | American Express Singapore | `americanexpress.com` | untested | https://www.americanexpress.com/sg/credit-cards/all-cards/, https://www.americanexpress.com/en-sg/credit-cards/ |
| 7 | SG | issuer | offers | American Express Singapore | `americanexpress.com` | untested |  |
| 8 | SG | issuer | cards | Citibank Singapore | `citibank.com.sg` | untested | https://www.citibank.com.sg/credit-cards/ |
| 8 | SG | issuer | offers | Citibank Singapore | `citibank.com.sg` | untested | https://www.citibank.com.sg/credit-cards/ |
| 9 | SG | issuer | cards | HSBC Singapore | `cardpromotions.hsbc.com.sg` | untested |  |
| 9 | SG | issuer | offers | HSBC Singapore | `cardpromotions.hsbc.com.sg` | untested |  |
| 9 | SG | issuer | cards | HSBC Singapore | `hsbc.com.sg` | untested | https://www.hsbc.com.sg/credit-cards/ |
| 9 | SG | issuer | offers | HSBC Singapore | `hsbc.com.sg` | untested | https://www.hsbc.com.sg/promotions/credit-cards/ |
| 10 | SG | issuer | cards | DCS Card Centre | `cards.dcscc.com` | untested | https://cards.dcscc.com/products |
| 10 | SG | issuer | offers | DCS Card Centre | `cards.dcscc.com` | untested |  |
| 10 | SG | issuer | cards | DCS Card Centre | `dcscc.com` | untested |  |
| 10 | SG | issuer | offers | DCS Card Centre | `dcscc.com` | untested |  |
| 10 | SG | issuer | cards | DCS Card Centre | `static.dcscc.com` | untested |  |
| 10 | SG | issuer | offers | DCS Card Centre | `static.dcscc.com` | untested |  |
| 11 | SG | issuer | cards | UOB | `uob.com.sg` | untested | https://www.uob.com.sg/personal/cards/index.page, https://www.uob.com.sg/personal/cards/compare.page |
| 11 | SG | issuer | offers | UOB | `uob.com.sg` | untested | https://www.uob.com.sg/personal/promotions/index.page, https://www.uob.com.sg/personal/promotions/cards/jbdeals/index.page |
| 12 | SG | issuer | cards | POSB | `dbs.com.sg` | untested |  |
| 12 | SG | issuer | offers | POSB | `dbs.com.sg` | untested |  |
| 12 | SG | issuer | cards | POSB | `posb.com.sg` | untested | https://www.posb.com.sg/personal/cards/cards-comparator.page |
| 12 | SG | issuer | offers | POSB | `posb.com.sg` | untested |  |
| 13 | SG | issuer | cards | DBS Bank | `dbs.com.sg` | untested | https://www.dbs.com.sg/personal/cards/cards-comparator.page, https://www.dbs.com.sg/personal/cards/default.page |
| 13 | SG | issuer | offers | DBS Bank | `dbs.com.sg` | untested | https://www.dbs.com.sg/personal/cards/promotions/default.page |
| 14 | SG | issuer | cards | Maybank Singapore | `cardspromo.maybank2u.com.sg` | untested |  |
| 14 | SG | issuer | offers | Maybank Singapore | `cardspromo.maybank2u.com.sg` | untested |  |
| 14 | SG | issuer | cards | Maybank Singapore | `maybank2u.com.sg` | untested | https://www.maybank2u.com.sg/en/personal/cards/credit-cards/index.page |
| 14 | SG | issuer | offers | Maybank Singapore | `maybank2u.com.sg` | untested |  |
| 15 | SG | issuer | cards | Standard Chartered Singapore | `av.sc.com` | untested |  |
| 15 | SG | issuer | offers | Standard Chartered Singapore | `av.sc.com` | untested |  |
| 15 | SG | issuer | cards | Standard Chartered Singapore | `sc.com` | untested | https://www.sc.com/sg/credit-cards/ |
| 15 | SG | issuer | offers | Standard Chartered Singapore | `sc.com` | untested | https://www.sc.com/sg/promotions/ |
| 16 | SG | issuer | cards | OCBC | `ocbc.com` | untested | https://www.ocbc.com/personal-banking/cards/credit-card, https://www.ocbc.com/personal-banking/cards |
| 16 | SG | issuer | offers | OCBC | `ocbc.com` | untested | https://www.ocbc.com/personal-banking/cards/card-promotion.page |
| 17 | MY | issuer | cards | Al Rajhi Bank Malaysia | `alrajhibank.com.my` | untested | https://www.alrajhibank.com.my/news/alrajhi-bank-malaysia-expands-retail-banking-business-with-new-visa-credit-cards/ |
| 17 | MY | issuer | offers | Al Rajhi Bank Malaysia | `alrajhibank.com.my` | untested | https://www.alrajhibank.com.my/ |
| 18 | MY | issuer | cards | BSN | `bsn.com.my` | untested | https://www.bsn.com.my/PersonalBanking/Cards/cards, https://www.bsn.com.my/page/site-map |
| 18 | MY | issuer | offers | BSN | `bsn.com.my` | untested |  |
| 19 | MY | issuer | cards | Bank Rakyat | `bankrakyat.com.my` | untested | https://www.bankrakyat.com.my/portal-main/compare-cards |
| 19 | MY | issuer | offers | Bank Rakyat | `bankrakyat.com.my` | untested |  |
| 20 | MY | issuer | cards | OCBC Malaysia | `ocbc.com.my` | untested | https://www.ocbc.com.my/personal-banking/cards/credit-cards |
| 20 | MY | issuer | offers | OCBC Malaysia | `ocbc.com.my` | untested |  |
| 21 | MY | issuer | cards | AEON Credit Service | `myaeoncredit.com.my` | untested | https://myaeoncredit.com.my/cards/credit-cards/ |
| 21 | MY | issuer | offers | AEON Credit Service | `myaeoncredit.com.my` | untested | https://myaeoncredit.com.my/promotions/ |
| 22 | MY | issuer | cards | Alliance Bank | `alliancebank.com.my` | untested | https://www.alliancebank.com.my/personal/cards/credit-cards |
| 22 | MY | issuer | offers | Alliance Bank | `alliancebank.com.my` | untested | https://www.alliancebank.com.my/promotions |
| 23 | MY | issuer | cards | Bank Islam | `bankislam.com` | untested | https://www.bankislam.com/personal-banking/bank-islam-cards/bank-islam-credit-card-i/, https://www.bankislam.com/personal-banking/bank-islam-cards/ |
| 23 | MY | issuer | offers | Bank Islam | `bankislam.com` | untested | https://www.bankislam.com/promotions/ |
| 24 | MY | issuer | cards | Bank Muamalat | `muamalat.com.my` | untested | https://www.muamalat.com.my/card/personal/credit-card-i/ |
| 24 | MY | issuer | offers | Bank Muamalat | `muamalat.com.my` | untested | https://www.muamalat.com.my/promotions/, https://www.muamalat.com.my/promotions/card/ |
| 25 | MY | issuer | cards | Hong Leong Bank | `hlb.com.my` | untested | https://www.hlb.com.my/en/personal-banking/credit-cards.html |
| 25 | MY | issuer | offers | Hong Leong Bank | `hlb.com.my` | untested | https://www.hlb.com.my/en/personal-banking/promotions.html |
| 26 | MY | issuer | cards | Affin Bank | `affinalways.com` | untested | https://www.affinalways.com/en/my-cards, https://www.affinalways.com/en/affin-duo, https://www.affinalways.com/en/affin-visa-mastercard-gold |
| 26 | MY | issuer | offers | Affin Bank | `affinalways.com` | untested |  |
| 27 | MY | issuer | cards | CIMB Bank | `cimb.com.my` | untested | https://www.cimb.com.my/en/personal/day-to-day-banking/cards/credit-card.html |
| 27 | MY | issuer | offers | CIMB Bank | `cimb.com.my` | untested | https://www.cimb.com.my/en/personal/promotions/latest-promotions.html |
| 28 | MY | issuer | cards | Public Bank | `pbebank.com` | untested | https://www.pbebank.com/en/cards/our-cards/, https://www.pbebank.com/en/cards/credit-cards/ |
| 28 | MY | issuer | offers | Public Bank | `pbebank.com` | untested | https://www.pbebank.com/en/promotions/credit-cards-promotions/, https://www.pbebank.com/en/promotions/credit-debit-cards-promotions/, https://www.pbebank.com/en/promotions/ |
| 29 | MY | issuer | cards | UOB Malaysia | `uob.com.my` | untested | https://www.uob.com.my/personal/cards/all-cards.page, https://www.uob.com.my/personal/cards/index.page |
| 29 | MY | issuer | offers | UOB Malaysia | `uob.com.my` | untested | https://www.uob.com.my/personal/promotions/index.page |
| 30 | MY | issuer | cards | HSBC Malaysia | `hsbc.com.my` | untested | https://www.hsbc.com.my/credit-cards/ |
| 30 | MY | issuer | offers | HSBC Malaysia | `hsbc.com.my` | untested | https://www.hsbc.com.my/offers/, https://www.hsbc.com.my/credit-cards/ |
| 30 | MY | issuer | cards | HSBC Malaysia | `hsbcamanah.com.my` | untested | https://www.hsbcamanah.com.my/credit-cards/ |
| 30 | MY | issuer | offers | HSBC Malaysia | `hsbcamanah.com.my` | untested |  |
| 30 | MY | issuer | cards | HSBC Malaysia | `sp.hsbc.com.my` | untested |  |
| 30 | MY | issuer | offers | HSBC Malaysia | `sp.hsbc.com.my` | untested |  |
| 31 | MY | issuer | cards | AmBank | `ambank.com.my` | untested | https://www.ambank.com.my/cards/credit-cards |
| 31 | MY | issuer | offers | AmBank | `ambank.com.my` | untested | https://www.ambank.com.my/promotions |
| 32 | MY | issuer | cards | Standard Chartered Malaysia | `av.sc.com` | untested |  |
| 32 | MY | issuer | offers | Standard Chartered Malaysia | `av.sc.com` | untested |  |
| 32 | MY | issuer | cards | Standard Chartered Malaysia | `sc.com` | untested | https://www.sc.com/my/credit-cards/ |
| 32 | MY | issuer | offers | Standard Chartered Malaysia | `sc.com` | untested | https://www.sc.com/my/promotions/ |
| 33 | MY | issuer | cards | RHB Bank | `rhbgroup.com` | untested | https://www.rhbgroup.com/personal/cards/credit-cards/overview/index.html |
| 33 | MY | issuer | offers | RHB Bank | `rhbgroup.com` | untested |  |
| 34 | MY | issuer | cards | Maybank | `maybank.com` | untested |  |
| 34 | MY | issuer | offers | Maybank | `maybank.com` | untested |  |
| 34 | MY | issuer | cards | Maybank | `maybank2u.com.my` | untested | https://www.maybank2u.com.my/maybank2u/malaysia/en/personal/cards/credit_cards/index.page |
| 34 | MY | issuer | offers | Maybank | `maybank2u.com.my` | untested |  |
| after-34 | MY | issuer | cards | ICBC Malaysia | `icbcmy.com` | untested |  |
| after-34 | MY | issuer | offers | ICBC Malaysia | `icbcmy.com` | untested |  |
| after-34 | MY | issuer | cards | ICBC Malaysia | `v.icbc.com.cn` | untested |  |
| after-34 | MY | issuer | offers | ICBC Malaysia | `v.icbc.com.cn` | untested |  |
| C1 | MY | network | offers | Mastercard | `mastercard.com` | untested |  |
| C1 | MY | network | offers | Mastercard | `priceless.com` | untested |  |
| C1 | MY | network | offers | Mastercard | `specials.priceless.com` | untested | https://specials.priceless.com/ |
| C2 | SG | network | offers | Mastercard | `mastercard.com` | untested |  |
| C2 | SG | network | offers | Mastercard | `priceless.com` | untested |  |
| C2 | SG | network | offers | Mastercard | `specials.priceless.com` | untested | https://specials.priceless.com/ |
| C3 | MY | network | offers | JCB | `jcb.co.jp` | untested |  |
| C3 | MY | network | offers | JCB | `specialoffers.jcb` | untested | https://www.specialoffers.jcb/, https://www.specialoffers.jcb/en/campaign/d/southeast-and-south-asia/malaysia/, https://www.specialoffers.jcb/en/offers/d/southeast-and-south-asia/malaysia/ |
| C4 | SG | network | offers | JCB | `jcb.co.jp` | untested |  |
| C4 | SG | network | offers | JCB | `specialoffers.jcb` | untested | https://www.specialoffers.jcb/, https://www.specialoffers.jcb/en/campaign/d/southeast-and-south-asia/singapore/, https://www.specialoffers.jcb/en/offers/d/southeast-and-south-asia/singapore/ |
| C5 | MY | network | offers | Visa | `visa.com` | untested |  |
| C6 | SG | network | offers | Visa | `visa.com` | untested |  |
| C7 | MY | network | offers | UnionPay | `unionpayintl.com` | untested | https://www.unionpayintl.com/my/ |
| C8 | SG | network | offers | UnionPay | `unionpayintl.com` | untested | https://www.unionpayintl.com/sg/ |
| C9 | MY | network | offers | American Express | `americanexpress.com` | untested |  |
| C10 | SG | network | offers | American Express | `americanexpress.com` | untested |  |
| C11 | MY | network | offers | Diners Club | `dinersclub.com` | untested |  |
| C12 | SG | network | offers | Diners Club | `dinersclub.com` | untested |  |
