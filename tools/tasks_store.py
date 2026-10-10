"""The owner's task list (MANTIS-IMP-018): storage, validation and the daily rollover.

Shared by tools/serve.py (the site's Today page) and tools/tasks.py (Claude adds tasks and
reminders on request). Data lives in mantis/tasks/:
    tasks.json        {"rev": n, "rollover": "YYYY-MM-DD", "dismissed": [...], "tasks": [...]}
    archive.json      done tasks from earlier days, deleted 7 days after archiving
    suggestions.json  Claude's daily nudges for the brief (written by Claude, read by the page)

A task: id, title, status (todo | blocked | done | parked | deleted), priority (high | medium | low | ""),
estimate (minutes), day (the date it is planned for, "" for the backlog), due, remind_on,
contact (who to reach out to), comments [{at, text}], created, done_at, order (rank, low = top),
was (the status before deletion) and deleted_at. Deleted tasks stay restorable for 7 days.
"""
import json, os, re, time, uuid
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "mantis" / "tasks"
TASKS, ARCHIVE, SUGGEST = DIR / "tasks.json", DIR / "archive.json", DIR / "suggestions.json"
LOCK = DIR / ".lock"
STATUS = {"todo", "blocked", "done", "parked", "deleted"}
PRIO = {"high", "medium", "low", ""}
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
KEEP_DAYS = 7


def today():
    return date.today().isoformat()


def _read(p, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write(p, data):
    DIR.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def _locked(fn):
    DIR.mkdir(parents=True, exist_ok=True)
    for _ in range(100):
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if time.time() - LOCK.stat().st_mtime > 30:
                LOCK.unlink(missing_ok=True)
            time.sleep(0.05)
    else:
        raise OSError("task list is busy; try again")
    try:
        return fn()
    finally:
        os.close(fd)
        LOCK.unlink(missing_ok=True)


def clean_task(t):
    """Validate one task coming from the page or the CLI; drop anything unexpected."""
    s = lambda v, n: " ".join(str(v or "").split())[:n]
    d = lambda v: str(v) if DATE.match(str(v or "")) else ""
    out = {"id": s(t.get("id"), 40) or uuid.uuid4().hex[:10], "title": s(t.get("title"), 300),
           "status": t.get("status") if t.get("status") in STATUS else "todo",
           "priority": t.get("priority") if t.get("priority") in PRIO else "",
           "estimate": max(0, min(int(t.get("estimate") or 0), 24 * 60)) if str(t.get("estimate") or "0").isdigit() else 0,
           "day": d(t.get("day")), "due": d(t.get("due")), "remind_on": d(t.get("remind_on")),
           "contact": s(t.get("contact"), 120), "created": d(t.get("created")) or today(),
           "done_at": d(t.get("done_at")), "order": float(t.get("order") or 0),
           "source": s(t.get("source"), 120), "deleted_at": d(t.get("deleted_at")),
           "was": t.get("was") if t.get("was") in STATUS - {"deleted"} else "",
           "comments": [{"at": s(c.get("at"), 20), "text": str(c.get("text") or "")[:2000]} for c in (t.get("comments") or [])[:100] if isinstance(c, dict)]}
    if not out["title"]:
        raise ValueError("a task needs a title")
    return out


def rollover(state):
    """Once a day: archive tasks done before today, drop archive entries older than 7 days, and
    purge tasks deleted more than 7 days ago."""
    if state.get("rollover") == today():
        return state
    keep, moved = [], []
    cutoff = (date.today() - timedelta(days=KEEP_DAYS)).isoformat()
    for t in state["tasks"]:
        if t["status"] == "deleted" and (t.get("deleted_at") or "") < cutoff:
            continue
        (moved if t["status"] == "done" and (t.get("done_at") or "") < today() else keep).append(t)
    arch = _read(ARCHIVE, [])
    arch += [dict(t, archived=today()) for t in moved]
    arch = [a for a in arch if a.get("archived", "") >= cutoff]
    _write(ARCHIVE, arch)
    state.update(tasks=keep, rollover=today())
    return state


def load():
    def go():
        st = _read(TASKS, {"rev": 0, "rollover": "", "dismissed": [], "tasks": []})
        before = st.get("rollover")
        st = rollover(st)
        if st.get("rollover") != before:
            st["rev"] = st.get("rev", 0) + 1
            _write(TASKS, st)
        return st
    return _locked(go)


def save(tasks, rev, dismissed=None):
    """Replace the list if `rev` matches (another tab may have saved meanwhile). Returns the new state."""
    def go():
        st = _read(TASKS, {"rev": 0, "rollover": today(), "dismissed": [], "tasks": []})
        if int(rev) != st.get("rev", 0):
            raise RuntimeError("conflict")
        clean = []
        for t in tasks[:2000]:
            try:
                clean.append(clean_task(t))
            except (ValueError, TypeError, AttributeError):
                pass   # a blank or broken row is dropped, never the whole list
        st.update(tasks=clean, rev=st.get("rev", 0) + 1)
        if dismissed is not None:
            st["dismissed"] = [str(x)[:60] for x in dismissed][-500:]
        _write(TASKS, rollover(st))
        return st
    return _locked(go)


def add(task):
    """Append one task at the top of its day (used by tools/tasks.py)."""
    def go():
        st = _read(TASKS, {"rev": 0, "rollover": today(), "dismissed": [], "tasks": []})
        t = clean_task(task)
        t["order"] = min([x["order"] for x in st["tasks"]] + [1]) - 1
        st["tasks"].append(t)
        st["rev"] = st.get("rev", 0) + 1
        _write(TASKS, st)
        return t
    return _locked(go)


def suggestions():
    s = _read(SUGGEST, {"date": "", "items": []})
    return s if s.get("date") == today() else {"date": s.get("date", ""), "items": [], "stale": True}


def archived():
    return _read(ARCHIVE, [])
