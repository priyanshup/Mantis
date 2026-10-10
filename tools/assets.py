"""Knowledge assets: reusable diagrams and visuals from the sources (MANTIS-IMP-008).

    python tools/assets.py scan               extract images from every source snapshot (only new or changed files are read)
    python tools/assets.py sheet [N] [--card SLUG | --doc ID]  contact sheets of the next N candidates, 4 per image, for triage
    python tools/assets.py review [N] [--doc ID]  the next N candidates waiting for a decision, largest first (one document's only)
    python tools/assets.py new <hash> [...]   print register entries pre-filled from the scan, for `entry.py add ast`
    python tools/assets.py ignore <hash>[,<hash>...] "why"  never offer these images (and their near-copies) again
    python tools/assets.py status             counts per tier

How it works. `scan` pulls every embedded image out of the PDFs, Confluence Word exports (.doc
MIME) and PowerPoint files in 01_sources/, hashes it, and groups exact and near copies (the same
diagram pasted into several documents) into one candidate. Code sorts each candidate into a tier:

    decorative   tiny images, icons, banners and logos repeated across many documents: ignored, never asked
    candidate    everything else: waits for a decision
    registered   has an entry in registers/assets/ (MANTIS-AST-*)
    ignored      someone decided it is not worth keeping (`ignore`)

Claude looks at candidates (`review`, then opens the image file) and registers the clear diagram
types itself (workflow, architecture, swimlane, sequence, decision tree, process flow, UI
screenshot, reference table). It asks the owner only about the ambiguous middle, on the Open
items page. A registered asset carries a one-paragraph description, so a page can reuse it
without anyone opening the image. Images live in mantis/knowledge/assets/files/<hash>.<ext>;
scan results in mantis/knowledge/assets/scan.json. Only raster images are found: a diagram drawn
as vector shapes inside a PDF is not an image and needs a screenshot by hand.
Needs: pypdf and Pillow.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import email, hashlib, io, json, re, time, zipfile
from email import policy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "mantis"
SOURCES = M / "01_sources"
A = M / "knowledge" / "assets"
FILES = A / "files"
SCAN = A / "scan.json"
DECISIONS = A / "decisions.json"
REG = M / "knowledge" / "registers" / "assets"
TYPES = ("workflow", "architecture", "swimlane", "sequence", "decision-tree", "process-flow",
         "ui-screenshot", "reference-table", "chart", "other")
NEAR = 5            # dHash bits that may differ for two images to count as copies of one diagram
MIN_SIDE, MIN_AREA, MIN_BYTES = 200, 60_000, 4_000   # below any of these: decorative
LOGO_DOCS = 6       # the same small image in this many documents is a logo or banner


def load(p, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


# ---------- extraction ----------

def dhash(img):
    g = img.convert("L").resize((9, 8))
    px = list(g.get_flattened_data() if hasattr(g, "get_flattened_data") else g.getdata())   # getdata goes in Pillow 14
    bits = sum(1 << i for i in range(64) if px[(i // 8) * 9 + i % 8] > px[(i // 8) * 9 + i % 8 + 1])
    return f"{bits:016x}"


def keep(data, where, out):
    """Hash and measure one image; store the file once. `where` is a page or slide number, or None."""
    from PIL import Image
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        return
    h = hashlib.sha256(data).hexdigest()[:16]
    fmt = (img.format or "png").lower()
    ext = {"jpeg": "jpg", "png": "png", "gif": "gif"}.get(fmt)
    w, hgt = img.size
    out.append({"hash": h, "page": where, "w": w, "h": hgt, "bytes": len(data), "ext": ext or "png", "dhash": dhash(img)})
    if out is _WANT.get("sink"):   # ensure_file() is looking for this exact image: write it
        if h in _WANT["hashes"]:
            store(data, img, FILES / f"{h}.{ext or 'png'}", ext)


_WANT = {}


def store(data, img, f, ext):
    FILES.mkdir(parents=True, exist_ok=True)
    if ext:
        f.write_bytes(data)
    else:   # JPEG 2000, TIFF and the like: browsers cannot show them
        img.convert("RGB").save(f, "PNG")


def ensure_file(g):
    """Make sure the image file for group g exists, extracting it again from its source if needed.
    Only registered assets are kept on disk; a candidate's file is written when a sheet, review or
    registration needs it, and pruned afterwards (MANTIS-IMP-067). Returns the path, or None."""
    f = A / g["file"]
    if f.exists():
        return f
    for w in g["where"]:
        src = next((s for s in SOURCES.glob(f"{w['doc']}/{w['version']}.*")), None)
        if not src:
            continue
        sink = []
        _WANT.update(sink=sink, hashes=set(g["copies"]))
        try:
            if src.suffix.lower() == ".pdf" and w.get("page"):
                import pypdf
                page = pypdf.PdfReader(str(src)).pages[w["page"] - 1]
                for im in page.images:
                    keep(im.data, w["page"], sink)
            else:
                globals()["extract_into"](src, sink)
        finally:
            _WANT.clear()
        for c in g["copies"]:   # the copy found may carry another hash of the same picture
            other = next(iter(A.joinpath("files").glob(f"{c}.*")), None)
            if other and other != f and not f.exists():
                other.rename(f)
        if f.exists():
            return f
    return None


def heal_registered():
    """Registered assets must always have their file (the site shows it): restore any that is missing."""
    fixed = 0
    for g in groups():
        if g["asset"] and not (A / g["file"]).exists() and ensure_file(g):
            fixed += 1
    return fixed


def prune_files():
    """Delete image files that belong to no registered asset; they come back on demand."""
    keepers = {h for h in registered()}
    gone = 0
    for f in FILES.glob("*.*"):
        if f.stem not in keepers:
            f.unlink(); gone += 1
    return gone


def from_pdf(p, out):
    import pypdf
    r = pypdf.PdfReader(str(p))
    for i, page in enumerate(r.pages):
        try:
            for im in page.images:
                keep(im.data, i + 1, out)
        except Exception:
            continue


def from_mime(p, out):
    msg = email.message_from_bytes(p.read_bytes(), policy=policy.default)
    for part in msg.walk():
        # Confluence's Word export labels its images application/octet-stream, so every binary part is tried;
        # keep() ignores anything that is not a readable image (fixed 2026-10-10: these images had been missed).
        if part.get_content_maintype() == "image" or part.get_content_type() == "application/octet-stream":
            keep(part.get_payload(decode=True) or b"", None, out)


def from_pptx(p, out):
    with zipfile.ZipFile(p) as z:
        slide_of = {}
        for n in z.namelist():
            m = re.match(r"ppt/slides/_rels/slide(\d+)\.xml\.rels$", n)
            if m:
                for t in re.findall(r'Target="\.\./media/([^"]+)"', z.read(n).decode("utf-8", "replace")):
                    slide_of.setdefault(t, int(m.group(1)))
        for n in z.namelist():
            if n.startswith("ppt/media/"):
                keep(z.read(n), slide_of.get(n.rsplit("/", 1)[1]), out)


def extract_into(p, out):
    ext = p.suffix.lower()
    if ext == ".pdf":
        from_pdf(p, out)
    elif ext in (".doc", ".mhtml", ".mht"):
        if p.read_bytes()[:400].lstrip().lower().startswith((b"date:", b"message-id:", b"mime-version:", b"from:", b"subject:")):
            from_mime(p, out)
    elif ext == ".pptx":
        from_pptx(p, out)
    return out


def extract(p):
    out = []
    ext = p.suffix.lower()
    if ext == ".pdf":
        from_pdf(p, out)
    elif ext in (".doc", ".mhtml", ".mht"):
        if p.read_bytes()[:400].lstrip().lower().startswith((b"date:", b"message-id:", b"mime-version:", b"from:", b"subject:")):
            from_mime(p, out)
    elif ext == ".pptx":
        from_pptx(p, out)
    return out


def scan(quiet=False):
    data = load(SCAN, {"sources": {}})
    seen, read = set(), 0
    for p in sorted(SOURCES.glob("MANTIS-DOC-*/*")):
        if not p.is_file() or p.suffix.lower() not in (".pdf", ".doc", ".mhtml", ".mht", ".pptx"):
            continue
        rel = p.relative_to(SOURCES).as_posix()
        seen.add(rel)
        st = p.stat()
        stamp = [st.st_size, int(st.st_mtime)]
        if data["sources"].get(rel, {}).get("stamp") == stamp:
            continue
        try:
            images = extract(p)
        except Exception as e:
            print(f"{rel}: could not read ({e})")
            images = []
        data["sources"][rel] = {"stamp": stamp, "images": images}
        read += 1
        if not quiet and read % 10 == 0:
            print(f"  {read} source files read...")
    gone = set(data["sources"]) - seen
    for rel in gone:
        del data["sources"][rel]
    if read or gone or not SCAN.exists():
        A.mkdir(parents=True, exist_ok=True)
        SCAN.write_text(json.dumps(data, indent=0), encoding="utf-8")
    return read


# ---------- grouping and tiers ----------

def ham(a, b):
    return (a ^ b).bit_count()


def registered():
    """{hash: asset ID} from the asset register (any hash listed in an entry's Hash line)."""
    out = {}
    for p in REG.glob("MANTIS-AST-*.md"):
        m = re.search(r"(?m)^- \*\*Hash:\*\*\s*(.+)$", p.read_text(encoding="utf-8"))
        for h in re.findall(r"[0-9a-f]{16}", m.group(1) if m else ""):
            out[h] = p.stem
    return out


def groups():
    """One record per distinct image, near copies merged, with every place it appears and its tier."""
    data = load(SCAN, {"sources": {}})
    by_hash = {}
    for rel, s in data["sources"].items():
        doc, version = rel.split("/")[0], rel.split("/")[1].rsplit(".", 1)[0]
        for im in s["images"]:
            g = by_hash.setdefault(im["hash"], {**im, "bits": int(im["dhash"], 16), "where": []})
            g["where"].append({"doc": doc, "version": version, "page": im["page"]})
    # Merge near copies: same picture at another resolution or re-encoded
    reps = []
    for h in sorted(by_hash, key=lambda h: -(by_hash[h]["w"] * by_hash[h]["h"])):
        im = by_hash[h]
        rep = next((r for r in reps if ham(r["bits"], im["bits"]) <= NEAR
                    and abs(r["w"] / max(r["h"], 1) - im["w"] / max(im["h"], 1)) < 0.15), None)
        if rep:
            rep["copies"].append(h)
            rep["where"] += im["where"]
        else:
            reps.append({**im, "copies": [h]})
    reg, dec = registered(), load(DECISIONS, {})
    for r in reps:
        docs = {w["doc"] for w in r["where"]}
        r["docs"] = sorted(docs)
        r["file"] = f"files/{r['hash']}.{r['ext']}"
        r["asset"] = next((reg[h] for h in r["copies"] if h in reg), "")
        r["decision"] = next((dec[h] for h in r["copies"] if h in dec), None)
        small = min(r["w"], r["h"]) < MIN_SIDE or r["w"] * r["h"] < MIN_AREA or r["bytes"] < MIN_BYTES
        banner = max(r["w"], r["h"]) / max(min(r["w"], r["h"]), 1) > 6
        logo = len(docs) >= LOGO_DOCS and r["w"] * r["h"] < 400_000
        r["tier"] = ("registered" if r["asset"] else "ignored" if r["decision"] else
                     "decorative" if small or banner or logo else "candidate")
        r["why"] = ("too small" if small else "banner shape" if banner else f"in {len(docs)} documents, logo-sized" if logo else "") if r["tier"] == "decorative" else ""
    return reps


def registry():
    """Every registered asset as a dict, for build_map, the cards and the site."""
    out = []
    for p in sorted(REG.glob("MANTIS-AST-*.md")):
        text = p.read_text(encoding="utf-8")

        def field(label):
            f = re.search(r"(?ms)^- \*\*%s:\*\*\s*(.*?)(?=^- \*\*|\Z)" % re.escape(label), text)
            return " ".join(f.group(1).split()) if f else ""
        fl = re.match(r"(\S+)", field("File"))
        out.append({"id": p.stem, "title": field("Title"), "type": field("Type").lower(), "description": field("Description"),
                    "caption": field("Caption"), "file": fl.group(1) if fl else "", "hash": re.findall(r"[0-9a-f]{16}", field("Hash")),
                    "docs": sorted(set(re.findall(r"MANTIS-DOC-\d{4}", field("Source documents")))),
                    "topics": [t.strip() for t in field("Topics").split(",") if t.strip() and not t.startswith("[")],
                    "related": re.findall(r"MANTIS-AST-\d+", field("Related assets")),
                    "status": field("Status").split(" ")[0] or "Registered"})
    return out


def referenced_by(assets, texts):
    """Fill each asset's `referenced_by` with the files (digests, outputs) that name its ID."""
    for a in assets:
        pat = re.compile(re.escape(a["id"]) + r"\b")
        a["referenced_by"] = sorted(name for name, t in texts.items() if pat.search(t))
    return assets


# ---------- commands ----------

def cmd_status():
    gs = groups()
    n = {}
    for g in gs:
        n[g["tier"]] = n.get(g["tier"], 0) + 1
    raw = sum(len(s["images"]) for s in load(SCAN, {"sources": {}})["sources"].values())
    print(f"{raw} embedded images, {len(gs)} distinct after merging copies: " + ", ".join(f"{k} {v}" for k, v in sorted(n.items())))


def cmd_review(n, doc=None):
    docs = titles()
    todo = sorted((g for g in groups() if g["tier"] == "candidate" and (not doc or doc in g["docs"])), key=lambda g: -(g["w"] * g["h"]))
    print(f"{len(todo)} candidate(s) waiting. Open the file to look at it, then `assets.py new <hash>` or `assets.py ignore <hash> \"why\"`.\n")
    for g in todo[:n]:
        where = "; ".join(f"{w['doc']} {docs.get(w['doc'], '')[:50]!r}" + (f" p{w['page']}" if w["page"] else "") for w in g["where"][:3])
        ensure_file(g)
        print(f"{g['hash']}  {g['w']}x{g['h']}  {(A / g['file']).relative_to(ROOT).as_posix()}\n    in: {where}" + (f" (+{len(g['where']) - 3} more)" if len(g["where"]) > 3 else ""))


def titles():
    out = {}
    for p in (M / "02_digests").glob("MANTIS-DOC-*.md"):
        m = re.search(r'(?m)^original_title:\s*"?(.*?)"?\s*$', p.read_text(encoding="utf-8")[:3000])
        out[p.stem] = m.group(1) if m else ""
    return out


def cmd_new(hashes):
    by = {h: g for g in groups() for h in g["copies"]}
    for h in hashes:
        g = by.get(h)
        if not g:
            sys.exit(f"No image with hash {h}. Run `assets.py scan` first.")
        if g["asset"]:
            sys.exit(f"{h} is already registered as {g['asset']}.")
        if not ensure_file(g):
            sys.exit(f"Could not extract {h} from its source again; is the source file still in 01_sources?")
        where = ", ".join(f"{w['doc']} (version {w['version']}" + (f", page {w['page']}" if w["page"] else "") + ")" for w in g["where"])
        print(f"""### MANTIS-AST-XXX

- **Title:** [what the diagram shows, in plain words]
- **Type:** [{" | ".join(TYPES)}]
- **Description:** [one paragraph: what it shows, the steps or parts and how they connect, so a reader can reuse it without opening the image. Cite the source.]
- **Caption:** [the source's own caption, e.g. "Figure 5", or none]
- **File:** {g['file']} ({g['w']}x{g['h']})
- **Hash:** {", ".join(g['copies'])}
- **Source documents:** {where}
- **Topics:** [digest topic tags it belongs to]
- **Key entities:** [systems, teams, roles it names]
- **Region:** [as the source document]
- **Related assets:** none
- **Status:** Registered
- **Date registered:** {time.strftime('%Y-%m-%d')}
""")


def cmd_ignore(hashes, why):
    """Ignore one or more images (comma-separated hashes) with one reason, in one write."""
    gs = groups()
    dec = load(DECISIONS, {})
    for h in [x.strip() for x in hashes.split(",") if x.strip()]:
        g = next((g for g in gs if h in g["copies"]), None)
        if not g:
            sys.exit(f"No image with hash {h}; nothing written.")
        for c in g["copies"]:
            dec[c] = {"decision": "ignored", "why": why, "date": time.strftime("%Y-%m-%d")}
        print(f"Ignored {h}" + (f" and {len(g['copies']) - 1} copies" if len(g["copies"]) > 1 else "") + ".")
    DECISIONS.write_text(json.dumps(dec, indent=1), encoding="utf-8")


SHEETS = A / "sheets"
TILE = 560   # measured 2026-10-10: the smallest tile at which diagram labels stay readable for triage


def cmd_sheet(n=12, doc=None, card=None):
    """Contact sheets for triage (MANTIS-IMP-057): four candidates per image, numbered with their hash.
    Deciding keep or ignore from a sheet costs about half of opening each image; open a keeper's full
    file only to write its description."""
    from PIL import Image, ImageDraw
    docs = None
    if card:
        mp = M / "knowledge" / "map"
        allc = json.loads((mp / "features.json").read_text(encoding="utf-8")) + json.loads((mp / "topics.json").read_text(encoding="utf-8"))
        c = next((x for x in allc if x["slug"] == card), None)
        if not c:
            sys.exit(f"No card called {card}.")
        docs = set(c["docs"])
    todo = [g for g in groups() if g["tier"] == "candidate" and (not doc or doc in g["docs"]) and (docs is None or set(g["docs"]) & docs)]
    todo.sort(key=lambda g: -(g["w"] * g["h"]))
    todo = todo[:n]
    if not todo:
        print("No candidates waiting" + (f" for {doc or card}" if doc or card else "") + ".")
        return
    SHEETS.mkdir(parents=True, exist_ok=True)
    for old in SHEETS.glob("sheet-*.png"):
        old.unlink()
    titles_ = titles()
    for s in range(0, len(todo), 4):
        batch = todo[s:s + 4]
        sheet = Image.new("RGB", (TILE * 2 + 30, TILE * ((len(batch) + 1) // 2) + 40 * ((len(batch) + 1) // 2)), "white")
        draw = ImageDraw.Draw(sheet)
        for i, g in enumerate(batch):
            path = ensure_file(g)
            if not path:
                continue
            im = Image.open(path).convert("RGB")
            im.thumbnail((TILE, TILE - 24))
            x, y = (i % 2) * (TILE + 30), (i // 2) * (TILE + 40)
            draw.text((x + 4, y + 4), f"{s + i + 1}. {g['hash']}  ({g['w']}x{g['h']})", fill="black")
            sheet.paste(im, (x, y + 24))
        out = SHEETS / f"sheet-{s // 4 + 1}.png"
        sheet.save(out)
        print(f"{out.relative_to(ROOT).as_posix()}:")
        for i, g in enumerate(batch):
            w = g["where"][0]
            print(f"  {s + i + 1}. {g['hash']}  from {w['doc']} {titles_.get(w['doc'], '')[:60]!r}" + (f" p{w['page']}" if w["page"] else ""))
    left = len([g for g in groups() if g["tier"] == "candidate"]) - len(todo)
    print(f"\nOpen each sheet, then: `assets.py ignore h1,h2,... \"why\"` for the rest in one call, and `assets.py new <hash>` "
          f"(open its full file to describe it) for the keepers. {left} more candidate(s) not on these sheets.")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["scan"]:
        t = time.time()
        n = scan()
        print(f"Scan: {n} source file(s) read in {time.time() - t:.0f}s.")
        cmd_status()
    elif a[:1] == ["status"]:
        cmd_status()
    elif a[:1] == ["review"]:
        doc = a[a.index("--doc") + 1] if "--doc" in a else None
        num = [x for x in a[1:] if x.isdigit()]
        cmd_review(int(num[0]) if num else 10, doc)
    elif a[:1] == ["new"] and len(a) > 1:
        cmd_new(a[1:])
    elif a[:1] == ["ignore"] and len(a) == 3:
        cmd_ignore(a[1], a[2])
    elif a[:1] == ["sheet"]:
        opt = lambda f: a[a.index(f) + 1] if f in a and a.index(f) + 1 < len(a) else None
        cmd_sheet(int(next((x for x in a[1:] if x.isdigit()), 12)), opt("--doc"), opt("--card"))
    else:
        sys.exit(__doc__)
