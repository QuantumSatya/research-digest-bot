"""Offline tests (no network): keyword matching, query building, feed parsing,
PDF report writing and a full mocked weekly run."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import digest   # noqa: E402
import feeds    # noqa: E402
import pdfreport  # noqa: E402
import rebuild_reports  # noqa: E402


class Matching(unittest.TestCase):
    def test_phrases_and_operators(self):
        t, a = "Quantum imaging with a time-tagging camera", "We use SPDC photons."
        self.assertTrue(feeds.matches("time tagging AND camera", t, a, []))
        self.assertTrue(feeds.matches("quantum imaging ANDNOT microscopy", t, a, []))
        self.assertFalse(feeds.matches("ghost imaging", t, a, []))
        self.assertTrue(feeds.matches("QKD OR SPDC photon", t, a, []))

    def test_dashes_plurals_and_accents(self):
        self.assertTrue(feeds.matches("Hong-Ou-Mandel AND photon", "Hong–Ou–Mandel dip", "two photons", []))
        self.assertTrue(feeds.matches("au:Grafe AND au:Markus", "x", "", ["Markus Gräfe"]))
        self.assertTrue(feeds.matches("ti:review AND quantum optics", "A review", "quantum optics", []))
        self.assertFalse(feeds.matches("ti:review AND quantum optics", "Squeezing", "we review quantum optics", []))


class Feeds(unittest.TestCase):
    def test_rss2_and_rdf(self):
        rss = b"""<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel>
        <item><title>Ghost imaging</title><link>https://ex.org/a</link>
        <description>&lt;p&gt;With light.&lt;/p&gt;</description><dc:creator>A. B, C. D</dc:creator>
        <pubDate>Wed, 04 Nov 2026 10:00:00 +0000</pubDate></item></channel></rss>"""
        it = feeds.parse_feed(rss, "J")[0]
        self.assertEqual(it["abstract"], "With light.")
        self.assertEqual(it["authors"], ["A. B", "C. D"])
        self.assertEqual(it["date"].year, 2026)


class Report(unittest.TestCase):
    def test_pdf_has_links_and_tick_boxes_and_rebuild_keeps_ticks(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "Report_2026-01-05_to_2026-01-12.pdf"
            papers = [dict(id="2601.00001", title="Title α", authors=["A"], abstract="Photons.",
                           abs_url="https://arxiv.org/abs/2601.00001", category="quant-ph",
                           published="2026-01-06", keywords=["k"])]
            pdfreport.build_report(out, "2026-01-05_to_2026-01-12", papers, [], liked={"like_1"})
            raw = out.read_bytes()
            self.assertTrue(raw.startswith(b"%PDF"))
            self.assertIn(b"/URI (https://arxiv.org/abs/2601.00001)", raw)
            self.assertIn(b"/T (like_1)", raw)
            p, j, liked = rebuild_reports.read_pdf(out)
            self.assertEqual(p[0]["title"], "Title alpha")
            self.assertEqual(liked, {"like_1"})


class FullRun(unittest.TestCase):
    def test_mocked_weekly_run(self):
        now = dt.datetime.now(dt.timezone.utc)
        atom = f"""<feed xmlns="http://www.w3.org/2005/Atom">
          <entry><id>http://arxiv.org/abs/2601.00007v1</id><published>{now:%Y-%m-%dT%H:%M:%SZ}</published>
          <title>Quantum imaging test</title><summary>Photon pairs.</summary><author><name>X Y</name></author></entry>
          <entry><id>http://arxiv.org/abs/2601.00008v1</id><published>{now:%Y-%m-%dT%H:%M:%SZ}</published>
          <title>Quantum imaging of farms</title><summary>Drones and tractors.</summary></entry></feed>""".encode()
        with tempfile.TemporaryDirectory() as d:
            os.environ["DIGEST_OUTPUT_DIR"] = d
            digest.http_get = lambda url, timeout=60: atom if "arxiv" in url else b"<rss><channel/></rss>"
            digest.time.sleep = lambda s: None
            digest.main(["--now"])
            reports = list(Path(d).glob("Report_*.pdf"))
            self.assertEqual(len(reports), 1)
            data = json.loads(next(Path(d, "_state", "reports").glob("*.json")).read_text())
            ids = [p["id"] for p in data["papers"]]
            self.assertIn("2601.00007", ids)          # on topic
            self.assertNotIn("2601.00008", ids)       # filtered out (no photon/light words)
            os.environ.pop("DIGEST_OUTPUT_DIR")


if __name__ == "__main__":
    unittest.main()
