# Robots policy: read the host anyway, and the recheck list

2026-11-12. Amends RULES.md section 2 step 3 and HARD_SITES.md. Applies to `pipeline/fetcher.py`,
`schema/observation.schema.json` and `tools/check_observations.py`.

## What changed, and why

`robots.txt` answering 401, 403 or 429 states no rule. It states a guard. Under version 2 of the rule
that also meant "do not read this host", so a bot guard cost us the whole issuer. Run 1 did read those
hosts anyway, which left its conclusions unsupported by the rule. Version 3 closes that gap the other
way round:

- 200: obey. 404 and 410: no rules, crawl.
- Every other answer - 401, 403, 429, 5xx, timeout, TLS error, redirect loop, too many redirects,
  redirect to a host that is not official: **unreadable, crawl anyway.**
- Each page read that way carries `robots_unreadable: true`, and the host keeps a `run.blocked` row
  with reason `robots_unreachable`. The blocked row is a flag, not "nothing was read".
- The gate enforces the pair: a fetch under an unreadable robots must be flagged, a flag needs the
  blocked row, and a flagged fetch is accepted as evidence.
- Such a page is blind evidence, kept and flagged for recheck. It is no longer dropped, and it is not
  re-fetched in the same run.

## Recheck list: conclusions resting on a 401/403 `robots.txt`

Every census row below cites evidence on a host that answered 403 to `robots.txt`. Under the old rule
its conclusion was unsupported; under version 3 the read stands but must be rechecked in a run where
`robots.txt` answers.

| issuer / entry | country | current result | host | what rests on it |
|---|---|---|---|---|
| PETRONAS Dagangan Berhad | MY | `no_consumer_card` | `www.mymesra.com.my` | SmartPay fleet card for businesses |
| RHB BANK BERHAD | SG | `no_consumer_card` | `www.rhbgroup.com.sg` | personal menu has deposits, loans, insurance, investments, no credit card |
| UBS AG | SG | `no_consumer_card` | `www.ubs.com` | SG wealth page lists planning, investing, financing, no card; the SG home page is 403 |
| BANK OF TAIWAN | SG | `out_of_scope_wholesale` | `www.bot.com.tw` | no SG consumer card on the official site |
| CHINA CITIC BANK INTERNATIONAL LIMITED | SG | `out_of_scope_wholesale` | `www.cncbinternational.com` | no SG consumer card on the official site |
| BANK OF INDIA | SG | `not_reached` | `www.boi.com.sg` | 403 challenge page |
| EUROCLEAR BANK SA/NV | SG | `not_reached` | `www.euroclear.com` | 403 |
| PHILIPPINE NATIONAL BANK | SG | `not_reached` | `www.pnb.com.ph` | 403 |
| QATAR NATIONAL BANK (Q.P.S.C.) | SG | `not_reached` | `www.qnb.com` | 403 |
| COOPERATIEVE RABOBANK U.A. | SG | `not_reached` | `www.rabobank.com` | 403 |
| CREDIT INDUSTRIEL ET COMMERCIAL | SG | `not_reached` | `www.cic.com.sg`, `www.cic.asia` | `cic.com.sg` redirects off-domain to `cic.asia`, both 403 |

The three `no_consumer_card` rows are the ones that matter most: each asserts a negative from a page
read while the rules were hidden. The `not_reached` rows change least - they already said blocked, and
version 3 gives them a route to a real answer.

### How this list was derived, and its limit

The run 1 private fetch log is not on this machine, so the 33 requests on 11 hosts could not be read
off it. The list is instead derived from the census evidence URLs: every distinct host in
`ISSUER_CENSUS.md` was asked for `robots.txt` once on 2026-11-12 (182 hosts, 1.5 s apart, no page
fetched), and the rows above are the ones citing a host that answered 401/403.

That gives **12 hosts, not 11**, and all of them 403, no 401. The difference is one host, and it is
not resolved: statuses move between runs, and a host that was 401 or 403 in run 1 can answer
differently today. Reconcile against the real log before this list is treated as final.

## Appendix: the rest of what the sweep found

These also answered with an unreadable `robots.txt`. Under version 3 they no longer stop a host, so
they are future recheck material rather than current blockers.

- 503: `ca-indosuez.com`, `card.paydee.co` (1 census row - the Paydee corporate-card decision).
- Network error, 23 hosts, including `www.pbebank.com` (3 rows - Public Bank and Public Islamic Bank),
  `www.agrobank.com.my` (1), `www.ccb.com` (1), `www.bankofchina.com` (2), `www.sgcib.com`,
  `www.ucobank.com`, `www.ing.nl`, `www.indian-bank.com`, `www.koexbank.co.kr`, `www.kol.co.kr`,
  `www.bbl.co.th`, `www.ktb.co.th`, `www.bdo.com.ph`, `www.hncb.com.tw`, `www.spdb.com.cn`,
  `www.ptbankmandiri.com.sg`, `www.mb.seb.se`, `www.mitsubishi-trust.co.jp`, `www.natwestmarkets.com`,
  `www.tdbank.ca`, `iob.com`, `www.alahli.com`, `www.bankcomm.com`.
- `robots.txt` redirect off-domain: `www.bankofchina.com`, `www.ntrs.com`, `www.taishinbank.com.tw`.
- `robots.txt` redirect with no target: `www.abchina.com`.

## Maybank Malaysia, HARD_SITES section 5

All three steps failed from this machine, so Maybank stays `network_unreachable`.

| step | result |
|---|---|
| 1. plain probe, card listing, 2026-11-12T01:50:27+08:00 | `TimeoutError: The read operation timed out` on `robots.txt`, then on the page |
| 2. the same probe 10 minutes later, 2026-11-12T02:03:08+08:00 | same timeout on both |
| 2. browser probe with `--disable-http2`, 2026-11-12T03:07:12+08:00 | `robots.txt` network error; page `net::ERR_FAILED` |

Spacing held at 30.1 s and 33.0 s. `--disable-http2` was honoured; the probe previously ignored it
(passing it now sets the browser launch argument). Nothing further was tried on Maybank, per section 5.
`maybank.com` remains unreported as an official host: the Islamic catalogue on it was read in the
census, and `official_domains` for `my-maybank` still lists only `maybank2u.com.my`.
