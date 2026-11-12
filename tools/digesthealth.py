"""The digest-health report (IMP-109): is the knowledge staying cheap to read?

    python tools/digesthealth.py            print the report and write mantis/knowledge/map/digest-health.json (build_map.py does this on every build)

What it measures, all advice and never a failure:
  - size budget: a digest over about 12 KB (BUDGET_BYTES) should be split by section; the report names the biggest section to split off;
  - front matter: a `confidence_reason` over 200 characters (the template asks for one line of 160);
  - roll-up candidates: a tag shared by 8 or more small digests (5 KB or less each) that one short summary digest could replace, for the owner's approval (consolidate.py);
  - archive candidates: an older source snapshot kept beside the newer one the digest cites;
  - the mirror: its size by folder against a budget (retention below).
Retention: the mirror (mantis/mirror) is a working copy, not a source. A page or ticket is re-fetched by a sync, diffs are rebuilt by every compare, attachments are fetched once by
content hash. Nothing in it is deleted automatically; the report warns at MIRROR_BUDGET and the owner decides what to prune. Digests and cards are never deleted: consolidation moves
originals to mantis/03_archive (tools/consolidate.py).
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import json, re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "mantis"
BUDGET_BYTES = 12_000
REASON_MAX = 200
ROLLUP_MIN = 8
ROLLUP_SMALL = 5_000
MIRROR_BUDGET = 150_000_000
FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def metrics(text):
    text = text.replace("\r\n", "\n")
    m = FRONT.match(text)
    head, body = (m.group(1), text[m.end():]) if m else ("", text)
    parts = [p for p in re.split(r"(?m)^(?=## )", body) if p.startswith("## ")]
    secs = [(p.split("\n", 1)[0][3:].strip(), len(p.encode("utf-8"))) for p in parts]
    get = lambda k: (re.search(rf'(?m)^{k}:\s*"?(.*?)"?\s*$', head) or [None, ""])[1]
    topics = [t.strip() for t in (re.search(r"(?m)^topics:\s*\[(.*?)\]", head) or [None, ""])[1].split(",") if t.strip()]
    return {"bytes": len(text.encode("utf-8")), "front_bytes": len(text.encode("utf-8")) - len(body.encode("utf-8")), "reason_len": len(get("confidence_reason")),
            "sections": secs, "largest": max(secs, key=lambda s: s[1], default=("", 0)), "topics": topics, "source_file": get("source_file")}


def split_hint(m):
    return f"split off '{m['largest'][0]}' ({m['largest'][1] / 1000:.1f} KB) into a digest of its own"


def scan(mantis=M):
    mantis = Path(mantis)
    digests = {p.stem: metrics(p.read_text(encoding="utf-8")) for p in sorted((mantis / "02_digests").glob("MANTIS-DOC-*.md"))}
    over = sorted(((i, m["bytes"]) for i, m in digests.items() if m["bytes"] > BUDGET_BYTES), key=lambda t: -t[1])
    long_reason = [i for i, m in digests.items() if m["reason_len"] > REASON_MAX]
    small = Counter(t for m in digests.values() if m["bytes"] <= ROLLUP_SMALL for t in m["topics"])
    rollup = sorted(((t, c, sum(1 for m in digests.values() if t in m["topics"])) for t, c in small.items() if c >= ROLLUP_MIN), key=lambda t: (-t[1], t[0]))
    old = []
    for i, m in digests.items():
        folder = mantis / "01_sources" / i
        if not folder.is_dir():
            continue
        files = sorted(f for f in folder.iterdir() if f.is_file())
        keep = {Path(m["source_file"]).name} if m["source_file"] else set()
        if len(files) > 1 and not keep:
            keep = {files[-1].name}   # the newest by name (the date)
        older = [f for f in files if f.name not in keep]
        if older and keep & {f.name for f in files}:
            old.append((i, older, sum(f.stat().st_size for f in older)))
    return {"digests": digests, "over_budget": over, "long_reason": long_reason, "rollup": rollup, "old_snapshots": old,
            "total_bytes": sum(m["bytes"] for m in digests.values()), "count": len(digests)}


def mirror_sizes(mirror=M / "mirror"):
    mirror = Path(mirror)
    by = {}
    if mirror.exists():
        for sub in sorted(mirror.iterdir()):
            files = [f for f in sub.rglob("*") if f.is_file()] if sub.is_dir() else [sub]
            by[sub.name] = sum(f.stat().st_size for f in files)
    return {"total": sum(by.values()), "by": {k: v for k, v in by.items() if v}}


def problems(report, mirror, mirror_budget=MIRROR_BUDGET):
    """[(level, message)] for the Health page. Always 'info': these are budgets and advice."""
    out = []
    n = len(report["over_budget"])
    if n:
        top = ", ".join(f"{i} ({b / 1000:.0f} KB)" for i, b in report["over_budget"][:3])
        out.append(("info", f"{n} digest{' is' if n == 1 else 's are'} over the {BUDGET_BYTES // 1000} KB budget, which costs tokens whenever one is opened: {top}. "
                            "`python tools/consolidate.py propose` says where to split."))
    n = len(report["long_reason"])
    if n:
        out.append(("info", f"{n} digest{' has' if n == 1 else 's have'} a confidence reason over {REASON_MAX} characters (the template asks for one line); shorten it when the digest is next touched."))
    if report["rollup"]:
        t, c, _ = report["rollup"][0]
        out.append(("info", f"{len(report['rollup'])} tag{'s' if len(report['rollup']) != 1 else ''} are shared by {ROLLUP_MIN} or more small digests (most: '{t}', {c}); a roll-up summary could replace them, "
                            "for your approval: `python tools/consolidate.py propose`."))
    if report["old_snapshots"]:
        size = sum(s for _, _, s in report["old_snapshots"])
        out.append(("info", f"{len(report['old_snapshots'])} source folder{'s hold' if len(report['old_snapshots']) != 1 else ' holds'} older snapshots beside the one the digest cites "
                            f"({size / 1e6:.1f} MB): `python tools/consolidate.py archive-snapshots` moves them to the archive."))
    if mirror["total"] > mirror_budget:
        big = max(mirror["by"].items(), key=lambda kv: kv[1])
        out.append(("info", f"The mirror is {mirror['total'] / 1e6:.0f} MB, over its {mirror_budget / 1e6:.0f} MB budget; the biggest folder is {big[0]} ({big[1] / 1e6:.0f} MB). "
                            "It is a working copy: prune old attachments or run a refresh, the owner decides."))
    return out


def write(out=M / "knowledge" / "map" / "digest-health.json", mantis=M, mirror_dir=None):
    """Save the summary; True when it changed."""
    import textcache
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    r = scan(mantis)
    mirror = mirror_sizes(mirror_dir if mirror_dir is not None else Path(mantis) / "mirror")
    summary = {"count": r["count"], "total_bytes": r["total_bytes"], "over_budget": [[i, b] for i, b in r["over_budget"]], "long_reason": r["long_reason"],
               "rollup": [list(t) for t in r["rollup"]], "old_snapshots": [[i, [f.name for f in fs], s] for i, fs, s in r["old_snapshots"]], "mirror": mirror}
    return textcache.write(Path(out), json.dumps(summary, indent=1, ensure_ascii=False))


def main():
    r = scan()
    mirror = mirror_sizes()
    print(f"{r['count']} digests, {r['total_bytes'] / 1e6:.2f} MB; mirror {mirror['total'] / 1e6:.0f} MB")
    for level, msg in problems(r, mirror):
        print(f"- {msg}")
    for i, b in r["over_budget"][:8]:
        print(f"  over budget: {i} {b / 1000:.1f} KB: {split_hint(r['digests'][i])}")
    for t, c, total in r["rollup"][:8]:
        print(f"  roll-up: '{t}' {c} small digests of {total}")
    write()
    return 0


if __name__ == "__main__":
    sys.exit(main())
