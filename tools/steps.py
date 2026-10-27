"""Next steps on cards (MANTIS-IMP-023): read the "## Next steps" table from every card's curated part.

    python tools/steps.py            every step, by card
    python tools/steps.py mine       steps owned by the owner that are not done

A card may carry a table under "## Next steps" (template: TEMPLATES/feature-card.md) with columns
Step | Who | Status | Due | Source, in any order; Due is optional (YYYY-MM-DD or "Fri 16 Oct 2026").
A step is done when its Status starts with "Done". build_map.py writes map/steps.json, which feeds
the roadmap's progress, the owner's follow-ups (steps waiting on someone else), suggested
deadlines and the away planner.
"""
import json, re, sys
from datetime import datetime
from pathlib import Path
import textcache

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
K = ROOT / "mantis" / "knowledge"
OUT = K / "map" / "steps.json"
MARK = "<!-- GENERATED"


def _date(s):
    s = (s or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s
    for fmt in ("%a %d %b %Y", "%d %b %Y", "%d %B %Y", "%a %d %B %Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            pass
    return ""


def _cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse(path):
    text = path.read_text(encoding="utf-8")
    curated = text.split(MARK)[0]
    title = (re.search(r'(?m)^title:\s*"?(.+?)"?\s*$', curated) or [None, path.stem])[1]
    m = re.search(r"(?ms)^##\s+Next steps\b.*?\n(\|.+?)(?:\n\s*\n|\Z)", curated)
    if not m:
        return []
    rows = [l for l in m.group(1).splitlines() if l.strip().startswith("|")]
    if len(rows) < 3:
        return []
    head = [h.lower() for h in _cells(rows[0])]
    col = lambda name: next((i for i, h in enumerate(head) if h.startswith(name)), None)
    i_step, i_who, i_st, i_due, i_src = col("step"), col("who"), col("status"), col("due"), col("source")
    if i_step is None:
        return []
    out = []
    for n, r in enumerate(rows[2:], 1):
        c = _cells(r)
        get = lambda i: c[i] if i is not None and i < len(c) else ""
        if not get(i_step) or get(i_step) == "#":
            continue
        step = get(i_step) if not get(i_step).isdigit() else (c[i_step + 1] if i_step + 1 < len(c) else "")
        status = get(i_st)
        out.append({"card": path.stem, "card_title": title, "n": n, "step": step, "who": get(i_who), "status": status,
                    "due": _date(get(i_due)), "source": get(i_src), "done": status.lower().startswith("done")})
    return out


def collect():
    out = []
    for d in ("features", "topics"):
        for p in sorted((K / d).glob("*.md")):
            if p.name != "README.md":
                out += parse(p)
    return out


def build():
    steps = collect()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    textcache.write(OUT, json.dumps(steps, indent=1, ensure_ascii=False) + "\n")
    return steps


def load():
    try:
        return json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return collect()


def progress():
    """{card slug: (done, total)} for the roadmap."""
    out = {}
    for s in load():
        d, t = out.get(s["card"], (0, 0))
        out[s["card"]] = (d + s["done"], t + 1)
    return out


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "tools"))
    rows = build()
    if sys.argv[1:] == ["mine"]:
        import people
        rows = [s for s in rows if not s["done"] and people.is_owner(s["who"])]
    for s in rows:
        print(f"{s['card']}: {'[x]' if s['done'] else '[ ]'} {s['step']} | {s['who']} | {s['status']}" + (f" | due {s['due']}" if s["due"] else ""))
