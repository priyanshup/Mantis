"""People the owner works with (MANTIS-IMP-022), read from mantis/knowledge/people.md.

    python tools/people.py                 list everyone with role
    python tools/people.py show NAME       one person: fields, follow-ups, steps waiting on them

people.md has one "## Full Name" section per person with bullet fields: Role, Team, Aliases,
Channel, Briefing style, Notes (and any other "**Field:** value" line). Matching a name accepts
the full name, an alias or a unique first name, ignoring case. The owner's own names are in
mantis/config/settings.json ("owner_names") so steps owned by the owner are recognised.
"""
import re, sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "mantis" / "knowledge" / "people.md"


def load():
    if not FILE.exists():
        return []
    out, cur = [], None
    text = re.sub(r"(?s)<!--.*?-->", "", FILE.read_text(encoding="utf-8"))   # the format example is not a person
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            cur = {"name": m.group(1), "fields": {}}
            out.append(cur)
            continue
        m = re.match(r"^\s*-\s+\*\*(.+?):\*\*\s*(.*)$", line)
        if cur and m:
            cur["fields"][m.group(1).strip().lower()] = m.group(2).strip()
    for p in out:
        f = p["fields"]
        p["role"] = f.get("role", "")
        p["team"] = f.get("team", "")
        p["aliases"] = [a.strip() for a in f.get("aliases", "").split(",") if a.strip()]
        p["channel"] = f.get("channel", "")
        p["briefing"] = f.get("briefing style", "")
        p["notes"] = f.get("notes", "")
        p["slug"] = slug(p["name"])
    return out


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def owner_names():
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        import local_config
        names = local_config.load().get("owner_names", [])
    except Exception:
        names = []
    return [n.lower() for n in names] + ["owner", "the owner", "me"]


def is_owner(text):
    t = (text or "").lower()
    return any(re.search(r"(?<![\w])" + re.escape(n) + r"(?![\w])", t) for n in owner_names())


def find(name, people=None):
    """The person a name refers to (full name, alias or unique first name), or None."""
    people = load() if people is None else people
    q = " ".join((name or "").lower().split())
    if not q:
        return None
    for p in people:
        if q == p["name"].lower() or q in (a.lower() for a in p["aliases"]):
            return p
    if " " in q:   # a first name only matches a one-word query ("sam"), never "vendor weekly sync"
        return None
    firsts = [p for p in people if p["name"].lower().split()[0] == q]
    return firsts[0] if len(firsts) == 1 else None


def mentioned(text, people=None):
    """Everyone a free-text field names (for 'Who' cells like 'Sam Lee or Alex Kim')."""
    people = load() if people is None else people
    t = (text or "").lower()
    hits = []
    for p in people:
        names = [p["name"]] + p["aliases"] + [p["name"].split()[0]]
        if any(re.search(r"(?<![\w])" + re.escape(n.lower()) + r"(?![\w])", t) for n in names if len(n) >= 3):
            hits.append(p)
    return hits


if __name__ == "__main__":
    a = sys.argv[1:]
    ps = load()
    if not a:
        for p in ps:
            print(f"{p['name']}: {p['role'] or '-'}")
    elif a[0] == "show" and len(a) > 1:
        p = find(" ".join(a[1:]), ps)
        if not p:
            sys.exit("No such person in people.md")
        print(p["name"])
        for k, v in p["fields"].items():
            print(f"  {k}: {v}")
        import followups
        for f in followups.for_person(p["name"]):
            print(f"  follow-up: {f['topic']} (since {f['created']}, raised {len(f['raised'])}x)")
