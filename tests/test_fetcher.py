"""The reference fetcher: robots policy, spacing, redirects, skipped URLs and the browser path. No network."""
import ast
import http.server
import io
import json
import os
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import patch

from pipeline.fetcher import (
    BrowserFetcher, PoliteFetcher, RealChromeError, Robots, _sleep_child, chrome_profile_dir, classify, clean_url,
    configured_min_gap, load_real_chrome_hosts, main, origin_of, real_chrome_host_allowed, resolve_probe,
    spacing_report, write_probe_page,
)

AGENT = "card-offer-crawler-test/1.0"


class FakeNet:
    """Scripted answers and a clock that moves only when the fetcher sleeps."""

    def __init__(self, answers):
        self.answers, self.now, self.calls = answers, 100.0, []

    def transport(self, url, timeout, user_agent):
        self.calls.append((url, self.now))
        answer = self.answers.get(url, (404, {}, b""))
        if isinstance(answer, Exception):
            raise answer
        return answer

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def make(answers, domains=("bank.example",)):
    net = FakeNet(answers)
    log = os.path.join(tempfile.mkdtemp(prefix="fetcher-"), "log.jsonl")
    return PoliteFetcher(log, domains, AGENT, transport=net.transport, clock=net.clock, sleep=net.sleep), net, log


PAGE = (200, {}, b"<html><body>" + b"offer words " * 60 + b"</body></html>")


class RobotsPolicyTests(unittest.TestCase):
    def run_with_robots(self, robots_answer):
        fetcher, net, _log = make({"https://www.bank.example/robots.txt": robots_answer, "https://www.bank.example/cards": PAGE})
        return fetcher.get("https://www.bank.example/cards"), fetcher, net

    def test_200_rules_are_obeyed(self):
        result, fetcher, _ = self.run_with_robots((200, {}, b"User-agent: *\nDisallow: /cards\n"))
        self.assertEqual(result["not_fetched"], "robots_disallow")
        result, _, _ = self.run_with_robots((200, {}, b"User-agent: *\nDisallow: /private\n"))
        self.assertEqual(result["status"], 200)

    def test_404_and_410_mean_no_rules(self):
        for status in (404, 410):
            result, _, _ = self.run_with_robots((status, {}, b""))
            self.assertEqual(result["status"], 200, status)

    def test_every_other_answer_is_read_but_marked_unreadable(self):
        """A guard that hides robots.txt must cost flags, not data: the page is still read, the record
        says so, and the host goes on the recheck list for the maintainer."""
        for answer in ((401, {}, b""), (403, {}, b""), (429, {}, b""), (500, {}, b""), (503, {}, b""),
                       OSError("timed out"), (302, {"Location": "https://other.example/robots.txt"}, b""),
                       (302, {}, b"")):
            result, fetcher, net = self.run_with_robots(answer)
            self.assertEqual(result["status"], 200, answer)
            self.assertTrue(result.get("robots_unreadable"), answer)
            self.assertIn("https://www.bank.example/cards", [url for url, _ in net.calls], answer)
            self.assertEqual(fetcher.blocked[0]["reason"], "robots_unreachable")
            self.assertEqual(fetcher.rechecks[0]["reason"], "robots_unreachable")
            self.assertEqual(fetcher.rechecks[0]["host"], "bank.example")

    def test_a_flagged_read_is_still_fetchable_and_spaced(self):
        result, _fetcher, net = self.run_with_robots((403, {}, b""))
        cards = [at for url, at in net.calls if url.endswith("/cards")]
        self.assertEqual(len(cards), 1)
        self.assertGreaterEqual(cards[0] - net.calls[0][1], 1.5, "the page must still be spaced from robots.txt")

    def test_a_readable_robots_is_not_flagged(self):
        result, fetcher, _ = self.run_with_robots((200, {}, b"User-agent: *\nDisallow: /private\n"))
        self.assertNotIn("robots_unreadable", result)
        self.assertEqual(fetcher.rechecks, [])

    def test_robots_redirect_inside_official_domains_is_followed(self):
        fetcher, net, _ = make({
            "https://www.bank.example/robots.txt": (301, {"Location": "https://static.bank.example/robots.txt"}, b""),
            "https://static.bank.example/robots.txt": (200, {}, b"User-agent: *\nDisallow: /x\n"),
            "https://www.bank.example/cards": PAGE,
        }, domains=("bank.example", "static.bank.example"))
        self.assertEqual(fetcher.get("https://www.bank.example/cards")["status"], 200)

    def test_an_html_page_with_status_200_is_not_a_robots_file(self):
        result, _fetcher, _ = self.run_with_robots((200, {}, b"<!DOCTYPE html><html><body>Disallow: / Page not found</body></html>"))
        self.assertEqual(result["status"], 200)
        self.assertNotIn("robots_unreadable", result)

    def test_robots_redirect_loop_marks_the_read_unreadable(self):
        fetcher, _, _ = make({
            "https://www.bank.example/robots.txt": (301, {"Location": "https://www.bank.example/r2"}, b""),
            "https://www.bank.example/r2": (301, {"Location": "https://www.bank.example/robots.txt"}, b""),
            "https://www.bank.example/cards": PAGE,
        })
        result = fetcher.get("https://www.bank.example/cards")
        self.assertEqual(result["status"], 200)
        self.assertTrue(result.get("robots_unreadable"))
        self.assertEqual(fetcher.rechecks[0]["detail"], "redirect_loop")

    def test_rule_matching(self):
        rules = Robots("User-agent: *\nDisallow: /a\nAllow: /a/public\nDisallow: /*.pdf$\n\nUser-agent: card-offer-crawler\nDisallow: /only-us\n")
        self.assertTrue(rules.allowed("https://h/a/x"))
        self.assertFalse(rules.allowed("https://h/only-us/1"))
        general = Robots("User-agent: *\nDisallow: /a\nAllow: /a/public\nDisallow: /*.pdf$\n")
        self.assertFalse(general.allowed("https://h/a/x"))
        self.assertTrue(general.allowed("https://h/a/public/x"))
        self.assertFalse(general.allowed("https://h/docs/terms.pdf"))
        self.assertTrue(general.allowed("https://h/docs/terms.pdf?x=1"))


class RequestRuleTests(unittest.TestCase):
    def test_gap_between_requests_to_one_host(self):
        fetcher, net, log = make({"https://www.bank.example/robots.txt": (404, {}, b""),
                                  "https://www.bank.example/a": PAGE, "https://www.bank.example/b": PAGE})
        fetcher.get("https://www.bank.example/a")
        fetcher.get("https://www.bank.example/b")
        times = [when for _url, when in net.calls]
        self.assertTrue(all(b - a >= 1.5 for a, b in zip(times, times[1:])), times)
        report = spacing_report(log)["bank.example"]
        self.assertEqual((report["requests"], report["gaps_under_min"]), (3, 0))
        with open(log, encoding="utf-8") as fh:
            first = json.loads(fh.readline())
        self.assertRegex(first["start_ts"], r"T\d\d:\d\d:\d\d\.\d{3}[+-]\d\d:\d\d$")
        self.assertIn("start_mono", first)

    def test_gap_cannot_be_set_under_the_minimum(self):
        with self.assertRaises(ValueError):
            PoliteFetcher("/tmp/x.jsonl", ["bank.example"], AGENT, min_gap=0.5)

    def test_search_engine_user_agent_is_refused(self):
        with self.assertRaises(ValueError):
            PoliteFetcher("/tmp/x.jsonl", ["bank.example"], "Mozilla/5.0 (compatible; Googlebot/2.1)")

    def test_host_that_is_not_official_is_not_requested(self):
        fetcher, net, _ = make({})
        self.assertEqual(fetcher.get("https://deals.other.example/x")["not_fetched"], "host_not_official")
        self.assertEqual(net.calls, [])

    def test_redirect_to_an_outside_host_is_recorded_and_not_followed(self):
        fetcher, net, _ = make({"https://www.bank.example/robots.txt": (404, {}, b""),
                                "https://www.bank.example/deals": (302, {"Location": "https://deals.other.example/sg"}, b"")})
        result = fetcher.get("https://www.bank.example/deals")
        self.assertEqual((result["not_fetched"], result["redirect_to"]), ("off_domain_redirect", "https://deals.other.example/sg"))
        self.assertNotIn("https://deals.other.example/sg", [url for url, _ in net.calls])
        self.assertEqual(fetcher.blocked[-1]["reason"], "off_domain_redirect")

    def test_sign_in_and_form_urls_are_not_requested(self):
        fetcher, net, _ = make({"https://www.bank.example/robots.txt": (404, {}, b"")})
        for path in ("/personal/login", "/cards/apply-now", "/register", "/online-banking/home"):
            self.assertEqual(fetcher.get("https://www.bank.example" + path)["not_fetched"], "login_required", path)
        self.assertEqual([url for url, _ in net.calls], [])

    def test_429_stops_the_host_for_the_run(self):
        fetcher, net, _ = make({"https://www.bank.example/robots.txt": (404, {}, b""),
                                "https://www.bank.example/a": (429, {}, b""), "https://www.bank.example/b": PAGE})
        self.assertEqual(fetcher.get("https://www.bank.example/a")["not_fetched"], "http_error")
        self.assertEqual(fetcher.get("https://www.bank.example/b")["not_fetched"], "http_error")
        self.assertNotIn("https://www.bank.example/b", [url for url, _ in net.calls])

    def test_session_id_is_not_recorded(self):
        self.assertEqual(clean_url("https://h/rhb.html;jsessionid=D079C5?x=1#top"), "https://h/rhb.html?x=1")
        self.assertEqual(clean_url("https://h/p?sid=abc&x=1"), "https://h/p?x=1")
        self.assertEqual(clean_url("https://h/p?x=1&PHPSESSID=abc"), "https://h/p?x=1")

    def test_fetch_records_fit_the_hand_in_file(self):
        fetcher, _, _ = make({"https://www.bank.example/robots.txt": (404, {}, b""), "https://www.bank.example/a": PAGE})
        fetcher.get("https://www.bank.example/a")
        row = fetcher.fetches[0]
        self.assertEqual(set(row), {"url", "final_url", "status", "fetched_at"})
        self.assertRegex(row["fetched_at"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$")

    def test_page_classes(self):
        self.assertEqual(classify(200, PAGE[2].decode()), "ok")
        self.assertEqual(classify(200, "<html><body><div id=root></div><script src=app.js></script></body></html>"), "js_shell")
        self.assertEqual(classify(403, "<h1>Access Denied</h1> Reference #18.2d3f1602.1700000000.1a2b3c"), "bot_wall")
        self.assertEqual(classify(200, "<p>Please complete the CAPTCHA to continue</p>"), "captcha")
        self.assertEqual(classify(200, "<form><input type='password' name=p></form>" + "word " * 100), "login")
        self.assertEqual(classify(None, ""), "error")


try:
    import playwright.sync_api  # noqa: F401
    HAVE_BROWSER = True
except ImportError:
    HAVE_BROWSER = False


class Site(http.server.BaseHTTPRequestHandler):
    hits = []
    pages = {
        "/robots.txt": ("text/plain", b"User-agent: *\nDisallow: /secret.json\n"),
        "/offers": ("text/html", b"<html><body><div id=list></div><script src='/app.js'></script>"
                                 b"<script src='http://127.0.0.1:1/tracker.js'></script><img src='/logo.png'></body></html>"),
        "/app.js": ("text/javascript", b"fetch('/data.json').then(r=>r.json()).then(d=>{document.getElementById('list').innerText=d.names.join(' | ')});"
                                       b"fetch('/secret.json').catch(()=>{});"),
        "/data.json": ("application/json", b'{"names": ["Example Kopi", "Sample Noodle Bar"]}'),
        "/secret.json": ("application/json", b'{"x": 1}'),
        "/logo.png": ("image/png", b"x"),
    }

    def do_GET(self):
        Site.hits.append(self.path)
        kind, body = self.pages.get(self.path, ("text/plain", b"missing"))
        self.send_response(200 if self.path in self.pages else 404)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@unittest.skipUnless(HAVE_BROWSER, "Playwright is not installed")
class BrowserPathTests(unittest.TestCase):
    def test_browser_requests_follow_robots_spacing_and_host_rules(self):
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Site)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_port}"
        log = os.path.join(tempfile.mkdtemp(prefix="fetcher-"), "log.jsonl")
        fetcher = PoliteFetcher(log, ["127.0.0.1"], AGENT, allow_http_hosts=[f"127.0.0.1:{server.server_port}"])
        Site.hits = []
        try:
            result = BrowserFetcher(fetcher).render(base + "/offers", settle_ms=6000)
        except Exception as err:
            if "Executable doesn't exist" in str(err):
                self.skipTest("no browser for Playwright. Set CRAWLER_CHROMIUM to a Chromium program.")
            raise
        finally:
            server.shutdown()
            server.server_close()
        self.assertEqual(result["status"], 200)
        self.assertIn("Example Kopi | Sample Noodle Bar", result["text"])
        self.assertEqual(result["via"], "browser")
        self.assertNotIn("/secret.json", Site.hits)
        self.assertNotIn("/logo.png", Site.hits)
        self.assertEqual(Site.hits[0], "/robots.txt")
        report = spacing_report(log)["127.0.0.1"]
        self.assertGreaterEqual(report["requests"], 4)
        with open(log, encoding="utf-8") as fh:
            rows = [json.loads(line) for line in fh]
        self.assertTrue(any(row.get("reason") == "robots_disallow" for row in rows))
        self.assertTrue(any(row.get("reason") in ("host_not_official", "not_https") for row in rows))
        self.assertTrue(all("mode" in row and "min_gap_s" in row and "gap_s" in row for row in rows))
        # robots.txt is fetched with urllib, so that line is plain. The page itself is the browser.
        self.assertTrue(any(row.get("kind") == "robots" and row.get("mode") == "plain" for row in rows))
        self.assertTrue(any(row.get("mode") == "browser" and row.get("event") == "request" for row in rows))
        paced = [row["start_mono"] for row in rows if row.get("event") == "request" and row.get("paced")]
        self.assertTrue(all(b - a >= 1.5 - 0.05 for a, b in zip(paced, paced[1:])), paced)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE_HTML = "<html><body>" + "offer words " * 60 + "</body></html>"
PAGE_TEXT = "offer words " * 60


def log_rows(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


class QuietPage:
    def __init__(self, url):
        self.url = url
        self.gotos = []
        self.contents = 0

    def route(self, *args, **kwargs):
        return None

    def goto(self, url, **kwargs):
        self.gotos.append(url)
        self.url = url

        def text():
            if url.endswith("/robots.txt"):
                return "User-agent: *\nDisallow: /secret\n"
            return PAGE_HTML

        return SimpleNamespace(status=200, url=url, headers={}, text=text)

    def wait_for_timeout(self, ms):
        return None

    def wait_for_load_state(self, state, timeout=None):
        return None

    def content(self):
        self.contents += 1
        return PAGE_HTML

    def evaluate(self, expression, *args, **kwargs):
        return PAGE_HTML

    def inner_text(self, selector, timeout=None):
        return PAGE_TEXT


class QuietBrowser:
    def close(self):
        return None


class PacingAndModeTests(unittest.TestCase):
    def test_min_gap_can_be_raised_and_the_spacing_report_still_works(self):
        net = FakeNet({"https://www.bank.example/robots.txt": (404, {}, b""),
                       "https://www.bank.example/a": PAGE, "https://www.bank.example/b": PAGE})
        log = os.path.join(tempfile.mkdtemp(prefix="fetcher-"), "log.jsonl")
        fetcher = PoliteFetcher(log, ["bank.example"], AGENT, min_gap=30, transport=net.transport,
                                clock=net.clock, sleep=net.sleep)
        fetcher.get("https://www.bank.example/a")
        fetcher.get("https://www.bank.example/b")
        times = [when for _url, when in net.calls]
        self.assertTrue(all(b - a >= 30 for a, b in zip(times, times[1:])), times)
        report = spacing_report(log)["bank.example"]
        self.assertEqual(report["requests"], 3)
        self.assertGreaterEqual(report["min_gap_s"], 30)
        self.assertEqual(report["gaps_under_min"], 0)
        self.assertEqual(report["configured_min_gap_s"], 30)
        self.assertEqual(report["gaps_under_configured"], 0)
        for row in log_rows(log):
            self.assertEqual(row["mode"], "plain")
            self.assertEqual(row["min_gap_s"], 30)
            self.assertIn("gap_s", row)

    def test_gap_flag_and_env_and_the_floor(self):
        self.assertEqual(configured_min_gap(["probe", "id", "https://h"], {}), 1.5)
        self.assertEqual(configured_min_gap(["probe", "id", "https://h"], {"CRAWLER_MIN_GAP": "30"}), 30.0)
        self.assertEqual(configured_min_gap(
            ["probe", "id", "https://h", "--min-gap", "45"], {"CRAWLER_MIN_GAP": "30"}), 45.0)
        with self.assertRaises(ValueError):
            configured_min_gap(["probe", "id", "https://h"], {"CRAWLER_MIN_GAP": "fast"})
        with self.assertRaises(ValueError):
            configured_min_gap(["probe", "id", "https://h", "--min-gap"], {})
        with self.assertRaises(ValueError):
            PoliteFetcher("/tmp/x.jsonl", ["bank.example"], AGENT, min_gap=configured_min_gap(
                ["probe", "id", "https://h", "--min-gap", "0.4"], {}))

    def test_every_plain_log_line_has_mode_and_gap(self):
        fetcher, _net, log = make({"https://www.bank.example/robots.txt": (404, {}, b""),
                                   "https://www.bank.example/a": PAGE})
        fetcher.get("https://www.bank.example/a")
        rows = log_rows(log)
        self.assertGreaterEqual(len(rows), 2)
        for row in rows:
            self.assertEqual(row["mode"], "plain")
            self.assertEqual(row["min_gap_s"], 1.5)
            self.assertIn("gap_s", row)

    def test_browser_and_real_chrome_modes_are_the_mode_that_fetched(self):
        fetcher, net, log = make({})
        page = QuietPage("https://www.bank.example/cards")
        BrowserFetcher(fetcher, launcher=lambda: (QuietBrowser(), page)).render(
            "https://www.bank.example/cards", settle_ms=0)
        rows = log_rows(log)
        self.assertTrue(any(row.get("kind") == "robots" and row["mode"] == "plain" for row in rows))
        self.assertTrue(any("robots.txt" in url for url, _when in net.calls))

        calls = []

        def transport(url, timeout, user_agent):
            calls.append(url)
            raise AssertionError("real chrome must not read robots.txt with urllib")

        log = os.path.join(tempfile.mkdtemp(prefix="fetcher-"), "log.jsonl")
        chrome_fetcher = PoliteFetcher(log, ["bank.example"], AGENT, transport=transport, clock=time.monotonic, sleep=lambda _s: None)
        page = QuietPage("https://www.bank.example/cards")
        result = BrowserFetcher(
            chrome_fetcher, real_chrome=True, approved_hosts=["bank.example"],
            launcher=lambda: (QuietBrowser(), page),
        ).render("https://www.bank.example/cards", settle_ms=0)
        self.assertEqual(result["status"], 200)
        self.assertEqual(calls, [])
        self.assertTrue(any(url.endswith("/robots.txt") for url in page.gotos))
        self.assertLess(page.gotos.index(next(url for url in page.gotos if url.endswith("/robots.txt"))),
                        page.gotos.index("https://www.bank.example/cards"))
        robots_rows = [row for row in log_rows(log) if row.get("kind") == "robots" or str(row.get("url", "")).endswith("/robots.txt")]
        self.assertTrue(robots_rows)
        self.assertTrue(all(row["mode"] == "real_chrome" for row in robots_rows))


class RealChromeTests(unittest.TestCase):
    def test_missing_display_raises(self):
        fetcher, _net, _log = make({})
        with patch("pipeline.fetcher.sys.platform", "linux"):
            with patch.dict(os.environ, {"DISPLAY": "", "WAYLAND_DISPLAY": ""}):
                with patch("pipeline.fetcher.find_chrome", return_value="/usr/bin/google-chrome"):
                    with self.assertRaises(RealChromeError) as caught:
                        BrowserFetcher(fetcher, real_chrome=True, approved_hosts=["bank.example"]).render(
                            "https://www.bank.example/cards")
        self.assertIn("display", str(caught.exception).lower())

    def test_missing_chrome_raises(self):
        fetcher, _net, _log = make({})
        with patch("pipeline.fetcher.sys.platform", "linux"):
            with patch.dict(os.environ, {"DISPLAY": ":99"}):
                with patch("pipeline.fetcher.find_chrome", return_value=None):
                    with self.assertRaises(RealChromeError) as caught:
                        BrowserFetcher(fetcher, real_chrome=True, approved_hosts=["bank.example"]).render(
                            "https://www.bank.example/cards")
        self.assertIn("Chrome", str(caught.exception))

    def test_launch_uses_channel_chrome_headed_profile_and_does_not_set_a_user_agent(self):
        fetcher, _net, _log = make({})
        profile = tempfile.mkdtemp(prefix="chrome-profile-")
        captured = {}

        class Context:
            pages = []

            def new_page(self):
                return SimpleNamespace()

            def close(self):
                return None

        class Chromium:
            def launch_persistent_context(self, user_data_dir, **kwargs):
                captured["user_data_dir"] = user_data_dir
                captured["kwargs"] = kwargs
                return Context()

        class Play:
            chromium = Chromium()

        browser = BrowserFetcher(fetcher, launch_args=["--disable-http2"], real_chrome=True, user_data_dir=profile)
        with patch("pipeline.fetcher.sys.platform", "linux"):
            with patch.dict(os.environ, {"DISPLAY": ":99"}):
                with patch("pipeline.fetcher.find_chrome", return_value="/usr/bin/google-chrome"):
                    browser._launch(Play())
        self.assertEqual(captured["user_data_dir"], profile)
        kwargs = captured["kwargs"]
        self.assertEqual(kwargs["channel"], "chrome")
        self.assertIs(kwargs["headless"], False)
        self.assertNotIn("user_agent", kwargs)
        self.assertEqual(kwargs["args"], ["--disable-http2"])
        self.assertNotIn("proxy", kwargs)
        self.assertNotIn("executable_path", kwargs)
        self.assertNotIn("ignore_default_args", kwargs)

    def test_a_chrome_launch_error_is_real_chrome_error(self):
        fetcher, _net, _log = make({})

        class Chromium:
            def launch_persistent_context(self, user_data_dir, **kwargs):
                raise RuntimeError("Missing X server or $DISPLAY")

        class Play:
            chromium = Chromium()

        browser = BrowserFetcher(fetcher, real_chrome=True, user_data_dir=tempfile.mkdtemp(prefix="chrome-profile-"))
        with patch("pipeline.fetcher.sys.platform", "linux"):
            with patch.dict(os.environ, {"DISPLAY": ":99"}):
                with patch("pipeline.fetcher.find_chrome", return_value="/usr/bin/google-chrome"):
                    with self.assertRaises(RealChromeError) as caught:
                        browser._launch(Play())
        self.assertIn("display", str(caught.exception).lower())

    def test_profile_defaults_to_the_gitignored_cache(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CRAWLER_CHROME_PROFILE", None)
            path = chrome_profile_dir()
        self.assertEqual(path, os.path.join(ROOT, ".cache", "chrome-profile"))
        with open(os.path.join(ROOT, ".gitignore"), encoding="utf-8") as fh:
            ignored = fh.read()
        self.assertIn(".cache/", ignored)
        with patch.dict(os.environ, {"CRAWLER_CHROME_PROFILE": "/tmp/crawler-chrome-profile"}):
            self.assertEqual(chrome_profile_dir(), "/tmp/crawler-chrome-profile")

    def test_document_is_read_when_settle_times_out(self):
        fetcher, _net, _log = make({})
        page = QuietPage("https://www.bank.example/cards")

        def settle(_state, timeout=None):
            raise TimeoutError("networkidle cap")

        page.wait_for_load_state = settle
        result = BrowserFetcher(fetcher, launcher=lambda: (QuietBrowser(), page)).render(
            "https://www.bank.example/cards", settle_ms=50)
        self.assertEqual(result["status"], 200)
        self.assertEqual(page.contents, 1)
        self.assertIn("offer words", result["text"])

    def test_parent_returns_when_the_child_hangs(self):
        fetcher, _net, log = make({})
        marker = os.path.join(tempfile.mkdtemp(prefix="fetcher-hang-"), "child.pid")
        browser = BrowserFetcher(fetcher, hard_timeout=1.0, worker_target=_sleep_child)
        browser.worker_spec = {"marker": marker}
        started = time.monotonic()
        result = browser.render("https://www.bank.example/cards", settle_ms=0)
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 12, "the parent must return when the child hangs")
        self.assertGreater(elapsed, 0.5)
        self.assertEqual(result["not_fetched"], "timeout")
        self.assertEqual(result["class"], "timeout")
        rows = log_rows(log)
        self.assertTrue(any(row.get("reason") == "timeout" and row.get("mode") == "browser" for row in rows))
        if os.path.exists(marker):
            with open(marker, encoding="ascii") as fh:
                pid = int(fh.read().strip())
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                try:
                    os.kill(pid, 0)
                except OSError:
                    break
                time.sleep(0.05)
            else:
                self.fail(f"grandchild {pid} was still alive after the process group was killed")

    def test_min_gap_applies_to_documents_xhr_and_fetch_but_not_to_scripts(self):
        net = FakeNet({})
        log = os.path.join(tempfile.mkdtemp(prefix="fetcher-"), "log.jsonl")
        fetcher = PoliteFetcher(log, ["bank.example"], AGENT, min_gap=30, transport=net.transport,
                                clock=net.clock, sleep=net.sleep)
        fetcher.robots["www.bank.example"] = ("allow_all", None)
        tool = BrowserFetcher(fetcher)
        tool._page_url = "https://www.bank.example/offers"

        class Request:
            def __init__(self, url, resource_type, navigation, method="GET"):
                self.url = url
                self.resource_type = resource_type
                self.method = method
                self.navigation = navigation

            def is_navigation_request(self):
                return self.navigation

        class Route:
            def __init__(self):
                self.action = None

            def fetch(self, **kwargs):
                return SimpleNamespace(status=200, headers={})

            def fulfill(self, **kwargs):
                self.action = ("fulfill", kwargs)

            def abort(self):
                self.action = ("abort",)

            def continue_(self, **kwargs):
                self.action = ("continue", kwargs)

        script = Request("https://www.bank.example/app.js", "script", False)
        route = Route()
        tool._route(route, script)
        style = Route()
        tool._route(style, Request("https://www.bank.example/app.css", "stylesheet", False))
        self.assertEqual(net.now, 100.0)
        self.assertEqual(fetcher.last_start, {})
        xhr = Route()
        tool._route(xhr, Request("https://www.bank.example/data.json", "xhr", False))
        self.assertIn("bank.example", fetcher.last_start)
        first = fetcher.last_start["bank.example"]
        tool._route(Route(), Request("https://www.bank.example/more.json", "fetch", False))
        self.assertGreaterEqual(fetcher.last_start["bank.example"] - first, 30)
        document = Request("https://www.bank.example/offers", "document", True)
        tool._route(Route(), document)
        after_xhr = fetcher.last_start["bank.example"]
        self.assertGreaterEqual(after_xhr - first, 30)
        off = Route()
        tool._route(off, Request("https://cdn.cookielaw.org/script.js", "script", False))
        self.assertEqual(off.action[0], "fulfill")
        self.assertEqual(off.action[1]["status"], 204)
        self.assertNotEqual(off.action[0], "abort")

    def test_probe_url_uses_the_network_domains(self):
        root = ROOT
        label, url, domains = resolve_probe(root, [
            "fetcher.py", "probe", "--url", "https://specials.priceless.com/en-my/homepage", "--country", "MY",
        ])
        self.assertEqual(label, "network-mastercard")
        self.assertEqual(url, "https://specials.priceless.com/en-my/homepage")
        normalized = {name[4:] if name.lower().startswith("www.") else name.lower() for name in domains}
        self.assertIn("specials.priceless.com", normalized)
        self.assertIn("priceless.com", normalized)
        self.assertIn("mastercard.com", normalized)
        with self.assertRaises(ValueError):
            resolve_probe(root, ["fetcher.py", "probe", "--url", "https://example.com/", "--country", "MY"])
        seen = {}

        class FakeFetcher:
            def __init__(self, log_path, official_domains, user_agent, min_gap=1.5, **kwargs):
                seen["domains"] = set(official_domains)
                seen["gap"] = min_gap
                self.blocked, self.rechecks = [], []
                self.mode, self.min_gap, self.log_path = "plain", min_gap, log_path
                os.makedirs(os.path.dirname(log_path), exist_ok=True)
                open(log_path, "a", encoding="utf-8").close()

            def get(self, page):
                seen["url"] = page
                return {"url": page, "status": 200, "text": "offer words " * 10, "class": "ok"}

        with patch.dict(os.environ, {"CRAWLER_USER_AGENT": AGENT}):
            with patch("pipeline.fetcher.PoliteFetcher", FakeFetcher):
                with redirect_stdout(io.StringIO()):
                    code = main([
                        "fetcher.py", "probe", "--url", "https://specials.priceless.com/en-my/homepage",
                        "--country", "MY", "--min-gap", "30",
                    ])
        self.assertEqual(code, 0)
        self.assertEqual(seen["url"], "https://specials.priceless.com/en-my/homepage")
        self.assertEqual(seen["gap"], 30)
        self.assertIn("specials.priceless.com", seen["domains"])


class FetcherGuardTests(unittest.TestCase):
    def test_fetcher_does_not_import_a_stealth_plugin_or_set_a_proxy(self):
        path = os.path.join(ROOT, "pipeline", "fetcher.py")
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
        self.assertNotIn("\u2014", source)
        tree = ast.parse(source)
        banned = ("stealth", "undetected_chromedriver", "puppeteer")
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""] + [alias.name for alias in node.names]
            else:
                names = []
            for name in names:
                lowered = name.lower().replace("-", "_")
                self.assertFalse(any(part in lowered for part in banned), name)
            if isinstance(node, ast.keyword) and (node.arg or "").lower() in {"proxy", "proxy_server"}:
                self.fail("fetcher.py sets a proxy")
            if isinstance(node, ast.Dict):
                for key in node.keys:
                    if isinstance(key, ast.Constant) and str(key.value).lower() in {"proxy", "proxy_server"}:
                        self.fail("fetcher.py sets a proxy")
            if isinstance(node, ast.Attribute) and node.attr.lower() in {"proxy", "proxy_server"}:
                self.fail("fetcher.py sets a proxy")




class MergeConditionTests(unittest.TestCase):
    """The eight conditions that must hold before real-Chrome mode can be merged."""

    def _tool(self, min_gap=30):
        net = FakeNet({})
        log = os.path.join(tempfile.mkdtemp(prefix="fetcher-"), "log.jsonl")
        fetcher = PoliteFetcher(log, ["bank.example"], AGENT, min_gap=min_gap, transport=net.transport,
                                clock=net.clock, sleep=net.sleep)
        fetcher.robots["www.bank.example"] = ("allow_all", None)
        tool = BrowserFetcher(fetcher)
        tool._page_url = "https://www.bank.example/offers"
        return tool, fetcher, net, log

    def _request(self, url, resource_type, navigation=False, method="GET"):
        class Request:
            def __init__(self):
                self.url = url
                self.resource_type = resource_type
                self.method = method
                self.navigation = navigation

            def is_navigation_request(self):
                return self.navigation

        return Request()

    def _route(self, status=200, error=None):
        class Route:
            def __init__(self):
                self.action = None

            def fetch(self, **kwargs):
                if error:
                    raise RuntimeError(error)
                return SimpleNamespace(status=status, headers={})

            def fulfill(self, **kwargs):
                self.action = ("fulfill", kwargs)

            def abort(self):
                self.action = ("abort",)

            def continue_(self, **kwargs):
                self.action = ("continue", kwargs)

        return Route()

    def test_approved_hosts_file_starts_empty(self):
        hosts = load_real_chrome_hosts(ROOT)
        self.assertEqual(hosts, [])
        self.assertFalse(real_chrome_host_allowed("https://specials.priceless.com/", hosts))

    def test_real_chrome_refuses_a_host_that_is_not_approved(self):
        fetcher, _net, _log = make({})
        with self.assertRaises(RealChromeError) as caught:
            BrowserFetcher(fetcher, real_chrome=True, launcher=lambda: (QuietBrowser(), QuietPage("https://www.bank.example/cards"))).render(
                "https://www.bank.example/cards", settle_ms=0)
        self.assertIn("real_chrome_hosts.json", str(caught.exception))
        self.assertIn("bank.example", str(caught.exception))

    def test_headless_browser_still_sets_the_configured_user_agent(self):
        fetcher, _net, _log = make({})
        captured = {}

        class Context:
            def new_page(self):
                return SimpleNamespace()

        class Browser:
            def new_context(self, **kwargs):
                captured["kwargs"] = kwargs
                return Context()

            def close(self):
                return None

        class Chromium:
            def launch(self, **kwargs):
                return Browser()

        class Play:
            chromium = Chromium()

        _browser, _page = BrowserFetcher(fetcher)._launch(Play())
        self.assertEqual(captured["kwargs"]["user_agent"], AGENT)

    def test_same_origin_non_get_is_continued_and_logged(self):
        tool, fetcher, _net, log = self._tool()
        route = self._route()
        tool._route(route, self._request("https://www.bank.example/api/offers", "fetch", method="POST"))
        self.assertEqual(route.action[0], "continue")
        rows = log_rows(log)
        match = [row for row in rows if row.get("event") == "request" and row.get("method") == "POST"]
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0]["url"], "https://www.bank.example/api/offers")
        self.assertEqual(match[0]["method"], "POST")
        self.assertTrue(match[0]["paced"])

    def test_non_same_origin_non_get_is_blanked(self):
        tool, fetcher, _net, log = self._tool()
        route = self._route()
        tool._route(route, self._request("https://other.example/collect", "xhr", method="POST"))
        self.assertEqual(route.action[0], "fulfill")
        self.assertEqual(route.action[1]["status"], 204)
        rows = log_rows(log)
        self.assertTrue(any(row.get("reason") == "not_a_get_request" and row.get("method") == "POST" for row in rows))
        self.assertEqual(tool._data_problems[0]["how"], "blanked")

    def test_page_is_not_ok_when_a_data_call_is_blanked_or_failed(self):
        tool, fetcher, _net, _log = self._tool()
        # Enough words that classify would otherwise return ok.
        html = "<html><body>" + "offer words " * 60 + "</body></html>"
        text = "offer words " * 60
        self.assertEqual(classify(200, html), "ok")
        tool._data_problems = [{"kind": "xhr", "how": "blanked", "url": "https://www.bank.example/data", "method": "GET"}]
        self.assertEqual(tool._page_class(200, html, text), "js_shell")
        tool._data_problems = [{"kind": "fetch", "how": "failed", "url": "https://www.bank.example/data", "method": "GET"}]
        self.assertEqual(tool._page_class(200, html, text), "js_shell")

    def test_js_shell_is_not_promoted_to_ok_when_a_data_call_failed(self):
        tool, fetcher, _net, _log = self._tool()
        html = "<html><body><div id=root></div><script src=app.js></script></body></html>"
        text = "offer words " * 60
        self.assertEqual(classify(200, html), "js_shell")
        tool._data_problems = []
        self.assertEqual(tool._page_class(200, html, text), "ok")
        tool._data_problems = [{"kind": "xhr", "how": "failed", "url": "https://www.bank.example/data", "method": "GET"}]
        self.assertEqual(tool._page_class(200, html, text), "js_shell")

    def test_fetched_at_is_the_start_time_after_the_wait(self):
        class Wall:
            def __init__(self, net):
                self.net = net

            def __call__(self):
                import datetime
                return datetime.datetime(2026, 11, 12, 21, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=8))) + datetime.timedelta(seconds=self.net.now - 100)

        net = FakeNet({"https://www.bank.example/robots.txt": (404, {}, b""),
                       "https://www.bank.example/a": PAGE, "https://www.bank.example/b": PAGE})
        log = os.path.join(tempfile.mkdtemp(prefix="fetcher-"), "log.jsonl")
        wall = Wall(net)
        fetcher = PoliteFetcher(log, ["bank.example"], AGENT, min_gap=30, transport=net.transport,
                                clock=net.clock, sleep=net.sleep, wall=wall)
        first = fetcher.get("https://www.bank.example/a")
        second = fetcher.get("https://www.bank.example/b")
        # robots at 100, first page after 1.5s default... min_gap is 30, so starts at 100, 130, 160
        self.assertEqual(first["fetched_at"], "2026-11-12T21:00:30+08:00")
        self.assertEqual(second["fetched_at"], "2026-11-12T21:01:00+08:00")
        # Browser document start uses the same helper after the wait.
        fetcher.robots["www.bank.example"] = ("allow_all", None)
        tool = BrowserFetcher(fetcher)
        tool._page_url = "https://www.bank.example/offers"
        route = self._route()
        before = net.now
        tool._route(route, self._request("https://www.bank.example/offers", "document", navigation=True))
        self.assertGreaterEqual(net.now - before, 30)
        # The document start is after this wait, not before it.
        self.assertIsNotNone(tool._document_started)
        self.assertGreaterEqual(net.now, before + 30)

    def test_spacing_report_orders_gaps_by_request_start(self):
        log = os.path.join(tempfile.mkdtemp(prefix="fetcher-"), "log.jsonl")
        # Completion order is reversed from start order, which used to print a negative min gap.
        rows = [
            {"event": "request", "host": "bank.example", "start_mono": 12.5, "min_gap_s": 1.5, "paced": True},
            {"event": "request", "host": "bank.example", "start_mono": 9.438, "min_gap_s": 1.5, "paced": True},
            {"event": "request", "host": "bank.example", "start_mono": 10.938, "min_gap_s": 1.5, "paced": True},
        ]
        with open(log, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(__import__("json").dumps(row) + "\n")
        report = spacing_report(log)["bank.example"]
        self.assertEqual(report["requests"], 3)
        self.assertGreaterEqual(report["min_gap_s"], 0)
        self.assertEqual(report["min_gap_s"], 1.5)
        self.assertEqual(report["gaps_under_min"], 0)
        # Unpaced script starts are not used for the gap figure.
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(__import__("json").dumps({
                "event": "request", "host": "bank.example", "start_mono": 10.95, "min_gap_s": 1.5, "paced": False,
            }) + "\n")
        report = spacing_report(log)["bank.example"]
        self.assertEqual(report["requests"], 4)
        self.assertEqual(report["min_gap_s"], 1.5)

    def test_probe_keeps_the_page_text_under_raw(self):
        root = tempfile.mkdtemp(prefix="probe-root-")
        result = {"url": "https://www.bank.example/cards", "status": 200,
                  "text": "visible page text", "body": b"<html>visible page text</html>", "class": "ok"}
        text_path, html_path = write_probe_page(root, "my-maybank", result, when=__import__("datetime").datetime(2026, 11, 12, 21, 45, 0))
        self.assertTrue(text_path.startswith(os.path.join(root, "raw", "probes")))
        self.assertIn("/raw/", text_path.replace("\\", "/"))
        with open(text_path, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "visible page text")
        with open(html_path, "rb") as fh:
            self.assertEqual(fh.read(), b"<html>visible page text</html>")
        with open(os.path.join(ROOT, ".gitignore"), encoding="utf-8") as fh:
            self.assertIn("raw/", fh.read())

    def test_probe_main_writes_the_page_text_and_does_not_drop_it(self):
        seen = {}

        class FakeFetcher:
            def __init__(self, log_path, official_domains, user_agent, min_gap=1.5, **kwargs):
                self.blocked, self.rechecks = [], []
                self.mode, self.min_gap, self.log_path = "plain", min_gap, log_path
                os.makedirs(os.path.dirname(log_path), exist_ok=True)
                open(log_path, "a", encoding="utf-8").close()

            def get(self, page):
                seen["url"] = page
                return {"url": page, "status": 200, "text": "kept page text " * 8,
                        "body": b"<html>kept page text</html>", "class": "ok"}

        with patch.dict(os.environ, {"CRAWLER_USER_AGENT": AGENT}):
            with patch("pipeline.fetcher.PoliteFetcher", FakeFetcher):
                with patch("pipeline.fetcher.write_probe_page") as writer:
                    writer.return_value = ("raw/probes/fake.txt", "raw/probes/fake.html")
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        code = main([
                            "fetcher.py", "probe", "--url", "https://specials.priceless.com/en-my/homepage",
                            "--country", "MY",
                        ])
        self.assertEqual(code, 0)
        self.assertTrue(writer.called)
        _args, kwargs = (writer.call_args[0], writer.call_args[1]) if writer.call_args else ((), {})
        result = writer.call_args[0][2]
        self.assertEqual(result["text"], "kept page text " * 8)
        self.assertEqual(result["body"], b"<html>kept page text</html>")
        out = buf.getvalue()
        self.assertIn("raw/probes/fake.txt", out)
        self.assertIn("page_text", out)


if __name__ == "__main__":
    unittest.main()
