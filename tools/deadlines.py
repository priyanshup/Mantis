"""Suggested deadlines for undated tasks (MANTIS-IMP-041).

    python tools/deadlines.py                       today's suggestions (at most 3)
    python tools/deadlines.py add TASK_ID DATE "why"   a suggestion Claude found in a source (daily brief)
    python tools/deadlines.py decide TASK_ID accept|decline [DATE]

An undated task has no deadline and is never shown as late. Mantis only suggests one, with the
reason, and the owner accepts, changes or declines it. A declined suggestion is not offered again
unless its reason changes. Free rules (code, no AI):
  1. dependency: the task matches a dated next step on a card -> the working day before it
  2. away:       the owner is away soon and the task is the owner's own -> the last working day before
  3. meeting:    the task names someone the owner meets regularly -> the day of that meeting
Claude adds a fourth kind while it prepares the daily brief: dates stated in sources ("by end of
month", "before go-live"), saved with `add`. Stored in mantis/tasks/deadlines.json.
"""
import hashlib, json, os, re, sys
from datetime import date, timedelta
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
FILE = ROOT / "mantis" / "tasks" / "deadlines.json"
MAX_PER_DAY = 3
STOP = set("the a an and or to of for on in with by from at is be this that it its your my our their get send ask check review".split())
RANK = {"dependency": 0, "away": 1, "source": 2, "meeting": 3}


def _read():
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"decided": {}, "claude": []}


def _write(d):
    FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, FILE)


def words(s):
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower()) if len(w) > 2 and w not in STOP}


def key(s):
    return hashlib.sha1(f"{s['task_id']}|{s['date']}|{s['kind']}".encode()).hexdigest()[:12]


def compute(today=None):
    import tasks_store, steps, schedule, people
    today = today or date.today()
    st = tasks_store.load()
    open_ = [t for t in st["tasks"] if t["status"] in ("todo", "blocked") and not t["due"]]
    out = []
    dated = [s for s in steps.load() if s["due"] and not s["done"]]
    for t in open_:
        tw = words(t["title"])
        # 1. dependency on a dated card step
        for s in dated:
            if len(tw & words(s["step"])) >= 2:
                d = schedule.working_day_before(date.fromisoformat(s["due"]))
                if d >= today:
                    out.append({"task_id": t["id"], "title": t["title"], "date": d.isoformat(), "kind": "dependency",
                                "why": f"\"{s['step']}\" on {s['card_title']} is due {s['due']}."})
                break
        # 2. owner away soon: own tasks (no one else to ask)
        p = schedule.next_away(today)
        if p and not t["contact"] and t["priority"] in ("high", "medium"):
            start = date.fromisoformat(p["start"])
            if today < start <= today + timedelta(days=21):
                d = max(schedule.working_day_before(start), today)   # leaving tomorrow: today is the last chance
                if True:
                    out.append({"task_id": t["id"], "title": t["title"], "date": d.isoformat(), "kind": "away",
                                "why": f"You're away from {start.strftime('%a %d %b')} and this one needs you."})
        # 3. a regular meeting with the person named
        if t["contact"]:
            ms = schedule.meetings_with(t["contact"])
            nds = [x for x in (schedule.next_date(m, today) for m in ms) if x]
            if nds:
                d = min(nds)
                m = ms[[schedule.next_date(x, today) for x in ms].index(d)]
                out.append({"task_id": t["id"], "title": t["title"], "date": d.isoformat(), "kind": "meeting",
                            "why": f"You meet {t['contact']} at \"{m['name']}\" on {d.strftime('%a %d %b')}."})
    data = _read()
    ids = {t["id"]: t for t in open_}
    out += [dict(c, title=ids[c["task_id"]]["title"]) for c in data.get("claude", []) if c["task_id"] in ids and c["date"] >= today.isoformat()]
    best = {}
    for s in sorted(out, key=lambda s: RANK.get(s["kind"], 9)):
        s["key"] = key(s)
        if data["decided"].get(s["task_id"], {}).get("key") == s["key"]:
            continue   # the owner already answered this exact suggestion
        best.setdefault(s["task_id"], s)
    return sorted(best.values(), key=lambda s: (RANK.get(s["kind"], 9), s["date"]))[:MAX_PER_DAY]


def add(task_id, d, why):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
        raise ValueError("date must be YYYY-MM-DD")
    data = _read()
    data["claude"] = [c for c in data.get("claude", []) if c["task_id"] != task_id] + [
        {"task_id": task_id, "date": d, "kind": "source", "why": str(why)[:300]}]
    _write(data)


def decide(task_id, action, d=""):
    """accept: set the task's due date (d or the suggested one); decline: never offer this one again."""
    import tasks_store
    sug = next((s for s in compute() if s["task_id"] == task_id), None)
    data = _read()
    data["decided"][task_id] = {"key": sug["key"] if sug else "", "action": action, "on": date.today().isoformat()}
    _write(data)
    if action == "accept":
        when = d or (sug or {}).get("date", "")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", when):
            raise ValueError("no date to set")
        st = tasks_store.load()
        for t in st["tasks"]:
            if t["id"] == task_id:
                t["due"] = when
        tasks_store.save(st["tasks"], st["rev"])
        return when
    return ""


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        for s in compute():
            print(f"{s['task_id']}: {s['title']} -> {s['date']} ({s['kind']}): {s['why']}")
    elif a[0] == "add" and len(a) >= 4:
        add(a[1], a[2], a[3])
        print("Saved.")
    elif a[0] == "decide" and len(a) >= 3:
        print(decide(a[1], a[2], a[3] if len(a) > 3 else "") or "Declined.")
    else:
        sys.exit(__doc__)
