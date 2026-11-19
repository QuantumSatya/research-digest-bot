"""Journal RSS/Atom feed reader and the local keyword matcher used for feeds."""
from __future__ import annotations

import datetime as dt
import email.utils
import html
import re
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path


# ---------------------------------------------------------------- matching
def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    for ch in "-_\u2010\u2011\u2012\u2013\u2014\u2212":
        s = s.replace(ch, " ")
    return re.sub(r"\s+", " ", s).strip()


def _term(term: str, text: str, authors: str, title: str = "") -> bool:
    term = term.strip()
    m = re.match(r"^(ti|au|abs|co|jr|cat|all):(.*)$", term)
    hay = text
    if m:
        field, term = m.group(1), m.group(2)
        if field == "au":
            hay = authors
        elif field == "ti" and title:
            hay = title
    t = norm(term.strip('"'))
    return bool(t) and re.search(r"\b" + re.escape(t) + r"(?:s|es)?\b", hay) is not None


def matches(keyword: str, title: str, abstract: str, authors: list[str]) -> bool:
    """Same syntax as keywords.txt: phrases, AND / OR / ANDNOT, au:Name."""
    text = norm(f"{title} {abstract} {' '.join(authors)}")
    auth = norm(" | ".join(authors))
    tnorm = norm(title)
    tokens = re.split(r"\s+(AND|OR|ANDNOT)\s+", keyword.strip())
    result = _term(tokens[0], text, auth, tnorm)
    for op, term in zip(tokens[1::2], tokens[2::2]):
        hit = _term(term, text, auth, tnorm)
        if op == "AND":
            result = result and hit
        elif op == "OR":
            result = result or hit
        else:
            result = result and not hit
    return result


# ---------------------------------------------------------------- feeds
def read_journals(path: Path) -> list[tuple[str, str]]:
    out = []
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "|" in line:
            name, url = line.split("|", 1)
            out.append((name.strip(), url.strip()))
    return out


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _clean(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")
    return " ".join(html.unescape(s).split())


def _date(s: str) -> dt.datetime | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        try:
            d = email.utils.parsedate_to_datetime(s)
        except (TypeError, ValueError):
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d


def parse_feed(data: bytes, journal: str) -> list[dict]:
    root = ET.fromstring(data)
    items = []
    for el in root.iter():
        if _local(el.tag) not in ("item", "entry"):
            continue
        f: dict[str, list] = {}
        for ch in el:
            name = _local(ch.tag)
            if name == "author":            # Atom <author><name>
                nm = next((c.text for c in ch if _local(c.tag) == "name"), ch.text)
                f.setdefault("creator", []).append(nm or "")
                continue
            if name == "link" and ch.get("href"):
                if ch.get("rel", "alternate") == "alternate":
                    f.setdefault("link", []).append(ch.get("href"))
                continue
            f.setdefault(name, []).append(ch.text or "")
        g = lambda *ks: next((f[k][0] for k in ks if f.get(k) and f[k][0]), "")
        title = _clean(g("title"))
        link = g("link", "guid").strip() or el.get(
            "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about", "")
        abstract = _clean(g("encoded", "description", "summary", "abstract", "content"))
        doi = g("doi").strip()
        if not doi:
            m = re.search(r"10\.\d{4,9}/[^\s\"<>]+", g("identifier") + " " + link)
            doi = m.group(0).rstrip(".") if m else ""
        authors = [_clean(a) for a in f.get("creator", []) if a.strip()]
        if len(authors) == 1 and ("," in authors[0] or " and " in authors[0]):
            authors = [a.strip() for a in re.split(r",| and ", authors[0]) if a.strip()]
        date = _date(g("date", "pubdate", "published", "updated", "issued"))
        if not title:
            continue
        items.append({"id": doi.lower() or link, "title": title, "link": link,
                      "doi": doi, "abstract": abstract, "authors": authors,
                      "journal": journal, "date": date})
    return items
