"""Tiny dependency-free PDF writer for the weekly research report.

Builds an A4 PDF with titles, authors, abstracts and clickable links,
using only the Python standard library (built-in Helvetica fonts).
"""
from __future__ import annotations

import unicodedata

_W_REG = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556, 333, 556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334, 260, 334, 584, 761, 556, 761, 222, 556, 333, 1000, 556, 556, 333, 1000, 667, 333, 1000, 761, 611, 761, 761, 222, 222, 333, 333, 350, 556, 1000, 333, 1000, 500, 333, 944, 761, 500, 667, 278, 333, 556, 556, 556, 556, 260, 556, 333, 737, 370, 556, 584, 333, 737, 333, 400, 584, 333, 333, 333, 556, 537, 278, 333, 333, 365, 556, 834, 834, 834, 611, 667, 667, 667, 667, 667, 667, 1000, 722, 667, 667, 667, 667, 278, 278, 278, 278, 722, 722, 778, 778, 778, 778, 778, 584, 778, 722, 722, 722, 722, 667, 667, 611, 556, 556, 556, 556, 556, 556, 889, 500, 556, 556, 556, 556, 278, 278, 278, 278, 556, 556, 556, 556, 556, 556, 556, 584, 611, 556, 556, 556, 556, 500, 556, 500]
_W_BOLD = [278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556, 556, 556, 556, 333, 333, 584, 584, 584, 611, 975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833, 722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556, 333, 556, 611, 556, 611, 556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611, 611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389, 280, 389, 584, 761, 556, 761, 278, 556, 500, 1000, 556, 556, 333, 1000, 667, 333, 1000, 761, 611, 761, 761, 278, 278, 500, 500, 350, 556, 1000, 333, 1000, 556, 333, 944, 761, 500, 667, 278, 333, 556, 556, 556, 556, 280, 556, 333, 737, 370, 556, 584, 333, 737, 333, 400, 584, 333, 333, 333, 611, 556, 278, 333, 333, 365, 556, 834, 834, 834, 611, 722, 722, 722, 722, 722, 722, 1000, 722, 667, 667, 667, 667, 278, 278, 278, 278, 722, 722, 778, 778, 778, 778, 778, 584, 778, 722, 722, 722, 722, 667, 667, 611, 556, 556, 556, 556, 556, 556, 889, 556, 556, 556, 556, 556, 278, 278, 278, 278, 611, 611, 611, 611, 611, 611, 611, 584, 611, 611, 611, 611, 611, 556, 611, 556]

_SUBST = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "Δ": "Delta", "ε": "epsilon",
    "ζ": "zeta", "η": "eta", "θ": "theta", "Θ": "Theta", "κ": "kappa", "λ": "lambda",
    "Λ": "Lambda", "μ": "mu", "µ": "mu", "ν": "nu", "ξ": "xi", "π": "pi", "Π": "Pi", "ρ": "rho",
    "σ": "sigma", "Σ": "Sigma", "τ": "tau", "φ": "phi", "ϕ": "phi", "Φ": "Phi", "χ": "chi",
    "ψ": "psi", "Ψ": "Psi", "ω": "omega", "Ω": "Omega", "ℏ": "hbar", "Ł": "L", "ł": "l", "Đ": "D", "đ": "d", "ı": "i", "ș": "s", "ț": "t", "Ș": "S", "Ț": "T",
    "≈": "~", "≃": "~", "∼": "~", "≤": "<=", "≥": ">=", "≠": "!=", "→": "->", "←": "<-",
    "↔": "<->", "∞": "inf", "√": "sqrt", "∝": "prop. to", "⟨": "<", "⟩": ">", "⊗": "x",
    "−": "-", "‐": "-", "‑": "-", "‒": "-", "ﬁ": "fi", "ﬂ": "fl", "\u2009": " ", "\u00a0": " ",
}

PAGE_W, PAGE_H = 595.0, 842.0
MARGIN = 50.0


def clean(text: str) -> bytes:
    out = []
    for ch in text or "":
        ch = _SUBST.get(ch, ch)
        try:
            out.append(ch.encode("cp1252"))
        except UnicodeEncodeError:
            base = unicodedata.normalize("NFKD", ch)
            base = "".join(c for c in base if not unicodedata.combining(c))
            try:
                out.append(base.encode("cp1252") if base else b"?")
            except UnicodeEncodeError:
                out.append(b"?")
    return b"".join(out)


def _width(b: bytes, size: float, bold: bool) -> float:
    table = _W_BOLD if bold else _W_REG
    return sum(table[c - 32] if 32 <= c < 256 else 556 for c in b) * size / 1000.0


def _esc(b: bytes) -> bytes:
    return b.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


class Report:
    def __init__(self) -> None:
        self.pages: list[dict] = []
        self.liked: set = set()
        self._new_page()

    # -------------------------------------------------- layout primitives
    def _new_page(self) -> None:
        self.pages.append({"ops": [], "annots": []})
        self.y = PAGE_H - MARGIN

    def _ensure(self, h: float) -> None:
        if self.y - h < MARGIN + 20:
            self._new_page()

    def _wrap(self, b: bytes, size: float, bold: bool, width: float) -> list[bytes]:
        lines, cur = [], b""
        for word in b.split():
            trial = word if not cur else cur + b" " + word
            if _width(trial, size, bold) <= width:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                while _width(word, size, bold) > width:        # very long token (URL)
                    cut = len(word)
                    while cut > 1 and _width(word[:cut], size, bold) > width:
                        cut -= 1
                    lines.append(word[:cut])
                    word = word[cut:]
                cur = word
        if cur:
            lines.append(cur)
        return lines or [b""]

    def text(self, text: str, size: float = 10, bold: bool = False,
             color: tuple = (0, 0, 0), link: str | None = None,
             indent: float = 0, gap_after: float = 2) -> None:
        width = PAGE_W - 2 * MARGIN - indent
        lead = size * 1.3
        for line in self._wrap(clean(text), size, bold, width):
            self._ensure(lead)
            self.y -= lead
            x = MARGIN + indent
            font = b"/F2" if bold else b"/F1"
            r, g, bl = color
            op = (b"BT %s %.1f Tf %.3f %.3f %.3f rg %.2f %.2f Td (%s) Tj ET" %
                  (font, size, r, g, bl, x, self.y, _esc(line)))
            page = self.pages[-1]
            page["ops"].append(op)
            if link:
                page["annots"].append(("link", (x, self.y - 2, x + _width(line, size, bold),
                                                self.y + size), link))
        self.y -= gap_after

    def height(self, calls: list[dict]) -> float:
        h = 0.0
        for c in calls:
            if c.get("rule"):
                h += 2 * c.get("gap", 6)
                continue
            size = c.get("size", 10)
            width = PAGE_W - 2 * MARGIN - c.get("indent", 0)
            n = len(self._wrap(clean(c["text"]), size, c.get("bold", False), width))
            h += n * size * 1.3 + c.get("gap_after", 2)
        return h

    def entry(self, calls: list[dict], like_name: str) -> None:
        """Lay out one article. Its title gets a 'like' tick box: ticking it turns the
        title background light green (the title text is redrawn inside the box so it
        stays fully readable)."""
        h = self.height(calls)
        if h <= PAGE_H - 2 * MARGIN - 20:
            self._ensure(h)
        for c in calls:
            if c.get("rule"):
                self.rule(c.get("gap", 6))
            elif c.get("like"):
                self.title_like(c, like_name)
            else:
                self.text(**c)

    def title_like(self, c: dict, like_name: str) -> None:
        size, color, link = c.get("size", 11.5), c.get("color", (0, 0, 0)), c.get("link")
        width = PAGE_W - 2 * MARGIN
        lines = self._wrap(clean(c["text"]), size, True, width)
        lead = size * 1.3
        self._ensure(lead * len(lines))
        page = self.pages[-1]
        top = self.y
        placed = []
        for line in lines:
            self.y -= lead
            placed.append((MARGIN, self.y, line))
            r, g, b = color                       # plain copy in the page (for text search / copy)
            page["ops"].append(b"BT /F2 %.1f Tf %.3f %.3f %.3f rg %.2f %.2f Td (%s) Tj ET" %
                               (size, r, g, b, MARGIN, self.y, _esc(line)))
        bottom = self.y - 4
        rect = (MARGIN - 24, bottom, PAGE_W - MARGIN + 4, top + 1)
        page["annots"].append(("like", rect, like_name, placed, size, color))
        if link:                                  # links on top of the widget: title still opens the article
            for (x, y, line) in placed:
                page["annots"].append(("link", (x, y - 2, x + _width(line, size, True), y + size), link))
        self.y -= c.get("gap_after", 2)

    def rule(self, gap: float = 6) -> None:
        self._ensure(gap * 2)
        self.y -= gap
        self.pages[-1]["ops"].append(
            b"0.8 0.8 0.8 RG 0.5 w %.2f %.2f m %.2f %.2f l S" %
            (MARGIN, self.y, PAGE_W - MARGIN, self.y))
        self.y -= gap

    def space(self, h: float) -> None:
        self.y -= h

    # -------------------------------------------------- output
    def save(self, path) -> None:
        objs: list[bytes] = []

        def add(b: bytes) -> int:
            objs.append(b)
            return len(objs)

        def reserve() -> int:
            objs.append(b"")
            return len(objs)

        f1 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        f2 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
        pages_id = reserve()
        fields: list[int] = []
        kids = []
        n = len(self.pages)
        for i, p in enumerate(self.pages, 1):
            foot = (b"BT /F1 8 Tf 0.5 0.5 0.5 rg %.2f %.2f Td (Page %d of %d) Tj ET" %
                    (PAGE_W / 2 - 25, MARGIN / 2, i, n))
            stream = b"\n".join(p["ops"] + [foot])
            content = add(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream))
            page_id = reserve()
            annots = []
            for a in p["annots"]:
                kind, (x0, y0, x1, y1), val = a[0], a[1], a[2]
                if kind == "link":
                    annots.append(add(
                        b"<< /Type /Annot /Subtype /Link /Rect [%.2f %.2f %.2f %.2f] /Border [0 0 0] "
                        b"/A << /S /URI /URI (%s) >> >>" % (x0, y0, x1, y1, _esc(clean(val)))))
                    continue
                placed, size, (cr, cg, cb) = a[3], a[4], a[5]
                st = b"On" if val in self.liked else b"Off"
                w, h = x1 - x0, y1 - y0
                bx, by = 6.0, h - 15.0                       # tick box next to the first title line
                txt = b" ".join(
                    b"BT /F2 %.1f Tf %.3f %.3f %.3f rg %.2f %.2f Td (%s) Tj ET" %
                    (size, cr, cg, cb, x - x0, y - y0, _esc(line)) for (x, y, line) in placed)
                off = (b"1 1 1 rg 0 0 %.2f %.2f re f "
                       b"0.55 0.55 0.55 RG 0.8 w %.2f %.2f 11 11 re S %s" % (w, h, bx, by, txt))
                on = (b"1 1 1 rg 0 0 %.2f %.2f re f "
                      b"0.80 0.95 0.80 rg %.2f 0 %.2f %.2f re f "
                      b"0.20 0.55 0.25 RG 1 w %.2f %.2f 11 11 re S "
                      b"0.15 0.55 0.20 RG 2 w 1 J 1 j %.2f %.2f m %.2f %.2f l %.2f %.2f l S %s" %
                      (w, h, 24 - 3, w - 21, h, bx, by, bx + 2.3, by + 5.5, bx + 4.7, by + 2.8,
                       bx + 9.5, by + 9.5, txt))
                res = b"/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >>" % (f1, f2)
                ap_on = add(b"<< /Type /XObject /Subtype /Form /BBox [0 0 %.2f %.2f] %s /Length %d >>"
                            b"\nstream\n%s\nendstream" % (w, h, res, len(on), on))
                ap_off = add(b"<< /Type /XObject /Subtype /Form /BBox [0 0 %.2f %.2f] %s /Length %d >>"
                             b"\nstream\n%s\nendstream" % (w, h, res, len(off), off))
                wid = add(b"<< /Type /Annot /Subtype /Widget /FT /Btn /T (%s) /TU (Like this article) "
                          b"/F 4 /Rect [%.2f %.2f %.2f %.2f] /P %d 0 R /V /%s /AS /%s "
                          b"/MK << /BG [1 1 1] >> /AP << /N << /On %d 0 R /Off %d 0 R >> >> >>" %
                          (_esc(clean(val)), x0, y0, x1, y1, page_id, st, st, ap_on, ap_off))
                annots.append(wid)
                fields.append(wid)
            ann = b" /Annots [%s]" % b" ".join(b"%d 0 R" % a for a in annots) if annots else b""
            objs[page_id - 1] = (
                b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %d %d] /Contents %d 0 R "
                b"/Resources << /Font << /F1 %d 0 R /F2 %d 0 R >> >>%s >>" %
                (pages_id, PAGE_W, PAGE_H, content, f1, f2, ann))
            kids.append(page_id)
        objs[pages_id - 1] = (b"<< /Type /Pages /Kids [%s] /Count %d >>" %
                              (b" ".join(b"%d 0 R" % k for k in kids), len(kids)))
        form = b""
        if fields:
            form = b" /AcroForm << /Fields [%s] >>" % b" ".join(b"%d 0 R" % f for f in fields)
        cat = add(b"<< /Type /Catalog /Pages %d 0 R%s >>" % (pages_id, form))

        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for i, o in enumerate(objs, 1):
            offsets.append(len(out))
            out += b"%d 0 obj\n%s\nendobj\n" % (i, o)
        xref = len(out)
        out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
        for off in offsets:
            out += b"%010d 00000 n \n" % off
        out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
            len(objs) + 1, cat, xref)
        with open(path, "wb") as fh:
            fh.write(out)


# ------------------------------------------------------------------ report
BLUE = (0.05, 0.27, 0.65)
GREY = (0.35, 0.35, 0.35)


def _authors(a: list[str], n: int = 8) -> str:
    return ", ".join(a[:n]) + (" et al." if len(a) > n else "")


def build_report(path, period: str, papers: list[dict], jitems: list[dict],
                 liked: set | None = None) -> None:
    """papers: arXiv dicts (title, authors, abstract, abs_url, id, category, published, keywords)
       jitems: journal dicts (title, authors, abstract, url, journal, date_str, keywords)"""
    r = Report()
    r.liked = set(liked or ())
    r.text("Weekly research report", 18, True, (0.12, 0.31, 0.47), gap_after=4)
    r.text(period.replace("_to_", " to ") + f"   ·   {len(papers)} arXiv + {len(jitems)} journal article(s)",
           10, False, GREY, gap_after=4)
    r.text("Click a title or link to open the article. Tick the small box left of a title to mark "
           "articles you like - the title turns light green (in Preview, press Cmd+S to keep your ticks).", 8.5, False, GREY)
    n = 0
    if papers:
        r.space(8)
        r.text("arXiv preprints", 14, True, (0.12, 0.31, 0.47))
    for p in papers:
        n += 1
        pdf = p.get("pdf_url") or p["abs_url"].replace("/abs/", "/pdf/")
        calls = [{"rule": True},
                 dict(text=f"{n}. {p['title']}", size=11.5, bold=True, color=BLUE, link=p["abs_url"], gap_after=2, like=True)]
        if p.get("authors"):
            calls.append(dict(text=_authors(p["authors"]), size=9, color=GREY))
        calls.append(dict(text=f"arXiv:{p['id']}  ·  {p.get('category','')}  ·  submitted {p.get('published','')[:10]}",
                          size=8.5, color=GREY))
        if p.get("keywords"):
            calls.append(dict(text="Matched: " + ", ".join(p["keywords"]), size=8.5, color=GREY, gap_after=4))
        if p.get("abstract"):
            calls.append(dict(text=p["abstract"], size=9.5, gap_after=3))
        calls.append(dict(text=p["abs_url"], size=9, color=BLUE, link=p["abs_url"]))
        calls.append(dict(text="PDF: " + pdf, size=9, color=BLUE, link=pdf))
        r.entry(calls, f"like_{n}")
    if jitems:
        r.space(10)
        r.text("Journal articles", 14, True, (0.12, 0.31, 0.47))
    for j in jitems:
        n += 1
        calls = [{"rule": True},
                 dict(text=f"{n}. {j['title']}", size=11.5, bold=True, color=BLUE, link=j["url"], gap_after=2, like=True)]
        if j.get("authors"):
            calls.append(dict(text=_authors(j["authors"]), size=9, color=GREY))
        calls.append(dict(text=f"{j['journal']}" + (f"  ·  {j['date_str']}" if j.get("date_str") else ""),
                          size=8.5, color=GREY))
        if j.get("keywords"):
            calls.append(dict(text="Matched: " + ", ".join(j["keywords"]), size=8.5, color=GREY, gap_after=4))
        if j.get("abstract"):
            calls.append(dict(text=j["abstract"], size=9.5, gap_after=3))
        calls.append(dict(text=j["url"], size=9, color=BLUE, link=j["url"]))
        r.entry(calls, f"like_{n}")
    if not papers and not jitems:
        r.space(10)
        r.text("No new articles matched your keywords in this period.", 11)
    r.save(path)
