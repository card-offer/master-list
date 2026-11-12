#!/usr/bin/env python3
"""The reference fetcher for the crawler. It applies section 2 of crawler/RULES.md in code.

    python pipeline/fetcher.py probe <issuer_id> <url>       one page, with a report of what the site did
    python pipeline/fetcher.py probe <issuer_id> <url> --browser
    python pipeline/fetcher.py probe <issuer_id> <url> --real-chrome --min-gap 30
    python pipeline/fetcher.py probe --url <url> --country <cc> --real-chrome --min-gap 30

Use this module for every request of a crawl. Do not make a request to a crawl host by any other path.

What it enforces:
- Only https, and only hosts in the official_domains that the caller gives.
- robots.txt is read first for each host. 200: obey. 404 or 410: no rules. Every other answer, an error,
  a timeout, a redirect loop, more than 5 redirects, or a redirect to a host that is not official:
  robots.txt is unreadable. The host is still crawled and every page read from it is marked
  robots_unreadable and listed in `rechecks`, so a guard that hides robots.txt costs us flags, not data.
- One request at a time, and 1.5 seconds or more between the starts of two paced requests to one host,
  on a monotonic clock. Redirect hops and robots.txt requests count. --min-gap or CRAWLER_MIN_GAP may
  raise the gap. It cannot go under 1.5 seconds. In every browser mode the same gap applies to
  document loads and to xhr and fetch calls. Scripts and style sheets can go without a gap.
- No sign-in, registration or application form URLs. A session id is removed from a recorded URL.
  A same-origin call that the page makes itself, with a method that is not GET, is permitted after a
  robots check, and is logged with its method and URL. The request is not changed. A non-same-origin
  call that is not GET is not sent.
- 429 or 503 on a page stops the host for the rest of the run.
- Every request is one line in a private JSONL log, with the wall time to the millisecond, the mode
  (plain, browser or real_chrome) and the configured gap. fetched_at is the start time of the request
  after the wait.
- The headless browser, and real Chrome when asked, send each of their requests through the same checks.
  Real Chrome is installed Google Chrome with a visible window. In real-Chrome mode the user agent is
  not set; Chrome sends its own. Other modes keep the configured user agent. Real Chrome does not
  change the fingerprint and it does not use a proxy. It is only permitted for hosts in
  config/real_chrome_hosts.json.

Only the standard library is needed for plain requests. The browser path needs Playwright.
"""
import datetime
import hashlib
import json
import multiprocessing
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlsplit, urlunsplit

MIN_GAP = 1.5
DEFAULT_HARD_TIMEOUT = 150.0
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


def origin_of(url):
    """Scheme, hostname and port. Hostnames are compared as the URL gives them, including www."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    port = parts.port
    if port is None:
        if parts.scheme == "https":
            port = 443
        elif parts.scheme == "http":
            port = 80
    return (parts.scheme, host, port)


def normalize_host(item):
    """A host name or URL, without a leading www."""
    text = str(item).strip()
    if "://" in text:
        return host_of(text)
    host = text.lower()
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
        self.source = text

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
        self.mode = "plain"  # plain, browser or real_chrome. A request can override this with the mode it used.
        self.robots_fetch = None  # real-Chrome sets this so robots.txt is not read with urllib
        self.lock = threading.Lock()
        self.last_start, self.robots, self.stopped = {}, {}, {}
        self.fetches, self.blocked, self.rechecks = [], [], []
        self.unreadable = set()  # hosts whose robots.txt could not be read this run
        os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)

    # ---- log
    def log(self, **row):
        # mode and both gaps are on every line so a run can be audited without the command that started it.
        # gap_s is the measured pause before this request (null when the line is not a request).
        # min_gap_s is the configured per-host minimum for the run.
        row = {
            "ts": self.wall().isoformat(timespec="milliseconds"), "mono": round(self.clock(), 6),
            "mode": self.mode, "min_gap_s": self.min_gap, "gap_s": None, **row,
        }
        with open(self.log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
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
            # urllib is the plain transport. The log mode is the mode that fetched this URL.
            self.log(event="request", kind=kind, mode="plain", paced=True, host=host, url=clean_url(url),
                     status=status, gap_s=gap, error=error, start_mono=round(start_mono, 6),
                     start_ts=started.isoformat(timespec="milliseconds"),
                     location=headers.get("Location") or headers.get("location"))
            return status, headers, body, started, error

    def note_paced_start(self, host):
        """Wait out the per-host gap and record this start. Used for documents, xhr and fetch."""
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
            return gap, start_mono, started

    def _scheme_ok(self, url):
        parts = urlsplit(url)
        return parts.scheme == "https" or (parts.scheme == "http" and parts.netloc in self.allow_http_hosts)

    # ---- robots
    def _robots_from_answer(self, status, headers, body, current):
        """One robots.txt answer. ('follow', url) or a final ('rules'|'allow_all'|'unreadable', value)."""
        if status is None:
            return ("unreadable", "network_error")
        if status == 200:
            text = body.decode("utf-8", "replace") if isinstance(body, (bytes, bytearray)) else (body or "")
            if re.match(r"(?is)\s*(?:<!doctype|<html|<head|<body)", text):
                # An error page sent with status 200 is not a robots.txt file. It states no rule.
                self.log(event="note", kind="robots_is_an_html_page", host=host_of(current), url=clean_url(current))
                return ("allow_all", None)
            return ("rules", Robots(text))
        if status in (404, 410):
            return ("allow_all", None)
        if status in (301, 302, 303, 307, 308):
            target = urljoin(current, (headers or {}).get("Location") or (headers or {}).get("location") or "")
            if not target or target == current:
                return ("unreadable", "redirect_without_target")
            if host_of(target) not in self.official or not self._scheme_ok(target):
                return ("unreadable", "redirect_to_a_host_that_is_not_official")
            return ("follow", target)
        return ("unreadable", f"http_{status}")

    def _commit_robots(self, url, decision):
        parts = urlsplit(url)
        key = parts.netloc.lower()
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

    def robots_for(self, url, fetch=None):
        """Return ('rules', Robots), ('allow_all', None) or ('unreadable', reason) for the host of the URL.

        fetch(url) returns (status, headers, body, started, error). The default fetch is urllib,
        which is logged as mode plain. A real-Chrome run passes a fetch that uses the Chrome page.
        """
        parts = urlsplit(url)
        key = parts.netloc.lower()
        if key in self.robots:
            return self.robots[key]
        fetch = fetch or self.robots_fetch or (lambda current: self._request(current, "robots"))
        current, seen, decision = f"{parts.scheme}://{parts.netloc}/robots.txt", set(), None
        for _hop in range(MAX_REDIRECTS + 1):
            if current in seen:
                decision = ("unreadable", "redirect_loop")
                break
            seen.add(current)
            status, headers, body, _started, error = fetch(current)
            if error or status is None:
                decision = ("unreadable", "network_error")
                break
            outcome = self._robots_from_answer(status, headers, body, current)
            if outcome[0] == "follow":
                current = outcome[1]
                continue
            decision = outcome
            break
        if decision is None:
            decision = ("unreadable", "too_many_redirects")
        return self._commit_robots(url, decision)

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


class RealChromeError(RuntimeError):
    """Google Chrome or a display is missing, so real-Chrome mode cannot start."""


_DISPLAY_MISSING = re.compile(
    r"(?i)(missing x server|\$display|no display|headed browser without having a xserver|x server)"
)


def display_available():
    """A visible Chrome window needs a display. Xvfb on a server sets DISPLAY."""
    if sys.platform in ("win32", "darwin"):
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def find_chrome():
    """Path of installed Google Chrome, or None. Bundled Chromium is not accepted here."""
    for name in ("google-chrome-stable", "google-chrome", "google-chrome-beta"):
        found = shutil.which(name)
        if found and os.access(found, os.X_OK):
            return found
    for path in (
        "/usr/bin/google-chrome-stable",
        "/usr/bin/google-chrome",
        "/opt/google/chrome/chrome",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ):
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def load_real_chrome_hosts(root=None):
    """Hosts the maintainer approved for real-Chrome mode, from config/real_chrome_hosts.json."""
    if root is None:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, "config", "real_chrome_hosts.json")
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return [normalize_host(item) for item in data.get("hosts") or []]


def real_chrome_host_allowed(url, approved):
    """True when the URL host is on the approved list (www. is ignored)."""
    allowed = {normalize_host(item) for item in approved or []}
    return host_of(url) in allowed


def write_probe_page(root, label, result, when=None):
    """Keep the probe page text in a private file under raw/. raw/ is gitignored."""
    stamp = (when or wall_now()).strftime("%Y%m%dT%H%M%S")
    folder = os.path.join(root, "raw", "probes")
    os.makedirs(folder, exist_ok=True)
    text_path = os.path.join(folder, f"{label}-{stamp}.txt")
    text = result.get("text")
    if text is None:
        body = result.get("body") or b""
        if isinstance(body, (bytes, bytearray)):
            text = body.decode("utf-8", "replace")
        else:
            text = body if isinstance(body, str) else ""
    with open(text_path, "w", encoding="utf-8") as fh:
        fh.write(text if isinstance(text, str) else str(text or ""))
    html_path = None
    body = result.get("body")
    if body:
        raw = body if isinstance(body, (bytes, bytearray)) else str(body).encode("utf-8")
        html_path = os.path.join(folder, f"{label}-{stamp}.html")
        with open(html_path, "wb") as fh:
            fh.write(raw)
    return text_path, html_path


def chrome_profile_dir():
    """Persistent Chrome profile. CRAWLER_CHROME_PROFILE, or a gitignored cache directory."""
    chosen = os.environ.get("CRAWLER_CHROME_PROFILE")
    if chosen:
        return chosen
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, ".cache", "chrome-profile")


def _kill_process_group(pid):
    """Kill a child and every process in its group. Does nothing to this process."""
    if not pid or pid <= 1 or pid == os.getpid():
        return
    try:
        os.killpg(pid, signal.SIGKILL)
    except OSError:
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass


def _safe_close(obj):
    try:
        close = getattr(obj, "close", None)
        if close:
            close()
    except Exception:
        pass


def _response_text(response, page):
    """Body text of a navigation. Prefer the response body over the wrapped page HTML."""
    text_fn = getattr(response, "text", None)
    if callable(text_fn):
        try:
            return text_fn()
        except Exception:
            pass
    if hasattr(page, "content"):
        try:
            return page.content()
        except Exception:
            return ""
    return ""


def _redirect_urls(response, requested):
    if response is None:
        return [requested]
    urls = []
    req = getattr(response, "request", None)
    while req is not None:
        urls.append(getattr(req, "url", None) or requested)
        req = getattr(req, "redirected_from", None)
    if urls:
        urls.reverse()
        return urls
    final = getattr(response, "url", None) or requested
    if final != requested:
        return [requested, final]
    return [requested]


def _export_payload(fetcher, result):
    robots = []
    for netloc, (state, value) in fetcher.robots.items():
        if state == "rules":
            robots.append([netloc, state, getattr(value, "source", "")])
        else:
            robots.append([netloc, state, value])
    safe = dict(result)
    body = safe.get("body")
    if isinstance(body, str):
        safe["body"] = body.encode("utf-8")
    return {
        "result": safe,
        "blocked": list(fetcher.blocked),
        "rechecks": list(fetcher.rechecks),
        "fetches": list(fetcher.fetches),
        "stopped": dict(fetcher.stopped),
        "unreadable": list(fetcher.unreadable),
        "last_start": dict(fetcher.last_start),
        "robots": robots,
    }


def _restore_fetcher(fetcher, spec):
    fetcher.last_start.update(spec.get("last_start") or {})
    fetcher.stopped.update(spec.get("stopped") or {})
    fetcher.unreadable.update(spec.get("unreadable") or [])
    for netloc, state, extra in spec.get("robots") or []:
        if state == "rules":
            fetcher.robots[netloc] = ("rules", Robots(extra or ""))
        else:
            fetcher.robots[netloc] = (state, extra)


def _browser_spec(browser, url, settle_ms, expand_selector, max_clicks, scroll_times):
    fetcher = browser.fetcher
    robots = []
    for netloc, (state, value) in fetcher.robots.items():
        if state == "rules":
            robots.append([netloc, state, getattr(value, "source", "")])
        else:
            robots.append([netloc, state, value])
    return {
        "url": url,
        "log_path": fetcher.log_path,
        "official_domains": sorted(fetcher.official),
        "user_agent": fetcher.user_agent,
        "min_gap": fetcher.min_gap,
        "timeout": fetcher.timeout,
        "allow_http_hosts": sorted(fetcher.allow_http_hosts),
        "real_chrome": browser.real_chrome,
        "approved_hosts": list(browser._approved_host_list()),
        "launch_args": list(browser.launch_args),
        "user_data_dir": browser.user_data_dir,
        "settle_ms": settle_ms,
        "expand_selector": expand_selector,
        "max_clicks": max_clicks,
        "scroll_times": scroll_times,
        "last_start": dict(fetcher.last_start),
        "robots": robots,
        "stopped": dict(fetcher.stopped),
        "unreadable": sorted(fetcher.unreadable),
        "marker": None,
        "sleep": 120,
    }


def _browser_job(spec):
    """Playwright session. Runs in a child process so a stalled driver cannot block the parent."""
    fetcher = PoliteFetcher(
        spec["log_path"], spec["official_domains"], spec["user_agent"],
        min_gap=spec["min_gap"], timeout=spec["timeout"],
        allow_http_hosts=spec.get("allow_http_hosts") or (),
    )
    fetcher.mode = "real_chrome" if spec["real_chrome"] else "browser"
    _restore_fetcher(fetcher, spec)
    tool = BrowserFetcher(
        fetcher, launch_args=spec.get("launch_args") or (),
        real_chrome=spec["real_chrome"], user_data_dir=spec.get("user_data_dir"),
        approved_hosts=spec.get("approved_hosts"),
    )
    from playwright.sync_api import sync_playwright
    with sync_playwright() as play:
        browser, page = tool._launch(play)
        try:
            result = tool._session(
                page, spec["url"], spec["settle_ms"], spec.get("expand_selector"),
                spec.get("max_clicks") or 0, spec.get("scroll_times") or 0,
            )
        finally:
            _safe_close(browser)
    return _export_payload(fetcher, result)


def _browser_child(conn, spec):
    try:
        os.setsid()
    except OSError:
        pass
    try:
        conn.send({"ok": True, "payload": _browser_job(spec)})
    except Exception as err:
        conn.send({"ok": False, "error_type": type(err).__name__, "error": f"{type(err).__name__}: {err}"[:160]})
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _sleep_child(conn, spec):
    """A child that does not answer. Used to prove the parent returns when the child hangs."""
    try:
        os.setsid()
    except OSError:
        pass
    marker = spec.get("marker")
    if marker:
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
        with open(marker, "w", encoding="ascii") as fh:
            fh.write(str(child.pid))
            fh.flush()
    time.sleep(float(spec.get("sleep") or 120))
    try:
        conn.send({"ok": True, "payload": {"result": {"class": "ok"}}})
    except Exception:
        pass


class BrowserFetcher:
    """A browser whose every request goes through the same robots, spacing and log as PoliteFetcher.

    The default is headless Chromium. real_chrome=True launches installed Google Chrome instead
    (channel chrome, headless False, a persistent profile). In real-Chrome mode the user agent is
    not set; Chrome sends its own. Other modes use the fetcher's user agent. This class does not
    set a proxy and does not change the browser fingerprint. Real-Chrome mode is only permitted
    for hosts listed in config/real_chrome_hosts.json.

    The real Playwright session runs in a child process. The parent keeps a wall-clock deadline
    (default 150 seconds) and kills that process group if the child does not return. The parent
    itself does not call Playwright, so a stalled driver cannot leave it blocked.

    In real-Chrome mode, robots.txt is read with page.goto in that same Chrome context.
    The per-host gap applies to document loads and to xhr and fetch calls, in every browser mode.
    Scripts and style sheets can go without a gap. A request that must not be sent is answered
    with an empty 204, not an abort. A same-origin call that the page makes itself, with a method
    that is not GET, is permitted after a robots check and is not changed.
    """

    DROP_TYPES = {"image", "media", "font"}
    DATA_TYPES = {"xhr", "fetch"}
    PACED_TYPES = {"document", "xhr", "fetch"}

    def __init__(self, fetcher, launch_args=(), real_chrome=False, user_data_dir=None, hard_timeout=None,
                 launcher=None, worker_target=None, approved_hosts=None):
        self.fetcher = fetcher
        self.launch_args = list(launch_args)
        self.real_chrome = real_chrome
        self.user_data_dir = user_data_dir
        self.hard_timeout = hard_timeout
        self.launcher = launcher  # tests pass a callable that returns (browser, page)
        self.worker_target = worker_target  # tests pass a child target that hangs
        self.approved_hosts = approved_hosts  # None means read config/real_chrome_hosts.json
        self.worker_spec = {}
        self._page = None
        self._page_url = None
        self._document_started = None
        self._data_problems = []
    def _require_real_chrome(self):
        if not display_available():
            raise RealChromeError(
                "real-Chrome mode opens a visible Chrome window and needs a display. "
                "On a server, start Xvfb and set DISPLAY."
            )
        if find_chrome() is None:
            raise RealChromeError(
                "real-Chrome mode needs Google Chrome (channel chrome). "
                "The bundled Chromium is not used for this mode."
            )

    def _chrome_launch_error(self, err):
        text = str(err)
        if _DISPLAY_MISSING.search(text):
            return RealChromeError(
                "real-Chrome mode opens a visible Chrome window and needs a display. "
                "On a server, start Xvfb and set DISPLAY. " + text[:180]
            )
        return RealChromeError(
            "real-Chrome mode needs Google Chrome (channel chrome). "
            "The bundled Chromium is not used for this mode. " + text[:180]
        )

    def _deadline(self):
        if self.hard_timeout is None:
            return DEFAULT_HARD_TIMEOUT
        return float(self.hard_timeout)

    def _is_top_document(self, request):
        if getattr(request, "resource_type", "") != "document":
            return False
        is_nav = getattr(request, "is_navigation_request", None)
        if callable(is_nav) and not is_nav():
            return False
        frame = getattr(request, "frame", None)
        if frame is not None and getattr(frame, "parent_frame", None) is not None:
            return False
        return True

    def _approved_host_list(self):
        if self.approved_hosts is not None:
            return [normalize_host(item) for item in self.approved_hosts]
        return load_real_chrome_hosts()

    def _require_approved_host(self, url):
        if not real_chrome_host_allowed(url, self._approved_host_list()):
            host = host_of(url)
            raise RealChromeError(
                "real-Chrome mode is only permitted for hosts the maintainer approved in "
                f"config/real_chrome_hosts.json. {host} is not on that list."
            )

    def _should_pace(self, request):
        kind = getattr(request, "resource_type", "") or ""
        return kind in self.PACED_TYPES or self._is_top_document(request)

    def _same_origin(self, url):
        if not self._page_url:
            return False
        return origin_of(url) == origin_of(self._page_url)

    def _note_data_problem(self, resource_type, how, url, method="GET"):
        if resource_type not in self.DATA_TYPES:
            return
        self._data_problems.append({
            "kind": resource_type, "how": how, "url": clean_url(url), "method": method,
        })

    def _pace(self, host, should_pace):
        if should_pace:
            gap, start_mono, started = self.fetcher.note_paced_start(host)
            return gap, start_mono, started, True
        started = self.fetcher.wall()
        return None, self.fetcher.clock(), started, False

    def _empty(self, route):
        """Answer a request we will not send, so the page script is not left waiting on an abort."""
        try:
            return route.fulfill(status=204, body=b"", headers={"content-type": "text/plain"})
        except TypeError:
            return route.fulfill(status=204, body="")

    def _route(self, route, request):
        url = request.url
        mode = "real_chrome" if self.real_chrome else "browser"
        method = getattr(request, "method", "GET") or "GET"
        kind = request.resource_type
        top = self._is_top_document(request)
        if kind in self.DROP_TYPES or url.startswith(("data:", "blob:", "about:")):
            self.fetcher.log(event="not_fetched", url=clean_url(url), host=host_of(url), mode=mode, via="browser",
                             reason="not_needed_for_text", method=method)
            return self._empty(route)
        if method != "GET" and not self._same_origin(url):
            self.fetcher.log(event="not_fetched", url=clean_url(url), host=host_of(url), mode=mode, via="browser",
                             reason="not_a_get_request", method=method)
            self._note_data_problem(kind, "blanked", url, method)
            return self._empty(route)
        reason = self.fetcher.may_fetch(url)
        if reason:
            self.fetcher.log(event="not_fetched", url=clean_url(url), host=host_of(url), mode=mode, via="browser",
                             reason=reason, method=method)
            self._note_data_problem(kind, "blanked", url, method)
            return self._empty(route)
        host = host_of(url)
        gap, start_mono, started, paced = self._pace(host, self._should_pace(request))
        start_ts = started.isoformat(timespec="milliseconds")
        if top:
            self._document_started = started
        if method != "GET":
            # Same-origin, permitted: leave the request as the page made it.
            self.fetcher.log(event="request", kind=kind, via="browser", mode=mode, paced=paced,
                             host=host, url=clean_url(url), method=method, status=None, gap_s=gap,
                             error=None, start_mono=round(start_mono, 6), start_ts=start_ts)
            return route.continue_()
        try:
            response = route.fetch(max_redirects=0, timeout=self.fetcher.timeout * 1000)
        except Exception as err:  # Playwright raises its own error types
            self.fetcher.log(event="request", kind=kind, via="browser", mode=mode, paced=paced,
                             host=host, url=clean_url(url), method=method, status=None, gap_s=gap,
                             error=str(err)[:160], start_mono=round(start_mono, 6), start_ts=start_ts)
            self._note_data_problem(kind, "failed", url, method)
            return self._empty(route)
        headers = getattr(response, "headers", {}) or {}
        status = response.status
        self.fetcher.log(event="request", kind=kind, via="browser", mode=mode, paced=paced,
                         host=host, url=clean_url(url), method=method, start_mono=round(start_mono, 6),
                         start_ts=start_ts, status=status, gap_s=gap, error=None,
                         location=headers.get("location"))
        if status in (429, 503) and top:
            self.fetcher.stopped[host] = "http_error"
        if kind in self.DATA_TYPES and (status is None or status >= 400):
            self._note_data_problem(kind, "failed", url, method)
        return route.fulfill(response=response)
    def _api_robots_fetch(self, page, current):
        """Read robots.txt for another host through Chrome, without navigating the page away."""
        context = getattr(page, "context", None)
        api = getattr(context, "request", None) if context is not None else None
        host = host_of(current)
        gap, start_mono, started = self.fetcher.note_paced_start(host)
        status, headers, body, error = None, {}, b"", None
        if api is None or not hasattr(api, "get"):
            error = "chrome_request_api_missing"
        else:
            try:
                response = api.get(current, timeout=self.fetcher.timeout * 1000, max_redirects=0)
                status = response.status
                headers = dict(getattr(response, "headers", {}) or {})
                raw = response.body() if hasattr(response, "body") else b""
                body = raw if isinstance(raw, (bytes, bytearray)) else str(raw).encode("utf-8")
            except Exception as err:
                error = str(err)[:160]
        self.fetcher.log(event="request", kind="robots", mode="real_chrome", via="browser", paced=True,
                         host=host, url=clean_url(current), status=status, gap_s=gap, error=error,
                         start_mono=round(start_mono, 6), start_ts=started.isoformat(timespec="milliseconds"),
                         location=headers.get("location") or headers.get("Location"))
        return status, headers, body, started, error

    def _robots_via_page(self, page, url):
        """Fetch this host's robots.txt with page.goto and apply the RULES v3 decision."""
        parts = urlsplit(url)
        if parts.netloc.lower() in self.fetcher.robots:
            return self.fetcher.robots[parts.netloc.lower()]
        robots_url = f"{parts.scheme}://{parts.netloc}/robots.txt"
        host = host_of(robots_url)
        gap, start_mono, started = self.fetcher.note_paced_start(host)
        try:
            response = page.goto(robots_url, wait_until="domcontentloaded", timeout=self.fetcher.timeout * 3000)
        except Exception as err:
            self.fetcher.log(event="request", kind="robots", mode="real_chrome", via="browser", paced=True,
                             host=host, url=clean_url(robots_url), status=None, gap_s=gap, error=str(err)[:160],
                             start_mono=round(start_mono, 6), start_ts=started.isoformat(timespec="milliseconds"))
            return self.fetcher._commit_robots(url, ("unreadable", "network_error"))
        status = response.status if response else None
        text = _response_text(response, page)
        chain = _redirect_urls(response, robots_url)
        final = chain[-1] if chain else robots_url
        self.fetcher.log(event="request", kind="robots", mode="real_chrome", via="browser", paced=True,
                         host=host_of(final), url=clean_url(final), status=status, gap_s=gap, error=None,
                         start_mono=round(start_mono, 6), start_ts=started.isoformat(timespec="milliseconds"))
        if len(chain) - 1 > MAX_REDIRECTS:
            decision = ("unreadable", "too_many_redirects")
        elif any(host_of(hop) not in self.fetcher.official or not self.fetcher._scheme_ok(hop) for hop in chain):
            decision = ("unreadable", "redirect_to_a_host_that_is_not_official")
        elif status in (301, 302, 303, 307, 308):
            decision = ("unreadable", "redirect_without_target")
        else:
            outcome = self.fetcher._robots_from_answer(status, {}, text.encode("utf-8"), final)
            decision = ("unreadable", "too_many_redirects") if outcome[0] == "follow" else outcome
        return self.fetcher._commit_robots(url, decision)

    def _launch(self, play):
        if self.real_chrome:
            self._require_real_chrome()
            profile = self.user_data_dir or chrome_profile_dir()
            os.makedirs(profile, exist_ok=True)
            try:
                # channel chrome is installed Google Chrome, not the bundled Chromium.
                # headless False is a visible window. No proxy and no fingerprint overrides.
                context = play.chromium.launch_persistent_context(
                    profile,
                    channel="chrome",
                    headless=False,
                    args=self.launch_args,
                )
            except RealChromeError:
                raise
            except Exception as err:
                raise self._chrome_launch_error(err) from err
            page = context.pages[0] if context.pages else context.new_page()
            return context, page
        browser = play.chromium.launch(args=self.launch_args, executable_path=os.environ.get("CRAWLER_CHROMIUM") or None)
        page = browser.new_context(user_agent=self.fetcher.user_agent).new_page()
        return browser, page

    def _page_text(self, page, read_ms):
        try:
            return page.inner_text("body", timeout=read_ms)
        except TypeError:
            return page.inner_text("body")

    def _read_document(self, page, read_ms):
        """Read the document after it has loaded. A failed settle does not skip this read."""
        if hasattr(page, "content"):
            html = page.content()
        elif hasattr(page, "evaluate"):
            html = page.evaluate("() => document.documentElement ? document.documentElement.outerHTML : ''")
        else:
            html = ""
        if not isinstance(html, str):
            html = "" if html is None else str(html)
        try:
            text = self._page_text(page, read_ms)
        except Exception:
            text = ""
        return html, text

    def _page_class(self, status, html, text):
        page_class = classify(status, html)
        if self._data_problems and page_class == "ok":
            return "js_shell"
        if page_class == "js_shell" and len(re.findall(r"\w{2,}", text or "")) >= 80:
            if self._data_problems:
                return "js_shell"
            return "ok"
        return page_class

    def _collect(self, url, page, unreadable, settle_ms, expand_selector, max_clicks, scroll_times):
        read_ms = int(float(self.fetcher.timeout) * 1000)
        if hasattr(page, "set_default_timeout"):
            page.set_default_timeout(read_ms)
        if hasattr(page, "set_default_navigation_timeout"):
            page.set_default_navigation_timeout(int(float(self.fetcher.timeout) * 3000))
        self._page = page
        self._page_url = url
        self._document_started = None
        self._data_problems = []
        if hasattr(page, "on"):
            def on_response(response, _self=self):
                request = getattr(response, "request", None)
                kind = getattr(request, "resource_type", "") if request is not None else ""
                if kind not in _self.DATA_TYPES:
                    return
                status = getattr(response, "status", None)
                if status is None or status >= 400:
                    method = getattr(request, "method", "GET") if request is not None else "GET"
                    url = getattr(request, "url", "") if request is not None else ""
                    _self._note_data_problem(kind, "failed", url, method)
            page.on("response", on_response)
        page.route("**/*", self._route)
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=self.fetcher.timeout * 3000)
            status = response.status if response else None
            try:
                if hasattr(page, "wait_for_load_state"):
                    page.wait_for_load_state("networkidle", timeout=max(int(settle_ms), 0))
            except Exception:
                pass  # the settle cap elapsed; the loaded document is still read
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
            final_url = page.url
            html, text = self._read_document(page, read_ms)
        except Exception as err:
            return self.fetcher._block(url, "timeout" if "imeout" in str(err) else "http_error", detail=str(err)[:160])
        if host_of(final_url) not in self.fetcher.official:
            return self.fetcher._block(url, "off_domain_redirect", redirect_to=clean_url(final_url))
        started = self._document_started or self.fetcher.wall()
        result = {
            "url": clean_url(url), "final_url": clean_url(final_url), "status": status, "body": html.encode("utf-8"),
            "text": text, "fetched_at": started.isoformat(timespec="seconds"),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "class": self._page_class(status, html, text), "via": "browser",
        }
        if unreadable:
            result["robots_unreadable"] = True
        if self._data_problems:
            result["data_calls_failed"] = list(self._data_problems)
        self.fetcher.fetches.append({key: result[key] for key in ("url", "final_url", "status", "fetched_at")})
        return result
    def _session(self, page, url, settle_ms, expand_selector, max_clicks, scroll_times):
        previous_fetch = self.fetcher.robots_fetch
        try:
            if self.real_chrome:
                self.fetcher.robots_fetch = lambda current, page=page: self._api_robots_fetch(page, current)
                self._robots_via_page(page, url)
            reason = self.fetcher.may_fetch(url)
            if reason:
                return self.fetcher._block(url, reason)
            unreadable = host_of(url) in self.fetcher.unreadable
            return self._collect(url, page, unreadable, settle_ms, expand_selector, max_clicks, scroll_times)
        finally:
            self.fetcher.robots_fetch = previous_fetch

    def _timeout_result(self, url):
        detail = "the browser process did not finish within the hard timeout"
        result = self.fetcher._block(url, "timeout", detail=detail)
        result["class"] = "timeout"
        result["via"] = "browser"
        return result

    def _accept_payload(self, payload):
        fetcher = self.fetcher
        for row in payload.get("blocked") or []:
            if row not in fetcher.blocked:
                fetcher.blocked.append(row)
        fetcher.rechecks.extend(payload.get("rechecks") or [])
        fetcher.fetches.extend(payload.get("fetches") or [])
        fetcher.stopped.update(payload.get("stopped") or {})
        fetcher.unreadable.update(payload.get("unreadable") or [])
        fetcher.last_start.update(payload.get("last_start") or {})
        for netloc, state, extra in payload.get("robots") or []:
            if state == "rules":
                fetcher.robots[netloc] = ("rules", Robots(extra or ""))
            else:
                fetcher.robots[netloc] = (state, extra)
        return payload["result"]

    def _render_in_child(self, url, settle_ms, expand_selector, max_clicks, scroll_times):
        """Run the browser in a spawned child. The parent only waits on the pipe, then kills the group."""
        spec = _browser_spec(self, url, settle_ms, expand_selector, max_clicks, scroll_times)
        spec.update(self.worker_spec or {})
        ctx = multiprocessing.get_context("spawn")
        parent_conn, child_conn = ctx.Pipe(duplex=False)
        target = self.worker_target or _browser_child
        proc = ctx.Process(target=target, args=(child_conn, spec))
        proc.start()
        child_conn.close()
        message = None
        try:
            if parent_conn.poll(self._deadline()):
                try:
                    message = parent_conn.recv()
                except EOFError:
                    message = None
            else:
                _kill_process_group(proc.pid)
                return self._timeout_result(url)
        finally:
            try:
                parent_conn.close()
            except Exception:
                pass
            if proc.is_alive():
                _kill_process_group(proc.pid)
            proc.join(2)
            if proc.is_alive():
                proc.kill()
                proc.join(1)
        if not message or not message.get("ok"):
            error = (message or {}).get("error") or "the browser process failed"
            if (message or {}).get("error_type") == "RealChromeError":
                raise RealChromeError(error)
            if "Executable doesn't exist" in error:
                raise RuntimeError(error)
            return self.fetcher._block(url, "http_error", detail=error[:160])
        return self._accept_payload(message["payload"])

    def render(self, url, settle_ms=3000, expand_selector=None, max_clicks=20, scroll_times=0):
        """Open one page and return its rendered text. expand_selector is a 'load more' or tab control."""
        previous = self.fetcher.mode
        self.fetcher.mode = "real_chrome" if self.real_chrome else "browser"
        try:
            if self.real_chrome:
                self._require_approved_host(url)
            if self.launcher is not None:
                browser, page = self.launcher()
                try:
                    return self._session(page, url, settle_ms, expand_selector, max_clicks, scroll_times)
                finally:
                    _safe_close(browser)
            if self.real_chrome and self.worker_target is None:
                self._require_real_chrome()
            return self._render_in_child(url, settle_ms, expand_selector, max_clicks, scroll_times)
        finally:
            self.fetcher.mode = previous


def spacing_report(log_path):
    """Smallest and mean gap between paced request starts for each host, in start-time order.

    Gaps are computed after sorting by start_mono, so a log written out of completion order
    cannot show a negative gap. gaps_under_min counts gaps under the rule floor of 1.5 seconds.
    gaps_under_configured counts gaps under the min_gap_s written on the log lines, so a slower
    run (for example 30 seconds) is checked too. Only paced requests (documents, xhr, fetch,
    and plain requests) are used for those gaps. Scripts and style sheets can go without a gap
    and are counted in requests but not in the gap figures.
    """
    starts, paced_starts, configured = {}, {}, {}
    with open(log_path, encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            if row.get("event") != "request" or row.get("start_mono") is None:
                continue
            host = row["host"]
            starts.setdefault(host, []).append(row["start_mono"])
            # A line with no paced flag is a plain request, which is always paced.
            if row.get("paced", True):
                paced_starts.setdefault(host, []).append(row["start_mono"])
            if row.get("min_gap_s") is not None:
                configured[host] = float(row["min_gap_s"])
    report = {}
    for host, times in starts.items():
        ordered = sorted(paced_starts.get(host) or times)
        gaps = [round(b - a, 3) for a, b in zip(ordered, ordered[1:])]
        floor = configured.get(host, MIN_GAP)
        report[host] = {"requests": len(times), "min_gap_s": min(gaps) if gaps else None,
                        "mean_gap_s": round(sum(gaps) / len(gaps), 3) if gaps else None,
                        "gaps_under_min": sum(1 for gap in gaps if gap < MIN_GAP - 0.001),
                        "configured_min_gap_s": floor,
                        "gaps_under_configured": sum(1 for gap in gaps if gap < floor - 0.001)}
    return report


def configured_min_gap(argv, environ=None):
    """The per-host gap in seconds. --min-gap wins over CRAWLER_MIN_GAP. The default is MIN_GAP."""
    environ = os.environ if environ is None else environ
    raw = environ.get("CRAWLER_MIN_GAP")
    try:
        gap = float(raw) if raw else MIN_GAP
    except ValueError as err:
        raise ValueError("CRAWLER_MIN_GAP must be a number of seconds, 1.5 or more") from err
    if "--min-gap" in argv:
        text = _option(argv, "--min-gap")
        try:
            gap = float(text)
        except (TypeError, ValueError) as err:
            raise ValueError("give --min-gap a number of seconds, 1.5 or more") from err
    return gap


def configured_hard_timeout(argv, environ=None):
    """Wall-clock seconds for one browser process. --hard-timeout wins over CRAWLER_HARD_TIMEOUT."""
    environ = os.environ if environ is None else environ
    raw = environ.get("CRAWLER_HARD_TIMEOUT")
    try:
        value = float(raw) if raw else DEFAULT_HARD_TIMEOUT
    except ValueError as err:
        raise ValueError("CRAWLER_HARD_TIMEOUT must be a number of seconds") from err
    if "--hard-timeout" in argv:
        text = _option(argv, "--hard-timeout")
        try:
            value = float(text)
        except (TypeError, ValueError) as err:
            raise ValueError("give --hard-timeout a number of seconds") from err
    if value <= 0:
        raise ValueError("the hard timeout must be greater than 0 seconds")
    return value


_VALUE_FLAGS = {"--min-gap", "--hard-timeout", "--url", "--country"}


def _option(argv, name):
    if name not in argv:
        return None
    index = argv.index(name)
    if index + 1 >= len(argv) or str(argv[index + 1]).startswith("--"):
        raise ValueError(f"give {name} a value")
    return argv[index + 1]


def _positionals(argv):
    skip = False
    found = []
    for arg in argv[2:]:
        if skip:
            skip = False
            continue
        if arg in _VALUE_FLAGS:
            skip = True
            continue
        if arg.startswith("--"):
            continue
        found.append(arg)
    return found


def _country_known(root, country):
    path = os.path.join(root, "config", "countries.json")
    with open(path, encoding="utf-8") as fh:
        codes = {item["code"].lower() for item in json.load(fh)["items"]}
    return country.lower() in codes


def _normalized_domains(domains):
    names = []
    for domain in domains or []:
        name = domain.lower()
        if name.startswith("www."):
            name = name[4:]
        names.append(name)
    return names


def _host_matches(host, domains):
    names = _normalized_domains(domains)
    if host in names:
        return True
    return any(host.endswith("." + name) for name in names)


def _domains_for_url(root, url, country):
    host = host_of(url)
    with open(os.path.join(root, "networks.json"), encoding="utf-8") as fh:
        networks = json.load(fh)["items"]
    for item in networks:
        domains = item.get("official_domains") or []
        if _host_matches(host, domains):
            return domains, f"network-{item['id']}"
    issuer_path = os.path.join(root, country, "issuers.json")
    if os.path.exists(issuer_path):
        with open(issuer_path, encoding="utf-8") as fh:
            issuers = json.load(fh)["items"]
        for item in issuers:
            domains = item.get("official_domains") or []
            if _host_matches(host, domains):
                return domains, item["id"]
    raise ValueError(f"{host} is not an official domain for country {country}")


def resolve_probe(root, argv):
    """Return (label, url, official_domains) for an issuer probe or a network-portal probe."""
    url_flag = _option(argv, "--url")
    country_flag = _option(argv, "--country")
    if url_flag or country_flag:
        if not url_flag or not country_flag:
            raise ValueError("probe --url needs --country")
        country = country_flag.lower()
        if not _country_known(root, country):
            raise ValueError(f"unknown country {country_flag}")
        domains, label = _domains_for_url(root, url_flag, country)
        return label, url_flag, domains
    positionals = _positionals(argv)
    if len(positionals) < 2:
        raise ValueError("usage: probe <issuer_id> <url> or probe --url <url> --country <cc>")
    issuer_id, url = positionals[0], positionals[1]
    path = os.path.join(root, issuer_id[:2], "issuers.json")
    with open(path, encoding="utf-8") as fh:
        issuers = json.load(fh)["items"]
    try:
        issuer = next(row for row in issuers if row["id"] == issuer_id)
    except StopIteration as err:
        raise ValueError(f"unknown issuer {issuer_id}") from err
    return issuer_id, url, issuer["official_domains"]


def main(argv):
    if len(argv) < 2 or argv[1] != "probe":
        print(__doc__)
        return 2
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    agent = os.environ.get("CRAWLER_USER_AGENT")
    if not agent:
        print("Set CRAWLER_USER_AGENT to the user agent that the maintainer chose.")
        return 2
    try:
        label, url, domains = resolve_probe(root, argv)
        gap = configured_min_gap(argv)
        hard = configured_hard_timeout(argv)
        log = os.path.join(root, "raw", "logs", f"probe-{label}-{wall_now().strftime('%Y%m%dT%H%M%S')}.jsonl")
        fetcher = PoliteFetcher(log, domains, agent, min_gap=gap)
    except (ValueError, OSError) as err:
        print(err)
        return 2
    real_chrome = "--real-chrome" in argv
    approved = load_real_chrome_hosts(root)
    if real_chrome:
        if not real_chrome_host_allowed(url, approved):
            print(
                "real-Chrome mode is only permitted for hosts the maintainer approved in "
                f"config/real_chrome_hosts.json. {host_of(url)} is not on that list."
            )
            return 2
        fetcher.mode = "real_chrome"
    elif "--browser" in argv:
        fetcher.mode = "browser"
    launch_args = [arg for arg in ("--disable-http2",) if arg in argv]
    try:
        if real_chrome or "--browser" in argv:
            result = BrowserFetcher(
                fetcher, launch_args=launch_args, real_chrome=real_chrome, hard_timeout=hard,
                approved_hosts=approved if real_chrome else None,
            ).render(url)
        else:
            result = fetcher.get(url)
    except RealChromeError as err:
        print(err)
        return 2
    text_path, html_path = write_probe_page(root, label, result)
    shown = {key: value for key, value in result.items() if key not in ("body", "text")}
    shown["words"] = len(re.findall(r"\w{2,}", result.get("text") or ""))
    shown["page_text"] = text_path
    if html_path:
        shown["page_html"] = html_path
    print(json.dumps({"result": shown, "blocked": fetcher.blocked, "rechecks": fetcher.rechecks,
                      "spacing": spacing_report(log), "mode": fetcher.mode, "min_gap_s": fetcher.min_gap,
                      "log": log, "page_text": text_path}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))


