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
                     "then process them per docs/rules/WORKFLOW.md, section 'Owner answers from the site', before other work unless "
                     "the owner says otherwise.")
    edits = sorted(INBOX.glob("edit-*.md"))
    if edits:
        notes.append(f"The owner saved {len(edits)} edited page(s), epic(s) or story(ies) from the site ({', '.join(p.name for p in edits)}). "
                     "Tell the owner, then apply them per docs/rules/WORKFLOW.md, section 'Owner edits from the site' (python tools/apply_edits.py).")
    other = [p.name for p in INBOX.iterdir() if p.is_file() and not p.name.startswith(("answers-", "edit-"))] if INBOX.exists() else []
    if other:
        notes.append(f"mantis/00_inbox also holds {len(other)} file(s) waiting for ingest: {', '.join(other[:10])}. Mention them to the owner.")
except Exception as e:
    notes.append(f"Inbox check failed: {e}")

try:  # once a day: Claude prepares the owner's daily brief suggestions for the Today page
    import json as _j
    sug = ROOT / "mantis" / "tasks" / "suggestions.json"
    from datetime import date as _d
    if not sug.exists() or _j.loads(sug.read_text(encoding="utf-8")).get("date") != _d.today().isoformat():
        notes.append("Today's brief has no suggestions yet. Prepare them per docs/rules/WORKFLOW.md, 'Daily brief': run "
                     "`python tools/tasks.py context`, write up to 5 suggestions, save with `python tools/tasks.py suggest <file>`, "
                     "and tell the owner in one line that today's brief is ready on the Today page.")
except Exception:
    pass

out = {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": " ".join(notes)}} if notes else {}
print(json.dumps(out))
