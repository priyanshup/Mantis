"""Decisions know what they rest on (MANTIS-IMP-080).

    python tools/decisions.py                    every decision, what it rests on, and whether any of it changed
    python tools/decisions.py reviewed <DEC-ID>  the owner says it still stands: record its dependencies as they are now

A decision entry's "Sources/knowledge it was based on" line is its watch list: every document,
assumption, gap and conflict it names. Each is snapshotted (a document's content, an entry's status).
When one changes after that, the decision is flagged for review with what changed, and with what is
built on it: the cards that cite the decision and their pages, epics and stories. Nothing is ever
reversed or rewritten; the owner decides, and `reviewed` records that the decision still stands.
The first run records the starting point, so changes made before it are not detected.
"""
import hashlib, json, re, sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import frontmatter

ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "mantis"
K = M / "knowledge"
SYNC = K / "decision-sync.json"
OUT = K / "map" / "decision-watch.json"
DEP = re.compile(r"MANTIS-(?:DOC-\d{4}|ASM-\d{3}|GAP-\d{3}|CFL-\d{3})")


def decisions():
    out = []
    for p in sorted((K / "registers" / "decisions").glob("MANTIS-DEC-*.md")):
        t = p.read_text(encoding="utf-8")
        field = lambda k: " ".join((re.search(r"\*\*%s:\*\*\s*(.+?)(?=\n- \*\*|\Z)" % re.escape(k), t, re.S) or [None, ""])[1].split())
        basis = field("Sources/knowledge it was based on")
        out.append({"id": p.stem, "date": field("Date"), "decision": field("Decision"),
                    "rests_on": sorted(set(DEP.findall(basis)))})
    return out


def state(dep):
    """What a dependency is now: a document's content (minus its change log), or an entry's status line."""
    if "-DOC-" in dep:
        p = M / "02_digests" / f"{dep}.md"
        if not p.exists():
            return "missing"
        fm, body = frontmatter.split(p.read_text(encoding="utf-8"))
        body = re.split(r"(?m)^##\s+Change Log\s*$", body)[0]
        return f"version {fm.get('version', '1')}, content {hashlib.sha1(body.encode('utf-8')).hexdigest()[:10]}"
    p = next(iter(K.glob(f"registers/*/{dep}.md")), None)
    if not p:
        return "missing"
    m = re.search(r"\*\*Status:\*\*\s*(.+)", p.read_text(encoding="utf-8"))
    return m.group(1).strip()[:160] if m else "no status"


def downstream(dec_id):
    """Cards that cite the decision, and the pages, epics and stories filed under them."""
    cards, outs = [], []
    feats = json.loads((K / "map" / "features.json").read_text(encoding="utf-8")) if (K / "map" / "features.json").exists() else []
    tops = json.loads((K / "map" / "topics.json").read_text(encoding="utf-8")) if (K / "map" / "topics.json").exists() else []
    short = dec_id.replace("MANTIS-", "")
    for c in feats + tops:
        p = M / c["card"]
        if p.exists() and re.search(r"\b(MANTIS-)?%s\b" % re.escape(short), p.read_text(encoding="utf-8").split("<!-- GENERATED")[0]):
            cards.append(c["slug"])
    for folder in ("confluence", "epics", "user-stories"):
        for p in (M / "outputs" / folder).rglob("*.md"):
            if frontmatter.parse(p.read_text(encoding="utf-8")).get("feature", "") in cards:
                outs.append(p.relative_to(M).as_posix())
    return cards, sorted(outs)


def scan(sync=None, state_of=state):
    """[(decision, changes)] where changes = [(dependency, was, now)]. New decisions and new dependencies are
    recorded, not flagged: there is nothing to compare them with yet."""
    sync = load() if sync is None else sync
    out = []
    for d in decisions():
        snap = sync.get(d["id"], {}).get("deps", {})
        changes = [(x, snap[x], state_of(x)) for x in d["rests_on"] if x in snap and snap[x] != state_of(x)]
        out.append((d, changes))
    return out


def load():
    return json.loads(SYNC.read_text(encoding="utf-8")) if SYNC.exists() else {}


def record(dec_ids=None, sync=None, state_of=state, today=None):
    """Snapshot the dependencies of the given decisions (all, for the starting point); keep others as they are."""
    sync = load() if sync is None else sync
    for d in decisions():
        if dec_ids is None and d["id"] in sync:
            known = sync[d["id"]]["deps"]   # only add dependencies first seen now; never overwrite a recorded state
            known.update({x: state_of(x) for x in d["rests_on"] if x not in known})
        elif dec_ids is None or d["id"] in dec_ids:
            sync[d["id"]] = {"reviewed": today or date.today().isoformat(), "deps": {x: state_of(x) for x in d["rests_on"]}}
    return sync


def build():
    """Flag decisions whose basis changed; record the starting point for anything new. Called by build_map.py."""
    sync = load()
    flagged = []
    for d, changes in scan(sync):
        if changes:
            cards, outs = downstream(d["id"])
            flagged.append({"id": d["id"], "decision": d["decision"][:200], "changes": changes, "cards": cards, "outputs": outs,
                            "reviewed": sync.get(d["id"], {}).get("reviewed", "")})
    SYNC.write_text(json.dumps(record(sync=sync), indent=1, ensure_ascii=False), encoding="utf-8")
    OUT.write_text(json.dumps({"flagged": flagged}, indent=1, ensure_ascii=False), encoding="utf-8")
    return flagged


def plain_change(dep, was, now):
    if "-DOC-" in dep:
        return f"{dep} changed ({was.split(',')[0]} to {now.split(',')[0]})" if was.split(",")[0] != now.split(",")[0] else f"{dep} was edited"
    return f"{dep} moved from \"{was[:50]}\" to \"{now[:50]}\""


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if argv[:1] == ["reviewed"] and len(argv) == 2:
        did = argv[1] if argv[1].startswith("MANTIS-") else "MANTIS-" + argv[1]
        if did not in {d["id"] for d in decisions()}:
            sys.exit(f"No decision {did}")
        SYNC.write_text(json.dumps(record({did}), indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"{did}: recorded as still standing on what it rests on today.")
        return 0
    sync = load()
    for d, changes in scan(sync):
        print(f"{d['id']} ({d['date']}): rests on {', '.join(x.replace('MANTIS-', '') for x in d['rests_on']) or 'nothing listed'}"
              + ("" if d["id"] in sync else "  [not recorded yet: the next rebuild records it]"))
        for x, was, now in changes:
            print("    CHANGED: " + plain_change(x, was, now))
        if changes:
            cards, outs = downstream(d["id"])
            print(f"    built on it: cards {', '.join(cards) or 'none'}; outputs {', '.join(outs) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
