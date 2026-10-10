"""Generate the knowledge index entries (registers/documents/<ID>.md) from digests (MANTIS-IMP-013).

Called by build_map.py on every rebuild. Each entry has a generated part, built from the
digest's front matter and the current gap, assumption and conflict registers, and a
hand-kept "#### Notes" section that is carried over unchanged. A file is rewritten only
when its content changes.

    python tools/index_gen.py --migrate   one-off: move hand-written detail into Notes (2026-10-09)
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "mantis"
DOCS = M / "knowledge" / "registers" / "documents"
ID_RE = re.compile(r"MANTIS-(?:DOC|GAP|ASM|CFL|DEC)-\d+")
MARK = "<!-- Generated from the digest front matter and the registers by tools/build_map.py. Edit the digest or a register, not these lines; only the Notes section below is hand-kept. -->"
NOTES = "#### Notes"


def ids(values):
    return [x for v in values for x in ID_RE.findall(v)]


def status_of(reg, rid):
    s = reg.get(rid, {}).get("status")
    return s if s else "not in register"


def generated(did, fm, gaps, asms, cfls):
    title = fm.get("original_title", "?")
    lines = [f"### {did} — {title}", MARK,
             f"- **Digest:** [02_digests/{did}.md](../../../02_digests/{did}.md)",
             f"- **Topics:** {', '.join(fm.get('topics', [])) or 'none'}",
             f"- **Key entities:** {', '.join(fm.get('key_entities', [])) or 'none'}",
             f"- **Region:** {fm.get('region', '') or 'not stated'}",
             f"- **Document Confidence:** {fm.get('document_confidence', '?')}"]
    for label, key, reg in (("Knowledge Gaps", "gaps_referenced", gaps), ("Assumptions", "assumptions_referenced", asms),
                            ("Conflicts", "conflicts_referenced", cfls)):
        refs = sorted(set(ids(fm.get(key, []))), key=lambda r: int(r.rsplit("-", 1)[1]))
        if refs or label == "Knowledge Gaps":
            lines.append(f"- **{label}:** " + (", ".join(f"{r} ({status_of(reg, r)})" for r in refs) or "none"))
    rel = sorted(set(ids(fm.get("related_documents", []))))
    lines.append(f"- **Related documents:** {', '.join(rel) or 'none'}")
    return "\n".join(lines) + "\n"


def notes_of(text):
    i = text.find(NOTES)
    return text[i + len(NOTES):].strip("\n") if i >= 0 else ""


def build(docs, gaps, asms, cfls):
    """docs: {doc_id: front matter}. Returns the number of entries rewritten."""
    import textcache
    DOCS.mkdir(parents=True, exist_ok=True)
    changed = 0
    for did, fm in docs.items():
        p = DOCS / f"{did}.md"
        old = textcache.read(p) if p.exists() else ""
        if old and MARK not in old:  # hand-written entry not yet migrated: never overwrite it
            print(f"Index: {did} is hand-written; run `python tools/index_gen.py --migrate` first.")
            continue
        notes = notes_of(old)
        new = generated(did, fm, gaps, asms, cfls) + (f"\n{NOTES}\n{notes}\n" if notes else "")
        if new != old:
            p.write_text(new, encoding="utf-8")
            changed += 1
    return changed


# ---------- one-off migration of the hand-written index ----------

def fields(text):
    """Split a hand-written entry into [(label, value)] keeping continuation lines with their field."""
    out = []
    for line in text.split("\n")[1:]:
        m = re.match(r"- \*\*(.+?):\*\*\s*(.*)", line)
        if m:
            out.append([m.group(1), m.group(2)])
        elif out and line.strip():
            out[-1][1] += " " + line.strip()
    return out


PLAIN = re.compile(r"(MANTIS-[A-Z]+-\d+|\bto\b|closed|open|new|all|none|potential resolution|resolved|promoted|confirmed|"
                   r"explicitly cited|none explicitly cited|raised|both|further reinforcing data point|[\s,;()\-—.:])", re.I)


def carry_over(old, fm):
    keep = []
    gen = {"Topics": set(fm.get("topics", [])), "Key entities": set(fm.get("key_entities", []))}
    for label, value in fields(old):
        v = value.strip()
        if label in ("Digest",):
            continue
        if label in gen:
            extra = [x.strip() for x in v.split(",") if x.strip() and x.strip() not in gen[label]]
            if extra:
                keep.append(f"- {label} the index listed that the digest does not: {', '.join(extra)}")
        elif label == "Region":
            if re.sub(r"\W", "", v.lower()) not in re.sub(r"\W", "", fm.get("region", "").lower()):
                keep.append(f"- Region as the index had it: {v}")
        elif label == "Document Confidence":
            if v.split()[0:1] != fm.get("document_confidence", "").split()[0:1]:
                keep.append(f"- Confidence as the index had it: {v}")
        elif label == "Related documents":  # link reasons live in the digest; keep only open actions
            if re.search(r"propos|pending", v, re.I):
                keep.append(f"- {label} as the index had it: {v}")
        elif label in ("Knowledge Gaps", "Conflicts", "Assumptions"):
            if PLAIN.sub("", v):
                keep.append(f"- {label} as the index had it: {v}")
        else:  # Note, Alternate title, and any other hand-written field
            keep.append(f"- {label}: {v}")
    return keep


def migrate(docs, gaps, asms, cfls):
    moved = 0
    for did, fm in docs.items():
        p = DOCS / f"{did}.md"
        old = p.read_text(encoding="utf-8") if p.exists() else ""
        if MARK in old:
            continue
        keep = carry_over(old, fm) if old else []
        notes = ("Carried over from the hand-written index on 2026-10-09 (IMP-013):\n" + "\n".join(keep)) if keep else ""
        p.write_text(generated(did, fm, gaps, asms, cfls) + (f"\n{NOTES}\n{notes}\n" if notes else ""), encoding="utf-8")
        moved += bool(keep)
    return moved


if __name__ == "__main__" and "--migrate" in sys.argv:
    sys.argv = [sys.argv[0]]
    import runpy
    g = runpy.run_path(str(Path(__file__).with_name("build_map.py")), run_name="index_migrate")
    print(f"Migrated {len(g['docs'])} entries; {migrate(g['docs'], g['gaps'], g['asms'], g['cfls'])} kept hand-written detail in Notes.")
