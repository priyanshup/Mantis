"""SessionStart hook: start the site and tell Claude what is waiting in the inbox.

Run by .claude/settings.json at the start of every Claude Code session in this project.
Prints one JSON object for Claude Code; never fails the session.
"""
import json, re, subprocess, sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "mantis" / "00_inbox"

try:
    subprocess.run([sys.executable, str(ROOT / "tools" / "serve.py"), "--background"], capture_output=True, timeout=20)
except Exception:
    pass

notes = []
try:  # weekly housekeeping (MANTIS-IMP-015): runs only if the last run was 7+ days ago
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "maintain.py"), "--if-due"], capture_output=True, text=True, timeout=60)
    if r.stdout.strip():
        notes.append("Weekly maintenance ran: " + r.stdout.strip() + " Mention anything marked 'to fix' to the owner.")
except Exception:
    pass
try:
    answers = sorted(INBOX.glob("answers-*.md"))
    n = sum(len(re.findall(r"(?m)^## MANTIS-", p.read_text(encoding="utf-8"))) for p in answers)
    if answers:
        notes.append(f"The owner submitted {n} answer(s) to open items from the site, in {len(answers)} file(s) in "
                     f"mantis/00_inbox ({', '.join(p.name for p in answers)}). Tell the owner at the start of your first reply, "
                     "then process them per docs/rules/workflow/answers.md, before other work unless "
                     "the owner says otherwise.")
    edits = sorted(INBOX.glob("edit-*.md"))
    if edits:
        notes.append(f"The owner saved {len(edits)} edited page(s), epic(s) or story(ies) from the site ({', '.join(p.name for p in edits)}). "
                     "Tell the owner, then apply them per docs/rules/workflow/edits.md (python tools/apply_edits.py).")
    other = [p.name for p in INBOX.iterdir() if p.is_file() and not p.name.startswith(("answers-", "edit-"))] if INBOX.exists() else []
    if other:
        notes.append(f"mantis/00_inbox also holds {len(other)} file(s) waiting for ingest: {', '.join(other[:10])}. Mention them to the owner.")
except Exception as e:
    notes.append(f"Inbox check failed: {e}")

try:  # once a day: Claude prepares the owner's daily brief suggestions for the Today page
    import json as _j
    sug = ROOT / "mantis" / "tasks" / "suggestions.json"
    from datetime import date as _d
    def _something_to_brief():   # MANTIS-IMP-060: no Claude run for the brief on a day with nothing in it
        sys.path.insert(0, str(ROOT / "tools"))
        import tasks_store, followups, schedule, steps, people, readiness
        today = _d.today()
        if any(r["state"] in ("review-overdue", "live-no-review") for r in readiness.scan()):
            return True
        if any(t["status"] in ("todo", "blocked") for t in tasks_store.load()["tasks"]):
            return True
        if any(f["status"] == "open" for g in followups.grouped().values() for f in g["items"]):
            return True
        if any(schedule.next_date(m, today) == today for m in schedule.meetings()):
            return True
        away = schedule.next_away(today)
        if away and (_d.fromisoformat(away["start"]) - today).days <= 7:
            return True
        return any(not s["done"] and people.is_owner(s["who"]) for s in steps.load())
    if (not sug.exists() or _j.loads(sug.read_text(encoding="utf-8")).get("date") != _d.today().isoformat()) and _something_to_brief():
        notes.append("Today's brief has no suggestions yet. Prepare them per docs/rules/workflow/day.md, 'Daily brief': run "
                     "`python tools/tasks.py context`, write up to 5 suggestions, save with `python tools/tasks.py suggest <file>`, "
                     "and tell the owner in one line that today's brief is ready on the Today page.")
except Exception:
    pass

try:  # a recurring meeting today (its regular day or a moved one): prepare its brief once, before it starts
    sys.path.insert(0, str(ROOT / "tools"))
    import schedule, brief
    from datetime import date as _d2
    for m in schedule.meetings():
        if schedule.next_date(m, _d2.today()) == _d2.today() and ((brief.latest(m["name"]) or {}).get("date") != _d2.today().isoformat()):
            notes.append(f"The owner's meeting '{m['name']}' is today{(' at ' + m['time']) if m.get('time') else ''}. Prepare its brief per "
                         f"docs/rules/workflow/day.md, 'Meeting briefs' (python tools/brief.py gather \"{m['name']}\"), save it, and "
                         "give the owner the bullets in your first reply. After the meeting, offer to save the takeaways.")
except Exception:
    pass

out ={"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": " ".join(notes)}} if notes else {}
print(json.dumps(out))
