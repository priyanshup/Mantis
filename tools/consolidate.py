"""Consolidation proposals and safe archiving of digests (IMP-109). Nothing is ever deleted: originals move to mantis/03_archive and each move is logged.

    python tools/consolidate.py propose                  what could be split, rolled up, merged or archived; writes mantis/knowledge/map/consolidation.md
    python tools/consolidate.py check <DOC>              who cites a digest (a cited digest is never archived)
    python tools/consolidate.py archive <DOC> --reason "..."   move an uncited digest and its source folder to 03_archive
    python tools/consolidate.py archive-snapshots [--apply]    older source snapshots beside the one a digest cites: list them, or with --apply move them

`propose` only proposes. Merging two digests or rolling several up needs a combined digest written from the originals (ask for it); once the owner approves, the
originals are archived here, not deleted. Archive layout: 03_archive/digests/<DOC>.md, 03_archive/sources/<DOC>/..., and a line in 03_archive/consolidation-log.md.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import re, shutil, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "mantis"
DOC_RE = re.compile(r"^MANTIS-DOC-\d{4}$")
SCAN_DIRS = ("knowledge", "outputs", "02_digests", "tasks")   # where a citation counts; the generated map and the sources do not


def _check_id(doc):
    if not DOC_RE.match(doc):
        raise ValueError(f"'{doc}' is not a digest id like MANTIS-DOC-0001")


def citers(mantis, doc):
    """Files that mention the digest, other than itself and generated map files."""
    mantis = Path(mantis)
    found = []
    for d in SCAN_DIRS:
        for p in sorted((mantis / d).rglob("*.md")) if (mantis / d).exists() else []:
            rel = p.relative_to(mantis).as_posix()
            if rel.startswith("knowledge/map/") or p.stem == doc:
                continue
            try:
                if doc in p.read_text(encoding="utf-8", errors="replace"):
                    found.append(rel)
            except OSError:
                pass
    return found


def _log(mantis, line):
    log = Path(mantis) / "03_archive" / "consolidation-log.md"
    log.parent.mkdir(parents=True, exist_ok=True)
    head = "" if log.exists() else "# Consolidation log\n\nEvery move to the archive: date, what, why. Nothing here was deleted; move a file back to restore it.\n\n"
    with log.open("a", encoding="utf-8") as f:
        f.write(head + line + "\n")


def archive(mantis, doc, reason):
    """Move an uncited digest and its source folder to the archive. Returns the list of moved paths; raises when cited, unknown or already archived."""
    _check_id(doc)
    mantis = Path(mantis)
    if not reason.strip():
        raise ValueError("a reason is required")
    src = mantis / "02_digests" / f"{doc}.md"
    if not src.exists():
        raise FileNotFoundError(f"{doc} has no digest")
    cited = citers(mantis, doc)
    if cited:
        raise PermissionError(f"{doc} is cited by {', '.join(cited[:5])}" + (f" and {len(cited) - 5} more" if len(cited) > 5 else "") + "; not archived")
    dest = mantis / "03_archive" / "digests" / f"{doc}.md"
    folder = mantis / "01_sources" / doc
    dest_folder = mantis / "03_archive" / "sources" / doc
    if dest.exists() or (folder.exists() and dest_folder.exists()):
        raise FileExistsError(f"{doc} already has an archived copy; not overwritten")
    dest.parent.mkdir(parents=True, exist_ok=True)
    moved = [dest]
    shutil.move(str(src), str(dest))
    if folder.exists():
        dest_folder.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(folder), str(dest_folder))
        moved.append(dest_folder)
    entry = mantis / "knowledge" / "registers" / "documents" / f"{doc}.md"   # the generated index entry would otherwise outlive its digest
    if entry.exists():
        (mantis / "03_archive" / "index").mkdir(parents=True, exist_ok=True)
        shutil.move(str(entry), str(mantis / "03_archive" / "index" / entry.name))
    _log(mantis, f"- {time.strftime('%Y-%m-%d')} {doc} archived: {reason.strip()}")
    return moved


def archive_snapshots(mantis, apply=False):
    """Older snapshots beside the one each digest cites. Returns [(doc, [names], bytes)]; with apply they move to 03_archive/sources/<DOC>/."""
    import digesthealth
    mantis = Path(mantis)
    out = []
    for doc, files, size in digesthealth.scan(mantis)["old_snapshots"]:
        out.append((doc, [f.name for f in files], size))
        if apply:
            dest = mantis / "03_archive" / "sources" / doc
            dest.mkdir(parents=True, exist_ok=True)
            for f in files:
                if (dest / f.name).exists():
                    raise FileExistsError(f"{dest / f.name} exists; not overwritten")
                shutil.move(str(f), str(dest / f.name))
            _log(mantis, f"- {time.strftime('%Y-%m-%d')} {doc}: {len(files)} older snapshot(s) archived ({size // 1000} KB), the cited one stays")
    return out


def proposals(mantis, pairs=()):
    """Markdown text of what could be consolidated. `pairs` is [(score, a, b)] from classify.pair_scores (near-duplicates)."""
    import digesthealth
    r = digesthealth.scan(mantis)
    L = ["# Consolidation proposals", "", "Generated by `python tools/consolidate.py propose`; never edited by hand. Each item needs the owner's approval. Nothing is deleted: originals move to the archive.", ""]
    L.append(f"## Split: digests over {digesthealth.BUDGET_BYTES // 1000} KB ({len(r['over_budget'])})")
    L += [f"- {i} ({b / 1000:.1f} KB): {digesthealth.split_hint(r['digests'][i])}" for i, b in r["over_budget"]] or ["- none"]
    L += ["", f"## Roll up: tags with {digesthealth.ROLLUP_MIN} or more small digests ({len(r['rollup'])})"]
    for t, c, total in r["rollup"]:
        ids = sorted(i for i, m in r["digests"].items() if t in m["topics"] and m["bytes"] <= digesthealth.ROLLUP_SMALL)
        L.append(f"- '{t}': {c} small digests of {total}: {', '.join(ids[:12])}" + (f" and {len(ids) - 12} more" if len(ids) > 12 else ""))
    if not r["rollup"]:
        L.append("- none")
    L += ["", f"## Merge: near-duplicate pairs ({len(pairs)})"]
    L += [f"- {a} ~ {b} (score {s:.2f})" for s, a, b in list(pairs)[:20]] or ["- none"]
    L += ["", f"## Archive: older snapshots ({len(r['old_snapshots'])} folders)"]
    L += [f"- {i}: {', '.join(f.name for f in fs[:4])} ({s // 1000} KB)" for i, fs, s in r["old_snapshots"][:30]] or ["- none"]
    L += ["", "Next: ask for a combined digest for a roll-up or merge, then `archive <DOC> --reason ...` for each original once nothing cites it (re-point the cards first).", ""]
    return "\n".join(L)


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    try:
        if cmd == "propose":
            import classify, json, textcache
            w = json.loads(classify.CONFIG.read_text(encoding="utf-8"))
            pairs = [p for p in classify.pair_scores(classify.corpus(), w["weights"], floor=0.5) if p[0] >= 0.5]
            text = proposals(M, pairs)
            textcache.write(M / "knowledge" / "map" / "consolidation.md", text)
            print(text)
        elif cmd == "check" and rest:
            _check_id(rest[0])
            c = citers(M, rest[0])
            print(f"{rest[0]} is cited by {len(c)} file(s)" + (":\n  " + "\n  ".join(c) if c else "; it can be archived."))
        elif cmd == "archive" and rest and "--reason" in rest:
            reason = " ".join(rest[rest.index("--reason") + 1:])
            moved = archive(M, rest[0], reason)
            print("Archived: " + ", ".join(p.relative_to(M).as_posix() for p in moved) + ". Now run python tools/build_map.py.")
        elif cmd == "archive-snapshots":
            got = archive_snapshots(M, "--apply" in rest)
            print(f"{len(got)} folder(s), {sum(s for _, _, s in got) / 1e6:.1f} MB " + ("archived." if "--apply" in rest else "would move; add --apply."))
        else:
            print(__doc__)
            return 2
    except (ValueError, FileNotFoundError, FileExistsError, PermissionError) as e:
        print(e)
        return 1
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
