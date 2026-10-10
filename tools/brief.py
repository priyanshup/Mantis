"""Meeting briefs (MANTIS-IMP-037): "I'm meeting Sam now, what should I discuss?"

    python tools/brief.py gather "Sam"              everything known for that person or meeting, compact (free)
    python tools/brief.py gather "Vendor weekly sync"
    python tools/brief.py save FILE                 save a brief Claude wrote (JSON, format below)
    python tools/brief.py status [DAYS]             what changed on followed cards in the last DAYS (default 7), for a status update (free)
    python tools/brief.py show "Sam"                the latest brief for that person

Code gathers the facts (no AI): the person's role, briefing style and notes; open follow-ups with
them (raise and wait, with age and how often raised); card steps waiting on them; the owner's own
steps on the cards they share; tasks naming them; decisions and card changes since the last brief;
open questions on shared cards and the questions they can answer anywhere; dates in the next two weeks. Claude then writes short bullets.

Brief JSON (save):
  {"for": "Sam Lee", "kind": "meeting", "title": "1-1 with Sam",
   "sections": [{"name": "Update him on", "bullets": [{"text": "...", "detail": "...", "source": "...",
                 "card": "card-slug", "followup": "<follow-up id or empty>"}]}, ...],
   "new_followups": [{"topic": "...", "detail": "...", "card": "...", "kind": "raise"}]}
Section names: "Update them on", "Ask them", "Decide together", "Chase", "Personal" (use the
person's pronoun-free name, e.g. "Update Sam on"). new_followups become open follow-ups so
anything not closed in the meeting is there next time.
"""
import json, re, sys
from datetime import date, timedelta
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
K = ROOT / "mantis" / "knowledge"
DIR = ROOT / "mantis" / "tasks" / "briefs"


def _json(p, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def latest(for_name, kind=None):
    if not DIR.exists():
        return None
    for p in sorted(DIR.glob("*.json"), reverse=True):
        b = _json(p, {})
        if b.get("for") == for_name and (not kind or b.get("kind") == kind):
            return dict(b, id=p.stem)
    return None


def decisions_since(since):
    out = []
    for p in sorted((K / "registers" / "decisions").glob("MANTIS-DEC-*.md")):
        t = p.read_text(encoding="utf-8")
        d = (re.search(r"\*\*Date:\*\*\s*(\S+)", t) or [None, ""])[1]
        if d >= since:
            out.append((d, (re.search(r"\*\*Decision:\*\*\s*(.+)", t) or [None, ""])[1][:220]))
    return out


def card_lines(slugs):
    """Status and freshness of the named cards, from the generated map."""
    rows = []
    feats = {f["slug"]: f for f in _json(K / "map" / "features.json", []) if isinstance(f, dict) and "slug" in f} if (K / "map" / "features.json").exists() else {}
    cards = (K / "map" / "cards.md").read_text(encoding="utf-8") if (K / "map" / "cards.md").exists() else ""
    for s in slugs:
        m = re.search(rf"(?m)^{re.escape(s)} \| (\w+) \| (\d+) \| (\d+)", cards)
        f = feats.get(s, {})
        rows.append(f"{s}: status {f.get('status', '?')}" + (f" ({f.get('status_note')})" if f.get("status_note") else "")
                    + (f"; {m.group(3)} source(s) not yet in its summary" if m and m.group(3) != "0" else ""))
    return rows


def open_items(slugs, person=None):
    items = _json(K / "map" / "open-items.json", [])
    out = []
    for o in items:
        if set(o.get("features", [])) & set(slugs):
            out.append(o)
    if person:   # items whose notes say to ask this person float up
        out.sort(key=lambda o: person.split()[0].lower() not in json.dumps(o).lower())
    return out[:10]


def gather(who):
    import people, followups, steps, schedule, tasks_store
    today = date.today()
    ps = people.load()
    person = people.find(who, ps)
    meeting = None if person else schedule.find_meeting(who)   # a person's name wins; otherwise a meeting name
    if not person and not meeting:
        sys.exit(f"Nobody called '{who}' in people.md and no meeting by that name. Add them on the People page or with tools/schedule.py.")
    attendees = [people.find(a, ps) or {"name": a, "role": "", "briefing": "", "notes": "", "aliases": []} for a in (meeting["attendees"] if meeting else [])]
    if person and person not in attendees:
        attendees = [person] + attendees
    names = [a["name"] for a in attendees]
    title = meeting["name"] if meeting and not person else (f"Meeting with {person['name']}" if person else who)
    print(f"BRIEF for: {title}. Today {today.isoformat()} ({today.strftime('%A')}).")
    if meeting:
        nd = schedule.next_date(meeting, today)
        print(f"Meeting: {meeting['name']}, {meeting['day']} {meeting['time']}, attendees {', '.join(meeting['attendees'])}; purpose: {meeting['purpose'] or '-'}; next {nd}.")
    shared_cards = set(meeting["cards"] if meeting else [])
    last = latest(names[0]) if names else None
    since = (last or {}).get("date", (today - timedelta(days=14)).isoformat())
    print(f"Last brief for {names[0] if names else who}: {last['date'] if last else 'none'}; changes counted since {since}.")
    for a in attendees:
        print(f"\nPERSON {a['name']}: role {a.get('role') or '-'}.")
        if a.get("briefing"):
            print(f"  Briefing style: {a['briefing']}")
        if a.get("notes"):
            print(f"  Owner's notes: {a['notes']}")
        for m in schedule.meetings_with(a["name"]):
            print(f"  Regular meeting: {m['name']} ({m['day']}), next {schedule.next_date(m, today)}")
            shared_cards |= set(m["cards"])
        g = followups.grouped().get(a["name"], {"items": [], "steps": []})
        for f in g["items"]:
            age = (today - date.fromisoformat(f["created"])).days
            shared_cards |= {f["card"]} if f["card"] else set()
            print(f"  FOLLOW-UP [{f['id']}] {f['kind']}: {f['topic']} (open {age} days, raised {len(f['raised'])}x"
                  + (f", last {f['raised'][-1]}" if f["raised"] else "") + (f", chase {f['chase']}" if f["chase"] else "")
                  + (f", card {f['card']}" if f["card"] else "") + ")" + (f" - {f['detail'][:200]}" if f["detail"] else ""))
        for s in g["steps"]:
            shared_cards.add(s["card"])
            print(f"  WAITING ON THEM (card {s['card']}): {s['step']} - status {s['status'] or 'open'}" + (f", due {s['due']}" if s["due"] else ""))
        st = tasks_store.load()
        for t in st["tasks"]:
            if t["status"] in ("todo", "blocked") and t["contact"] and people.find(t["contact"], ps) is a if people.find(t["contact"], ps) else False:
                print(f"  TASK naming them: {t['title']}" + (f" (due {t['due']})" if t["due"] else "") + (f" - note: {t['comments'][-1]['text'][:150]}" if t["comments"] else ""))
        done_recent = [f for f in followups.for_person(a["name"], include_done=True) if f["status"] == "done" and f["done_at"] >= since]
        for f in done_recent:
            print(f"  Closed since last brief: {f['topic']}")
    # Questions this person can answer (MANTIS-IMP-046), whatever card they sit on
    asked = [o for o in _json(K / "map" / "open-items.json", []) if (o.get("ask") or {}).get("name") in names]
    for o in sorted(asked, key=lambda o: o["ask"]["how"] != "named"):
        print(f"QUESTION THEY CAN ANSWER ({'named in a note' if o['ask']['how'] == 'named' else 'suggested: ' + o['ask']['why'].lower()}) "
              f"[{o['status']}] on {', '.join(o['features']) or 'no card'}: {o['topic'][:170]}")
    asked_ids = {o["id"] for o in asked}
    mine = [s for s in steps.load() if not s["done"] and people.is_owner(s["who"]) and s["card"] in shared_cards]
    for s in mine:
        print(f"OWNER'S OWN STEP (card {s['card']}): {s['step']} - {s['status'] or 'open'}" + (f", due {s['due']}" if s["due"] else ""))
    if not shared_cards:   # nothing shared (a manager, a 1-1): the owner's followed cards give the status picture
        shared_cards = set(_json(K / "focus.json", {}).get("following", [])[:10])
        print("\nNo cards shared with them; the owner's followed cards follow (status picture for a 1-1).")
    if shared_cards:
        print("\nSHARED CARDS: " + "; ".join(card_lines(sorted(c for c in shared_cards if c))))
        for o in [x for x in open_items(sorted(shared_cards), names[0] if names else None) if x["id"] not in asked_ids]:
            print(f"  OPEN QUESTION [{o['status']}] on {', '.join(o['features'])}: {o['topic'][:170]}")
    for d, txt in decisions_since(since):
        print(f"DECISION {d}: {txt}")
    away = schedule.next_away(today)
    if away:
        print(f"OWNER AWAY: {away['start']} to {away['end']}, cover {', '.join(away['cover']) or 'not set'}.")
    print("\nWrite the brief as JSON (format in tools/brief.py) with sections like 'Update <first name> on', 'Ask <first name>', "
          "'Decide together', 'Chase', 'Personal'. One short line per bullet, a 'detail' with the background and a 'source' in words. "
          "Order by what matters most to this person (briefing style). Put new topics worth tracking in new_followups. Save with: python tools/brief.py save <file>")


def gather_status(days=7):
    """Weekly status update (MANTIS-IMP-028): what actually changed on the owner's followed cards."""
    import steps, followups, schedule
    today = date.today()
    since = (today - timedelta(days=days)).isoformat()
    focus = _json(K / "focus.json", {}).get("following", [])
    print(f"STATUS UPDATE for the week to {today.isoformat()} (changes since {since}). Followed cards: {', '.join(focus) or 'none'}.")
    print("\nCARDS:")
    for line in card_lines(focus):
        print("  " + line)
    # What changed comes from What's new (map/changes.json, MANTIS-IMP-066): one source for both, so they never disagree
    ch = _json(K / "map" / "changes.json", {})
    titles = {c["slug"]: c["title"] for c in _json(K / "map" / "features.json", []) + _json(K / "map" / "topics.json", [])}
    mine = {titles[s] for s in focus if s in titles}
    label = {"source": "NEW SOURCE", "question": "NEW QUESTION", "assumption": "NEW ASSUMPTION", "answer": "ANSWERED",
             "likely": "LIKELY ANSWER", "closed": "CLOSED", "possible": "POSSIBLE CONFLICT", "conflict": "NEW CONFLICT",
             "decision": "DECISION", "stage": "STAGE CHANGED", "page": "UPDATED", "jira": "MOVED TO JIRA", "diagram": "NEW DIAGRAM"}
    events = [e for e in ch.get("events", []) if e["date"] >= since and e["kind"] in label]
    answered = {e["title"] for e in events if e["kind"] == "answer"}
    events = [e for e in events if not (e["kind"] == "closed" and e["title"] in answered)]   # one line per answered question
    print(f"\nCHANGES IN THE WINDOW ({len(events)}; cards you follow first; summary refreshes left out):")
    for e in sorted(events, key=lambda e: (e.get("card") not in mine and e["title"] not in mine, e["date"])):
        print(f"  {e['date']} {label[e['kind']]}: {e['title']}" + (f" ({e['detail'][:120]})" if e.get("detail") else "")
              + (f" [{e['card']}]" if e.get("card") and e["card"] != e["title"] else ""))
    for st in steps.load():
        m = re.search(r"(\d{4}-\d{2}-\d{2})", st["status"])
        if st["done"] and m and m.group(1) >= since:
            print(f"STEP DONE {m.group(1)} ({st['card']}): {st['step']}")
        elif not st["done"]:
            print(f"STEP OPEN ({st['card']}): {st['step']} - {st['who']} - {st['status'] or 'open'}" + (f", due {st['due']}" if st["due"] else ""))
    for person, g in followups.grouped(include_steps=False).items():
        for f in g["items"]:
            print(f"WAITING/RAISE {person}: {f['topic']} (open since {f['created']})")
    for f in followups.load()["items"]:
        if f["status"] == "done" and f["done_at"] >= since:
            print(f"CLOSED {f['done_at']} with {f['person']}: {f['topic']}")
    for o in open_items(focus):
        if o["status"] != "Open":
            print(f"DECISION NEEDED [{o['status']}] {', '.join(o['features'][:3])}: {o['topic'][:160]}")
    away = schedule.next_away(today)
    if away:
        print(f"OWNER AWAY {away['start']} to {away['end']}, cover {', '.join(away['cover']) or 'not set'}.")
    import readiness   # outcomes, not only delivery (MANTIS-IMP-076)
    for r in readiness.scan():
        if r["slug"] in focus and r["state"] in ("reviewed", "reviewed-no-data", "review-overdue", "measuring", "live-no-review"):
            print(f"OUTCOME ({r['slug']}): {readiness.STATES[r['state']][0]}: {r['why']}")
    print("\nWrite a short status update as JSON (format in tools/brief.py) with \"for\": \"Weekly status\", \"kind\": \"status\" and sections "
          "'Done this week', 'In progress', 'Blocked or at risk', 'Decisions needed', 'Outcomes' (only if OUTCOME lines exist; "
          "never call a feature a success without a measured result), 'Next week'. One line per bullet, plain words, "
          "no internal IDs; detail and source in words. Save with: python tools/brief.py save <file>")


def save(path, kind_default="meeting"):
    import people, followups
    b = json.loads(Path(path).read_text(encoding="utf-8"))
    who = str(b.get("for", "")).strip()
    if not who or not isinstance(b.get("sections"), list):
        raise ValueError("a brief needs 'for' and 'sections'")
    p = people.find(who)
    name = p["name"] if p else who
    kind = b.get("kind") if b.get("kind") in ("meeting", "handover", "status") else kind_default
    clean = {"for": name, "kind": kind, "date": date.today().isoformat(), "title": str(b.get("title", ""))[:120] or name,
             "sections": [{"name": str(s.get("name", ""))[:60], "bullets": [
                 {"text": str(x.get("text", ""))[:400], "detail": str(x.get("detail", ""))[:2500], "source": str(x.get("source", ""))[:200],
                  "card": str(x.get("card", ""))[:80], "followup": str(x.get("followup", ""))[:20]}
                 for x in s.get("bullets", [])[:25] if x.get("text")]} for s in b["sections"][:10]],
             "away": b.get("away") if kind == "handover" else None}
    for f in b.get("new_followups", [])[:10]:
        if f.get("topic"):
            fu = followups.add(name, f["topic"], f.get("detail", ""), f.get("card", ""), f.get("kind", "raise"), "", f"From the {kind} brief, {clean['date']}")
            print(f"Follow-up added: {fu['topic']}")
    DIR.mkdir(parents=True, exist_ok=True)
    out = DIR / f"{clean['date']}-{people.slug(name)}-{kind}.json"
    out.write_text(json.dumps(clean, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Saved the {kind} brief for {name}: it shows on the Today page.")
    return clean


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "status":
        gather_status(int(a[1]) if len(a) > 1 and a[1].isdigit() else 7)
    elif len(a) >= 2 and a[0] == "gather":
        gather(" ".join(a[1:]))
    elif len(a) >= 2 and a[0] == "save":
        save(a[1])
    elif len(a) >= 2 and a[0] == "show":
        import people
        p = people.find(" ".join(a[1:]))
        b = latest(p["name"] if p else " ".join(a[1:]))
        print(json.dumps(b, indent=1, ensure_ascii=False) if b else "No brief yet.")
    else:
        sys.exit(__doc__)
