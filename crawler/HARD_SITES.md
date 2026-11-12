# Sites that are hard to crawl

Use this file when a site does not answer, shows no text without JavaScript, or blocks the crawler. Section 2 of `crawler/RULES.md` is the rule. This file is the method.

The purpose is to read what the site shows to every visitor. The purpose is not to get past a control that the site put in place. If the site says no, the answer is no, and the issuer is recorded as blocked.
An unreadable `robots.txt` is not a no: it states no rule, so the host is crawled and the pages are marked `robots_unreadable` for a recheck (RULES.md section 2, step 3).

## 1. The tool

Make every request with `pipeline/fetcher.py`. It reads `robots.txt` first, keeps 1.5 seconds between paced requests to one host (raise it with `--min-gap` or `CRAWLER_MIN_GAP`; do not go under 1.5), stops at hosts that are not official, and writes each request to a private log with its start time to the millisecond. Every log line includes `mode` (`plain`, `browser` or `real_chrome`) and `min_gap_s`. The per-host gap applies to document loads and to xhr and fetch calls, in every browser mode. Scripts and style sheets can go without a gap. A probe also keeps the page text in a private file under `raw/`.

For plain and headless-browser requests, set the user agent that the maintainer chose. In real-Chrome mode do not set a user agent; Chrome sends its own.


```bash
export CRAWLER_USER_AGENT="<the user agent that the maintainer gave you>"
```

Look at one page before you crawl a site:

```bash
python pipeline/fetcher.py probe my-maybank https://www.maybank2u.com.my/maybank2u/malaysia/en/personal/cards/credit_cards_listing.page
```

```bash
python pipeline/fetcher.py probe my-maybank https://www.maybank2u.com.my/maybank2u/malaysia/en/personal/cards/credit_cards_listing.page --browser
```

```bash
python pipeline/fetcher.py probe my-maybank https://www.maybank2u.com.my/maybank2u/malaysia/en/personal/cards/credit_cards_listing.page --real-chrome --min-gap 30
```

The report gives the status, the page class, the blocked list and the measured gaps. The page classes are:

| Class | Meaning | What to do |
|---|---|---|
| `ok` | The page has its text. | Read it. |
| `js_shell` | The page has scripts and almost no text. | Step 3 of the ladder. |
| `bot_wall` | The site answered with a block page. | Step 4 of the ladder, once. If it is still a block page, stop. Section 4. |
| `captcha` | The site asks for a test that only a person can do. | Stop. Section 4. |
| `login` | The page asks for a password. | Stop. It is not a public page. |
| `error` | Network error or an HTTP error. | Step 1 of the ladder. |

## 2. The ladder

Go down one step at a time. Stop at the first step that gives the text. Write the step that worked in your report.

1. **Plain request.** `fetcher.get(url)`. An unreadable `robots.txt` does not stop here: the page is read and its record is marked `robots_unreadable`. Go down the ladder as normal; the flag travels with the fact.
2. **Network error, timeout or a protocol error, on `robots.txt` or on a page.** Try one time more after 10 minutes. If the browser reported an HTTP/2 protocol error, start the browser with the option `--disable-http2`. That is a normal client setting. If the plain request and the browser fail in the same way two times, go to section 4 with the class `network_unreachable`. When the site refuses the plain request and the headless browser with a block page, rather than leaving the host unreachable, the real Chrome rung below is allowed once.
3. **The page needs JavaScript (`js_shell`).** Do these in order:
   1. Look in the page source for the data: a JSON block in a script tag, or a link to a JSON file on an official host. Many listings load one public JSON file. Fetch that file with `fetcher.get`. This is the best source: it is complete and it needs no browser.
   2. Read `sitemap.xml` on the host for the card pages and the offer pages.
   3. Render the page with `BrowserFetcher(fetcher).render(url)`. The browser sends each of its requests through the same checks.
4. **Plain requests and the headless browser were refused.** One real Chrome attempt is allowed, and only for a host in `config/real_chrome_hosts.json`. This step gets past a block page. The maintainer approved it for the listed hosts on 12 Nov 2026. It is a real browser; Chrome sends its own user agent, with no fingerprint change. If the host is not on the approved list, do not run real-Chrome mode.

   ```bash
   python pipeline/fetcher.py probe <issuer_id> <url> --real-chrome --min-gap 30
   ```

   `--real-chrome` (or `BrowserFetcher(fetcher, real_chrome=True)`) launches installed Google Chrome through Playwright with `channel="chrome"` and `headless=False`, using `launch_persistent_context`. On a server, run it under a virtual display such as Xvfb. The profile directory is `CRAWLER_CHROME_PROFILE`, or `.cache/chrome-profile` when that is unset. That directory is gitignored. Do not commit it, and do not point it at a person's signed-in profile.

   Do not set a user agent in this mode. Chrome sends its own. Do not add a stealth plugin, a proxy, a new IP, or a captcha solver. Those stay forbidden in section 3. If Chrome or a display is missing, or if the host is not in `config/real_chrome_hosts.json`, the probe raises `RealChromeError` instead of waiting.

   In real-Chrome mode, `robots.txt` is read with `page.goto` in that same Chrome context, and the log line says `real_chrome`. A plain urllib fetch is logged as `plain`, which is the mode that actually fetched it.

   The browser runs in a child process. The parent waits at most `--hard-timeout` seconds (`CRAWLER_HARD_TIMEOUT`, default 150). If the child does not return, the parent kills the whole process group and logs `timeout`. The parent does not call Playwright, so it cannot stay blocked after the child is gone.

   The per-host gap applies to document loads and to xhr and fetch calls, in every browser mode, including `robots.txt` and the page. Scripts and style sheets can go without a gap. A request that must not be sent, such as a third-party script, is answered with an empty 204 so the page does not stall on an abort. A same-origin call that the page makes itself, with a method that is not GET, is permitted after a robots check, is logged with its method and URL, and is not changed. A non-same-origin call that is not GET is not sent. The page waits for `domcontentloaded`, then for `networkidle` only up to the settle cap, and the HTML is read even if that cap elapses. `fetched_at` is the start time of the page request, after the wait. If one of the page's own data calls (xhr or fetch) was blanked or failed, the page class is not `ok`.

   `--min-gap SECONDS` or `CRAWLER_MIN_GAP` raises the per-host gap. The default stays 1.5 seconds. A slow run can use 30. The spacing report still reads the log.

   A network portal (Mastercard, Visa and the other rows in `networks.json`) is probed with the country, not an issuer id:

   ```bash
   python pipeline/fetcher.py probe --url https://specials.priceless.com/en-my/homepage --country MY --real-chrome --min-gap 30
   ```

   If this attempt is also a block page or a captcha, stop. Section 4.
5. **The listing shows only a part.** Use `render(url, expand_selector=..., scroll_times=...)` for a load more button, a next page link, tabs or an endless scroll. Count the tiles before and after. Set `listing_complete` to true only when a click or a scroll adds no tile.
6. **A second official host.** If the issuer shows the same cards or offers on a second host of its own (for example a group site or a promotions site), report the host and the official page that links to it. The maintainer adds it to `official_domains` first.
7. **Documents.** Product disclosure sheets, fee tables and terms are often PDF files on the same host. They are official sources for card facts and offer terms.
8. **Nothing works.** Section 4.

Quotes from a rendered page come from the rendered text, not from the page source. Set `via` to `browser` on the fetch record, including a real Chrome run. The log line records the mode.

## 3. What you must not do

These actions get past a control. They are not permitted, for any site, for any reason.

1. Do not use a proxy service, a VPN, a residential proxy or a change of IP address to get past a block.
2. Do not use a user agent that is not true. Do not use the name of a search engine. Do not use a stealth plugin or change the browser fingerprint.
3. Do not solve or pass a captcha, by yourself or with a service.
4. Do not sign in, register, or use a session or a cookie from a person's account.
5. Do not call an endpoint of a mobile app, or an endpoint that the public page does not load.
6. Do not send a request faster or in parallel to finish sooner.
7. Do not use a copy of the page from a search engine cache, a web archive or an aggregator. They are not official sources.
8. Do not try again more than the ladder says. Repeated requests to a host that blocks you are not permitted.

## 4. When the site says no

1. Record the URL in `run.blocked` with the reason and a short `detail`:

| Reason | Use it when |
|---|---|
| `robots_unreachable` | `robots.txt` did not give status 200, 404 or 410. The host is still crawled, so this row flags every fact read blind. |
| `robots_disallow` | `robots.txt` does not permit the path. |
| `bot_wall` | The site answered with a block page. |
| `captcha` | The site asks for a captcha. |
| `login_required` | The page needs a sign-in, a form or typed text. |
| `network_unreachable` | The host does not answer from the crawl machine, two times, 10 minutes apart. |
| `app_only` | The site says that the offers are in its mobile app only. |
| `off_domain_redirect` | An official URL sends you to a host that is not official. Give `redirect_to`. |
| `timeout`, `http_error`, `not_found` | One page failed. |

2. Keep `listing_complete` false. Hand in what you read from the pages that did answer. A host read with an unreadable `robots.txt` still hands in its facts, flagged.
3. Do not fill the gap from memory, from an old crawl or from a different site.
4. Report the issuer in the list of issuers that are not complete, with the class and the URL.
5. The maintainer decides the next step. The choices are: a run from the maintainer's own network in the country of the issuer, with this same tool and these same rules; a request to the issuer for a feed or for permission, with the issuer submission form of the repository; or no crawl. The crawler does not make this choice.

## 5. Maybank Malaysia (`my-maybank`)

What is known, from the earlier runs:

- `maybank2u.com.my` and `maybank.com` did not answer from the crawl machine: a timeout with a plain request, and an HTTP/2 protocol error in a browser. The cause is not known. It can be the network of the crawl machine or a control of the site.
- The repository has 33 Maybank cards from a hand copy of the listing. They are not confirmed under the rule. It has no Maybank offer.
- The census found the Maybank Islamic card listing on `maybank.com`. That host is not in `official_domains` of `my-maybank`.

Do this, and stop at the first step that fails:

1. Run the probe on the card listing with a plain request. Report the class and the detail.
2. If the class is `error`, do step 2 of the ladder: one more try after 10 minutes, then one browser probe with `--disable-http2`.
3. If a probe gives `ok` or `js_shell`, continue with the ladder for the cards, then for the offers at `https://www.maybank2u.com.my/maybank2u/malaysia/en/personal/promotions/maybank_cards.page`.
4. If all probes fail, record `network_unreachable` with the error text, and report. Do not try a different route to the site.
5. Report `maybank.com` to the maintainer as a possible official host, with the official page that links to it.

## 6. Notes for sites seen so far

Add a line here when a run finds the method for a site. Give the fact and the date, with no private data.

| Issuer | What was found | Date |
|---|---|---|
| `sg-cimb` | The promotions listing and the card listing load from public `.list` endpoints on `cimb.com.sg`. The merchant deals are on `deals.cimb.com`, which loads a public JSON listing. | 2026-11-11 |
| `sg-ocbc` | The promotions page loads one public JSON file on `ocbc.com`. The terms are popups on the listing: use terms scope `listing_popup`. | 2026-11-09 |
| `my-affin` | The card list loads from a public JSON file on `affinalways.com`. | 2026-11-11 |
| `my-bank-rakyat` | Every request, `robots.txt` included, was sent to an error page. Status: blocked. | 2026-11-11 |
| `my-maybank` | Section 5. | 2026-11-11 |
| `sg-trust` | The correct host is `trustbank.sg` (in the census pull request). | 2026-11-11 |
