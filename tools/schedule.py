"""The owner's recurring meetings and away periods (MANTIS-IMP-037, MANTIS-IMP-038).

    python tools/schedule.py meetings                         list meetings with their next date
    python tools/schedule.py add-meeting "Name" DAY [--time HH:MM] [--with "A, B"] [--purpose TEXT] [--cards a,b] [--every 1|2]
    python tools/schedule.py remove-meeting ID
    python tools/schedule.py away                             list away periods
    python tools/schedule.py add-away START END [--cover "A, B"] [--note TEXT]
    python tools/schedule.py remove-away ID

DAY is Mon..Fri (weekly; --every 2 for fortnightly). Stored in mantis/tasks/meetings.json and
mantis/tasks/away.json; the site edits the same files. Dates are YYYY-MM-DD.
"""
import json, os, re, sys, uuid
from datetime import date, timedelta
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
MEET = ROOT / "mantis" / "tasks" / "meetings.json"
AWAY = ROOT / "mantis" / "tasks" / "away.json"
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _read(p, key):
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    d.setdefault(key, [])
    return d


def _write(p, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def iso(d):
    return d.isoformat() if isinstance(d, date) else str(d)


def parse(s):
    return date.fromisoformat(s) if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(s or "")) else None


def working_day_before(d):
    d = d - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


# ---- meetings ----
def meetings():
    return _read(MEET, "meetings")["meetings"]


def next_date(m, after=None):
    """The next date (today included) a recurring meeting happens, skipping the owner's away days."""
    after = after or date.today()
    if m.get("day", "")[:3].lower() not in DAYS:
        return None
    wd = DAYS.index(m["day"][:3].lower())
    d = after + timedelta(days=(wd - after.weekday()) % 7)
    every = int(m.get("every", 1) or 1)
    anchor = parse(m.get("anchor"))
    for _ in range(30):
        fortnight_ok = every == 1 or not anchor or ((d - anchor).days // 7) % every == 0
        if fortnight_ok and not away_on(d):
            return d
        d += timedelta(days=7)
    return None


def add_meeting(name, day, time="", attendees=(), purpose="", cards=(), every=1):
    if day[:3].lower() not in DAYS:
        raise ValueError("day must be Mon..Sun")
    d = _read(MEET, "meetings")
    m = {"id": uuid.uuid4().hex[:6], "name": " ".join(name.split())[:80], "day": day[:3].title(), "time": time[:5],
         "attendees": [a.strip() for a in attendees if a.strip()][:12], "purpose": purpose[:300],
         "cards": [c.strip() for c in cards if c.strip()][:12], "every": max(1, min(int(every or 1), 4)),
         "anchor": date.today().isoformat()}
    d["meetings"].append(m)
    _write(MEET, d)
    return m


def remove(kind, mid):
    p, key = (MEET, "meetings") if kind == "meeting" else (AWAY, "periods")
    d = _read(p, key)
    d[key] = [x for x in d[key] if x["id"] != mid]
    _write(p, d)


def meetings_with(person):
    import people
    p = people.find(person)
    names = {person.lower()} | ({p["name"].lower()} | {a.lower() for a in p["aliases"]} if p else set())
    return [m for m in meetings() if names & {a.lower() for a in m["attendees"]} or (p and any(people.find(a) is p for a in m["attendees"]))]


def find_meeting(q):
    q = q.lower().strip()
    ms = meetings()
    return next((m for m in ms if m["id"] == q or m["name"].lower() == q), None) or next((m for m in ms if q in m["name"].lower()), None)


# ---- away ----
def periods():
    return sorted(_read(AWAY, "periods")["periods"], key=lambda x: x["start"])


def away_on(d):
    return any(parse(p["start"]) <= d <= parse(p["end"]) for p in periods() if parse(p["start"]) and parse(p["end"]))


def next_away(today=None):
    """The current or next away period, or None."""
    today = today or date.today()
    for p in periods():
        if parse(p["end"]) and parse(p["end"]) >= today:
            return p
    return None


def add_away(start, end, cover=(), note=""):
    s, e = parse(start), parse(end)
    if not s or not e or e < s:
        raise ValueError("away needs a start and an end date (YYYY-MM-DD), end on or after start")
    d = _read(AWAY, "periods")
    p = {"id": uuid.uuid4().hex[:6], "start": iso(s), "end": iso(e), "cover": [c.strip() for c in cover if c.strip()][:6], "note": note[:300]}
    d["periods"].append(p)
    _write(AWAY, d)
    return p


def arg(a, name, default=""):
    return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "tools"))
    a = sys.argv[1:]
    if not a or a[0] == "meetings":
        for m in meetings():
            nd = next_date(m)
            print(f"[{m['id']}] {m['name']} ({m['day']} {m['time']}, with {', '.join(m['attendees']) or '-'}): next {nd or '-'}")
    elif a[0] == "add-meeting" and len(a) >= 3:
        m = add_meeting(a[1], a[2], arg(a, "--time"), arg(a, "--with").split(","), arg(a, "--purpose"), arg(a, "--cards").split(","), arg(a, "--every", "1"))
        print(f"Added meeting {m['name']} [{m['id']}], next {next_date(m)}")
    elif a[0] == "away":
        for p in periods():
            print(f"[{p['id']}] {p['start']} to {p['end']}, cover: {', '.join(p['cover']) or '-'} {p['note']}")
    elif a[0] == "add-away" and len(a) >= 3:
        p = add_away(a[1], a[2], arg(a, "--cover").split(","), arg(a, "--note"))
        print(f"Added away {p['start']} to {p['end']} [{p['id']}]")
    elif a[0] in ("remove-meeting", "remove-away") and len(a) >= 2:
        remove(a[0].split("-")[1], a[1])
        print("Removed", a[1])
    else:
        sys.exit(__doc__)
