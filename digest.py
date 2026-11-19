#!/usr/bin/env python3
"""
Research Digest Bot
===================

Watches arXiv and journal RSS feeds for your keywords and authors, and once a
week writes ONE summary PDF (titles, authors, abstracts, clickable links, and a
"like" tick box per article). Optionally emails you when a report is ready.

* Pure Python standard library – no pip install needed (Python 3.8+).
* Runs on macOS, Linux and Windows; schedule it with launchd / cron / Task Scheduler.

Usage
-----
    python3 digest.py                      normal run (weekly report on the report day)
    python3 digest.py --now                make a report right now
    python3 digest.py --now --from 2026-01-05   report for a chosen period
    python3 digest.py --test-email         send a test email
    python3 digest.py --show-queries       print the arXiv queries and exit

See README.md and docs/ for the full documentation.
"""

from __future__ import annotations

import configparser
import datetime as dt
import json
import os
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import feeds  # noqa: E402
import pdfreport  # noqa: E402

__version__ = "1.0.0"

# ---------------------------------------------------------------- configuration
CONFIG_FILE = Path(os.environ.get("DIGEST_CONFIG", HERE / "config.ini"))
USER_FILES = {                     # user file -> shipped example it is created from
    "config.ini": "config.example.ini",
    "keywords.txt": "keywords.example.txt",
    "journals.txt": "journals.example.txt",
    "filters.txt": "filters.example.txt",
}
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
API_URL = "https://export.arxiv.org/api/query"
NS = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}


def ensure_user_files() -> None:
    """On first run, copy the *.example.* files to the editable user files."""
    for user, example in USER_FILES.items():
        if not (HERE / user).exists() and (HERE / example).exists():
            shutil.copyfile(HERE / example, HERE / user)


class Settings:
    def __init__(self, path: Path) -> None:
        cp = configparser.ConfigParser(inline_comment_prefixes=("#", ";"))
        cp.read(path, encoding="utf-8")
        g = lambda sec, key, default: cp.get(sec, key, fallback=default).strip()  # noqa: E731
        out = os.environ.get("DIGEST_OUTPUT_DIR") or g("paths", "output_dir", "~/ResearchDigest")
        self.output_dir = Path(os.path.expanduser(out))
        self.keywords_file = HERE / g("paths", "keywords_file", "keywords.txt")
        self.journals_file = HERE / g("paths", "journals_file", "journals.txt")
        self.filters_file = HERE / g("paths", "filters_file", "filters.txt")

        day = g("schedule", "report_weekday", "monday").lower()
        self.report_weekday = WEEKDAYS.index(day) if day in WEEKDAYS else 0
        self.first_run_lookback_days = int(g("schedule", "first_run_lookback_days", "7"))
        self.max_age_days = int(g("schedule", "max_age_days", "21"))

        self.max_results = int(g("arxiv", "max_results_per_keyword", "300"))
        self.api_pause = max(3.0, float(g("arxiv", "pause_seconds", "3.5")))
        self.user_agent = g("arxiv", "user_agent", f"research-digest-bot/{__version__}")

        self.email_method = g("email", "method", "none").lower()
        self.email_to = g("email", "to", "")
        self.smtp_host = g("email", "smtp_host", "")
        self.smtp_port = int(g("email", "smtp_port", "587"))
        self.smtp_user = g("email", "smtp_user", "")
        self.smtp_from = g("email", "smtp_from", "") or self.smtp_user
        self.attach_pdf = g("email", "attach_pdf", "yes").lower() in ("1", "yes", "true", "on")

        self.state_dir = self.output_dir / "_state"
        self.seen_file = self.state_dir / "seen.json"
        self.log_file = self.state_dir / "digest.log"
        self.reports_store = self.state_dir / "reports"


S: Settings  # set in main()


# ---------------------------------------------------------------- helpers
def log(msg: str) -> None:
    line = f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    try:
        S.state_dir.mkdir(parents=True, exist_ok=True)
        with S.log_file.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except (OSError, NameError):
        pass


def read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.strip().startswith("#")]


FILTER_CATS: list[str] = []
FILTER_TERMS: list[str] = []


def load_filters(path: Path) -> None:
    """filters.txt: 'categories: a, b' and 'must_mention: x, y' – keeps results on topic."""
    FILTER_CATS.clear()
    FILTER_TERMS.clear()
    for line in read_lines(path):
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        items = [v.strip() for v in val.split(",") if v.strip()]
        if key.strip().lower() == "categories":
            FILTER_CATS.extend(items)
        elif key.strip().lower() == "must_mention":
            FILTER_TERMS.extend(items)


def on_topic(title: str, abstract: str) -> bool:
    if not FILTER_TERMS:
        return True
    return feeds.matches(" OR ".join(FILTER_TERMS), title, abstract, [])


def build_query(keyword: str) -> str:
    """keywords.txt line -> arXiv API query.
       'quantum imaging'          -> all:"quantum imaging"
       'time tagging AND camera'  -> (all:"time tagging" AND all:"camera")
       'au:Padgett'               -> au:Padgett
    plus the category / must-mention filters from filters.txt."""
    tokens = re.split(r"\s+(AND|OR|ANDNOT)\s+", keyword)
    out = []
    for t in tokens:
        if t in ("AND", "OR", "ANDNOT"):
            out.append(t)
        elif re.match(r"^(ti|au|abs|co|jr|cat|all):", t.strip()):
            out.append(t.strip())
        else:
            out.append(f'all:"{t.strip()}"')
    q = " ".join(out)
    q = f"({q})" if len(out) > 1 else q
    if FILTER_CATS:
        q += " AND (" + " OR ".join(f"cat:{c}" for c in FILTER_CATS) + ")"
    if FILTER_TERMS:
        q += " AND (" + " OR ".join(f'abs:"{t}"' for t in FILTER_TERMS) + ")"
    return q


def http_get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": S.user_agent})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if attempt == 2:
                raise
            log(f"  retry after error: {e}")
            time.sleep(10 * (attempt + 1))
    return b""


def search_arxiv_raw(keyword: str) -> list[dict]:
    params = {"search_query": build_query(keyword), "sortBy": "submittedDate",
              "sortOrder": "descending", "start": 0, "max_results": S.max_results}
    root = ET.fromstring(http_get(API_URL + "?" + urllib.parse.urlencode(params)))
    papers = []
    for e in root.findall("a:entry", NS):
        full_id = e.findtext("a:id", "", NS).rsplit("/abs/", 1)[-1]
        base_id = re.sub(r"v\d+$", "", full_id)
        pc = e.find("arxiv:primary_category", NS)
        papers.append({
            "id": base_id,
            "title": " ".join(e.findtext("a:title", "", NS).split()),
            "abstract": " ".join(e.findtext("a:summary", "", NS).split()),
            "authors": [a.findtext("a:name", "", NS) for a in e.findall("a:author", NS)],
            "published": e.findtext("a:published", "", NS),
            "category": pc.get("term") if pc is not None else "",
            "abs_url": f"https://arxiv.org/abs/{base_id}",
            "pdf_url": f"https://arxiv.org/pdf/{base_id}",
        })
    return papers


def load_state() -> dict:
    if S.seen_file.exists():
        try:
            return json.loads(S.seen_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"seen": {}, "last_run": None}


def save_state(state: dict) -> None:
    S.state_dir.mkdir(parents=True, exist_ok=True)
    tmp = S.seen_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1), encoding="utf-8")
    tmp.replace(S.seen_file)


# ---------------------------------------------------------------- email
MAIL_SCRIPT = """
on run argv
    set theSubject to item 1 of argv
    set theBody to item 2 of argv
    set theTo to item 3 of argv
    tell application "Mail"
        set m to make new outgoing message with properties {subject:theSubject, content:theBody, visible:false}
        tell m to make new to recipient at end of to recipients with properties {address:theTo}
        send m
    end tell
end run
"""


def send_email(subject: str, body: str, attachment: Path | None = None) -> None:
    if S.email_method in ("", "none") or not S.email_to:
        return
    try:
        if S.email_method == "mail_app":                 # macOS Mail.app, no password stored
            import subprocess
            if not shutil.which("osascript"):
                log("  email skipped: mail_app needs macOS")
                return
            r = subprocess.run(["osascript", "-e", MAIL_SCRIPT, subject, body, S.email_to],
                               capture_output=True, text=True, timeout=120)
            if r.returncode:
                raise RuntimeError(r.stderr.strip())
        elif S.email_method == "smtp":                   # any provider; password from env
            import smtplib
            from email.message import EmailMessage
            pw = os.environ.get("DIGEST_SMTP_PASSWORD", "")
            msg = EmailMessage()
            msg["Subject"], msg["From"], msg["To"] = subject, S.smtp_from, S.email_to
            msg.set_content(body)
            if attachment and S.attach_pdf and attachment.exists():
                msg.add_attachment(attachment.read_bytes(), maintype="application",
                                   subtype="pdf", filename=attachment.name)
            with smtplib.SMTP(S.smtp_host, S.smtp_port, timeout=60) as s:
                s.starttls()
                if S.smtp_user:
                    s.login(S.smtp_user, pw)
                s.send_message(msg)
        else:
            log(f"  unknown email method '{S.email_method}'")
            return
        log(f"  email sent to {S.email_to}")
    except Exception as e:  # noqa: BLE001
        log(f"  email FAILED: {e}")


def _authors(a: list[str], n: int) -> str:
    return ", ".join(a[:n]) + (" et al." if len(a) > n else "")


def email_body(papers: list[dict], jitems: list[dict], period: str, report: Path) -> str:
    lines = [f"Research digest: {len(papers)} arXiv + {len(jitems)} journal article(s) "
             f"— {period.replace('_to_', ' to ')}", f"Summary PDF: {report}", ""]
    n = 0
    for p in papers:
        n += 1
        lines += ["=" * 70, f"{n}. {p['title']}", f"   {_authors(p['authors'], 6)}",
                  f"   {p['abs_url']}", f"   Matched: {', '.join(p['keywords'])}", ""]
    for j in jitems:
        n += 1
        lines += ["=" * 70, f"{n}. [{j['journal']}] {j['title']}",
                  f"   {_authors(j['authors'], 6)}", f"   {j['url']}",
                  f"   Matched: {', '.join(j['keywords'])}", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------- journals
def _jdump(it: dict) -> dict:
    d = dict(it)
    d["date"] = it["date"].isoformat() if it.get("date") else None
    return d


def _jload(d: dict) -> dict:
    it = dict(d)
    it["date"] = dt.datetime.fromisoformat(d["date"]) if d.get("date") else None
    return it


def collect_journals(keywords: list[str], state: dict, now: dt.datetime,
                     force_from: dt.datetime | None = None) -> None:
    """Check every feed and add new keyword matches to state['pending_journal'].
    Runs on every (daily) run so items don't roll off a feed before report day."""
    seen = state.setdefault("journal_seen", {})
    pending = state.setdefault("pending_journal", {})
    inited = state.setdefault("journal_feeds", [])
    first_cutoff = now - dt.timedelta(days=S.first_run_lookback_days)
    for name, url in feeds.read_journals(S.journals_file):
        try:
            items = feeds.parse_feed(http_get(url, timeout=60), name)
        except Exception as e:  # noqa: BLE001
            log(f"  journal feed failed: {name}: {e}")
            continue
        first = url not in inited
        hits = 0
        for it in items:
            if it["id"] in pending:
                continue
            if it["id"] in seen and not (force_from and it["date"] and it["date"] >= force_from):
                continue
            kws = [k for k in keywords if feeds.matches(k, it["title"], it["abstract"], it["authors"])]
            if not kws or not on_topic(it["title"], it["abstract"]):
                continue
            too_old = it["date"] is not None and it["date"] < (force_from or now - dt.timedelta(days=14))
            if too_old or (not force_from and first and it["date"] is None):
                seen[it["id"]] = {"date": "baseline", "title": it["title"]}
                continue
            if not force_from and first and it["date"] < first_cutoff:
                seen[it["id"]] = {"date": "baseline", "title": it["title"]}
                continue
            it["keywords"] = kws
            pending[it["id"]] = _jdump(it)
            seen[it["id"]] = {"date": "pending", "title": it["title"]}
            hits += 1
        if first:
            inited.append(url)
        log(f"  journal {name}: {len(items)} checked, {hits} new")
        time.sleep(1)


def search_arxiv(keywords: list[str], state: dict, since: dt.datetime,
                 ignore_seen: bool) -> tuple[list[dict], int]:
    new: dict[str, dict] = {}
    ok = 0
    for i, kw in enumerate(keywords):
        if i:
            time.sleep(S.api_pause)
        try:
            results = search_arxiv_raw(kw)
        except Exception as e:  # noqa: BLE001
            log(f"  search failed for '{kw}': {e}")
            continue
        ok += 1
        hits = 0
        for p in results:
            pub = dt.datetime.fromisoformat(p["published"].replace("Z", "+00:00"))
            if pub < since or (p["id"] in state["seen"] and not ignore_seen):
                continue
            if not on_topic(p["title"], p["abstract"]):
                continue
            if p["id"] in new:
                new[p["id"]]["keywords"].append(kw)
            else:
                p["keywords"] = [kw]
                new[p["id"]] = p
                hits += 1
        log(f"  arXiv '{kw}': {len(results)} checked, {hits} new")
    return sorted(new.values(), key=lambda p: p["published"], reverse=True), ok


# ---------------------------------------------------------------- report
def write_report(period: str, papers: list[dict], jitems: list[dict]) -> Path:
    S.output_dir.mkdir(parents=True, exist_ok=True)
    report = S.output_dir / f"Report_{period}.pdf"
    k = 2
    while report.exists():
        report = S.output_dir / f"Report_{period}_{k}.pdf"
        k += 1
    jlist = jitems
    pdfreport.build_report(report, period, papers, jlist)
    keep = ("id", "title", "authors", "abstract", "abs_url", "pdf_url", "category",
            "published", "keywords", "url", "journal", "date_str")
    S.reports_store.mkdir(parents=True, exist_ok=True)
    (S.reports_store / f"{report.stem[len('Report_'):]}.json").write_text(json.dumps({
        "papers": [{k: p.get(k) for k in keep if k in p} for p in papers],
        "journals": [{k: j.get(k) for k in keep if k in j} for j in jlist]}, indent=1),
        encoding="utf-8")
    return report


# ---------------------------------------------------------------- main
def main(argv: list[str]) -> None:
    global S
    ensure_user_files()
    S = Settings(CONFIG_FILE)
    load_filters(S.filters_file)
    keywords = read_lines(S.keywords_file)

    if "--show-queries" in argv:
        for k in keywords:
            print(f"{k}\n    {build_query(k)}")
        return
    if "--test-email" in argv:
        send_email("Research digest: test email", "If you can read this, email works.")
        return
    if not keywords:
        sys.exit(f"No keywords found in {S.keywords_file}")

    force = "--now" in argv
    force_from = None
    if "--from" in argv:
        force = True
        d = dt.date.fromisoformat(argv[argv.index("--from") + 1])
        force_from = dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc)

    state = load_state()
    now = dt.datetime.now(dt.timezone.utc)
    today = dt.date.today()
    report_day = today - dt.timedelta(days=(today.weekday() - S.report_weekday) % 7)
    last_report = dt.date.fromisoformat(state["last_report"]) if state.get("last_report") else None
    log(f"Run start ({'forced' if force else 'scheduled'}), {len(keywords)} keywords, "
        f"last report: {last_report or 'never'}")

    collect_journals(keywords, state, now, force_from)
    save_state(state)

    if not force and last_report is not None and last_report >= report_day:
        log(f"Not report day yet; next report {report_day + dt.timedelta(days=7)} "
            f"({len(state.get('pending_journal', {}))} journal article(s) waiting)")
        return

    start = force_from.date() if force_from else (last_report or today - dt.timedelta(days=7))
    since = dt.datetime(start.year, start.month, start.day, tzinfo=dt.timezone.utc)
    if not force_from:
        since -= dt.timedelta(days=1)
    since = max(since, now - dt.timedelta(days=S.max_age_days))
    log(f"Making report {start} to {today}")

    papers, ok = search_arxiv(keywords, state, since, ignore_seen=bool(force_from))
    if ok == 0:
        log("All arXiv searches failed (offline?). Will try again next run.")
        return
    jitems = sorted((_jload(d) for d in state.get("pending_journal", {}).values()),
                    key=lambda j: (j["journal"], j["title"]))
    for j in jitems:
        j["url"] = f"https://doi.org/{j['doi']}" if j.get("doi") else j["link"]
        j["date_str"] = j["date"].strftime("%Y-%m-%d") if j.get("date") else ""
    period = f"{start}_to_{today}"
    report = write_report(period, papers, jitems)
    for p in papers:
        state["seen"][p["id"]] = {"date": period, "title": p["title"]}
    for j in jitems:
        state["journal_seen"][j["id"]] = {"date": period, "title": j["title"]}
    state.update(pending_journal={}, last_report=today.isoformat(), last_run=now.isoformat())
    save_state(state)
    log(f"Report done: {len(papers)} arXiv + {len(jitems)} journal -> {report}")
    send_email(f"Research digest: {len(papers)} arXiv + {len(jitems)} journal "
               f"({start} – {today})", email_body(papers, jitems, period, report), report)


if __name__ == "__main__":
    main(sys.argv[1:])
