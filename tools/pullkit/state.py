"""Where a pull keeps things, the pull state and the cards it can pass."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import atl_updates
import frontmatter
import json
import re
import textcache
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent


K = ROOT / "mantis" / "knowledge"


INBOX = ROOT / "mantis" / "00_inbox"


BRIEF = ROOT / "mantis" / "tasks" / "pull-brief.json"


PACKETS = "packets"            # under mantis/mirror/


CAP_ITEM, CAP_PACKET = 6000, 24000   # characters of diff per item and per packet; the rest is pointed to


NEW_ROW = re.compile(r"(?m)^\| (MANTIS-DOC-\d{4}) \| [^|]*\(new\) \| ([^|]*) \| ([^|]*) \|")


def say(msg=""):
    print(msg, flush=True)


def state():
    s = atl_updates.load_state()
    run = s.setdefault("run", {})
    for k, v in (("noise", {"jira": {}, "confluence": {}}), ("done", {}), ("headlines", {}), ("needs", []), ("skipped", [])):
        run.setdefault(k, v)
    return s


# ------------------------------------------------------------------ cards
def cards():
    """{slug: {"title", "path", "match", "followed"}}, followed cards first in the owner's order."""
    focus = json.loads((K / "focus.json").read_text(encoding="utf-8")) if (K / "focus.json").exists() else {}
    order = focus.get("following", [])
    out = {}
    for folder in ("features", "topics"):
        for p in sorted((K / folder).glob("*.md")):
            if p.name == "README.md" or p.stem in focus.get("archived", []):
                continue
            fm = frontmatter.parse(textcache.read(p))
            out[p.stem] = {"title": fm.get("title") or p.stem, "path": p, "match": set(fm.get("match_topics", [])),
                           "followed": p.stem in order}
    rank = {s: i for i, s in enumerate(order)}
    return dict(sorted(out.items(), key=lambda kv: (rank.get(kv[0], 999), kv[0])))


def inbox_files():
    if not INBOX.exists():
        return []
    return sorted(p.name for p in INBOX.iterdir() if p.is_file() and not p.name.startswith(("answers-", "edit-", ".")))


def cmd_skip(ids):
    cleared = atl_updates.mark_digested(ids)
    s = state()
    s["run"]["skipped"] = sorted(set(s["run"]["skipped"]) | set(cleared))
    atl_updates.save_state(s)
    say(f"Skipped {len(cleared)} item(s).")
