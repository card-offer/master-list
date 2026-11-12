#!/usr/bin/env python3
"""The reference fetcher for the crawler. It applies section 2 of crawler/RULES.md in code.

    python pipeline/fetcher.py probe <issuer_id> <url>       one page, with a report of what the site did
    python pipeline/fetcher.py probe <issuer_id> <url> --browser

Use this module for every request of a crawl. Do not make a request to a crawl host by any other path.

What it enforces:
- Only https, and only hosts in the official_domains that the caller gives.
- robots.txt is read first for each host. 200: obey. 404 or 410: no rules. Every other answer, an error,
  a timeout, a redirect loop, more than 5 redirects, or a redirect to a host that is not official:
  robots.txt is unreadable. The host is still crawled and every page read from it is marked
  robots_unreadable and listed in `rechecks`, so a guard that hides robots.txt costs us flags, not data.
- One request at a time, and 1.5 seconds or more between the starts of two requests to one host, on a
  monotonic clock. Redirect hops and robots.txt requests count.
- No sign-in, registration or application form URLs. A session id is removed from a recorded URL.
- 429 or 503 on a page stops the host for the rest of the run.
- Every request is one line in a private JSONL log, with the wall time to the millisecond.
- The headless browser sends each of its requests through the same checks.

Only the standard library is needed for plain requests. The browser path needs Playwright.
"""
import datetime
import hashlib
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlsplit, urlunsplit

MIN_GAP = 1.5
MAX_REDIRECTS = 5
USER_AGENT_TOKEN = "card-offer-crawler"
SKIP_URL = re.compile(
    r"(?i)(?:log-?in|sign-?in|sign-?on|log-?on|sign-?up|signup|register|registration|/auth\b|oauth|/sso\b"
    r"|e-?banking|internet-?banking|online-?banking|apply-?now|/apply\b|application-?form|/otp\b|password)"
)
SESSION_ID = re.compile(r"(?i);jsessionid=[^?#/;]*|([?&])(?:jsessionid|phpsessid|sessionid|sid|aspsessionid\w*)=[^&#]*&?")
BLOCK_MARKERS = (
    ("captcha", re.compile(r"(?i)captcha|are you a robot|verify you are human|challenge-platform|hcaptcha|recaptcha")),
    ("bot_wall", re.compile(r"(?i)access denied|request unsuccessful|incapsula incident|reference #\d+\.[0-9a-f]+|"
                            r"pardon our interruption|unusual traffic|bot detection|attention required")),
    ("login", re.compile(r"(?i)<input[^>]+type=[\"']?password")),
)


def host_of(url):
    host = (urlsplit(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def clean_url(url):
    """The URL to record: no fragment and no session id."""
    parts = urlsplit(url)
    url = urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))
    url = SESSION_ID.sub(lambda m: m.group(1) or "", url)
    return url.rstrip("?&")


def wall_now():
    return datetime.datetime.now(datetime.timezone.utc).astimezone()


class Robots:
    """robots.txt rules for one host (RFC 9309): longest match wins, Allow wins a tie."""

    def __init__(self, text=""):
        self.groups = []
        agents, rules, last_was_agent = [], [], False
        for raw in text.splitlines():
            line = raw.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            key, value = (part.strip() for part in line.split(":", 1))
            key = key.lower()
            if key == "user-agent":
                if not last_was_agent and (agents or rules):
                    self.groups.append((agents, rules))
                    agents, rules = [], []
                agents.append(value.lower())
                last_was_agent = True
            elif key in ("allow", "disallow"):
                rules.append((key == "allow", value))
                last_was_agent = False
            else:
                last_was_agent = False
        if agents or rules:
            self.groups.append((agents, rules))

    def _rules(self, token):
        named = [rules for agents, rules in self.groups if any(a != "*" and a in token.lower() for a in agents)]
        if named:
            return [rule for rules in named for rule in rules]
        return [rule for agents, rules in self.groups if "*" in agents for rule in rules]

    def allowed(self, url, token=USER_AGENT_TOKEN):
        parts = urlsplit(url)
        path = parts.path or "/"
        if parts.query:
            path += "?" + parts.query
        best_len, best_allow = -1, True
        for allow, pattern in self._rules(token):
            if not pattern:
                continue
            regex = "".join(".*" if ch == "*" else re.escape(ch) for ch in pattern.rstrip("$"))
            regex += "$" if pattern.endswith("$") else ""
            if re.match(regex, path) and (len(pattern) > best_len or (len(pattern) == best_len and allow)):
                best_len, best_allow = len(pattern), allow
        return best_allow


def classify(status, body_text):
    """What a page answer is: ok, js_shell, captcha, bot_wall, login or error. For the report, not for evidence."""
    if status is None or status >= 400:
        for name, pattern in BLOCK_MARKERS[:2]:
            if pattern.search(body_text or ""):
                return name
        return "error"
    text = body_text or ""
    for name, pattern in BLOCK_MARKERS:
        if pattern.search(text):
            return name
    visible = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>|<[^>]+>", " ", text)
    words = len(re.findall(r"\w{2,}", visible))
    scripts = len(re.findall(r"(?i)<script\b", text))
    if words < 80 and scripts >= 1:
        return "js_shell"
    return "ok"


def urllib_transport(url, timeout, user_agent):
    """One request, no redirect following. Returns (status, headers, body). Raises OSError on a network failure."""

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    request = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept-Language": "en"})
    try:
        with opener.open(request, timeout=timeout) as response:
            return response.status, dict(response.headers), response.read(5_000_000)
    except urllib.error.HTTPError as err:
        return err.code, dict(err.headers or {}), err.read(200_000) if err.fp else b""


class PoliteFetcher:
    def __init__(self, log_path, official_domains, user_agent, min_gap=MIN_GAP, timeout=30.0, transport=urllib_transport,
                 clock=time.monotonic, sleep=time.sleep, wall=wall_now, allow_http_hosts=()):
        if min_gap < MIN_GAP:
            raise ValueError(f"the gap for one host is {MIN_GAP} seconds or more")
        if not user_agent or re.search(r"(?i)googlebot|bingbot|baiduspider|yandex", user_agent):
            raise ValueError("give a true user agent. Do not use the name of a search engine.")
        self.log_path = log_path
        self.official = {d.lower()[4:] if d.lower().startswith("www.") else d.lower() for d in official_domains}
        self.user_agent, self.min_gap, self.timeout = user_agent, float(min_gap), timeout
        self.transport, self.clock, self.sleep, self.wall = transport, clock, sleep, wall
        self.allow_http_hosts = set(allow_http_hosts)
        self.lock = threading.Lock()
        self.last_start, self.robots, self.stopped = {}, {}, {}
        self.fetches, self.blocked, self.rechecks = [], [], []
        self.unreadable = set()  # hosts whose robots.txt could not be read this run
        os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)

    # ---- log
    def log(self, **row):
        row = {"ts": self.wall().isoformat(timespec="milliseconds"), "mono": round(self.clock(), 6), **row}
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    def _block(self, url, reason, **extra):
        row = {"url": clean_url(url), "reason": reason, **extra}
        if row not in self.blocked:
            self.blocked.append(row)
        self.log(event="not_fetched", url=clean_url(url), host=host_of(url), reason=reason, **extra)
        return {"url": clean_url(url), "status": None, "not_fetched": reason, **extra}

    # ---- one request, spaced
    def _request(self, url, kind):
        host = host_of(url)
        with self.lock:
            last = self.last_start.get(host)
            gap = None
            if last is not None:
                wait = self.min_gap - (self.clock() - last)
                if wait > 0:
                    self.sleep(wait)
                gap = round(self.clock() - last, 3)
            start_mono = self.last_start[host] = self.clock()
            started = self.wall()
            try:
                status, headers, body = self.transport(url, self.timeout, self.user_agent)
                error = None
            except OSError as err:
                status, headers, body, error = None, {}, b"", f"{type(err).__name__}: {str(err)[:160]}"
            self.log(event="request", kind=kind, host=host, url=clean_url(url), status=status, gap_s=gap, error=error,
                     start_mono=round(start_mono, 6), start_ts=started.isoformat(timespec="milliseconds"),
                     location=headers.get("Location") or headers.get("location"))
            return status, headers, body, started, error

    def _scheme_ok(self, url):
        parts = urlsplit(url)
        return parts.scheme == "https" or (parts.scheme == "http" and parts.netloc in self.allow_http_hosts)

    # ---- robots
    def robots_for(self, url):
        """Return ('rules', Robots), ('allow_all', None) or ('unreadable', reason) for the host of the URL."""
        parts = urlsplit(url)
        key = parts.netloc.lower()
        if key in self.robots:
            return self.robots[key]
        current, seen, decision = f"{parts.scheme}://{parts.netloc}/robots.txt", set(), None
        for _hop in range(MAX_REDIRECTS + 1):
            if current in seen:
                decision = ("unreadable", "redirect_loop")
                break
            seen.add(current)
            status, headers, body, _started, error = self._request(current, "robots")
            if error or status is None:
                decision = ("unreadable", "network_error")
            elif status == 200:
                decision = ("rules", Robots(body.decode("utf-8", "replace")))
            elif status in (404, 410):
                decision = ("allow_all", None)
            elif status in (301, 302, 303, 307, 308):
                target = urljoin(current, headers.get("Location") or headers.get("location") or "")
                if not target or target == current:
                    decision = ("unreadable", "redirect_without_target")
                elif host_of(target) not in self.official or not self._scheme_ok(target):
                    decision = ("unreadable", "redirect_to_a_host_that_is_not_official")
                else:
                    current = target
                    continue
            else:
                decision = ("unreadable", f"http_{status}")
            break
        if decision is None:
            decision = ("unreadable", "too_many_redirects")
        self.robots[key] = decision
        self.log(event="robots_decision", host=host_of(url), state=decision[0],
                 reason=decision[1] if decision[0] == "unreadable" else None)
        if decision[0] == "unreadable":
            host = host_of(url)
            self.unreadable.add(host)
            self._block(f"{parts.scheme}://{parts.netloc}/robots.txt", "robots_unreachable", detail=decision[1])
            self.rechecks.append({"url": clean_url(f"{parts.scheme}://{parts.netloc}/robots.txt"), "host": host,
                                  "reason": "robots_unreachable", "detail": decision[1]})
        return decision

    def may_fetch(self, url):
        """None when the URL can be requested, or the reason why not. Reads robots.txt when needed."""
        if not self._scheme_ok(url):
            return "not_https"
        if host_of(url) not in self.official:
            return "host_not_official"
        if SKIP_URL.search(urlsplit(url).path):
            return "login_required"
        if host_of(url) in self.stopped:
            return self.stopped[host_of(url)]
        state, value = self.robots_for(url)
        if state == "unreadable":
            return None  # read the page anyway; the record carries robots_unreadable
        if state == "rules" and not value.allowed(url):
            return "robots_disallow"
        return None

    # ---- a page
    def get(self, url, kind="page"):
        """Fetch one URL. Returns a dict: url, final_url, status, body, text, fetched_at, class, or not_fetched."""
        if urlsplit(url).scheme == "http" and urlsplit(url).netloc not in self.allow_http_hosts:
            url = "https://" + url[len("http://"):]
        current, seen, unreadable = url, set(), False
        for _hop in range(MAX_REDIRECTS + 1):
            reason = self.may_fetch(current)
            unreadable = unreadable or host_of(current) in self.unreadable
            if reason == "host_not_official" and current != url:
                return self._block(url, "off_domain_redirect", redirect_to=clean_url(current))
            if reason:
                return self._block(current, reason)
            if current in seen:
                return self._block(url, "http_error", detail="redirect_loop")
            seen.add(current)
            status, headers, body, started, error = self._request(current, kind if current == url else "redirect_hop")
            if error:
                return self._block(current, "timeout" if "imeout" in error else "http_error", detail=error)
            if status in (429, 503):
                self.stopped[host_of(current)] = "http_error"
                return self._block(current, "http_error", detail=f"http_{status}, the host is stopped for this run")
            if status in (301, 302, 303, 307, 308):
                target = urljoin(current, headers.get("Location") or headers.get("location") or "")
                if not target:
                    return self._block(current, "http_error", detail="redirect_without_target")
                current = target
                continue
            text = body.decode("utf-8", "replace") if body else ""
            result = {
                "url": clean_url(url), "final_url": clean_url(current), "status": status, "body": body, "text": text,
                "fetched_at": started.isoformat(timespec="seconds"), "sha256": hashlib.sha256(body).hexdigest(),
                "class": classify(status, text), "via": "http",
            }
            if unreadable:
                result["robots_unreadable"] = True
            self.fetches.append({key: result[key] for key in ("url", "final_url", "status", "fetched_at")})
            if status == 404:
                self._block(current, "not_found")
            elif result["class"] in ("captcha", "bot_wall"):
                self._block(current, result["class"])
            elif result["class"] == "login":
                self._block(current, "login_required")
            return result
        return self._block(url, "http_error", detail="too_many_redirects")


class BrowserFetcher:
    """A headless browser whose every request goes through the same robots, spacing and log as PoliteFetcher.

    Requests to hosts that are not official are stopped. Images, media and fonts are stopped: text does not need them.
    The only permitted actions are scroll and a click on a control that shows more of the same public content
    (load more, next page, tab, accordion, category filter). No typing, no sign-in, no form.
    """

    DROP_TYPES = {"image", "media", "font"}

    def __init__(self, fetcher, launch_args=()):
        self.fetcher = fetcher
        self.launch_args = list(launch_args)

    def _route(self, route, request):
        url = request.url
        if request.resource_type in self.DROP_TYPES or url.startswith(("data:", "blob:", "about:")):
            return route.abort()
        if request.method != "GET":
            self.fetcher.log(event="not_fetched", url=clean_url(url), host=host_of(url), reason="not_a_get_request")
            return route.abort()
        reason = self.fetcher.may_fetch(url)
        if reason:
            self.fetcher.log(event="not_fetched", url=clean_url(url), host=host_of(url), reason=reason, via="browser")
            return route.abort()
        host = host_of(url)
        with self.fetcher.lock:
            last = self.fetcher.last_start.get(host)
            gap = None
            if last is not None:
                wait = self.fetcher.min_gap - (self.fetcher.clock() - last)
                if wait > 0:
                    self.fetcher.sleep(wait)
                gap = round(self.fetcher.clock() - last, 3)
            start_mono = self.fetcher.last_start[host] = self.fetcher.clock()
            start_ts = self.fetcher.wall().isoformat(timespec="milliseconds")
            try:
                response = route.fetch(max_redirects=0, timeout=self.fetcher.timeout * 1000)
            except Exception as err:  # Playwright raises its own error types
                self.fetcher.log(event="request", kind=request.resource_type, via="browser", host=host, url=clean_url(url),
                                 status=None, gap_s=gap, error=str(err)[:160], start_mono=round(start_mono, 6), start_ts=start_ts)
                return route.abort()
            self.fetcher.log(event="request", kind=request.resource_type, via="browser", host=host, url=clean_url(url),
                             start_mono=round(start_mono, 6), start_ts=start_ts,
                             status=response.status, gap_s=gap, error=None, location=response.headers.get("location"))
            if response.status in (429, 503) and request.resource_type == "document":
                self.fetcher.stopped[host] = "http_error"
        return route.fulfill(response=response)

    def render(self, url, settle_ms=3000, expand_selector=None, max_clicks=20, scroll_times=0):
        """Open one page and return its rendered text. expand_selector is a 'load more' or tab control."""
        from playwright.sync_api import sync_playwright

        reason = self.fetcher.may_fetch(url)
        if reason:
            return self.fetcher._block(url, reason)
        unreadable = host_of(url) in self.fetcher.unreadable
        started = self.fetcher.wall()
        with sync_playwright() as play:
            browser = play.chromium.launch(args=self.launch_args, executable_path=os.environ.get("CRAWLER_CHROMIUM") or None)
            page = browser.new_context(user_agent=self.fetcher.user_agent).new_page()
            page.route("**/*", self._route)
            try:
                response = page.goto(url, wait_until="domcontentloaded", timeout=self.fetcher.timeout * 3000)
                page.wait_for_timeout(settle_ms)
                for _ in range(scroll_times):
                    page.mouse.wheel(0, 20000)
                    page.wait_for_timeout(1500)
                clicks = 0
                while expand_selector and clicks < max_clicks:
                    control = page.locator(expand_selector).first
                    if control.count() == 0 or not control.is_visible():
                        break
                    control.click()
                    clicks += 1
                    self.fetcher.log(event="action", kind="expand_click", url=clean_url(url), selector=expand_selector, n=clicks)
                    page.wait_for_timeout(settle_ms)
                status = response.status if response else None
                final_url, html, text = page.url, page.content(), page.inner_text("body")
            except Exception as err:
                browser.close()
                return self.fetcher._block(url, "timeout" if "imeout" in str(err) else "http_error", detail=str(err)[:160])
            browser.close()
        if host_of(final_url) not in self.fetcher.official:
            return self.fetcher._block(url, "off_domain_redirect", redirect_to=clean_url(final_url))
        result = {
            "url": clean_url(url), "final_url": clean_url(final_url), "status": status, "body": html.encode("utf-8"),
            "text": text, "fetched_at": started.isoformat(timespec="seconds"),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "class": classify(status, html), "via": "browser",
        }
        if unreadable:
            result["robots_unreadable"] = True
        if result["class"] == "js_shell" and len(re.findall(r"\w{2,}", text)) >= 80:
            result["class"] = "ok"
        self.fetcher.fetches.append({key: result[key] for key in ("url", "final_url", "status", "fetched_at")})
        return result


def spacing_report(log_path):
    """Smallest and mean gap between request starts for each host, from the monotonic start times in a log."""
    starts = {}
    with open(log_path, encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            if row.get("event") == "request":
                starts.setdefault(row["host"], []).append(row["start_mono"])
    report = {}
    for host, times in starts.items():
        gaps = [round(b - a, 3) for a, b in zip(times, times[1:])]
        report[host] = {"requests": len(times), "min_gap_s": min(gaps) if gaps else None,
                        "mean_gap_s": round(sum(gaps) / len(gaps), 3) if gaps else None,
                        "gaps_under_min": sum(1 for gap in gaps if gap < MIN_GAP - 0.001)}
    return report


def main(argv):
    if len(argv) < 4 or argv[1] != "probe":
        print(__doc__)
        return 2
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    issuer_id, url = argv[2], argv[3]
    path = os.path.join(root, issuer_id[:2], "issuers.json")
    with open(path, encoding="utf-8") as fh:
        issuer = next(row for row in json.load(fh)["items"] if row["id"] == issuer_id)
    agent = os.environ.get("CRAWLER_USER_AGENT")
    if not agent:
        print("Set CRAWLER_USER_AGENT to the user agent that the maintainer chose.")
        return 2
    log = os.path.join(root, "raw", "logs", f"probe-{issuer_id}-{wall_now().strftime('%Y%m%dT%H%M%S')}.jsonl")
    fetcher = PoliteFetcher(log, issuer["official_domains"], agent)
    launch_args = [arg for arg in ("--disable-http2",) if arg in argv]
    result = (BrowserFetcher(fetcher, launch_args=launch_args).render(url)
              if "--browser" in argv else fetcher.get(url))
    shown = {key: value for key, value in result.items() if key not in ("body", "text")}
    shown["words"] = len(re.findall(r"\w{2,}", result.get("text") or ""))
    print(json.dumps({"result": shown, "blocked": fetcher.blocked, "rechecks": fetcher.rechecks,
                      "spacing": spacing_report(log), "log": log}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
