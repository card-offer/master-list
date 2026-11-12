# Robots policy: run 1 recheck list, reconciled against the fetch log

2026-11-12. This file corrects `crawler/RECHECK_ROBOTS_20261112.md`. It uses the
run 1 private fetch log (sha256 `c92d169cee74850abef749ecb3afdcfab0e80b41aabb8009b08faf34d089bd5e`,
1,127 lines, read only) and RULES.md section 2 version 3. No historical log was
rewritten. Rechecks of these rows are not started in this run; they wait for the
maintainer's go.

## The discrepancy

The draft said: 11 rows across 12 hosts, all 403, no 401. It also said the run 1
log was not on that machine, so the list was derived from a fresh robots.txt
sweep of census evidence hosts on 2026-11-12 (182 hosts, no page fetched). That
sweep is why the draft has 12 hosts, not 11.

The run 1 log, under https, has **12 requests** that returned 403 for `robots.txt`,
on **11 unique hosts**, and **no 401**. That is the 11-host count from the log.
`www.ipb.citibank.com.sg` was asked twice.

The two 403 sets are not the same set. Only five hosts are in both.

Run 1 unique https 403 hosts (11):

- `aeoncredit.com.my`
- `www.mymesra.com.my`
- `www.rhbgroup.com.sg`
- `www.rabobank.com`
- `www.emiratesnbd.com`
- `www.euroclear.com`
- `www.hdfcbank.com`
- `www.qnb.com`
- `www.unicreditgroup.eu`
- `www.ipb.citibank.com.sg`
- `velocity.ocbc.com`

Draft hosts from the 12 Nov sweep (12):

- In both lists (5): `www.mymesra.com.my`, `www.rhbgroup.com.sg`,
  `www.euroclear.com`, `www.qnb.com`, `www.rabobank.com`
- In the draft only (7): `www.ubs.com`, `www.bot.com.tw`,
  `www.cncbinternational.com`, `www.boi.com.sg`, `www.pnb.com.ph`,
  `www.cic.com.sg`, `www.cic.asia`

Why those seven are not run 1 https 403:

- `www.cncbinternational.com`: run 1 https `robots.txt` was **404**. Under
  version 3 that means no rules, and the home page was read as 200. The later
  sweep's 403 does not make the run 1 read blind. This row is removed.
- `www.ubs.com`, `www.bot.com.tw`, `www.boi.com.sg`, `www.pnb.com.ph`,
  `www.cic.com.sg`: run 1 asked `robots.txt` over **http only** and recorded
  HTTP 500. The rule requires https. An http 500 is not a version 3 unreadable
  decision, because https was never tried and might have answered 200, 404 or
  something else. `www.cic.asia` has no robots.txt row in run 1 at all:
  `www.cic.com.sg` later redirected off-domain to it, and that hop was recorded
  as `off_domain_redirect` and not fetched.

The six run 1 403 hosts that the draft omitted are discussed below. Two of them
back a census `not_reached` row. The other four do not back a census evidence
URL.

Statuses other than 403 do occur in run 1, and version 3 treats them as
unreadable too: 429, 5xx, a timeout, a TLS or connection error, a redirect
loop, more than 5 redirects, a redirect with no target, or a redirect to a host
that is not official. 404 and 410 are readable (no rules). A same-host redirect
of `robots.txt` should have been followed; run 1 often did not follow it, so
those hosts are not classed as unreadable from this log.

## What this list includes

A row is listed when, in run 1:

1. https `robots.txt` for the host was in the unreadable set, and
2. at least one page on that host was read, and that page is what the census
   conclusion rests on (or, for `not_reached`, is the blocked answer that
   stopped a first real read).

One row per conclusion. Facts already read under an unreadable `robots.txt` are
kept and flagged as blind evidence. They are not dropped, and they are not
re-fetched in this run.

## Corrected list: conclusions that rest on a page read under unreadable robots

These are the rows that matter most. Each one asserts something from a 200 page
(or, for Bank of China SG, from 200 pages on the official host) after https
`robots.txt` failed.

| issuer / entry | country | current result | host | robots in run 1 | what rests on it |
|---|---|---|---|---|---|
| PETRONAS Dagangan Berhad | MY | `no_consumer_card` | `www.mymesra.com.my` | 403 | SmartPay fleet card for businesses, at `https://www.mymesra.com.my/for-business/petronas-smartpay/` (200) |
| RHB BANK BERHAD | SG | `no_consumer_card` | `www.rhbgroup.com.sg` | 403 | personal menu at `https://www.rhbgroup.com.sg/rhb/personal` has deposits, loans, insurance, investments, no credit card (18 pages on the host were 200) |
| Industrial and Commercial Bank of China (Malaysia) Berhad | MY | `new_issuer` | `www.icbcmy.com` | TLS error on https `robots.txt` at 11:55:18 KL | card names and the product page `https://www.icbcmy.com/en/column/1438058793715253368.html` (200), plus three other 200 pages on the same host. The BNM issuer list still supports a new-issuer listing; the names and domains need a compliant recheck. |
| Public Bank Berhad | MY | `in_repository` | `www.pbebank.com` | timeout on https `robots.txt` at 11:57:43 KL | the credit card listing `https://www.pbebank.com/en/cards/our-cards/?type=Credit` (200) |
| Public Islamic Bank Berhad | MY | `same_group` | `www.pbebank.com` | same timeout | Public Islamic Bank Visa Platinum Credit Card-i, on the same listing (200) |
| BANK OF CHINA LIMITED | SG | `in_repository` | `www.bankofchina.com` | 302 to `www.boc.cn` (a host that is not official) | the SG card listing `https://www.bankofchina.com/sg/bcservice/bc1/` and related 200 pages on `bankofchina.com`. The redirect itself was not followed, which is correct. |
| AGRICULTURAL BANK OF CHINA LIMITED | SG | `out_of_scope_wholesale` | `www.abchina.com` | 302 with no Location (redirect without target) | the official site `https://www.abchina.com/en/` was 200. The wholesale result is a maintainer scope decision; the official-site read is still blind evidence. |

## Corrected list: `not_reached` on a host whose robots.txt was unreadable

These rows already say that no real answer was read. Version 3 still gives them
a route to try again, with the pages flagged if a later read also happens under
an unreadable `robots.txt`. No 200 content from these hosts supports a product
decision in run 1.

| issuer / entry | country | current result | host | robots in run 1 | what rests on it |
|---|---|---|---|---|---|
| EUROCLEAR BANK SA/NV | SG | `not_reached` | `www.euroclear.com` | 403 | the host answered 403 to the page as well; no 200 evidence |
| QATAR NATIONAL BANK (Q.P.S.C.) | SG | `not_reached` | `www.qnb.com` | 403 | same: 403 on the page, no 200 evidence |
| COOPERATIEVE RABOBANK U.A. | SG | `not_reached` | `www.rabobank.com` | 403 | same |
| EMIRATES NBD BANK (P.J.S.C) | SG | `not_reached` | `www.emiratesnbd.com` | 403 | same. This host was a run 1 403 and was missing from the draft |
| UNICREDIT BANK GMBH | SG | `not_reached` | `www.unicreditgroup.eu` | 403 | same. This host was a run 1 403 and was missing from the draft |

Related `not_reached` rows whose https `robots.txt` was also unreadable, but
where run 1 got no 200 page either (included so the unreadable set is complete):

| issuer / entry | country | current result | host | robots in run 1 | what rests on it |
|---|---|---|---|---|---|
| Bank Pertanian Malaysia Berhad (Agrobank) | MY | `not_reached` | `www.agrobank.com.my` | TLS error (certificate verify failed) | no official page was read; evidence URL is null |
| BDO UNIBANK, INC. | SG | `not_reached` | `www.bdo.com.ph` | timeout | no 200 page |
| NATIXIS | SG | `not_reached` | `www.natixis.com` | 301 to `natixis.groupebpce.com` (not official) | no 200 page on the official host |
| HACHIJUNI NAGANO BANK, LTD. | SG | `not_reached` | `www.82bank.co.jp` | 301 to `bank.82group.jp` (not official) | the official host then 301'd the home page to the same off-domain host; no 200 page was kept |

## Run 1 403 hosts that do not back a census evidence URL

These were 403 for https `robots.txt` in run 1, and they are why a raw host
count of 11 does not equal 11 census rows.

- `aeoncredit.com.my`: 403, and `https://aeoncredit.com.my/` was 200. The AEON
  census evidence is on `myaeoncredit.com.my`, whose `robots.txt` was 200. The
  `in_repository` result does not rest on the 403 host.
- `www.hdfcbank.com`: 403, then the home page 301'd to `www.hdfc.bank.in`. No
  census evidence URL uses this host.
- `www.ipb.citibank.com.sg`: 403, then sign-on URLs also returned 403. Those
  paths should not have been requested (they are sign-in). No census evidence
  URL uses this host.
- `velocity.ocbc.com`: 403, then a login path returned 403. No census evidence
  URL uses this host.

## Appendix: draft rows that were not unreadable in run 1

Under version 3 these are not run 1 blind-evidence rows. A later sweep that
saw 403 can still put them on a future list, but that is a new observation,
not a correction of run 1.

- UBS AG (SG, `no_consumer_card`, `www.ubs.com`): http `robots.txt` 500 only;
  the SG wealth page was read (200) after that http answer. https `robots.txt`
  was not tried in run 1.
- BANK OF TAIWAN (SG, `out_of_scope_wholesale`, `www.bot.com.tw`): http
  `robots.txt` 500 only; a 200 page was read. https was not tried.
- CHINA CITIC BANK INTERNATIONAL LIMITED (SG, `out_of_scope_wholesale`,
  `www.cncbinternational.com`): https `robots.txt` **404**, home page 200. This
  is a valid readable run 1 read. Remove from the unreadable list.
- BANK OF INDIA (SG, `not_reached`, `www.boi.com.sg`): http `robots.txt` 500
  only; no 200 page. https was not tried.
- PHILIPPINE NATIONAL BANK (SG, `not_reached`, `www.pnb.com.ph`): same pattern.
- CREDIT INDUSTRIEL ET COMMERCIAL (SG, `not_reached`, `www.cic.com.sg` and
  `www.cic.asia`): http `robots.txt` 500 on `cic.com.sg`; later
  `https://www.cic.com.sg` redirected off-domain to `www.cic.asia`, which was
  not fetched. No robots.txt row for `cic.asia` in run 1.

A larger set of run 1 hosts had `robots.txt` asked over http only (61 http
requests, every one HTTP 500). Many census pages were then read on those
hosts. That was the old crawler's http-fallback bug, not a version 3
unreadable decision. Those hosts need a proper https `robots.txt` read before
they are classed as readable or unreadable. They are not added to the list
above. Among them, hosts that already have a 200 page backing
`no_consumer_card` or `in_repository` (for example `www.ubs.com`,
`arabbank.com`, `bankofamerica.com`, `db.com`, `hkbea.com.sg`, `jpmorgan.com`,
`ocbc.com`) should be treated as "https robots not yet known", not as confirmed
blind evidence.

## Appendix: same-host robots.txt redirects that run 1 did not follow

These are not unreadable under version 3, because a redirect of `robots.txt` to
a host in the same official list (here, the same host after stripping `www`)
must be followed. Run 1 stopped at the 301/302. The census conclusions below
rest on pages read without a completed https robots decision.

- E.SUN COMMERCIAL BANK, LTD. (`out_of_scope_wholesale`): `www.esunbank.com`
  301 to `https://www.esunbank.com/seo/www/robots.txt`
- TAIPEI FUBON COMMERCIAL BANK CO., LTD. (`no_consumer_card`): `www.fubon.com`
  302 to a not-found HTML page on the same host
- ICICI BANK LIMITED (`no_consumer_card`): `www.icicibank.com.sg` 301 to
  `https://www.icicibank.com.sg/retail-banking`
- MACQUARIE BANK LIMITED (`no_consumer_card`): `www.macquarie.com` 302 to
  `https://www.macquarie.com/assets/macq/robots.txt.html`
- STATE BANK OF INDIA (`no_consumer_card`): `sg.statebank` 301 to
  `https://sg.statebank`
- Maybank Islamic Berhad (`same_group`): `www.maybank.com` 302 to
  `https://www.maybank.com/en/404-error.page`. In a later 12 Nov fetch that
  target returned 200 HTML, and `pipeline/fetcher.py` treated it as `rules`
  (an HTML 404 page, likely with no robots directives). The Islamic catalogue
  evidence itself was not in the run 1 log as a 200 page (the first run noted
  timeouts); a later follow-up read it.

Bank Rakyat's `robots.txt` 302'd to a JPEG on the same host. The census result
is `in_repository` by legal name, with a note that the site was not readable.

## Counts

- Draft: 11 rows, 12 hosts, described as all 403.
- Run 1 https 403: 11 hosts, 12 requests, no 401.
- Overlap of those two host sets: 5.
- Corrected list, confirmed unreadable plus a 200 page that supports the
  conclusion: 7 rows (6 hosts; Public Bank and Public Islamic Bank share
  `www.pbebank.com`).
- Plus 5 `not_reached` rows on a 403 host, including 2 the draft missed
  (Emirates NBD and UniCredit).
- Plus 4 `not_reached` rows on a timeout, TLS error, or off-domain robots
  redirect, with no 200 page.
- Removed from the unreadable list: the 6 draft hosts that were not unreadable
  in run 1, in particular China CITIC Bank International (404, allowed).

The original draft file is left in git history. This file is the corrected
list. Rechecks wait for the go.
