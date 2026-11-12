"""Rules for what is yours, what needs attention today and the health line. No page of its own; the app and the tests use it."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import hashlib
import json
import re
from pagebuild.labels import PRIO_RANK, WORK
from pagebuild.markup import plain
from pagebuild.paths import M
from pagebuild.registry import CHANGES, FOCUS, OPEN, READY, archived


def scope_of(o):
    """Questions page side: 'tidy' for names and terms to confirm (housekeeping, not decisions), 'others' when
    someone else is named to answer an open question, else 'you'."""
    if o["kind"] in ("name", "term"):
        return "tidy"
    return "others" if o["status"] == "Open" and o.get("ask") else "you"


def qkey(o):
    return hashlib.sha1(o["id"].encode("utf-8")).hexdigest()[:10]


def topic_text(o):
    return re.sub(r" ?[(]MANTIS-[A-Z]+-[0-9]+(?:[,;] ?MANTIS-[A-Z]+-[0-9]+)*[)]", "", o["topic"])


def yours():
    """Questions waiting for the owner, the ones to decide first, then by priority, newest first."""
    mine = [o for o in OPEN if scope_of(o) == "you"]
    mine.sort(key=lambda o: (o.get("raised", ""), o["id"]), reverse=True)
    mine.sort(key=lambda o: (o["status"] == "Open", PRIO_RANK[o.get("priority", "")]))
    return mine


def attention(work):
    """What Mantis noticed that is not a question: decision readiness, decisions whose basis moved, drafts to
    review, outputs behind their card, summaries behind their sources, health warnings. [(href, text, action)]"""
    att = []
    for slug, msg, act in READY.get("attention", []):
        if not archived(slug):
            att.append((f"features/{slug}.html", msg, act))
    for d in READY.get("decisions", []):
        what = "; ".join(("a source it rests on was edited" if "-DOC-" in x else f"a question it rests on is now \"{now.split(' (')[0]}\"")
                         for x, _, now in d["changes"][:2])
        text = re.sub(r"\s*\([^)]*\)", "", d["decision"])
        short = text if len(text) <= 90 else text[:90].rsplit(" ", 1)[0].rstrip(",;:") + "…"
        att.append(("library.html#decisions", f"Decision \"{short}\" may need a look: {what}.", "Review"))
    for x in work:
        if x["status"] in ("draft", "review") and x["file"] not in FOCUS.get("archived_work", []) and not archived(x["feature"]):
            att.append((x["href"], f'{"Epic" if x["kind"] == "epic" else "Story"} "{x["title"]}" is {WORK[x["status"]][0].lower()}', "Review"))
    for b in CHANGES.get("behind", []):
        att.append((b["href"], f'{b["kind"]} "{b["title"]}" may be out of date. {b["why"]}.', "Update"))
    for r in CHANGES.get("refresh", []):
        att.append((r["href"], f'{r["title"]}: {r["why"]}.', "Refresh"))
    hp = M / "knowledge" / "map" / "health.json"
    for i in (json.loads(hp.read_text(encoding="utf-8"))["items"] if hp.exists() else []):
        if i["level"] == "warn":
            att.append(("sources.html#health", f'{i["area"]}: {plain(i["msg"], 220)}', "Fix"))
    return att


def health():
    p = M / "knowledge" / "map" / "health.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"date": "", "items": []}
