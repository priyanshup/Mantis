"""Away planner and handover (MANTIS-IMP-038).

    python tools/away.py scan                 what falls inside the next away period, and what needs the owner first (free)
    python tools/away.py gather "Alex"      everything for a handover written for that person (free)
    python tools/away.py save FILE            save a handover Claude wrote (same JSON as tools/brief.py, "kind": "handover")

Away periods live in mantis/tasks/away.json (Today page, or tools/schedule.py add-away). The scan
lists every dated thing inside the window: tasks due or reminded, dated card steps, follow-up
chase dates and recurring meetings; and what is the owner's own to finish before leaving. The
daily brief and the Today page nudge from 5 working days before the start. The handover is the
same facts framed for the recipient's briefing style (people.md): a BA gets steps and contacts,
a senior PO gets decisions and priorities, a manager gets status, risks and escalations.
"""
import json, sys
from datetime import date, timedelta
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
NUDGE_DAYS = 5   # working days before leaving


def working_days_until(start, today):
    n, d = 0, today
    while d < start:
        if d.weekday() < 5:
            n += 1
        d += timedelta(days=1)
    return n


def scan(today=None, quiet=False):
    import schedule, steps, followups, tasks_store, people
    today = today or date.today()
    p = schedule.next_away(today)
    if not p:
        if not quiet:
            print("No away period planned. Add one on the Today page or: python tools/schedule.py add-away START END --cover NAME")
        return None
    start, end = date.fromisoformat(p["start"]), date.fromisoformat(p["end"])
    inside = lambda d: d and start.isoformat() <= d <= end.isoformat()
    within, before = [], []
    st = tasks_store.load()
    for t in st["tasks"]:
        if t["status"] not in ("todo", "blocked"):
            continue
        if inside(t["due"]) or inside(t["remind_on"]) or inside(t["day"]):
            within.append(("task", t["due"] or t["remind_on"] or t["day"], t["title"] + (f" (ask {t['contact']})" if t["contact"] else "")))
        own = not t["contact"]
        if own and ((t["due"] and t["due"] <= end.isoformat()) or t["priority"] == "high"):
            before.append(("task", t["due"], t["title"]))
    for s in steps.load():
        if s["done"]:
            continue
        if inside(s["due"]):
            within.append(("step", s["due"], f"{s['card_title']}: {s['step']} ({s['who']})"))
        if people.is_owner(s["who"]):
            before.append(("step", s["due"], f"{s['card_title']}: {s['step']}"))
    for person, g in followups.grouped(include_steps=False).items():
        for f in g["items"]:
            if inside(f["chase"]):
                within.append(("chase", f["chase"], f"Chase {person}: {f['topic']}"))
    for m in schedule.meetings():
        d = start
        while d <= end:
            if d.weekday() == schedule.DAYS.index(m["day"][:3].lower()):
                within.append(("meeting", d.isoformat(), f"{m['name']} with {', '.join(m['attendees']) or '-'} (you'll miss it)"))
            d += timedelta(days=1)
    within.sort(key=lambda x: x[1] or "9")
    wd = working_days_until(start, today)
    if not quiet:
        print(f"AWAY {p['start']} to {p['end']} ({'now' if today >= start else f'{wd} working day(s) from now'}); cover: {', '.join(p['cover']) or 'not set'}.")
        print(f"\nINSIDE THE WINDOW ({len(within)}):")
        for k, d, t in within:
            print(f"  {d or '-'} [{k}] {t}")
        print(f"\nNEEDS YOU BEFORE YOU GO ({len(before)}):")
        for k, d, t in before:
            print(f"  [{k}] {t}" + (f" (due {d})" if d else ""))
    return {"period": p, "within": within, "before": before, "working_days": wd, "nudge": wd <= NUDGE_DAYS}   # from 5 working days before until the last day away


def gather(who):
    import people, brief, schedule, steps, followups
    ps = people.load()
    r = people.find(who, ps)
    if not r:
        sys.exit(f"Nobody called '{who}' in people.md. Add them on the People page first.")
    s = scan()
    if not s:
        return
    print(f"\nHANDOVER for {r['name']}: role {r['role'] or '-'}.")
    print(f"  Briefing style: {r['briefing'] or 'not set: write for someone who will act on it (steps, who, when, contacts).'}")
    focus = brief._json(ROOT / "mantis" / "knowledge" / "focus.json", {}).get("following", [])
    print("\nFOLLOWED CARDS (status, then open next steps):")
    for line in brief.card_lines(focus):
        print("  " + line)
    for st in steps.load():
        if not st["done"]:
            print(f"  STEP {st['card']}: {st['step']} | who {st['who']} | {st['status'] or 'open'}" + (f" | due {st['due']}" if st["due"] else ""))
    print("\nWAITING ON OTHERS (follow-ups and steps by person, with how long each usually takes to reply):")
    end = date.fromisoformat(s["period"]["end"])
    risks = []
    for person, g in followups.grouped().items():
        days, n = followups.turnaround(person)
        basis = f"usually {days} working day(s), from {n} closed request(s)" if n else f"no reply history: ASSUMED {days} working days"
        print(f"  {person} ({basis}):")
        for f in g["items"]:
            print(f"    {f['kind']} - {f['topic']}" + (f" (chase {f['chase']})" if f["chase"] else ""))
            if f["kind"] == "wait" and f["chase"] and f["chase"] <= end.isoformat():
                risks.append(f"chase {person} on {f['chase']} about '{f['topic']}' (the owner is away then: the cover chases)")
        for st in g["steps"]:
            print(f"    step on {st['card']} - {st['step']} ({st['status'] or 'open'})" + (f" | due {st['due']}" if st["due"] else ""))
            reply = _add_working(date.today(), days)
            if st["due"] and reply.isoformat() > st["due"]:
                risks.append(f"{st['card']}: '{st['step']}' is due {st['due']}, but {person} usually needs until {reply.isoformat()}")
            elif st["due"] and st["due"] <= end.isoformat():
                risks.append(f"{st['card']}: '{st['step']}' (due {st['due']}, {person}) falls while the owner is away: the cover chases it")
    print("\nAT RISK (from the usual reply times; say how sure, and what the cover should do):")
    for r_ in risks or ["nothing dated depends on someone slower than the time left"]:
        print("  " + r_)
    print("\nOPEN QUESTIONS ON FOLLOWED CARDS (decisions pending first):")
    for o in sorted(brief.open_items(focus), key=lambda o: o["status"] == "Open")[:12]:
        print(f"  [{o['status']}] {', '.join(o['features'][:3])}: {o['topic'][:160]}")
    for d, txt in brief.decisions_since((date.today() - timedelta(days=30)).isoformat()):
        print(f"DECISION {d}: {txt}")
    print("\nCONTACTS:")
    names = {p for p in followups.grouped()} | {a for m in schedule.meetings() for a in m["attendees"]}
    for n in sorted(names):
        p = people.find(n, ps)
        if p:
            print(f"  {p['name']}: {p['role'][:120]}" + (f"; {p['channel']}" if p["channel"] else ""))
    print("\nWrite the handover from mantis/TEMPLATES/handover.md as JSON (format in tools/brief.py, \"kind\": \"handover\"), "
          "framed by the recipient's briefing style. Each fact once, plain words, no internal IDs; then "
          "python tools/repeats.py <file>. Save with: python tools/away.py save <file>")


def _add_working(d, n):
    while n > 0:
        d += timedelta(days=1)
        n -= d.weekday() < 5
    return d


def save(path):
    import brief
    return brief.save(path, kind_default="handover")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "scan":
        scan()
    elif a[0] == "gather" and len(a) > 1:
        gather(" ".join(a[1:]))
    elif a[0] == "save" and len(a) > 1:
        save(a[1])
    else:
        sys.exit(__doc__)
