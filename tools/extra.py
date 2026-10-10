"""Live data for the Today and People pages: follow-ups, suggested deadlines, meetings, away, briefs.

Used by tools/serve.py (GET /api/extra, POST /api/followups, /api/deadlines, /api/schedule). The
data lives in mantis/tasks/ (followups.json, deadlines.json, meetings.json, away.json, briefs/)
and is read fresh on every request, so the page never needs a rebuild to show it.
"""
import json, sys
from datetime import date, timedelta
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import followups, deadlines, people, schedule, steps


def briefs_index():
    d = ROOT / "mantis" / "tasks" / "briefs"
    out = []
    for p in sorted(d.glob("*.json"), reverse=True)[:40] if d.exists() else []:
        try:
            b = json.loads(p.read_text(encoding="utf-8"))
            out.append({"id": p.stem, "for": b.get("for", ""), "kind": b.get("kind", "meeting"), "date": b.get("date", ""),
                        "title": b.get("title", "")})
        except (OSError, ValueError):
            pass
    return out


def payload():
    ps = people.load()
    today = date.today()
    ms = []
    for m in schedule.meetings():
        nd = schedule.next_date(m, today)
        ms.append(dict(m, next=nd.isoformat() if nd else ""))
    away = schedule.next_away(today)
    before = []
    if away:   # what needs the owner before leaving: own open steps, own dated tasks, waiting follow-ups to chase
        import tasks_store
        start = date.fromisoformat(away["start"])
        st = tasks_store.load()
        for t in st["tasks"]:
            if t["status"] in ("todo", "blocked") and not t["contact"] and (not t["due"] or t["due"] <= away["end"]) and (t["due"] or t["priority"] == "high"):
                before.append({"kind": "task", "title": t["title"], "due": t["due"], "id": t["id"]})
        for s in steps.load():
            if not s["done"] and people.is_owner(s["who"]):
                before.append({"kind": "step", "title": s["step"], "due": s["due"], "card": s["card"], "card_title": s["card_title"]})
    return {"today": today.isoformat(),
            "people": [{"name": p["name"], "slug": p["slug"], "role": p["role"], "team": p["team"], "channel": p["channel"],
                        "briefing": p["briefing"], "notes": p["notes"], "aliases": p["aliases"]} for p in ps],
            "followups": followups.grouped(),
            "deadlines": deadlines.compute(),
            "meetings": ms,
            "away": away, "away_periods": schedule.periods(), "before_away": before,
            "briefs": briefs_index()}


def act_followup(b):
    a = str(b.get("action", ""))
    if a == "add":
        return followups.add(b.get("person", ""), b.get("topic", ""), b.get("detail", ""), b.get("card", ""), b.get("kind", "raise"), b.get("chase", ""), "Added on the site")
    followups.update(str(b.get("id", "")), a, b.get("note", ""), **{k: b[k] for k in ("topic", "detail", "chase", "kind") if k in b})
    return {"ok": True}


def act_deadline(b):
    return {"due": deadlines.decide(str(b.get("task_id", "")), "accept" if b.get("action") == "accept" else "decline", str(b.get("date", "")))}


def act_schedule(b):
    a = str(b.get("action", ""))
    split = lambda v: [x.strip() for x in (v if isinstance(v, list) else str(v or "").split(",")) if x.strip()]
    if a == "add-meeting":
        return schedule.add_meeting(str(b.get("name", "")), str(b.get("day", "")), str(b.get("time", "")), split(b.get("attendees")),
                                    str(b.get("purpose", "")), split(b.get("cards")), int(b.get("every", 1) or 1))
    if a == "add-away":
        return schedule.add_away(str(b.get("start", "")), str(b.get("end", "")), split(b.get("cover")), str(b.get("note", "")))
    if a in ("remove-meeting", "remove-away"):
        schedule.remove(a.split("-")[1], str(b.get("id", "")))
        return {"ok": True}
    raise ValueError("unknown action")


def brief(bid):
    p = ROOT / "mantis" / "tasks" / "briefs" / f"{bid}.json"
    if not p.exists() or "/" in bid or "\\" in bid:
        raise ValueError("no such brief")
    return json.loads(p.read_text(encoding="utf-8"))
