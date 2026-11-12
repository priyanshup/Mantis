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
    _site_note = ""
except Exception as e:   # the hook must never fail; the owner is told below
    _site_note = f"The site could not be started ({e}). Tell the owner in one line; python tools/serve.py --background retries."

notes = [_site_note] if _site_note else []
try:  # weekly housekeeping (MANTIS-IMP-015): runs only if the last run was 7+ days ago
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "maintain.py"), "--if-due"], capture_output=True, text=True, timeout=60)
    if r.stdout.strip():
        notes.append("Weekly maintenance ran: " + r.stdout.strip() + " Mention anything marked 'to fix' to the owner.")
except Exception as e:   # the hook must never fail
    notes.append(f"Weekly maintenance could not run ({e}).")
try:   # what waits is processed by the next pull, which only the owner starts (MANTIS-IMP-094): mention it, do not start it
    answers = sorted(INBOX.glob("answers-*.md"))
    edits = sorted(INBOX.glob("edit-*.md"))
    other = [p.name for p in INBOX.iterdir() if p.is_file() and not p.name.startswith(("answers-", "edit-", "."))] if INBOX.exists() else []
    n = sum(len(re.findall(r"(?m)^## MANTIS-", p.read_text(encoding="utf-8"))) for p in answers)
    waiting = [f"{n} answer(s) to open questions" if answers else "", f"{len(edits)} page edit(s)" if edits else "",
               f"{len(other)} file(s)" if other else ""]
    if any(waiting):
        notes.append("Waiting in mantis/00_inbox: " + ", ".join(w for w in waiting if w) + ". Tell the owner in one line that the "
                     "next pull processes them (docs/rules/workflow/pull.md); start it only if the owner asks.")
except Exception as e:
    notes.append(f"Inbox check failed: {e}")

try:   # every skill goes through SkillSpector before it is trusted (owner rule, 2026-11-12); this only reads the record, it scans nothing
    sys.path.insert(0, str(ROOT / "tools"))
    import skillscan
    if not skillscan.installed():
        notes.append("SkillSpector is not installed, so skills cannot be checked. Tell the owner in one line; the install command is in tools/skillscan.py.")
    else:
        bad = skillscan.problems()
        if bad:
            notes.append(f"{len(bad)} Claude skill(s) are not cleared by SkillSpector ({', '.join(r['name'] + ': ' + r['state'] for r in bad[:5])}). "
                         "Do not use them. Tell the owner in one line; python tools/skillscan.py scans them.")
except Exception as e:
    notes.append(f"Skill check failed: {e}")

try:   # the owner's data is copied once a day (tools/backup.py); the site server does it too, this covers a day it was not running
    subprocess.run([sys.executable, str(ROOT / "tools" / "backup.py")], capture_output=True, timeout=120)
except Exception as e:   # the hook must never fail
    notes.append(f"The daily backup could not run ({e}). Tell the owner in one line; python tools/backup.py retries.")

try:   # the safety net's last result (tools/guard.py): read only, it runs inside the site server
    import guard
    failing = [m for lvl, m in guard.problems() if lvl == "warn"]
    if failing:
        notes.append("The safety net found problems: " + " ".join(failing)[:500] + " Tell the owner in one line.")
except Exception as e:
    notes.append(f"Safety-net status failed: {e}")

# The daily brief and today's meeting briefs are prepared in the first session of a day only; after that the owner
# asks for them (the owner's choice, 2026-10-27). The stamp lives outside OneDrive.
import os as _os
from datetime import date as _today
_stamp = (Path(_os.environ["LOCALAPPDATA"]) / "Mantis" if _os.environ.get("LOCALAPPDATA") else ROOT) / "hook-day.txt"
try:
    first_today = _stamp.read_text(encoding="utf-8").strip() != _today.today().isoformat()
except OSError:
    first_today = True
try:
    _stamp.parent.mkdir(parents=True, exist_ok=True)
    _stamp.write_text(_today.today().isoformat(), encoding="utf-8")
except OSError:
    pass

try:  # once a day: Claude prepares the owner's daily brief suggestions for the Today page
    import json as _j
    sug = ROOT / "mantis" / "tasks" / "suggestions.json"
    from datetime import date as _d
    def _something_to_brief():   # MANTIS-IMP-060 and IMP-099: no Claude run for a brief that would repeat the last one
        sys.path.insert(0, str(ROOT / "tools"))
        import tasks_store, followups, schedule, steps, people, readiness, briefcheck
        today = _d.today()
        pb = ROOT / "mantis" / "tasks" / "pull-brief.json"
        try:
            last_pull = briefcheck.parse(_j.loads(pb.read_text(encoding="utf-8")).get("last", {}).get("at"))
        except (OSError, ValueError):
            last_pull = None
        try:
            last_brief = briefcheck.parse(_j.loads(sug.read_text(encoding="utf-8")).get("date"))
        except (OSError, ValueError):
            last_brief = None
        away = schedule.next_away(today)
        return briefcheck.needed(
            today, last_brief, last_pull,
            meeting_today=any(schedule.next_date(m, today) == today for m in schedule.meetings()),
            review_due=any(r["state"] in ("review-overdue", "live-no-review") for r in readiness.scan()),
            away_soon=bool(away and (_d.fromisoformat(away["start"]) - today).days <= 7),
            open_work=(any(t["status"] in ("todo", "blocked") for t in tasks_store.load()["tasks"])
                       or any(f["status"] == "open" for g in followups.grouped().values() for f in g["items"])
                       or any(not s["done"] and people.is_owner(s["who"]) for s in steps.load())))
    if first_today and (not sug.exists() or _j.loads(sug.read_text(encoding="utf-8")).get("date") != _d.today().isoformat()) and _something_to_brief():
        notes.append("Today's brief has no suggestions yet. Prepare them per docs/rules/workflow/day.md, 'Daily brief': run "
                     "`python tools/tasks.py context`, write up to 5 suggestions, save with `python tools/tasks.py suggest <file>`, "
                     "and tell the owner in one line that today's brief is ready on the Today page.")
except Exception as e:   # the hook must never fail
    notes.append(f"Today's brief check failed ({e}).")

try:  # a recurring meeting today (its regular day or a moved one): prepare its brief once, before it starts
    sys.path.insert(0, str(ROOT / "tools"))
    import schedule, brief
    from datetime import date as _d2
    for m in (schedule.meetings() if first_today else []):   # first session of the day only
        if schedule.next_date(m, _d2.today()) == _d2.today() and ((brief.latest(m["name"]) or {}).get("date") != _d2.today().isoformat()):
            notes.append(f"The owner's meeting '{m['name']}' is today{(' at ' + m['time']) if m.get('time') else ''}. Prepare its brief per "
                         f"docs/rules/workflow/day.md, 'Meeting briefs' (python tools/brief.py gather \"{m['name']}\"), save it, and "
                         "give the owner the bullets in your first reply. After the meeting, offer to save the takeaways.")
except Exception as e:   # the hook must never fail
    notes.append(f"Today's meeting-brief check failed ({e}).")

out ={"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": " ".join(notes)}} if notes else {}
print(json.dumps(out))
