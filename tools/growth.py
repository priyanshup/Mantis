"""The owner's growth record (Growth tab): opportunities to step up, what came of them, learnings, recognition.

    python tools/growth.py list                       everything open, waiting for the owner, and done
    python tools/growth.py add "Title" [--kind contribution|learning|recognition] [--area a,b] [--card SLUG]
                          [--meeting NAME] [--why TEXT] [--source TEXT] [--outcome TEXT] [--evidence URL]
                          [--seen NAMES] [--said-by NAME] [--date D]
                                                      the owner's own entry (a learning or recognition is saved as done)
    python tools/growth.py done ID --outcome TEXT [--evidence URL] [--seen NAMES]
    python tools/growth.py shared ID                  the owner told their manager about it (today)
    python tools/growth.py propose FILE               Mantis's proposals from a JSON list (see docs/rules/workflow/growth.md)
    python tools/growth.py context                    compact input for the daily brief's growth proposals
    python tools/growth.py sweep                      compact list of past work that may be a contribution (seeding)
    python tools/growth.py record [--months 12]       the appraisal record as Markdown, grouped by strength

Data in mantis/growth/ (local, never committed): growth.json {"rev", "items", "dismissed"} and framework.json
(the target role, its strength areas quoted from the job description, the manager and the review dates).
An item: id, kind, title, state (proposed | open | done | dropped), past (a proposed past win, not an
opportunity), areas, card, meeting, why, source (in words), outcome, evidence, seen_by, said_by, shared (date the
owner told the manager), tasks (ids of its steps on Today), created, done_at, by (owner | mantis).
Mantis only ever proposes: nothing becomes an opportunity or a win until the owner takes or confirms it, and a
proposal the owner declines is never proposed again (matched by words, as tasks are).
"""
import json, os, re, sys, time, uuid
from datetime import date, timedelta
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
DIR = ROOT / "mantis" / "growth"
STORE, FRAME, LOCK = DIR / "growth.json", DIR / "framework.json", DIR / ".lock"
KINDS = ("contribution", "learning", "recognition")
STATES = ("proposed", "open", "done", "dropped")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
GROUP = {"id": "g-growth", "name": "Growth", "card": "", "pin": None, "collapsed": False}
THIN_DAYS = 90      # a strength with no evidence for this long is "thin"
WAITING_CAP = 3     # proposals shown at once (DESIGN.md rule 8)


def today():
    return date.today().isoformat()


def _read(p, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def framework():
    return _read(FRAME, {"role": "", "areas": [], "manager": "", "review": {}, "sources": {}})


def area_keys():
    return [a["key"] for a in framework().get("areas", [])]


def _locked(fn):
    DIR.mkdir(parents=True, exist_ok=True)
    for _ in range(100):
        try:
            fd = os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if time.time() - LOCK.stat().st_mtime > 30:
                LOCK.unlink(missing_ok=True)
            time.sleep(0.05)
    else:
        raise OSError("the growth record is busy; try again")
    try:
        return fn()
    finally:
        os.close(fd)
        LOCK.unlink(missing_ok=True)


def load():
    return _read(STORE, {"rev": 0, "items": [], "dismissed": []})


def edit(fn):
    """Change the record under the lock; saved only when fn returns something truthy. Returns fn's result."""
    def go():
        st = load()
        out = fn(st)
        if out:
            st["rev"] = st.get("rev", 0) + 1
            tmp = STORE.with_suffix(".tmp")
            tmp.write_text(json.dumps(st, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            os.replace(tmp, STORE)
        return out
    return _locked(go)


def clean(x, by="owner"):
    """One item from the page, the command line or a proposal file; anything unexpected is dropped."""
    s = lambda v, n: " ".join(str(v or "").split())[:n]
    d = lambda v: str(v) if DATE.match(str(v or "")) else ""
    keys = set(area_keys())
    names = lambda v: [s(n, 80) for n in (v if isinstance(v, list) else str(v or "").split(",")) if s(n, 80)][:8]
    kind = x.get("kind") if x.get("kind") in KINDS else "contribution"
    out = {"id": s(x.get("id"), 20) or uuid.uuid4().hex[:8], "kind": kind, "title": s(x.get("title"), 300),
           "state": x.get("state") if x.get("state") in STATES else ("open" if kind == "contribution" else "done"),
           "past": bool(x.get("past")),
           "areas": [a for a in (x.get("areas") if isinstance(x.get("areas"), list) else str(x.get("areas") or "").split(",")) if a in keys][:2],
           "card": s(x.get("card"), 80), "meeting": s(x.get("meeting"), 120), "why": s(x.get("why"), 600),
           "source": s(x.get("source"), 200), "outcome": s(x.get("outcome"), 800), "evidence": s(x.get("evidence"), 500),
           "seen_by": names(x.get("seen_by")), "said_by": s(x.get("said_by"), 80), "shared": d(x.get("shared")),
           "tasks": [s(t, 40) for t in (x.get("tasks") or [])][:30], "created": d(x.get("created")) or today(),
           "done_at": d(x.get("done_at")), "by": "mantis" if (x.get("by") or by) == "mantis" else "owner"}
    if not out["title"]:
        raise ValueError("an entry needs a title")
    if out["state"] == "done" and not out["done_at"]:
        out["done_at"] = today()
    return out


def _same(title, items):
    """An item with the same words (the task list's rule: tasks_store.SAME)."""
    import tasks_store as T
    w = T._words(title)
    for it in items:
        o = T._words(it["title"])
        if len(w & o) >= 2 and len(w & o) / max(1, len(w | o)) >= T.SAME:
            return it
    return None


def add(x, by="owner"):
    item = clean(x, by)
    def go(st):
        st["items"].append(item)
        return item
    return edit(go)


def propose(items, source=""):
    """Mantis's proposals (daily brief, meeting takeaways, the past-work sweep): saved as 'proposed', never as the
    owner's. A proposal matching an existing entry or one the owner declined is skipped. Returns (added, skipped)."""
    added, skipped = [], []
    def go(st):
        for x in items[:20]:
            try:
                it = clean(dict(x, state="proposed", source=x.get("source") or source), by="mantis")
            except (ValueError, TypeError, AttributeError):
                continue
            if _same(it["title"], st["items"]) or _same(it["title"], [{"title": t} for t in st.get("dismissed", [])]):
                skipped.append(it["title"])
                continue
            st["items"].append(it)
            added.append(it)
        return added
    edit(go)
    return added, skipped


def _find(st, iid):
    it = next((i for i in st["items"] if i["id"] == iid), None)
    if not it:
        raise ValueError(f"no growth entry {iid}")
    return it


def act(b):
    """One change from the Growth tab: {"action", "id", ...}. Returns the item (or True)."""
    a, iid = str(b.get("action", "")), str(b.get("id", ""))[:20]
    if a == "add":
        return add(b.get("item") or {})
    if a == "step":
        return add_step(iid, str(b.get("title", "")))

    def go(st):
        if a == "restore":   # Undo: the entry exactly as it was, and no longer declined
            it = clean(b.get("item") or {}, by=(b.get("item") or {}).get("by", "owner"))
            st["items"] = [x for x in st["items"] if x["id"] != it["id"]] + [it]
            st["dismissed"] = [t for t in st.get("dismissed", []) if t != it["title"]]
            return it
        if a == "dismiss":   # declining a proposal: gone, and never proposed again
            it = _find(st, iid)
            st["items"].remove(it)
            st.setdefault("dismissed", []).append(it["title"])
            st["dismissed"] = st["dismissed"][-500:]
            return True
        it = _find(st, iid)
        if a == "take":      # an opportunity the owner takes on
            it.update(state="open", by="owner")
        elif a == "confirm":  # a past win the owner confirms, with the outcome as they put it
            out = " ".join(str(b.get("outcome") or it["outcome"]).split())
            if not out and it["kind"] == "contribution":
                raise ValueError("say what changed because of it")
            it.update(state="done", by="owner", outcome=out[:800], done_at=it["done_at"] or today())
        elif a == "done":
            out = " ".join(str(b.get("outcome", "")).split())
            if not out and it["kind"] == "contribution":
                raise ValueError("say what changed because of it")
            it.update(state="done", outcome=out[:800], done_at=today(),
                      evidence=str(b.get("evidence", it["evidence"]))[:500].strip(),
                      seen_by=clean({"title": "x", "seen_by": b.get("seen_by", it["seen_by"])})["seen_by"])
        elif a == "drop":
            it["state"] = "dropped"
        elif a == "reopen":
            it.update(state="open", done_at="")
        elif a == "shared":
            it["shared"] = "" if it["shared"] else today()
        elif a == "update":   # fields the owner edits on an entry
            f = b.get("fields") or {}
            c = clean(dict(it, **{k: f[k] for k in ("title", "areas", "card", "outcome", "evidence", "seen_by", "why", "said_by", "kind") if k in f}))
            it.update({k: c[k] for k in ("title", "areas", "card", "outcome", "evidence", "seen_by", "why", "said_by", "kind")})
        elif a == "delete":
            st["items"].remove(it)
        else:
            raise ValueError("unknown action")
        return it
    return edit(go)


def add_step(iid, title):
    """A step toward an opportunity: an ordinary task on Today, in the owner's Growth group."""
    import tasks_store as T
    title = " ".join(title.split())[:300]
    if not title:
        raise ValueError("a step needs a title")
    _find(load(), iid)
    def group(st):
        if not any(g.get("id") == GROUP["id"] for g in st.get("groups", [])):
            st.setdefault("groups", []).append(dict(GROUP))
            return True
        return False
    T.edit(group)
    t = T.add({"title": title, "day": today(), "group": GROUP["id"], "source": "Growth"})
    def link(st):
        it = _find(st, iid)
        it["tasks"].append(t["id"])
        if it["state"] == "proposed":
            it["state"] = "open"
        return it
    return edit(link)


def _archived():
    import tasks_store as T
    a = T._read(T.ARCHIVE, [])
    return a.get("tasks", []) if isinstance(a, dict) else a


def _tasks():
    import tasks_store as T
    out = {t["id"]: t for t in _archived()}
    out.update({t["id"]: t for t in T.load()["tasks"]})
    return out


def coverage(items, days=365):
    """Done entries per strength in the window (contributions, learnings and recognition), and the date of each
    strength's latest one."""
    since = (date.today() - timedelta(days=days)).isoformat()
    out = {k: {"n": 0, "last": ""} for k in area_keys()}
    for it in items:
        if it["state"] == "done" and it["done_at"] >= since:
            for a in it["areas"]:
                if a in out:
                    out[a]["n"] += 1
                    out[a]["last"] = max(out[a]["last"], it["done_at"])
    thin = (date.today() - timedelta(days=THIN_DAYS)).isoformat()
    for v in out.values():
        v["thin"] = v["last"] < thin
    return out


def record(months=12):
    """The appraisal record: done contributions by strength, then learnings and recognition, newest first."""
    since = (date.today() - timedelta(days=round(months * 30.5))).isoformat()
    items = [i for i in load()["items"] if i["state"] == "done" and i["done_at"] >= since]
    fw = framework()
    by = lambda k: sorted([i for i in items if i["kind"] == "contribution" and (i["areas"][:1] == [k] if k else not i["areas"])],
                          key=lambda i: i["done_at"], reverse=True)
    secs = [{"key": a["key"], "name": a["name"], "means": a["means"], "items": by(a["key"])} for a in fw.get("areas", [])]
    secs.append({"key": "", "name": "Other", "means": "Not yet tied to a strength", "items": by("")})
    return {"since": since, "role": fw.get("role", ""), "sections": [s for s in secs if s["items"]],
            "learnings": sorted([i for i in items if i["kind"] == "learning"], key=lambda i: i["done_at"], reverse=True),
            "recognition": sorted([i for i in items if i["kind"] == "recognition"], key=lambda i: i["done_at"], reverse=True)}


def payload():
    """What the Growth tab draws: the framework, every entry with its steps' state, and coverage."""
    st, tasks, fw = load(), _tasks(), framework()
    items = []
    for it in st["items"]:
        steps = [{"id": t, "title": tasks[t]["title"], "status": tasks[t]["status"], "day": tasks[t]["day"]} for t in it["tasks"] if t in tasks]
        items.append(dict(it, steps=steps))
    return {"today": today(), "rev": st.get("rev", 0), "framework": {k: fw.get(k) for k in ("role", "areas", "manager", "review")},
            "items": items, "coverage": coverage(st["items"]), "record": record()}


def for_meeting(cards, names, out=print):
    """Lines for a meeting brief (tools/brief.py gather): opportunities on the meeting's cards ("Step up") and,
    when the owner's manager attends, done work the manager has not heard about yet ("Wins to share")."""
    fw, items = framework(), load()["items"]
    cards = set(cards)
    up = [i for i in items if i["kind"] == "contribution" and i["state"] in ("open", "proposed") and not i["past"] and i["card"] in cards]
    for i in up[:2]:
        out(f"STEP UP{' (proposed by Mantis, not taken yet)' if i['state'] == 'proposed' else ''} on {i['card']}: {i['title']}"
            + (f" - why: {i['why'][:160]}" if i["why"] else ""))
    if up:
        out("  Put these in a 'Step up' section (two bullets at most): what the owner can offer or lead in this meeting.")
    if fw.get("manager") and fw["manager"] in names:
        wins = sorted([i for i in items if i["state"] == "done" and i["kind"] == "contribution" and not i["shared"]], key=lambda i: i["done_at"], reverse=True)
        for i in wins[:3]:
            out(f"WIN TO SHARE (done {i['done_at']}, not yet told to {fw['manager'].split()[0]}): {i['title']} - result: {i['outcome'][:200]}")
        if wins:
            out("  Put these in a 'Wins to share' section; the owner ticks each one Shared on the Growth tab after the meeting.")


def context():
    """Compact input for the daily brief: what is open, what waits, which strengths are thin."""
    st, fw = load(), framework()
    items = st["items"]
    print(f"GROWTH toward {fw.get('role') or 'the next role'}; year-end review {fw.get('review', {}).get('year_end', '?')}, "
          f"mid-year {fw.get('review', {}).get('mid_year', '?')}. Manager: {fw.get('manager') or '?'}.")
    print("Strengths: " + "; ".join(f"{a['key']} = {a['means']}" for a in fw.get("areas", [])))
    for i in items:
        if i["state"] == "open":
            print(f"OPEN [{i['id']}] {i['title']} ({', '.join(i['areas']) or 'no strength'}{', card ' + i['card'] if i['card'] else ''}, {len(i['tasks'])} steps)")
    waiting = [i for i in items if i["state"] == "proposed"]
    print(f"WAITING FOR THE OWNER: {len(waiting)} proposals" + (" (do not add more until they are handled)" if len(waiting) >= WAITING_CAP else ""))
    cov = coverage(items)
    thin = [k for k, v in cov.items() if v["thin"]]
    print("THIN (no evidence in 90 days): " + (", ".join(thin) or "none"))
    unshared = [i for i in items if i["state"] == "done" and i["kind"] == "contribution" and not i["shared"]]
    print(f"DONE, NOT YET SHARED WITH THE MANAGER: {len(unshared)}")
    last = max([i["created"] for i in items if i["by"] == "owner"] or [""])
    print(f"Owner's last entry: {last or 'none yet'}.")
    if date.today().day <= 7 and date.today().weekday() < 5:
        print("MONTHLY CHECK due this week: one suggestion 'Look at your Growth tab' naming the thinnest strength and any done work not yet shared.")
    print("Declined before (never propose again): " + "; ".join(st.get("dismissed", [])[-15:]))


def sweep():
    """Past work that may count as a contribution, from what the map already holds (no reading of sources):
    done steps owned by the owner, done tasks, published pages and epics, decisions the owner took."""
    import people, steps, tasks_store as T
    def fm(p):
        head = p.read_text(encoding="utf-8").split("---", 2)
        return dict(re.findall(r"(?m)^(\w+):\s*\"?(.*?)\"?\s*$", head[1])) if len(head) > 2 else {}
    print("PAST WORK (sweep). Already in the record: " + "; ".join(i["title"][:60] for i in load()["items"]) )
    print("\nSTEPS THE OWNER DID (card: step - status):")
    for s in steps.load():
        if s["done"] and people.is_owner(s["who"]):
            print(f"  {s['card']}: {s['step'][:140]} - {s['status'][:40]}")
    print("\nTASKS DONE (recent; older ones are archived and deleted after 7 days):")
    for t in _archived() + T.load()["tasks"]:
        if t["status"] == "done":
            print(f"  {t['done_at']} {t['title'][:140]}")
    print("\nOUTPUTS (pages and epics the owner published, with their card):")
    for kind in ("confluence", "epics"):
        for p in sorted((ROOT / "mantis" / "outputs" / kind).glob("*.md")):
            f = fm(p)
            if f.get("status") in ("published", "in-jira"):
                print(f"  {kind[:-1] if kind == 'epics' else 'page'} {p.stem}: {f.get('title', p.stem)[:80]} ({f.get('status')}, updated {f.get('updated', '?')})")
    print("\nCARDS (slug: status note):")
    fmap = _read(ROOT / "mantis" / "knowledge" / "map" / "features.json", [])
    for c in fmap:
        if c.get("status_note"):
            print(f"  {c['slug']}: {c['status_note'][:150]}")
    print("\nPropose up to 8 past wins as JSON for `growth.py propose` with \"past\": true, each with title, areas (1-2 keys), card, "
          "outcome (only what the sources say changed) and source in words. Do not read source files for this; ask the owner when unsure.")


def arg(name, default=""):
    a = sys.argv
    return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default


def show(i):
    tag = {"proposed": "waiting", "open": "doing", "done": "done", "dropped": "let go"}[i["state"]]
    return (f"[{i['id']}] {tag:7} {i['kind'][:5]} {i['title']}" + (f" ({', '.join(i['areas'])})" if i["areas"] else "")
            + (f" - result: {i['outcome']}" if i["outcome"] else "") + (f" - shared {i['shared']}" if i["shared"] else ""))


def main():
    a = sys.argv[1:]
    cmd = a[0] if a else "list"
    if cmd == "list":
        for i in sorted(load()["items"], key=lambda i: STATES.index(i["state"])):
            print(show(i))
    elif cmd == "add" and len(a) > 1:
        kind = arg("--kind", "contribution")
        it = add({"title": a[1], "kind": kind, "areas": arg("--area"), "card": arg("--card"), "meeting": arg("--meeting"),
                  "why": arg("--why"), "source": arg("--source"), "outcome": arg("--outcome"), "evidence": arg("--evidence"),
                  "seen_by": arg("--seen"), "said_by": arg("--said-by"), "done_at": arg("--date"),
                  "state": "done" if kind != "contribution" or arg("--outcome") else "open"})
        print("Added: " + show(it))
    elif cmd == "done" and len(a) > 1:
        print("Done: " + show(act({"action": "done", "id": a[1], "outcome": arg("--outcome"), "evidence": arg("--evidence"), "seen_by": arg("--seen")})))
    elif cmd == "shared" and len(a) > 1:
        print("Shared: " + show(act({"action": "shared", "id": a[1]})))
    elif cmd == "propose" and len(a) > 1:
        added, skipped = propose(json.loads(Path(a[1]).read_text(encoding="utf-8-sig")))
        print(f"Proposed {len(added)} on the Growth tab; skipped {len(skipped)} already there or declined before.")
    elif cmd == "context":
        context()
    elif cmd == "sweep":
        sweep()
    elif cmd == "record":
        r = record(int(arg("--months", "12")))
        print(f"# Contributions toward {r['role']}, since {r['since']}\n")
        for s in r["sections"]:
            print(f"## {s['name']}: {s['means']}\n")
            for i in s["items"]:
                print(f"- **{i['title']}** ({i['done_at'][:7]}). {i['outcome']}" + (f" Evidence: {i['evidence']}." if i["evidence"] else "")
                      + (f" Seen by {', '.join(i['seen_by'])}." if i["seen_by"] else ""))
            print()
        for head, key, fmt in (("Recognition", "recognition", lambda i: f"\"{i['title']}\" ({i['said_by'] or 'unnamed'}, {i['done_at']})"),
                               ("Learnings", "learnings", lambda i: f"{i['title']} ({i['done_at'][:7]})" + (f". {i['outcome']}" if i["outcome"] else ""))):
            if r[key]:
                print(f"## {head}\n\n" + "\n".join("- " + fmt(i) for i in r[key]) + "\n")
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
