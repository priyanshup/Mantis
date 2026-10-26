"""Free space in the source snapshots without losing evidence (MANTIS-IMP-089). Stdlib for planning; pypdf to keep text.

    python tools/prune_sources.py            report what would be removed and the space it frees (changes nothing)
    python tools/prune_sources.py --apply    do it

Two rules, both decided by code:
  1. Identical copies. A file in a source folder byte-identical to another one there, or whose text is
     word-for-word the cited snapshot's (an export saved twice, e.g. "<date>-duplicate-export.pdf"), is
     deleted; the copy the digest cites stays.
  2. Superseded snapshots. When a document has a newer snapshot and its digest cites the newer one, the
     older binary (PDF, Word export) is replaced by "<date>-text.md": its full text with "<!-- page N -->"
     markers, so page citations in the archived old digest still resolve. The binary is then deleted and
     the archived digest's source_file is pointed at the text.
Never touched: the snapshot a current digest cites, Markdown snapshots, anything outside 01_sources.
Images in removed PDFs: registered diagrams are kept in knowledge/assets/files; the live page's images
come from Confluence (tools/atl.py attachments).
"""
import hashlib, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "mantis"
SRC, DIG, ARCH = M / "01_sources", M / "02_digests", M / "03_archive"
BINARY = {".pdf", ".doc", ".docx", ".pptx", ".mhtml", ".mht", ".html", ".htm"}


def sha(p):
    return hashlib.sha1(p.read_bytes()).hexdigest()


def cited(doc_id):
    p = DIG / f"{doc_id}.md"
    m = re.search(r"(?m)^source_file:\s*(\S+)", p.read_text(encoding="utf-8")) if p.exists() else None
    return (M / m.group(1)).resolve() if m else None


def plan():
    dupes, superseded = [], []
    for d in sorted(x for x in SRC.iterdir() if x.is_dir()):
        files = sorted(f for f in d.iterdir() if f.is_file())
        cur = cited(d.name)
        seen = {}
        for f in sorted(files, key=lambda f: (f.resolve() != cur, "duplicate" in f.name, f.name)):
            if f.suffix.lower() not in BINARY:
                continue
            h = sha(f)
            if h in seen:
                dupes.append((f, seen[h]))
            else:
                seen[h] = f
        # Exports saved twice differ in bytes (each PDF embeds its export time), so also compare the text:
        # a binary whose words equal the cited snapshot's words is a duplicate as well.
        if cur and cur.exists() and cur.suffix.lower() in BINARY:
            cur_words = norm_text(text_of(cur))
            for f in files:
                if f.suffix.lower() in BINARY and f.resolve() != cur and f not in {x for x, _ in dupes}:
                    if cur_words and norm_text(text_of(f)) == cur_words:
                        dupes.append((f, cur))
        kept = {f for f in files if f not in {x for x, _ in dupes}}
        for f in sorted(kept):
            if f.suffix.lower() in BINARY and cur and f.resolve() != cur and f.name[:10] < cur.name[:10]:
                superseded.append(f)
    return dupes, superseded


_texts = {}


def text_of(f):
    if f not in _texts:
        sys.path.insert(0, str(ROOT / "tools"))
        import extract
        try:
            _texts[f] = extract.convert(f) or ""
        except Exception:
            _texts[f] = ""
    return _texts[f]


def norm_text(t):
    """Words only, page markers dropped: two exports of the same page compare equal."""
    return " ".join(re.findall(r"[a-z0-9]+", re.sub(r"<!-- page \d+ -->", " ", t).lower()))


def backup(files):
    """Zip the files about to be removed into the local backups folder (outside OneDrive), so a removal can
    be undone; maintain.py keeps the newest five backups."""
    import os, tempfile, zipfile
    from datetime import datetime
    if not files:
        return None
    d = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "Mantis" / "backups"
    d.mkdir(parents=True, exist_ok=True)
    z = d / f"pruned-sources-{datetime.now():%Y%m%d-%H%M%S}.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, f.relative_to(M).as_posix())
    return z


def apply(dupes, superseded):
    z = backup([f for f, _ in dupes] + list(superseded))
    if z:
        print(f"  backup of everything removed: {z}")
    freed = 0
    for f, keep in dupes:
        freed += f.stat().st_size
        f.unlink()
    for f in superseded:
        text = text_of(f)
        if len(text.strip()) < 200:
            print(f"  kept {f.relative_to(M)}: its text could not be extracted, so the file stays")
            continue
        out = f.with_name(f.stem + "-text.md")
        out.write_text(f"<!-- Text of {f.name}, kept when the binary was removed (tools/prune_sources.py). "
                       f"Page markers match the original's pages. -->\n\n{text}\n", encoding="utf-8")
        old_rel, new_rel = f.relative_to(M).as_posix(), out.relative_to(M).as_posix()
        for a in ARCH.glob(f"{f.parent.name}-v*.md"):
            t = a.read_text(encoding="utf-8")
            if old_rel in t:
                a.write_text(t.replace(old_rel, new_rel), encoding="utf-8")
        freed += f.stat().st_size - out.stat().st_size
        f.unlink()
    return freed


def main(argv):
    sys.stdout.reconfigure(errors="replace")
    dupes, superseded = plan()
    size = lambda fs: sum(f.stat().st_size for f in fs) / 1e6
    print(f"Identical copies: {len(dupes)} file(s), {size([f for f, _ in dupes]):.1f} MB")
    for f, keep in dupes:
        print(f"  {f.relative_to(M)}  (same content as {keep.name})")
    print(f"Superseded snapshots: {len(superseded)} file(s), {size(superseded):.1f} MB (each keeps a page-marked text copy)")
    for f in superseded:
        print(f"  {f.relative_to(M)}")
    if "--apply" in argv:
        print(f"Freed {apply(dupes, superseded) / 1e6:.1f} MB.")
    else:
        print("Nothing changed. Run with --apply to do it.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
