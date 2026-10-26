"""Match mirrored Confluence pages to Mantis digests by title and content, and diff the ones that changed (MANTIS-IMP-087). Stdlib only.

No AI. For each page with real content:
  0. Page ID: a digest whose front matter names the page (confluence_page_id) is its match, and the
     page's version against the digest's confluence_version decides same or changed. No guessing.
  1. Title: the closest digest original_title (difflib ratio after stripping emoji, case and punctuation).
  2. Content: 4-word shingles of the page against the text of every digest's source snapshot.
     `cover` = share of the page found in the source, `back` = share of the source found in the page.
  3. Verdict:
       same       the source holds the page (cover and back both high), or atl.py finds the page
                  was not edited since the snapshot date (the text differs only by export format)
       changed    a digest clearly matches (content, or title with some content) and the page was edited since
       check      only the title matches and the content does not: probably a different page with the same name
       related    some overlap with a source, no clear match: probably covered in part elsewhere
       new        nothing in Mantis matches
The source text of each digest is extracted once and cached in mantis/mirror/.cache/.
"""
import difflib, re, sys
from pathlib import Path

import atl_store

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
DIGESTS = ROOT / "mantis" / "02_digests"
SAME_COVER, SAME_BACK = 0.85, 0.70
MATCH_COVER, TITLE_MATCH = 0.40, 0.90
RELATED = 0.15


def norm_title(t):
    t = re.sub(r"[^\w\s]", " ", (t or "").lower())
    return re.sub(r"\s+", " ", t).strip()


def words(text):
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def shingles(text, n=4):
    w = words(text)
    return {hash(" ".join(w[i:i + n])) for i in range(max(0, len(w) - n + 1))}


def source_text(doc_id, source_file):
    cache = atl_store.MIRROR / ".cache" / "srctext" / f"{doc_id}.txt"
    if cache.exists():
        return cache.read_text(encoding="utf-8")
    src = ROOT / "mantis" / source_file
    if not src.exists():
        return ""
    folder = src.parent
    text_md = folder / (src.stem + "-text.md")
    try:
        if text_md.exists():
            text = text_md.read_text(encoding="utf-8")
        else:
            sys.path.insert(0, str(ROOT / "tools"))
            import extract
            text = extract.convert(src) or ""
    except Exception as exc:          # a broken snapshot must not stop the run
        text = ""
        print(f"  could not read {source_file}: {exc}")
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(text, encoding="utf-8")
    return text


def load_digests():
    sys.path.insert(0, str(ROOT / "tools"))
    import frontmatter
    out = {}
    for p in sorted(DIGESTS.glob("*.md")):
        fm = frontmatter.parse(p.read_text(encoding="utf-8"))
        did = fm.get("document_id") or p.stem
        sf = fm.get("source_file", "")
        m = re.search(r"(\d{4}-\d{2}-\d{2})", sf)
        out[did] = {"title": fm.get("original_title", ""), "source_file": sf, "snapshot": m.group(1) if m else fm.get("generated_on", ""),
                    "version": fm.get("version", "1"), "page_id": str(fm.get("confluence_page_id", "") or ""),
                    "page_version": int(fm["confluence_version"]) if str(fm.get("confluence_version", "")).isdigit() else None}
    return out


def page_body(pid):
    text = atl_store.read(f"confluence/pages/{pid}.md")
    parts = text.split("\n---\n", 2)
    body = parts[1] if len(parts) > 1 else text
    return body


def match_all(index, digests, log=print):
    """Verdict per content page: {pid: {verdict, doc, title_score, cover, back, others}}."""
    log(f"  reading the source text of {len(digests)} digests (cached after the first run)")
    src = {d: shingles(source_text(d, v["source_file"])) for d, v in digests.items()}
    inverted = {}
    for d, s in src.items():
        for h in s:
            inverted.setdefault(h, []).append(d)
    titles = {d: norm_title(v["title"]) for d, v in digests.items()}
    by_page = {v["page_id"]: d for d, v in digests.items() if v["page_id"]}
    out = {}
    for pid, e in index.items():
        if pid.startswith("_") or e.get("kind") != "content":
            continue
        if pid in by_page:      # the digest names this page: exact match, decided by version number
            d = by_page[pid]
            same = digests[d]["page_version"] == e.get("version")
            out[pid] = {"verdict": "same" if same else "changed", "doc": d, "cover": 1.0, "back": 1.0, "title_score": 1.0,
                        "others": [], "linked": True, "version_then": digests[d]["page_version"]}
            continue
        ps = shingles(page_body(pid))
        hits = {}
        for h in ps:
            for d in inverted.get(h, ()):
                hits[d] = hits.get(d, 0) + 1
        nt = norm_title(e["title"])
        tscore = {d: difflib.SequenceMatcher(None, nt, t).ratio() for d, t in titles.items() if t}
        cands = set(sorted(hits, key=hits.get, reverse=True)[:5]) | {d for d, s in tscore.items() if s >= TITLE_MATCH}
        rows = []
        for d in cands:
            cover = hits.get(d, 0) / max(1, len(ps))
            back = hits.get(d, 0) / max(1, len(src[d]))
            rows.append((cover, d, cover, back, tscore.get(d, 0)))
        rows.sort(reverse=True)
        best, namesake = (rows[0] if rows else None), False
        # Content decides. A title match wins only when content is weak and the titled source has some
        # overlap or no text at all (a diagram-only export); a namesake with other content is "check".
        if best and best[2] < MATCH_COVER:
            titled = sorted((r for r in rows if r[4] >= TITLE_MATCH), key=lambda r: (-r[4], -r[2]))
            if titled:
                namesake = titled[0][2] < 0.10 and bool(src[titled[0][1]])
                best = titled[0]
        if best and best[2] >= SAME_COVER and best[3] >= SAME_BACK:
            verdict = "same"
        elif namesake:
            verdict = "check"
        elif best and (best[2] >= MATCH_COVER or best[4] >= TITLE_MATCH):
            verdict = "changed"
        elif best and best[2] >= RELATED:
            verdict = "related"
        else:
            verdict = "new"
        out[pid] = {"verdict": verdict, "doc": best[1] if best and verdict != "new" else None,
                    "cover": round(best[2], 2) if best else 0, "back": round(best[3], 2) if best else 0,
                    "title_score": round(best[4], 2) if best else 0,
                    "others": [r[1] for r in rows[1:4] if r[2] >= RELATED]}
    return out


def section_diff(old, new, context=1):
    """Unified diff grouped under the heading each change sits in; returns (markdown, added, removed, sections)."""
    a, b = [l for l in old.splitlines() if l.strip()], [l for l in new.splitlines() if l.strip()]
    added = removed = 0
    sections, out, heading = [], [], "(top of page)"
    # Compare words only, so a heading level, bold marks or spacing never count as a change.
    key = lambda l: " ".join(words(l))
    sm = difflib.SequenceMatcher(None, [key(l) for l in a], [key(l) for l in b], autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        for l in b[j1:j2] if tag == "equal" else ():
            if l.startswith("#"):
                heading = l.lstrip("# ").strip()
        if tag == "equal":
            continue
        for l in b[j1:j2]:
            if l.startswith("#"):
                heading = l.lstrip("# ").strip()
        if heading not in sections:
            sections.append(heading)
            out.append(f"\n### {heading}\n")
        out += [f"- removed: {l[:400]}" for l in a[i1:i2]]
        out += [f"+ added: {l[:400]}" for l in b[j1:j2]]
        removed, added = removed + (i2 - i1), added + (j2 - j1)
    return "\n".join(out), added, removed, sections
