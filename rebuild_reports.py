"""Rebuild every Report_*.pdf in the output folder with the current layout.

Useful after updating pdfreport.py. Uses _state/reports/<period>.json when present,
otherwise reads the text back out of the existing report PDF. Ticks already set
("liked" articles) are kept.

    python3 rebuild_reports.py            # uses output_dir from config.ini
    python3 rebuild_reports.py /path/to/output_dir"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pdfreport

OP = re.compile(rb"BT (/F\d) ([\d.]+) Tf ([\d.]+) ([\d.]+) ([\d.]+) rg [\d.]+ [\d.]+ Td \(((?:\\.|[^\\)])*)\) Tj ET")


def _s(b: bytes) -> str:
    b = re.sub(rb"\\(.)", rb"\1", b)
    return b.decode("cp1252", errors="replace")


def read_pdf(path: Path):
    raw = path.read_bytes()
    lines = []
    for m in re.finditer(rb"stream\n(.*?)\nendstream", raw, re.S):
        for o in OP.finditer(m.group(1)):
            font, size, r, g, b, txt = o.groups()
            lines.append((font.decode(), float(size), (float(r), float(g), float(b)), _s(txt)))
    import zlib
    chunks = []                                   # plain objects + decompressed object streams, in file order
    for o in re.finditer(rb"(\d+\s+\d+\s+obj)(.*?)endobj", raw, re.S):
        body = o.group(2)
        chunks.append(body)
        m = re.search(rb"stream\r?\n(.*?)\r?\nendstream", body, re.S)
        if m and b"FlateDecode" in body:
            try:
                chunks.append(zlib.decompress(m.group(1)))
            except zlib.error:
                pass
    def pdfstr(tok: bytes) -> bytes:
        if tok.startswith(b"<"):
            try:
                return bytes.fromhex(tok[1:-1].decode())
            except ValueError:
                return b""
        t = tok[1:-1]
        t = re.sub(rb"\\([0-7]{1,3})", lambda m: bytes([int(m.group(1), 8)]), t)
        return re.sub(rb"\\(.)", rb"\1", t)

    state = {}
    for body in chunks:                           # later versions win
        for t in re.finditer(rb"/T\s*(\((?:\\.|[^\\)])*\)|<[0-9A-Fa-f\s]*>)", body):
            name = pdfstr(t.group(1))
            if not re.fullmatch(rb"like_\d+", name):
                continue
            # the /V entry of the same dictionary (search a little before and after /T)
            start = body.rfind(b"/Widget", 0, t.start())
            seg = body[max(start, t.start() - 600): t.end() + 600]
            v = re.search(rb"/V\s*/(\w+)", seg)
            state[name] = bool(v and v.group(1) != b"Off")
    liked = {k for k, on in state.items() if on}
    papers, jitems, section, cur, prev, mode = [], [], None, None, None, None

    def close():
        if cur:
            cur["title"] = re.sub(r"^\d+\.\s+", "", cur["title"]).strip()
            cur["authors"] = [a.strip() for a in cur.pop("_auth", "").split(",") if a.strip()]
            cur["keywords"] = [k.strip() for k in cur.pop("_kw", "").split(",") if k.strip()]
            (papers if section == "arxiv" else jitems).append(cur)

    for font, size, col, t in lines:
        kind = None
        if font == "/F2" and size == 14:
            close(); cur = None
            section = "journal" if t.startswith("Journal") else "arxiv"
            prev = "section"; continue
        if section is None or (font == "/F1" and size == 8 and col[0] == 0.5):
            continue                                     # header / footer
        if font == "/F2" and size == 11.5:
            if prev != "title":
                close(); cur = {"title": t, "_auth": "", "_kw": "", "abstract": "", "url": "", "pdf": "", "meta": ""}
                mode = None
            else:
                cur["title"] += " " + t
            prev = "title"; continue
        if cur is None:
            continue
        if size == 9 and col[2] < 0.5:                   # grey authors
            cur["_auth"] += (" " if cur["_auth"] else "") + t; prev = "auth"
        elif size == 8.5:
            if t.startswith("Matched: "):
                cur["_kw"] = t[len("Matched: "):]; mode = "kw"
            elif mode == "kw":
                cur["_kw"] += " " + t
            else:
                cur["meta"] += t
            prev = "meta"
        elif size == 9.5:
            cur["abstract"] += (" " if cur["abstract"] else "") + t; prev = "abs"
        elif size == 9:                                   # blue link lines
            if t.startswith("PDF: "):
                cur["pdf"] = t[5:]; prev = "pdf"
            elif t.startswith("http") or not cur["url"]:
                cur["url"] = t; prev = "url"
            elif prev == "pdf":
                cur["pdf"] += t
            else:
                cur["url"] += t
    close()
    for p in papers:
        m = re.match(r"arXiv:(\S+)\s+·\s+(.*?)\s+·\s+submitted (\S+)", p["meta"])
        if m:
            p.update(id=m.group(1), category=m.group(2), published=m.group(3))
        p["abs_url"] = p.pop("url"); p["pdf_url"] = p.pop("pdf") or None
    for j in jitems:
        parts = [x.strip() for x in j["meta"].split("·")]
        j["journal"] = parts[0]; j["date_str"] = parts[1] if len(parts) > 1 else ""
    return papers, jitems, {x.decode() for x in liked}


def main(arts: Path):
    store = arts / "_state" / "reports"
    store.mkdir(parents=True, exist_ok=True)
    for pdf in sorted(arts.glob("Report_*.pdf")):
        period = pdf.stem[len("Report_"):]
        js = store / f"{period}.json"
        liked = read_pdf(pdf)[2]
        if js.exists():
            data = json.loads(js.read_text(encoding="utf-8"))
            papers, jitems = data["papers"], data["journals"]
        else:
            papers, jitems, _ = read_pdf(pdf)
            js.write_text(json.dumps({"papers": papers, "journals": jitems}, indent=1), encoding="utf-8")
        pdfreport.build_report(pdf, re.sub(r"_\d+$", "", period), papers, jitems, liked=liked)
        print(f"{pdf.name}: {len(papers)} arXiv + {len(jitems)} journal, {len(liked)} liked kept")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(Path(sys.argv[1]).expanduser())
    else:
        import digest
        digest.ensure_user_files()
        main(digest.Settings(digest.CONFIG_FILE).output_dir)
