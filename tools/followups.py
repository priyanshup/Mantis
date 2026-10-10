"""Follow-ups per person (MANTIS-IMP-020): topics to raise with someone, or things waiting on them.

    python tools/followups.py list [PERSON]                       open follow-ups, grouped by person
    python tools/followups.py add PERSON "Topic" [--detail TEXT] [--card SLUG] [--kind raise|wait] [--chase YYYY-MM-DD] [--source TEXT]
    python tools/followups.py raised ID                            record that it was raised today (it stays open)
    python tools/followups.py done ID [--note TEXT]                close it
    python tools/followups.py reopen ID

Stored in mantis/tasks/followups.json. A follow-up stays open until it is marked done, so anything
not closed in a meeting is still there for the next one. "raise": a topic the owner wants to bring
up; "wait": something the owner is waiting for from that person (chase on the chase date).
Steps on cards that are waiting on someone are shown alongside, read from the cards (tools/steps.py).
"""
import json, os, sys, time, uuid
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
FILE = ROOT / "mantis" / "tasks" / "followups.json"
LOCK = FILE.with_suffix(".lock")


def _read():
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"rev": 0, "items": []}


def _write(st):
    FILE.parent.mkdir(parents=True, exist_ok=True)
    st["rev"] = st.get("rev", 0) + 1
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, FILE)
    return st


def _locked(fn):
    FILE.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(100):
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if time.time() - LOCK.stat().st_mtime > 30:
                LOCK.unlink(missing_ok=True)
            time.sleep(0.05)
    else:
        raise OSError("follow-ups are busy; try again")
    try:
        return fn()
    finally:
        os.close(fd)
        LOCK.unlink(missing_ok=True)


def canonical(person):
    import people
    p = people.find(person)
    return p["name"] if p else " ".join(str(person).split())[:80]


def load():
    return _read()


def for_person(person, include_done=False):
    name = canonical(person)
    return [i for i in _read()["items"] if i["person"] == name and (include_done or i["status"] == "open")]


def add(person, topic, detail="", card="", kind="raise", chase="", source=""):
    if not str(topic).strip() or not str(person).strip():
        raise ValueError("a follow-up needs a person and a topic")
    item = {"id": uuid.uuid4().hex[:8], "person": canonical(person), "topic": " ".join(str(topic).split())[:200],
            "detail": str(detail)[:2000], "card": str(card)[:80], "kind": kind if kind in ("raise", "wait") else "raise",
            "chase": chase if len(str(chase)) == 10 else "", "source": str(source)[:160], "created": date.today().isoformat(),
            "raised": [], "status": "open", "done_at": "", "note": ""}

    def go():
        st = _read()
        st["items"].append(item)
        return _write(st)
    _locked(go)
    return item


def update(fid, action, note="", **fields):
    """action: raised | done | reopen | delete | edit."""
    def go():
        st = _read()
        for i in st["items"]:
            if i["id"] == fid:
                if action == "raised":
                    i["raised"] = sorted(set(i["raised"] + [date.today().isoformat()]))
                elif action == "done":
                    i.update(status="done", done_at=date.today().isoformat(), note=str(note)[:500] or i.get("note", ""))
                elif action == "reopen":
                    i.update(status="open", done_at="")
                elif action == "delete":
                    st["items"].remove(i)
                elif action == "edit":
                    for k in ("topic", "detail", "chase", "kind", "card"):
                        if k in fields:
                            i[k] = str(fields[k])[:2000]
                return _write(st)
        raise ValueError("no such follow-up")
    return _locked(go)


def grouped(include_steps=True):
    """Open follow-ups by person, plus card steps waiting on that person (not owned by the owner)."""
    out = {}
    for i in _read()["items"]:
        if i["status"] == "open":
            out.setdefault(i["person"], {"items": [], "steps": []})["items"].append(i)
    if include_steps:
        import steps, people
        ps = people.load()
        for s in steps.load():
            if s["done"] or people.is_owner(s["who"]):
                continue
            for p in people.mentioned(s["who"], ps):
                out.setdefault(p["name"], {"items": [], "steps": []})["steps"].append(s)
    return out


def arg(a, name, default=""):
    return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "list":
        g = grouped()
        who = canonical(a[1]) if len(a) > 1 else None
        for person, v in sorted(g.items()):
            if who and person != who:
                continue
            print(person)
            for i in v["items"]:
                print(f"  [{i['id']}] {'wait' if i['kind'] == 'wait' else 'raise'}: {i['topic']} (since {i['created']}, raised {len(i['raised'])}x"
                      + (f", chase {i['chase']}" if i["chase"] else "") + ")")
            for s in v["steps"]:
                print(f"  step on {s['card']}: {s['step']} ({s['status'] or 'open'}" + (f", due {s['due']}" if s["due"] else "") + ")")
    elif a[0] == "add" and len(a) >= 3:
        i = add(a[1], a[2], arg(a, "--detail"), arg(a, "--card"), arg(a, "--kind", "raise"), arg(a, "--chase"), arg(a, "--source"))
        print(f"Added for {i['person']}: {i['topic']} [{i['id']}]")
    elif a[0] in ("raised", "done", "reopen", "delete") and len(a) >= 2:
        update(a[1], a[0], arg(a, "--note"))
        print(f"{a[0].capitalize()}: {a[1]}")
    else:
        sys.exit(__doc__)
