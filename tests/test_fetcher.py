"""The reference fetcher: robots policy, spacing, redirects, skipped URLs and the browser path. No network."""
import http.server
import json
import os
import tempfile
import threading
import unittest

from pipeline.fetcher import BrowserFetcher, PoliteFetcher, Robots, classify, clean_url, spacing_report

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

    def test_every_other_answer_stops_the_host(self):
        for answer in ((401, {}, b""), (403, {}, b""), (429, {}, b""), (500, {}, b""), (503, {}, b""),
                       OSError("timed out"), (302, {"Location": "https://other.example/robots.txt"}, b""),
                       (302, {}, b"")):
            result, fetcher, net = self.run_with_robots(answer)
            self.assertEqual(result.get("not_fetched"), "robots_unreachable", answer)
            self.assertNotIn("https://www.bank.example/cards", [url for url, _ in net.calls], answer)
            self.assertEqual(fetcher.blocked[0]["reason"], "robots_unreachable")

    def test_robots_redirect_inside_official_domains_is_followed(self):
        fetcher, net, _ = make({
            "https://www.bank.example/robots.txt": (301, {"Location": "https://static.bank.example/robots.txt"}, b""),
            "https://static.bank.example/robots.txt": (200, {}, b"User-agent: *\nDisallow: /x\n"),
            "https://www.bank.example/cards": PAGE,
        }, domains=("bank.example", "static.bank.example"))
        self.assertEqual(fetcher.get("https://www.bank.example/cards")["status"], 200)

    def test_robots_redirect_loop_stops_the_host(self):
        fetcher, _, _ = make({
            "https://www.bank.example/robots.txt": (301, {"Location": "https://www.bank.example/r2"}, b""),
            "https://www.bank.example/r2": (301, {"Location": "https://www.bank.example/robots.txt"}, b""),
        })
        self.assertEqual(fetcher.get("https://www.bank.example/cards")["not_fetched"], "robots_unreachable")

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
        self.assertEqual(result["status"], 200)
        self.assertIn("Example Kopi | Sample Noodle Bar", result["text"])
        self.assertEqual(result["via"], "browser")
        self.assertNotIn("/secret.json", Site.hits)
        self.assertNotIn("/logo.png", Site.hits)
        self.assertEqual(Site.hits[0], "/robots.txt")
        report = spacing_report(log)["127.0.0.1"]
        self.assertGreaterEqual(report["requests"], 4)
        self.assertEqual(report["gaps_under_min"], 0)
        with open(log, encoding="utf-8") as fh:
            rows = [json.loads(line) for line in fh]
        self.assertTrue(any(row.get("reason") == "robots_disallow" for row in rows))
        self.assertTrue(any(row.get("reason") in ("host_not_official", "not_https") for row in rows))


if __name__ == "__main__":
    unittest.main()
