"""Live data for the Today and People pages: follow-ups, suggested deadlines, meetings, away, briefs.

Used by tools/serve.py (GET /api/extra, POST /api/followups, /api/deadlines, /api/schedule). The
data lives in mantis/tasks/ (followups.json, deadlines.json, meetings.json, away.json, briefs/)
and is read fresh on every request, so the page never needs a rebuild to show it.
"""
import json, re, sys
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


AGENDA_CAP = 5   # items per agenda section; the rest is counted, not listed
QUIET = re.compile(r"(no (real |new )?change|nothing (changed|new))", re.I)   # a pull line saying nothing happened


def _qkey(rid):
    """The anchor the Questions page uses for an open item (a hash, so no Mantis ID shows in the address)."""
    import hashlib
    return hashlib.sha1(rid.encode("utf-8")).hexdigest()[:10]


def _who(m):
    return {people.find(a)["name"] if people.find(a) else a for a in m.get("attendees", [])}


def owners(meetings, open_items):
    """Each open question goes on one agenda only (2026-10-31): the meeting with the person named to answer it,
    else the meeting whose subjects match the question's best (shared subjects over all subjects of both, so a
    question about one product goes to that product's sync and one spanning many features to the weekly sync),
    the sooner on a tie. {question id: meeting id}"""
    who = {m["id"]: _who(m) for m in meetings}
    soon = lambda m: m.get("next") or "9999"
    out = {}
    for o in open_items:
        name = (o.get("ask") or {}).get("name")
        cand = [m for m in meetings if name and name in who[m["id"]]]
        if not cand:
            f = set(o.get("features", []))
            score = {m["id"]: len(f & set(m.get("cards", []))) / max(1, len(f | set(m.get("cards", [])))) for m in meetings}
            best = max(score.values(), default=0)
            cand = [m for m in meetings if best and score[m["id"]] == best]
        if cand:
            out[o["id"]] = min(cand, key=soon)["id"]
    return out


def agenda(m, fus, open_items, titles, brief_cards):
    """A regular meeting's agenda, built from what is open (MANTIS-IMP-094): decide, ask, chase, update.
    Each section lists links, never restated text, so one fact has one home (the question, the follow-up).
    `open_items` and `brief_cards` are already narrowed to what this meeting owns (see owners())."""
    who = _who(m)
    cards = set(m.get("cards", []))
    card = lambda o: titles.get(next((s for s in o.get("features", []) if s in cards), ""), "")
    decide = [o for o in open_items if o["status"] != "Open" and set(o.get("features", [])) & cards]
    ask = [o for o in open_items if o["status"] == "Open" and (o.get("ask") or {}).get("name") in who]
    ask.sort(key=lambda o: o["ask"]["how"] != "named")
    q = lambda o: {"text": o["topic"].split(" (MANTIS-")[0][:200], "href": f"questions.html#k={_qkey(o['id'])}", "note": card(o)}
    f = lambda x: {"text": x["topic"], "fu": x["id"], "note": x["person"].split()[0] + (f", chase {x['chase']}" if x.get("chase") else "")}
    mine = [x for p in who for x in fus.get(p, {}).get("items", [])]
    secs = [("Decide", [q(o) for o in decide]),
            ("Ask", [f(x) for x in mine if x["kind"] == "raise"] + [q(o) for o in ask]),
            ("Chase", [f(x) for x in mine if x["kind"] == "wait"]),
            ("Update them on", [{"text": line, "note": c["title"]} for c in brief_cards if c["slug"] in cards for line in c["lines"]
                                if not QUIET.match(line.strip())])]
    if len(cards) <= 3:   # a meeting about one or two subjects: what is still open on them is worth raising too
        seen = {o["id"] for o in decide + ask}
        secs.append(("Still open", [q(o) for o in open_items if o["status"] == "Open" and set(o.get("features", [])) & cards and o["id"] not in seen]))
    return [{"name": n, "items": items[:AGENDA_CAP], "more": max(0, len(items) - AGENDA_CAP)} for n, items in secs if items]


def last_time(m):
    """The meeting's last saved takeaways, each action with its status now."""
    import brief, tasks_store
    t = brief.latest_takeaways(m["name"])
    if not t:
        return None
    tasks = {x["id"]: x for x in tasks_store.load()["tasks"]}
    fus = {x["id"]: x for x in followups.load()["items"]}
    return {"date": t["date"], "decisions": t.get("decisions", []), "notes": t.get("notes", "")[:600],
            "actions": [{"text": a["title"], "who": "You", "state": (tasks.get(a["task"]) or {}).get("status", "done")} for a in t.get("mine", [])]
                       + [{"text": a["topic"], "who": a["person"].split()[0], "state": (fus.get(a["followup"]) or {}).get("status", "removed")}
                          for a in t.get("theirs", [])]}


def payload():
    ps = people.load()
    today = date.today()
    mp = ROOT / "mantis" / "knowledge" / "map"
    read = lambda n: json.loads((mp / n).read_text(encoding="utf-8")) if (mp / n).exists() else []
    open_items = [o for o in read("open-items.json") if o["kind"] in ("gap", "conflict", "assumption")]
    titles = {c["slug"]: c["title"] for c in read("features.json") + read("topics.json")}
    try:
        last = json.loads((ROOT / "mantis" / "tasks" / "pull-brief.json").read_text(encoding="utf-8")).get("last") or {}
    except (OSError, ValueError):
        last = {}
    fus = followups.grouped(include_steps=False)
    ms = []
    for m in schedule.meetings():
        nd = schedule.next_date(m, today)
        ms.append(dict(m, next=nd.isoformat() if nd else "", key=people.slug(m["name"])))
    ms.sort(key=lambda m: m["next"] or "9999")
    owner = owners(ms, open_items)
    for m in ms:   # a change goes to the most specific meeting that covers its card, like a question
        mine_ = lambda slug: min((x for x in ms if slug in x.get("cards", [])), key=lambda x: (len(x.get("cards", [])), x["next"] or "9999"))["id"] == m["id"]
        news = [c for c in last.get("cards", []) if c["slug"] in m.get("cards", []) and mine_(c["slug"])]
        m["agenda"] = agenda(m, fus, [o for o in open_items if owner.get(o["id"]) == m["id"]], titles, news)
        m["last"] = last_time(m)
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
