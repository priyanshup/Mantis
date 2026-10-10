"""Add to or read the owner's task list from the command line (Claude uses this on request).

    python tools/tasks.py list                          today's open tasks, carry-overs and reminders
    python tools/tasks.py add "Title" [--due D] [--remind D] [--day D] [--contact NAME] [--priority high|medium|low] [--estimate MIN] [--note TEXT]
    python tools/tasks.py suggest FILE                  set today's brief suggestions from a JSON list (see docs/rules/WORKFLOW.md)
    python tools/tasks.py context                       compact input for writing today's suggestions

Dates are YYYY-MM-DD. --day plans it for that date (default: today; "backlog" for no date).
"""
import json, sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).parent))
import tasks_store as T


def arg(name, default=""):
    a = sys.argv
    return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default


def cmd_list():
    st, d = T.load(), T.today()
    open_ = [t for t in st["tasks"] if t["status"] not in ("done", "deleted")]
    rows = sorted(open_, key=lambda t: t["order"])
    print(f"Today {d}: {sum(1 for t in rows if t['day'] == d)} planned, {sum(1 for t in rows if t['day'] and t['day'] < d)} carried over, "
          f"{sum(1 for t in rows if t['remind_on'] == d)} reminders, {sum(1 for t in rows if t['status'] == 'blocked')} blocked")
    for t in rows:
        tag = "carried over" if t["day"] and t["day"] < d else (t["day"] or "backlog")
        print(f"- [{t['status']}] {t['title']} ({t['priority'] or '-'}, {t['estimate']} min, {tag}"
              + (f", due {t['due']}" if t["due"] else "") + (f", ask {t['contact']}" if t["contact"] else "")
              + (f", remind {t['remind_on']}" if t["remind_on"] else "") + ")")


def cmd_add(title):
    day = arg("--day", T.today())
    t = {"title": title, "due": arg("--due"), "remind_on": arg("--remind"), "day": "" if day == "backlog" else day,
         "contact": arg("--contact"), "priority": arg("--priority"), "estimate": arg("--estimate", "0"), "source": "Added by Mantis"}
    if arg("--note"):
        t["comments"] = [{"at": T.today(), "text": arg("--note")}]
    if t["remind_on"] and not arg("--day"):
        t["day"] = t["remind_on"]   # a reminder for a later day lands on that day
    print("Added:", T.add(t)["title"])


def cmd_suggest(path):
    items = json.loads(Path(path).read_text(encoding="utf-8"))
    clean = []
    for i, s in enumerate(items[:8]):
        clean.append({"id": f"{T.today()}-{i + 1}", "title": str(s.get("title", ""))[:200], "why": str(s.get("why", ""))[:600],
                      "who": str(s.get("who", ""))[:120], "say": str(s.get("say", ""))[:1200],
                      "questions": [str(q)[:300] for q in s.get("questions", [])[:6]],
                      "estimate": int(s.get("estimate", 15) or 15), "priority": s.get("priority", "medium") if s.get("priority") in T.PRIO else "medium",
                      "source": str(s.get("source", ""))[:160]})
    T._write(T.SUGGEST, {"date": T.today(), "items": clean})
    print(f"Saved {len(clean)} suggestion(s) for {T.today()}.")


def cmd_context():
    """Everything needed to write the daily suggestions, in one short read."""
    st, d = T.load(), T.today()
    root = Path(__file__).resolve().parent.parent / "mantis" / "knowledge"
    focus = json.loads((root / "focus.json").read_text(encoding="utf-8")) if (root / "focus.json").exists() else {}
    items = json.loads((root / "map" / "open-items.json").read_text(encoding="utf-8")) if (root / "map" / "open-items.json").exists() else []
    follow = set(focus.get("following", []))
    print(f"Date {d}. Followed cards: {', '.join(sorted(follow)) or 'none'}.")
    open_ = [x for x in st["tasks"] if x["status"] in ("todo", "blocked")]
    for label, rows in (("Blocked", [x for x in open_ if x["status"] == "blocked"]),
                        ("Due or overdue", [x for x in open_ if x["due"] and x["due"] <= d]),
                        ("Reminders today", [x for x in open_ if x["remind_on"] == d]),
                        ("Carried over", [x for x in open_ if x["day"] and x["day"] < d])):
        for x in rows:
            note = x["comments"][-1]["text"][:160] if x["comments"] else ""
            print(f"{label}: {x['title']}" + (f" (ask {x['contact']})" if x["contact"] else "") + (f" - last note: {note}" if note else ""))
    mine = [o for o in items if o["kind"] in ("gap", "conflict", "assumption") and (set(o["features"]) & follow)]
    waiting = [o for o in mine if o["status"] != "Open"]
    for o in (waiting + [o for o in mine if o["status"] == "Open"])[:15]:
        print(f"Open item {o['id']} [{o['status']}] on {', '.join(o['features'])}: {o['topic'][:150]}")
    # Follow-ups, away nudges and undated tasks (MANTIS-IMP-020, 038, 041)
    import followups, away, deadlines
    from datetime import date as _date
    for person, g in followups.grouped().items():
        for f in g["items"]:
            age = (_date.today() - _date.fromisoformat(f["created"])).days
            due_chase = f["chase"] and f["chase"] <= d
            print(f"Follow-up with {person} ({f['kind']}, open {age} days{', CHASE TODAY' if due_chase else ''}): {f['topic']}")
        for s in g["steps"]:
            print(f"Waiting on {person} ({s['card']}): {s['step']} - {s['status'] or 'open'}")
    sc = away.scan(quiet=True)
    if sc and sc["nudge"]:
        p = sc["period"]
        print(f"AWAY SOON: {p['start']} to {p['end']}, cover {', '.join(p['cover']) or 'NOT SET'}, {sc['working_days']} working day(s) left.")
        for k, dd, t in sc["before"]:
            print(f"  Before you go ({k}): {t}" + (f" (due {dd})" if dd else ""))
        for k, dd, t in sc["within"]:
            print(f"  While away {dd} ({k}): {t}")
    undated = [x for x in open_ if not x["due"]]
    if undated:
        print("Undated open tasks (if a source states a date for one, save it: python tools/deadlines.py add TASK_ID YYYY-MM-DD \"why\"):")
        for x in undated[:15]:
            print(f"  {x['id']}: {x['title']}")
    for s in deadlines.compute():
        print(f"Suggested deadline (shown on Today): {s['title']} -> {s['date']} ({s['why']})")
    print("Write up to 5 suggestions (who to contact, what to say, questions to ask) and save them with: python tools/tasks.py suggest <file>")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "list":
        cmd_list()
    elif a[0] == "add" and len(a) > 1:
        cmd_add(a[1])
    elif a[0] == "context":
        cmd_context()
    elif a[0] == "suggest" and len(a) > 1:
        cmd_suggest(a[1])
    else:
        sys.exit(__doc__)
