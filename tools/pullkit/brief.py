"""The Since-last-pull brief: what it holds, what closed by itself, and how it prints."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import atl_updates
import json
import re
from datetime import datetime
from pullkit.grouping import unmapped
from pullkit.state import BRIEF, K, inbox_files, say


def auto_closed(since_day):
    out = []
    for p in sorted((K / "registers" / "gaps").glob("MANTIS-GAP-*.md")):
        t = p.read_text(encoding="utf-8")
        m = re.search(r"(?m)^- \*\*Status:\*\* Closed \(auto, (\d{4}-\d{2}-\d{2})", t)
        if m and m.group(1) >= since_day:
            topic = re.search(r"(?m)^- \*\*Topic:\*\*\s*(.+)$", t)
            out.append({"id": p.stem, "topic": (topic.group(1) if topic else "")[:160]})
    return out


def load_brief():
    try:
        return json.loads(BRIEF.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"last": None, "history": []}


def pending_counts():
    """What waits for the next pull right now: Jira and Confluence items, and files in the inbox (for the site)."""
    s = atl_updates.load_state()
    loose = sum(len(e["keys"]) for e in unmapped())   # tickets no card owns wait for the owner, not for a pull
    return {"jira": len(s["pending"]["jira"]) - loose, "confluence": len(s["pending"]["confluence"]), "files": len(inbox_files()),
            "last_fetch": max(s["jira"].get("last_fetch", ""), s["confluence"].get("last_fetch", ""))}


def when(stamp):
    try:
        return datetime.strptime(stamp, "%Y-%m-%dT%H:%M").strftime("%d %b %H:%M").lstrip("0")
    except ValueError:
        return stamp or "the start"


def print_brief(b):
    if not b:
        say("No pull has finished yet.")
        return
    say(f"Since last pull ({when(b['since'])} to {when(b['at'])})")
    for c in b["cards"]:
        say(f"\n{c['title']}")
        for line in c["lines"]:
            say(f"- {line}")
    extra = []
    if b["status_moves"]:
        extra.append(f"{len(b['status_moves'])} ticket(s) moved status or parent only")
    if b["formatting"]:
        extra.append(f"{len(b['formatting'])} page(s) had formatting-only edits")
    if extra:
        say("\nAlso: " + "; ".join(extra) + ".")
    if b["closed"]:
        say("\nClosed automatically (undo: python tools/entry.py reopen <ID>):")
        for x in b["closed"]:
            say(f"- {x['id']}: {x['topic']}")
    if b["needs"]:
        say("\nNeeds you:")
        for n in b["needs"]:
            say(f"- {n}")
    if b["waiting"]:
        say(f"\n{b['waiting']} item(s) still wait for the next pull.")
