"""Build the read-only Mantis website from the Markdown files.

    python tools/build_site.py      (build_map.py also calls this, so a normal rebuild covers it)
    python tools/serve.py           (serves it at http://localhost:8000 and rebuilds on change)

Markdown stays the only source. This script writes the site to %LOCALAPPDATA%/Mantis/site
(outside OneDrive) and nothing else. Every page is cleaned for pasting into Confluence or Jira: Mantis IDs, source columns, repo paths and
HTML comments are removed. Needs the `markdown` package (pip install markdown).
Reads mantis/knowledge/map/features.json and work.json, which build_map.py writes.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import html, json, os, re, shutil, tempfile
from urllib.parse import quote
from datetime import datetime
from pathlib import Path

import markdown

import edit_common

ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "mantis"
# Generated output lives outside OneDrive (rebuilt on every save; syncing it only causes churn and locks).
SITE = Path(os.environ["LOCALAPPDATA"]) / "Mantis" / "site" if os.environ.get("LOCALAPPDATA") else ROOT / "site"

STATUS = {  # feature status -> (label, css class); order is the board order
    "none": ("Not started", "s-none"), "discovery": ("Discovery", "s-disc"), "refinement": ("Refinement", "s-ref"),
    "build": ("In build", "s-build"), "live": ("Completed", "s-done"),
}
WORK = {  # epic, story and page status -> (label, css class)
    "draft": ("Draft", "w-draft"), "review": ("In review", "w-review"), "in-jira": ("In Jira", "w-jira"),
    "done": ("Done", "w-done"), "published": ("Published", "w-done"),
}
ID = r"(?:MANTIS-)?(?:DOC|GAP|ASM|CFL|DEC|IMP)-\d+|\bAD-\d{3}\b"
DROP_COLS = {"source", "sources", "doc", "docs", "source document", "source documents", "evidence", "id"}


# ---------- Markdown cleaning ----------

def front_matter(text):
    m = re.match(r"---\n(.*?)\n---\n?", text, re.S)
    fm = {}
    if m:
        for line in m.group(1).splitlines():
            k, _, v = line.partition(":")
            if k and not line.startswith(" "):
                fm[k.strip()] = v.split(" #")[0].strip().strip('"')
        text = text[m.end():]
    return fm, text


def drop_columns(text):
    out, table = [], []

    def flush():
        if table:
            rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in table]
            keep = [i for i, h in enumerate(rows[0]) if h.lower().strip("* ") not in DROP_COLS] or [0]
            out.extend("| " + " | ".join(r[i] if i < len(r) else "" for i in keep) + " |" for r in rows)
            table.clear()

    for line in text.split("\n"):
        if line.lstrip().startswith("|"):
            table.append(line)
        else:
            flush()
            out.append(line)
    flush()
    return "\n".join(out)


def clean(text):
    """Remove everything that only makes sense inside Mantis."""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = drop_columns(text)
    text = re.sub(r"\[([^\]]+)\]\((?!https?:)[^)]*\.(?:md|json|py)\)", r"\1", text)  # links to repo files
    for _ in range(3):  # parentheses that hold an ID or a repo path, innermost first
        text = re.sub(r"\s*\((?:[^()]*?(?:%s)|[^()]*?`[^`]*\.(?:md|json|py)`)[^()]*\)" % ID, "", text)
    text = re.sub(r"(?m)^(\s*(?:[-*]|\d+\.)\s+)(?:%s)\s*[:\-–—]\s*" % ID, r"\1", text)  # "- GAP-057: x"
    text = re.sub(r"`[^`\n]*\.(?:md|json|py)`", "", text)
    text = re.sub(ID, "", text)
    text = re.sub(r"\bP-\d{2}\s+", "", text)  # persona register codes
    text = re.sub(r"(?m)^## Open\s*$", "## Open questions", text)
    text = re.sub(r"[ \t]+([,.;:)])", r"\1", text)
    text = re.sub(r"\(\s*[;,]?\s*\)|\[\s*\]", "", text)
    text = re.sub(r"(?<=\S)[ \t]{2,}(?=\S)", " ", text)
    text = re.sub(r"(?m)^\s*\*\(?Sources?:?\s*\)?\*\s*$", "", text)  # emptied "*Source:*" lines
    text = re.sub(r"(?m)^(\s*[-*]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)
    return text


def fix_lists(text):
    """Python-Markdown needs a blank line before a list; Jira-style text often has none."""
    out = []
    item = re.compile(r"^\s*(?:[-*+]|\d+\.)\s")
    for line in text.split("\n"):
        if item.match(line) and out and out[-1].strip() and not item.match(out[-1]) and not out[-1].startswith((" ", "|")):
            out.append("")
        out.append(line)
    return "\n".join(out)


def render(text, breaks=False, sections=True):
    exts = ["tables", "sane_lists", "fenced_code"] + (["nl2br"] if breaks else [])
    body = markdown.markdown(fix_lists(clean(text)), extensions=exts)
    body = body.replace("<table>", '<div class="tbl"><table>').replace("</table>", "</table></div>")
    if not sections:
        return body
    parts = [p for p in re.split(r"(?=<h2)", body) if p.strip()]
    return "".join(f'<section class="sec"><button class="copy-sec nocopy" title="Copy this section">Copy</button>{p}</section>' for p in parts)


def first_sentence(text, limit=170):
    m = re.search(r"(?ms)^## In one paragraph\s*\n(.+?)(?=^## |\Z)", text)
    para = re.sub(r"\s+", " ", clean(m.group(1) if m else "")).strip()
    s = re.split(r"(?<=[.!?])\s", para)[0] if para else ""
    return s if len(s) <= limit else s[:limit - 1].rsplit(" ", 1)[0] + "…"


def read(rel):
    return front_matter((M / rel).read_text(encoding="utf-8"))


# ---------- Page shell ----------

def esc(s):
    return html.escape(str(s or ""), quote=True)


def n_(count, one, many=None):
    """'1 story', '4 stories': never '1 stories'."""
    return f"{count} {one if count == 1 else (many or one + 's')}"


def pill(label, cls):
    return f'<span class="pill {cls}">{esc(label)}</span>'


def work_pill(status):
    label, cls = WORK.get(status or "", (status.title() if status else "No status", "w-draft"))
    return pill(label, cls)


def prio_pill(p):
    return pill(p, "p-" + p.lower()) if p else ""


NAV = (("home", "index.html", "Home"), ("today", "today.html", "Today"), ("roadmap", "roadmap.html", "Roadmap"), ("topics", "topics.html", "Topics"),
       ("work", "work.html", "Epics & stories"), ("people", "people.html", "People"), ("review", "review.html", "Open items"))
NAV_MORE = (("graph", "graph.html", "Graph"), ("library", "library.html", "Library"), ("decisions", "decisions.html", "Decisions"),
            ("health", "health.html", "Health"), ("backlog", "backlog.html", "Mantis backlog"))


def shell(title, body, base="", active="", built=""):
    badge = lambda k: f' <span class="badge" title="Waiting for you">{BADGES[k]}</span>' if BADGES.get(k) else ""
    link = lambda key, href: href + ("#waiting" if key == "review" and BADGES.get("review") else "")
    nav = "".join(f'<a href="{base}{link(key, href)}" class="{"on" if key == active else ""}">{name}{badge(key)}</a>' for key, href, name in NAV)
    more_on = any(k == active for k, _, _ in NAV_MORE)
    nav += (f'<details class="nav-more"><summary class="{"on" if more_on else ""}">More</summary><div class="nav-pop">'
            + "".join(f'<a href="{base}{href}" class="{"on" if key == active else ""}">{name}</a>' for key, href, name in NAV_MORE) + '</div></details>')
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#f5f5f7" media="(prefers-color-scheme: light)"><meta name="theme-color" content="#000000" media="(prefers-color-scheme: dark)">
<title>{esc(title)} · Mantis</title>
<link rel="icon" type="image/png" href="{base}assets/mantis.png">
<script>try{{var m=localStorage.getItem("mantis-theme");if(m==="light"||m==="dark")document.documentElement.dataset.theme=m}}catch(e){{}}</script>
<link rel="stylesheet" href="{base}assets/style.css"></head>
<body>
<header class="top"><div class="wrap top-in">
<a class="brand" href="{base}index.html"><img class="logo" src="{base}assets/mantis.png" alt="" width="36" height="36"><span>Mantis</span></a>
<nav class="mainnav" id="mainnav" aria-label="Main">{nav}</nav>
<div class="gsearch"><input id="gsearch" type="search" placeholder="Search Mantis" aria-label="Search all of Mantis" autocomplete="off" data-base="{base}">
<div id="gresults" class="gresults" hidden></div></div>
<button type="button" id="theme" class="theme-btn" title="Theme: auto (follows your system)" aria-label="Change theme">◐</button>
<button type="button" class="menu-btn" aria-controls="mainnav" aria-expanded="false" aria-label="Menu"><span></span><span></span><span></span></button></div></header>
<main class="wrap">{body}</main>
<footer class="wrap foot"><span>Mantis</span>
<span>Read-only view of the Mantis Markdown files; answers and edits go to the inbox. Built {esc(built)}.</span></footer>
<div id="toast" role="status"></div>
<script src="{base}assets/app.js"></script>
</body></html>
"""


def copy_bar(label, edit=""):
    """Panel header: copy button, plus an Edit button when `edit` (the output file, relative to mantis/) is given."""
    btn = f'<button class="btn-line edit-btn" type="button">Edit</button>' if edit else ""
    return (f'<div class="panel-bar nocopy"><span class="muted small bar-note">Formatted for Confluence and Jira</span>'
            f'<span class="bar-btns">{btn}<button class="btn copy-all">{esc(label)}</button></span></div>' + edit_source(edit) + sync_panel(edit))


def _sections(body):
    """A Markdown body split at its level-2 headings: [(heading, text)]; text before the first is "Top of the page"."""
    out, head, buf = [], "Top of the page", []
    for line in body.replace("\r\n", "\n").split("\n"):
        if line.startswith("## "):
            out.append((head, "\n".join(buf).strip()))
            head, buf = line[3:].strip(), []
        else:
            buf.append(line)
    out.append((head, "\n".join(buf).strip()))
    return [(h, t) for h, t in out if h != "Top of the page" or t]


def sync_panel(rel):
    """Confluence sync (MANTIS-IMP-019): what changed since the owner last copied this page, section by section."""
    if not rel or not rel.startswith("outputs/confluence/"):
        return ""
    f = M / rel
    snap = M / "outputs" / ".published" / (rel[len("outputs/"):] + ".json")
    _, _, body = edit_common.split(f.read_text(encoding="utf-8"))
    mark = (f'<button type="button" class="btn-line" data-publish="mantis/{esc(rel)}" title="Remember this version as the one now in Confluence">'
            f'I copied this to Confluence</button>')
    if not snap.exists():
        return (f'<div class="sync nocopy"><span class="sync-ico" aria-hidden="true"></span><span><b>Not tracked yet.</b> After you paste this page into Confluence, '
                f'press the button: next time Mantis shows only the sections that changed.</span>{mark}</div>')
    pub = json.loads(snap.read_text(encoding="utf-8"))
    old, new = dict(_sections(pub.get("body", ""))), _sections(body)
    norm = lambda t: " ".join(t.split())
    changed = [(h, t, "new" if h not in old else "changed") for h, t in new if h not in old or norm(old[h]) != norm(t)]
    removed = [h for h in old if h not in dict(new)]
    when = pub.get("date", "")
    if not changed and not removed:
        return f'<div class="sync ok nocopy"><span class="sync-ico" aria-hidden="true"></span><span>Same as the version you copied to Confluence on {esc(when)}.</span></div>'
    items = "".join(f'<details class="sync-sec"><summary><span class="pill {"w-jira" if k == "new" else "w-review"} plain">{"New" if k == "new" else "Changed"}</span>'
                    f'<b>{esc(h)}</b><button type="button" class="mini copy-sec">Copy section</button></summary>'
                    f'<div class="sync-body doc"><h2>{esc(h)}</h2>{render(t)}</div></details>' for h, t, k in changed)
    items += "".join(f'<div class="sync-sec gone"><span class="pill s-none plain">Removed</span><b>{esc(h)}</b><span class="muted small">delete it in Confluence</span></div>' for h in removed)
    n = len(changed) + len(removed)
    return (f'<details class="sync changed nocopy" open><summary><span class="sync-ico" aria-hidden="true"></span><span><b>{n} section{"s" if n != 1 else ""} changed</b> since you copied this page '
            f'to Confluence on {esc(when)}. Update only these.</span>{mark.replace("I copied this to Confluence", "I updated Confluence")}</summary>{items}</details>')


def edit_source(rel):
    """The exact Markdown body behind a page, rendered for the editor (not cleaned), with its fingerprint."""
    if not rel:
        return ""
    f = M / rel
    _, _, body = edit_common.split(f.read_text(encoding="utf-8"))
    breaks = "/epics/" in rel or "/user-stories/" in rel
    html_ = markdown.markdown(fix_lists(body), extensions=["tables", "sane_lists", "fenced_code"] + (["nl2br"] if breaks else []))
    return (f'<template class="edit-src" data-path="mantis/{esc(rel)}" data-base="{edit_common.body_hash(body)}" '
            f'data-breaks="{int(breaks)}">{html_}</template>')


def job_btn(job, label, arg="", cls="btn-line", ai=True):
    """A button that starts a background job (tools/jobs.py). ai=True marks jobs that use Claude."""
    tip = "Uses Claude, on your normal quota" if ai else "Free: no AI"
    return (f'<button type="button" class="{cls} job{" ai" if ai else ""} nocopy" data-job="{job}"'
            f'{f" data-arg=\"{esc(arg)}\"" if arg else ""} title="{tip}">{label}</button>')


INBOX_STRIP = ('<div class="inbox-strip nocopy" hidden><span class="is-ico" aria-hidden="true"></span><span class="is-what"></span>'
               + '{btn}</div>')


def fresh(c):
    """How current a card's curated summary is."""
    n, total = len(c.get("new_docs", [])), len(c.get("docs", []))
    if n:
        return f'<span class="pill w-review" title="Linked sources the summary does not cover yet">{n} new source{"s" if n != 1 else ""} since the summary</span>'
    return f'<span class="pill w-done" title="The summary covers every linked source">Summary covers all {total} source{"s" if total != 1 else ""}</span>'


def empty(what, prompt):
    return (f'<div class="empty-state"><p>No {what} yet.</p><p class="muted">Ask Mantis in VS Code:</p>'
            f'<div class="prompt"><code>{esc(prompt)}</code><button class="copy-text nocopy" data-text="{esc(prompt)}">Copy prompt</button></div></div>')


# ---------- Data ----------

def load():
    mp = M / "knowledge" / "map"
    features = json.loads((mp / "features.json").read_text(encoding="utf-8"))
    work = json.loads((mp / "work.json").read_text(encoding="utf-8"))
    titles = {f["slug"]: f["title"] for f in features}
    epics = {e["id"]: e for e in work["epics"]}
    for x in work["epics"] + work["stories"]:
        x["md"] = read(x["file"])[1]
        x["feature_title"] = titles.get(x["feature"], "")
        x["epic_title"] = epics[x["epic"]]["title"] if x.get("epic") in epics else ""
        x["href"] = (f"features/{x['feature']}.html#{'epic' if x['kind'] == 'epic' else 'story'}-{x['anchor']}"
                     if x["feature"] != "none" else f"pages/work-{x['id']}.html")
    for f in features:
        card = read(f["card"])[1]
        f["card_md"], f["summary"] = card, first_sentence(card)
        f["page_md"], f["page_status"] = None, ""
        if f["page"]:
            fm, f["page_md"] = read(f["page"])
            f["page_status"] = fm.get("status", "")
        mine = {x["id"]: x for x in work["epics"] + work["stories"] if x["feature"] == f["slug"]}
        f["epics"] = [mine[e["id"]] for e in f["epics"]]
        f["stories"] = [mine[s["id"]] for s in f["stories"]]
        f["updated"] = max([f["updated"]] + [x["updated"] for x in mine.values() if x["updated"]])
        f["open"] = len(f["open_gaps"])
        f["status"] = f["status"] if f["status"] in STATUS else "discovery"
    later = []
    readme = (M / "knowledge" / "features" / "README.md").read_text(encoding="utf-8")
    m = re.search(r"(?ms)^## Roadmap items with no card yet.*?\n(\|.+?)(?:\n\n|\Z)", readme)
    if m:
        rows = [[c.strip() for c in r.strip().strip("|").split("|")] for r in m.group(1).strip().split("\n")[2:]]
        later = [{"title": r[0], "note": re.sub(r"\s+", " ", clean(r[1])).strip()} for r in rows if r and r[0]]
    return features, later, work["epics"] + work["stories"], epics


def load_topics():
    p = M / "knowledge" / "map" / "topics.json"
    topics = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    for t in topics:
        t["card_md"] = read(t["card"])[1]
        t["summary"] = first_sentence(t["card_md"], 220)
        t["open"] = sum(1 for o in OPEN if o["kind"] in ("gap", "assumption", "conflict") and {d["id"] for d in o["docs"]} & set(t["docs"]))
    return topics


def library_items(features, work):
    items = []
    pages = {f["page"]: f for f in features if f["page"]}
    for x in work:
        items.append({"kind": "Epic" if x["kind"] == "epic" else "Story", "title": x["title"], "href": x["href"],
                      "status": x["status"], "updated": x["updated"], "where": x["feature_title"] or "No feature"})
    for p in sorted((M / "outputs").rglob("*.md")):
        rel = p.relative_to(M).as_posix()
        if rel.startswith(("outputs/epics/", "outputs/user-stories/")):
            continue
        fm, body = front_matter(p.read_text(encoding="utf-8"))
        kind = "Confluence page" if "/confluence/" in rel else "Knowledge doc"
        h = re.search(r"(?m)^#\s+(.+)$", body)
        title = fm.get("title") or (h.group(1).strip() if h else p.stem.replace("-", " ").capitalize())
        f = pages.get(rel)
        items.append({"kind": kind, "title": re.sub(ID, "", title).strip(), "status": fm.get("status", ""),
                      "updated": fm.get("updated", ""), "where": f["title"] if f else "",
                      "href": f"features/{f['slug']}.html#page" if f else f"pages/{p.stem}.html", "md": None if f else body,
                      "file": rel})
    return items


def backlog():
    bp = ROOT / "docs" / "project" / "IMPROVEMENT_BACKLOG.md"   # local project history; absent on a fresh clone
    text = bp.read_text(encoding="utf-8") if bp.exists() else "# IMPROVEMENT_BACKLOG\n"
    out = []
    for blk in re.split(r"(?m)^### ", text)[1:]:
        head, _, body = blk.partition("\n")
        rid, _, title = head.partition(":")
        f = lambda k: " ".join((re.search(r"\*\*%s:\*\*\s*(.+?)(?=\n\*\*|\n---|\Z)" % k, body, re.S) or [None, ""])[1].split())
        status = f("Status")
        word = status.split(" (")[0].split()[0].strip(",.;") if status else "Parked"
        out.append({"id": rid.strip(), "title": title.strip(), "status": "In" if word == "In" else word,
                    "size": f("Complexity").split(" ")[0], "value": f("Expected Value").split(" ")[0],
                    "body": body.replace("\n---", "").strip()})
    return out


# ---------- Pages ----------

def page_home(features, later, work, items, built):
    counts = {k: sum(1 for f in features if f["status"] == k) for k in STATUS}
    counts["none"] = len(later)
    tiles = "".join(f'<a class="stat {STATUS[k][1]}" href="roadmap.html#status={k}"><b>{counts[k]}</b><span>{STATUS[k][0]}</span></a>' for k in STATUS)
    recent = sorted(features, key=lambda f: f["updated"], reverse=True)[:5]
    rec = "".join(f'<a class="row" href="features/{f["slug"]}.html"><span class="row-t">{esc(f["title"])}</span>'
                  f'{prio_pill(f["priority"])}{pill(*STATUS[f["status"]])}<span class="muted">{esc(f["updated"])}</span></a>' for f in recent)
    # Needs attention: one list of everything waiting on the owner, most useful first.
    att = []
    waiting = sum(1 for o in OPEN if o["status"] != "Open")
    names = sum(1 for o in OPEN if o["kind"] in ("name", "term"))
    if waiting:
        att.append(("review.html", f"{waiting} open question{'s' if waiting != 1 else ''} with a likely answer, waiting for your decision", "Decide"))
    if names:
        att.append(("review.html", f"{n_(names, 'name or term', 'names and terms')} to confirm", "Answer"))
    for x in work:
        if x["status"] in ("draft", "review") and x["file"] not in FOCUS.get("archived_work", []) and not archived(x["feature"]):
            att.append((x["href"], f'{"Epic" if x["kind"] == "epic" else "Story"} "{x["title"]}" is {WORK[x["status"]][0].lower()}', "Review"))
    for c in features + TOPICS:
        if c.get("new_docs"):
            att.append((("features/" if c in features else "topics/") + c["slug"] + ".html",
                        f'{c["title"]}: {len(c["new_docs"])} new source(s) not yet in its summary; ask Mantis to refresh it', "Refresh"))
    hp = M / "knowledge" / "map" / "health.json"
    for i in (json.loads(hp.read_text(encoding="utf-8"))["items"] if hp.exists() else []):
        if i["level"] == "warn" or i["area"] == "Inbox":
            att.append(("health.html", f'{i["area"]}: {plain(i["msg"], 220)}', "Fix" if i["level"] == "warn" else "Check"))
    wk = "".join(f'<a class="row att" href="{h}"><span class="row-t">{esc(m)}</span><span class="tag">{esc(a)}</span></a>' for h, m, a in att[:9]) \
        or '<p class="empty">Nothing needs you right now.</p>'
    # My focus, in the owner's own order (focus.json "following"), with the signals that help pick what to do first.
    by_slug = {c["slug"]: (c, c in features) for c in features + TOPICS}
    mine = [by_slug[s] for s in FOCUS["following"] if s in by_slug]
    waiting_of = lambda slug: sum(1 for o in OPEN if o["status"] != "Open" and slug in o["features"])

    def focus_row(i, c, feat):
        sig = []
        if waiting_of(c["slug"]):
            sig.append(f'<span class="pill w-jira" title="Open questions with a likely answer">{waiting_of(c["slug"])} to decide</span>')
        if c.get("new_docs"):
            sig.append(f'<span class="pill w-review" title="Sources not yet in the summary">{len(c["new_docs"])} new</span>')
        sig.append(f'<span class="muted small f-open">{c["open"]} open</span>' if c.get("open") else '<span class="f-open"></span>')
        sig.append(pill(*STATUS[c["status"]]) if feat else '<span class="tag">Topic</span>')
        return (f'<li class="f-row" draggable="true" data-slug="{c["slug"]}"><span class="t-grip" title="Drag to rank">⋮⋮</span><span class="f-rank">{i}</span>'
                f'<a class="row-t" href="{"features" if feat else "topics"}/{c["slug"]}.html">{esc(c["title"])}</a><span class="f-sig">{"".join(sig)}</span>'
                f'<span class="f-move nocopy"><button type="button" data-m="-1" title="Move up">↑</button><button type="button" data-m="1" title="Move down">↓</button></span></li>')

    foc = (('<input type="search" id="f-filter" placeholder="Filter my focus…" aria-label="Filter my focus">' if len(mine) > 8 else "")
           + '<ol class="focus-list" id="focus-list">' + "".join(focus_row(i + 1, c, f) for i, (c, f) in enumerate(mine)) + "</ol>"
           + '<p class="muted small f-hint">Drag or use ↑ ↓ to rank: put what you will tackle first at the top.</p>') if mine \
        else '<p class="empty">You follow nothing yet. On <a href="topics.html">Topics</a>, press ☆ Follow on the subjects you own.</p>'
    body = f"""
<section class="hero hero-compact"><div><p class="hello" id="hello">Hello</p><h1>What needs you today</h1></div>
<a class="btn" href="today.html">Open today's list →</a></section>
{INBOX_STRIP.format(btn=job_btn("process-inbox", "Process inbox", cls="btn"))}
<section class="stats">{tiles}</section>
<div class="grid2">
<div class="stack"><section class="panel-box"><div class="box-h"><h2>Needs attention <span class="muted">{len(att)}</span></h2><a href="health.html">Health →</a></div>{wk}</section>
<a class="link-card" href="topics.html"><b>Topics</b><span>{n_(len(TOPICS), "subject")} beyond the roadmap, each summarised on one page</span></a>
<a class="link-card" href="work.html"><b>Epics &amp; stories</b><span>{n_(sum(1 for x in work if x["kind"] == "epic"), "epic")}, {n_(sum(1 for x in work if x["kind"] == "story"), "story", "stories")}, by status</span></a>
<a class="link-card" href="library.html"><b>Library</b><span>{n_(len(items), "page")}, epics and stories ready to copy</span></a></div>
<section class="panel-box"><div class="box-h"><h2>My focus <span class="muted">{len(mine)}</span></h2><a href="topics.html">Choose topics →</a></div>{foc}</section>
</div>"""
    return shell("Home", body, active="home", built=built)


def page_roadmap(features, later, built):
    data = [{k: f[k] for k in ("slug", "title", "type", "status", "status_note", "priority", "jira", "estimate", "updated", "summary", "open")}
            | {"epics": len(f["epics"]), "page": bool(f["page"]), "stories": len(f["stories"]),
               "storiesDone": sum(1 for s in f["stories"] if s["status"] in ("in-jira", "done"))}
            for f in features if on_roadmap(f, True)]
    for f in data:
        f["url"] = f"features/{f['slug']}.html"
    for t in TOPICS:
        if on_roadmap(t, False):
            fm = read(t["card"])[0]
            data.append({"slug": t["slug"], "url": f"topics/{t['slug']}.html", "title": t["title"], "type": "topic",
                         "status": fm.get("status", "discovery") if fm.get("status") in STATUS else "discovery", "status_note": "",
                         "priority": fm.get("priority", "") if fm.get("priority") in ("P1", "P2", "P3") else "", "jira": "none",
                         "estimate": "", "updated": t["updated"], "summary": t["summary"], "open": t["open"], "epics": 0,
                         "page": False, "stories": 0, "storiesDone": 0})
    data += [{"slug": "", "title": l["title"], "type": "feature", "status": "none", "status_note": "", "priority": "", "jira": "",
              "estimate": "", "updated": "", "summary": l["note"], "open": 0, "epics": 0, "page": False, "stories": 0, "storiesDone": 0} for l in later]
    labels = {k: v[0] for k, v in STATUS.items()}
    chips = "".join(f'<button data-v="{k}">{v[0]}</button>' for k, v in STATUS.items())
    body = f"""
<div class="page-h"><div><h1>Roadmap</h1><p class="lead">Your roadmap: the roadmap features plus any topic you added. Add or remove items on the <a href="topics.html">Topics</a> page.</p></div>
<div class="seg" id="view"><button data-v="board" class="on">Board</button><button data-v="list">List</button></div></div>
<div class="toolbar">
<input id="q" type="search" placeholder="Search topics…" aria-label="Search topics">
<div class="chips" id="f-status"><button data-v="all" class="on">All</button>{chips}</div>
<div class="chips" id="f-prio"><button data-v="all" class="on">Any priority</button><button data-v="P1">P1</button><button data-v="P2">P2</button><button data-v="P3">P3</button></div>
</div>
<div id="board"></div><div id="list" hidden></div>
<script id="data" type="application/json">{json.dumps({"items": data, "labels": labels})}</script>"""
    return shell("Roadmap", body, active="roadmap", built=built)


def story_list(stories, epics_by_id, base_href=""):
    """Stories grouped by epic, for the side panel."""
    groups = {}
    for s in stories:
        groups.setdefault(s["epic"] if s["epic"] in epics_by_id else "", []).append(s)
    out = []
    for key in sorted(groups, key=lambda k: (k == "", epics_by_id[k]["title"] if k else "")):
        name = f'Epic: {epics_by_id[key]["title"]}' if key else "Not in an epic"
        out.append(f'<p class="grp">{esc(name)}</p>')
        out += [f'<a class="story" href="{base_href}#story-{s["anchor"]}" data-anchor="story-{s["anchor"]}"><span><span class="k-ico k-story">▤</span>{esc(s["title"])}</span>{work_pill(s["status"])}</a>' for s in groups[key]]
    return "".join(out)


def page_feature(f, features, epics_by_id, built):
    label, cls = STATUS[f["status"]]
    switch = "".join(f'<option value="{x["slug"]}.html"{" selected" if x is f else ""}>{esc(x["title"])} · {STATUS[x["status"]][0]}</option>' for x in features if x is f or not archived(x["slug"]))
    meta = [prio_pill(f["priority"]), pill(label, cls)]
    if f["type"] == "workstream":
        meta.append('<span class="tag">Platform workstream</span>')
    if f["jira"] and f["jira"] != "none":
        meta.append(f'<button class="pill p-jira copy-text" data-text="{esc(f["jira"])}" title="Copy the Jira key">Jira {esc(f["jira"])}</button>')
    if f["estimate"]:
        meta.append(f'<span class="muted small">2027 estimate: {esc(f["estimate"])}</span>')
    meta.append(fresh(f))
    if archived(f["slug"]):
        meta.insert(0, '<span class="tag">Archived</span>')
    note = f'<p class="muted">{esc(f["status_note"])}</p>' if f["status_note"] else ""
    t = f["title"]
    epics = f["epics"]
    epic_tab = f'#epic-{epics[0]["anchor"]}' if epics else "#epic-none"
    epic_label = '<span class="k-ico k-epic">◆</span>' + ("Epic" if len(epics) <= 1 else f"Epics ({len(epics)})")
    tabs = (f'<a href="#overview" data-match="overview">One-pager</a>'
            f'<a href="#page" data-match="page">Confluence page{" " + work_pill(f["page_status"]) if f["page_status"] else ""}</a>'
            f'<a href="{epic_tab}" data-match="epic-">{epic_label}{" " + work_pill(epics[0]["status"]) if len(epics) == 1 else ""}</a>')
    panels = [("overview", copy_bar("Copy one-pager"), render(f["card_md"])),
              ("page", copy_bar("Copy page", f["page"]) if f["page_md"] else "",
               render(f["page_md"]) if f["page_md"] else empty("Confluence page", f"Write the Confluence page for {t}"))]
    if not epics:
        panels.append(("epic-none", "", empty("epic", f"Write the epic for {t}")))
    for e in epics:
        others = "".join(f'<a class="chip{" on" if o is e else ""}" href="#epic-{o["anchor"]}">{esc(o["title"])}</a>' for o in epics) if len(epics) > 1 else ""
        head = f'<div class="epic-switch nocopy">{others}</div>' if others else ""
        panels.append((f"epic-{e['anchor']}", copy_bar("Copy epic", e["file"]), head + render(e["md"], breaks=True, sections=False)))
    for s in f["stories"]:
        ep = f'<p class="muted small nocopy">Story{" in epic " + esc(s["epic_title"]) if s["epic_title"] else ", not in an epic"} · {WORK.get(s["status"], (s["status"],))[0]}</p>'
        panels.append((f"story-{s['anchor']}", copy_bar("Copy story", s["file"]), ep + render(s["md"], breaks=True, sections=False)))
    ph = "".join(f'<div class="tab-panel" id="p-{k}" hidden>{bar}<article class="doc">{body}</article></div>' for k, bar, body in panels)
    done = sum(1 for s in f["stories"] if s["status"] in ("in-jira", "done"))
    stories = story_list(f["stories"], epics_by_id) or empty("stories", f"Write the user stories for {t}")
    body = f"""
<div class="crumbs"><a href="../roadmap.html">Roadmap</a><span>›</span>
<select id="switch" aria-label="Go to another topic">{switch}</select></div>
<div class="feat-h"><h1>{esc(t)}</h1><div class="meta">{"".join(m for m in meta if m)}</div>{note}
<p class="muted small">Updated {esc(f["updated"])}{f" · {f['open']} open question" + ("s" if f["open"] != 1 else "") if f["open"] else ""}</p>
<div class="card-acts">{job_btn("refresh-card", "Refresh summary", arg=f["slug"], cls="mini")}{job_btn("rebuild", "Rebuild", ai=False, cls="mini")}</div></div>
<div class="feat">
<div class="feat-main"><nav class="tabs">{tabs}</nav>{ph}</div>
<aside class="side"><div class="side-h"><h2>Stories</h2><span class="muted small">{done}/{len(f["stories"])} in Jira</span></div>{stories}{feature_entities(f["slug"])}</aside>
</div>"""
    return shell(t, body, base="../", active="roadmap", built=built)


def page_work(work, features, built):
    data = [{k: x[k] for k in ("kind", "title", "status", "feature", "feature_title", "epic_title", "jira", "updated")}
            | {"href": x["href"], "file": x["file"], "mine": x["feature"] in FOCUS["following"],
               "own": x["file"] in FOCUS.get("archived_work", []), "archived": archived(x["feature"]) or x["file"] in FOCUS.get("archived_work", [])} for x in work]
    feats = "".join(f'<option value="{f["slug"]}">{esc(f["title"])}</option>' for f in features if (f["epics"] or f["stories"]) and not archived(f["slug"]))
    body = f"""<div class="page-h"><div><h1>Epics &amp; stories</h1><p class="lead">Everything written for Jira, by status. Includes generic epics and stories that stand alone.</p></div>
<div class="seg" id="view"><button data-v="board" class="on">Board</button><button data-v="list">List</button></div></div>
<div class="toolbar"><input id="q" type="search" placeholder="Search epics and stories…" aria-label="Search epics and stories">
<div class="chips" id="f-kind"><button data-v="all" class="on">All</button><button data-v="epic">Epics</button><button data-v="story">Stories</button></div>
<select id="f-feature" class="sel" aria-label="Filter by topic"><option value="all">All topics</option><option value="mine">My focus</option><optgroup label="Topic">{feats}<option value="none">No topic</option></optgroup><option value="archived">Archived</option></select></div>
<div id="board"></div><div id="list" hidden></div>
<script id="work" type="application/json">{json.dumps({"items": data, "labels": {k: v[0] for k, v in WORK.items()}})}</script>"""
    return shell("Epics & stories", body, active="work", built=built)


def page_loose(x, work, built):
    """A generic epic or stand-alone story with no feature: its own page."""
    kids = [s for s in work if s["kind"] == "story" and s.get("epic") == x["id"]] if x["kind"] == "epic" else []
    side = (f'<aside class="side"><div class="side-h"><h2>Stories</h2></div>' +
            "".join(f'<a class="story" href="../{s["href"]}"><span>{esc(s["title"])}</span>{work_pill(s["status"])}</a>' for s in kids) +
            "</aside>") if kids else ""
    where = "Generic epic" if x["kind"] == "epic" else (f"Story in epic {esc(x['epic_title'])}" if x["epic_title"] else "Stand-alone story")
    body = f"""<div class="crumbs"><a href="../work.html">Epics &amp; stories</a><span>›</span><span>{esc(x["title"])}</span></div>
<div class="feat-h"><h1>{esc(x["title"])}</h1><div class="meta">{work_pill(x["status"])}<span class="tag">{where}</span>
{f'<button class="pill p-jira copy-text" data-text="{esc(x["jira"])}">Jira {esc(x["jira"])}</button>' if x["jira"] not in ("", "none") else ""}</div></div>
<div class="feat{"" if kids else " solo"}"><div class="feat-main"><div class="tab-panel">{copy_bar("Copy " + ("epic" if x["kind"] == "epic" else "story"), x["file"])}
<article class="doc">{render(x["md"], breaks=True, sections=False)}</article></div></div>{side}</div>"""
    return shell(x["title"], body, base="../", active="work", built=built)


def page_library(items, built):
    rows = "".join(f'<a class="row lib" data-kind="{esc(it["kind"])}" href="{it["href"]}"><span class="row-t">{esc(it["title"])}</span>'
                   f'<span class="tag">{esc(it["kind"])}</span><span class="muted">{esc(it["where"])}</span>{work_pill(it["status"]) if it["status"] else ""}</a>' for it in items)
    kinds = sorted({it["kind"] for it in items})
    body = f"""<div class="page-h"><div><h1>Library</h1><p class="lead">Every page, epic and story Mantis has written. Open one to copy it.</p></div></div>
<div class="toolbar"><div class="chips" id="f-lib"><button data-v="all" class="on">All</button>{"".join(f'<button data-v="{esc(k)}">{esc(k)}s</button>' for k in kinds)}</div></div>
<section class="panel-box">{rows or '<p class="empty">Nothing written yet.</p>'}</section>"""
    return shell("Library", body, active="library", built=built)


def page_single(it, built):
    body = f"""<div class="crumbs"><a href="../library.html">Library</a><span>›</span><span>{esc(it["title"])}</span></div>
<div class="tab-panel">{copy_bar("Copy page", it.get("file"))}<article class="doc">{render(it["md"])}</article></div>"""
    return shell(it["title"], body, base="../", active="library", built=built)


GRAPH = {}  # filled by build() from map/entities.json


def feature_entities(slug, n=10, kind="feature"):
    """Side-panel chips: the people and systems most often named in this card's sources."""
    ranked = sorted(((x["docs"], e) for e in GRAPH.get("entities", []) for x in e["features"]
                     if x["slug"] == slug and x.get("kind", "feature") == kind and e["type"] not in ("concept", "unknown")), key=lambda t: -t[0])[:n]
    if not ranked:
        return ""
    chips = "".join(f'<a class="chip ent t-{e["type"]}" href="../graph.html#e={quote(e["name"])}">{esc(e["name"])}</a>' for _, e in ranked)
    return f'<div class="side-h ents-h"><h2>People and systems</h2></div><div class="ent-chips">{chips}</div>'


def page_graph(built):
    titles = {d: t for d, t in GRAPH.get("titles", {}).items()}
    keep = [e for e in GRAPH.get("entities", []) if len(e["docs"]) >= 2 or e["relations"] or e["type"] != "unknown"]
    names = {e["name"] for e in keep}
    data = [{"n": e["name"], "t": e["type"], "a": e["aliases"], "d": len(e["docs"]),
             "docs": [re.sub(ID, "", titles.get(d, "")).strip() for d in e["docs"][:20]],
             "f": [[x["slug"], x["title"], x["docs"], x.get("kind", "feature")] for x in e["features"]],
             "r": [[r["rel"], r["to"], r["dir"]] for r in e["relations"]],
             "l": [[n, w] for n, w in e["neighbours"] if n in names]} for e in keep]
    types = ["system", "person", "team", "organisation", "distributor", "market", "concept", "unknown"]
    chips = "".join(f'<button data-v="{t}">{t.capitalize()}</button>' for t in types)
    body = f"""<div class="page-h"><div><h1>Knowledge graph</h1><p class="lead">The people, systems and places the sources name, and how they connect. Pick one to see its neighbourhood.</p></div></div>
<div class="toolbar"><input id="gq" type="search" placeholder="Search names and aliases…" aria-label="Search entities">
<div class="chips" id="f-type"><button data-v="all" class="on">All</button>{chips}</div></div>
<div class="graph-wrap"><section class="panel-box ent-list" id="ent-list"></section><section class="tab-panel ent-detail" id="ent-detail"></section></div>
<script id="graph" type="application/json">{json.dumps(data, ensure_ascii=False)}</script>"""
    return shell("Graph", body, active="graph", built=built)


def plain(md, limit=6000):
    """Markdown to searchable plain text, with Mantis IDs and repo paths removed."""
    t = clean(md)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"[#*_`>|]+", " ", t)
    t = re.sub(r"-{3,}", " ", t)
    return re.sub(r"\s+", " ", t).strip()[:limit]


def search_index(features, work, items, entries):
    """One record per thing worth finding (IMP-006). Built at no token cost; searched in the browser."""
    idx = []
    add = lambda kind, title, url, text="", where="": idx.append({"k": kind, "t": title, "u": url, "w": where, "x": text})
    for t in TOPICS:
        add("Topic", t["title"], f"topics/{t['slug']}.html", plain(t["card_md"]), n_(len(t['docs']), "source"))
    for f in features:
        u = f"features/{f['slug']}.html"
        add("Roadmap", f["title"], u + "#overview", plain(f["card_md"]), STATUS[f["status"]][0])
        if f["page_md"]:
            add("Confluence page", f["title"], u + "#page", plain(f["page_md"]), f["title"])
    for x in work:
        add("Epic" if x["kind"] == "epic" else "Story", x["title"], x["href"], plain(x["md"]), x["feature_title"] or "No topic")
    for it in items:
        if it.get("md"):
            add(it["kind"], it["title"], it["href"], plain(it["md"]))
    for e in GRAPH.get("entities", []):
        if len(e["docs"]) >= 2 or e["type"] != "unknown":
            add("Entity", e["name"], f"graph.html#e={quote(e['name'])}", "Also called: " + ", ".join(e["aliases"]) if e["aliases"] else "", f"{e['type']}, {n_(len(e['docs']), 'document')}")
            idx[-1]["a"] = "|".join(e["aliases"])
    titles = GRAPH.get("titles", {})
    for p in sorted((M / "02_digests").glob("MANTIS-DOC-*.md"), reverse=True):
        m = re.search(r"(?ms)^## Summary\s*\n(.*?)(?=^## |\Z)", p.read_text(encoding="utf-8"))
        title = re.sub(ID, "", titles.get(p.stem, "")).strip()
        if title:
            add("Source", title, "", plain(m.group(1), 900) if m else "")
    for e in entries:
        add("Mantis backlog", e["title"], "backlog.html", plain(e["body"], 1500), e["id"].replace("MANTIS-", ""))
    for o in OPEN:
        add("Open item", plain(o["topic"], 140), f"review.html#{o['id']}", plain(o["status_full"]), o["id"].replace("MANTIS-", ""))
    return idx


OPEN = []  # filled by build() from map/open-items.json
TOPICS = []  # filled by build() from map/topics.json
FOCUS = {"following": [], "on_roadmap": [], "off_roadmap": [], "archived": []}  # the owner's choices, mantis/knowledge/focus.json


def archived(slug):
    """An archived card is hidden from focus, roadmap, lists and filters; its page, sources and search stay."""
    return slug in FOCUS.get("archived", [])
BADGES = {}  # nav counts, filled by build()


VERDICT_SETS = {
    "name": (("same", "Same thing"), ("different", "Different things"), ("someone", "Someone else must answer")),
    "term": (("answers", "I know what it is"), ("someone", "Someone else must answer")),
}
PLACEHOLDER = {"gap": "Your answer: facts, decision, or what you know so far",
               "name": "Optional: which name Mantis should use, or how they differ",
               "term": "What it stands for and what it is (a system, team, process...)"}


def verdicts(kind):
    opts = VERDICT_SETS.get(kind, (("answers", "Answers it"), ("partly", "Partly answers it"), ("someone", "Someone else must answer")))
    return "".join(f'<button type="button" data-v="{v}">{esc(l)}</button>' for v, l in opts)


def on_roadmap(c, is_feature):
    if archived(c["slug"]):
        return False
    return (c["slug"] not in FOCUS["off_roadmap"]) if is_feature else (c["slug"] in FOCUS["on_roadmap"])


def page_topics(topics, features, built):
    cards = [(f, True) for f in features] + [(t, False) for t in topics]

    def tile(c, feat):
        url = ("features/" if feat else "topics/") + c["slug"] + ".html"
        fol, road = c["slug"] in FOCUS["following"], on_roadmap(c, feat)
        kind = "" if feat else '<span class="tag">Topic</span>'
        arc = archived(c["slug"])
        return (f'<div class="tile topic-tile" data-slug="{c["slug"]}" data-following="{int(fol)}" data-roadmap="{int(road)}" data-archived="{int(arc)}">'
                f'<h3><a href="{url}">{esc(c["title"])}</a></h3>{kind}<p>{esc(c["summary"])}</p>'
                f'<div class="facts"><span><b>{len(c["docs"])}</b> {"source" if len(c["docs"]) == 1 else "sources"}</span>' + (f'<span><b>{c["open"]}</b> open {"question" if c["open"] == 1 else "questions"}</span>' if c.get("open") else "")
                + (f'<span class="warn-text">{len(c["new_docs"])} new since summary</span>' if c.get("new_docs") else '<span>Summary current</span>') + '</div>'
                f'<div class="tile-acts nocopy"><button type="button" class="act follow{" on" if fol else ""}" data-a="follow" aria-pressed="{str(fol).lower()}">{"★ Following" if fol else "☆ Follow"}</button>'
                f'<button type="button" class="act road{" on" if road else ""}" data-a="roadmap" aria-pressed="{str(road).lower()}">{"✓ On roadmap" if road else "+ Roadmap"}</button>'
                f'<button type="button" class="act arc" data-a="archive" title="Hide this card everywhere; restore it from the Archived tab">{"Restore" if arc else "Archive"}</button></div></div>')

    n_f = sum(1 for c, f in cards if c["slug"] in FOCUS["following"] and not archived(c["slug"]))
    n_r = sum(1 for c, f in cards if on_roadmap(c, f))
    n_a = sum(1 for c, f in cards if archived(c["slug"]))
    body = f"""<div class="page-h"><div><h1>Topics</h1><p class="lead">One summary page per subject, each kept up to date from its sources. Follow the ones you are responsible for, and choose which belong on your roadmap.</p></div></div>
<div class="toolbar"><div class="seg" id="ttab"><button data-v="focus" class="on">My focus <span class="muted">{n_f}</span></button><button data-v="roadmap">On roadmap <span class="muted">{n_r}</span></button><button data-v="all">All <span class="muted">{len(cards) - n_a}</span></button><button data-v="archived">Archived <span class="muted">{n_a}</span></button></div>
<input id="tq" type="search" placeholder="Filter…" aria-label="Filter topics"><div class="bulk nocopy" id="t-bulk" aria-label="Change several at once"></div></div>
<p class="empty" id="t-empty" hidden>Nothing here yet. Open <b>All</b> and press ☆ Follow on the subjects you own.</p>
<div class="later topic-grid">{"".join(tile(c, f) for c, f in cards)}</div>"""
    return shell("Topics", body, active="topics", built=built)


def page_topic(t, topics, built):
    switch = "".join(f'<option value="{x["slug"]}.html"{" selected" if x is t else ""}>{esc(x["title"])}</option>' for x in topics if x is t or not archived(x["slug"]))
    body = f"""
<div class="crumbs"><a href="../topics.html">Topics</a><span>›</span>
<select id="switch" aria-label="Go to another topic">{switch}</select></div>
<div class="feat-h"><h1>{esc(t["title"])}</h1><div class="meta"><span class="tag">Topic</span>{'<span class="tag">Archived</span>' if archived(t["slug"]) else ""}{fresh(t)}<span class="muted small">{n_(len(t["docs"]), "source")}{f" · {n_(t['open'], 'open question')}" if t["open"] else ""}</span></div>
<div class="card-acts">{job_btn("refresh-card", "Refresh summary", arg=t["slug"], cls="mini")}{job_btn("rebuild", "Rebuild", ai=False, cls="mini")}</div></div>
<div class="feat">
<div class="feat-main"><div class="tab-panel" id="p-overview">{copy_bar("Copy summary")}<article class="doc">{render(t["card_md"])}</article></div></div>
<aside class="side">{feature_entities(t["slug"], 14, "topic") or '<p class="empty">No people or systems named yet.</p>'}</aside>
</div>"""
    return shell(t["title"], body, base="../", active="topics", built=built)


def page_people(built):
    """Everyone in knowledge/people.md (MANTIS-IMP-022). Follow-ups, meetings and briefs are filled live by app.js."""
    import people as people_mod
    cards = []
    for p in people_mod.load():
        f = p["fields"]
        def clean(v):   # citations stay in the knowledge base; the page shows them on hover only
            cites = re.findall(r"\(([^()]*(?:MANTIS-|User knowledge|Confluence|Owner)[^()]*)\)", v)
            text = re.sub(r"\s*\([^()]*(?:MANTIS-|User knowledge|Confluence|Owner)[^()]*\)", "", v).strip()
            proposed = text.startswith("*proposed:*")
            text = esc(text.replace("*proposed:*", "").strip())
            cite = re.sub(r"MANTIS-[A-Z]+-\d+", "a source document", "; ".join(cites))
            return (('<span class="tag">Proposed</span> ' if proposed else "") + text, cite)
        rows = ""
        for k, v in (("role", p["role"]), ("team", p["team"]), ("channel", p["channel"]), ("briefing style", p["briefing"]), ("notes", p["notes"])):
            if v:
                text, cite = clean(v)
                rows += f'<div class="pp-f"><span class="muted small">{esc(k.capitalize())}</span><span{f" title=\"Source: {esc(cite)}\"" if cite else ""}>{text}</span></div>'
        cards.append(f'<article class="tile person" id="{esc(p["slug"])}" data-name="{esc(p["name"])}"><h3><span>{esc(p["name"])}</span>'
                     f'<span class="pp-n nocopy" hidden></span></h3>{rows}'
                     f'<div class="pp-live nocopy"></div>'
                     f'<div class="tile-acts nocopy">{job_btn("meeting-brief", "Brief me", arg=p["name"], cls="act")}'
                     f'<button type="button" class="act pp-add" data-person="{esc(p["name"])}">+ Follow-up</button></div></article>')
    body = f"""<div class="page-h"><div><h1>People</h1><p class="lead">Everyone you work with: role, how to reach them, how they like to be briefed, and what is open with them. Edit details in the knowledge base (people file); follow-ups and briefs update live.</p></div>
<div class="toolbar"><input type="search" id="pp-filter" placeholder="Filter people…" aria-label="Filter people"></div></div>
<section class="panel-box pp-meet nocopy"><div class="box-h"><h2>Your regular meetings</h2><span class="muted small">Briefs and deadline suggestions use these</span></div><div id="pp-meetings"><p class="muted small">Loading…</p></div></section>
<div class="later people-grid">{"".join(cards) or '<p class="empty">No people yet. Add them to mantis/knowledge/people.md.</p>'}</div>"""
    return shell("People", body, active="people", built=built)


def page_decisions(built):
    """Every logged decision (MANTIS-IMP-027): what was chosen, why, and what else was considered."""
    rows = []
    for f in sorted((M / "knowledge" / "registers" / "decisions").glob("MANTIS-DEC-*.md"), reverse=True):
        t = f.read_text(encoding="utf-8")
        field = lambda k: re.sub(r"\s+", " ", (re.search(rf"\*\*{k}:\*\*\s*(.+?)(?=\n- \*\*|\Z)", t, re.S) or [None, ""])[1]).strip()
        clean = lambda v: re.sub(r"\s*\(?MANTIS-[A-Z]+-\d+\)?[;,]?", "", v).replace("()", "").strip()
        when, what = field("Date"), clean(field("Decision"))
        if not what:
            continue
        rows.append(f'<article class="tile dec"><p class="muted small">{esc(when)}</p><h3>{esc(what)}</h3>'
                    + "".join(f'<div class="pp-f"><span class="muted small">{lab}</span><span>{esc(clean(field(k)))}</span></div>'
                              for k, lab in (("Reasoning", "Why"), ("Alternatives considered", "Not chosen"), ("Consequences", "What it means")) if field(k))
                    + "</article>")
    body = f"""<div class="page-h"><div><h1>Decisions</h1><p class="lead">Choices made along the way, newest first: what was decided, why, and what else was on the table. Facts live on the cards; decisions live here, so a new source never silently rewrites why something was done.</p></div></div>
<div class="dec-list">{"".join(rows) or '<p class="empty">No decisions logged yet.</p>'}</div>"""
    return shell("Decisions", body, active="decisions", built=built)


def page_today(built):
    """The owner's task list. A static shell; app.js loads and saves the tasks through tools/serve.py."""
    est = "".join(f'<option value="{v}">{l}</option>' for v, l in (("0", "Time?"), ("15", "15 min"), ("30", "30 min"), ("60", "1 hour"),
                                                                    ("120", "2 hours"), ("240", "Half day"), ("480", "Full day")))
    body = f"""<div class="page-h today-h"><div><p class="hello" id="hello">Hello</p><h1 id="t-date">Today</h1><p class="lead" id="t-sum">Loading your tasks…</p></div></div>
<p class="empty" id="t-offline" hidden>Your tasks are saved by the Mantis site server. Open the site at http://localhost:8000 (it starts with each Claude Code session, or run <code>python tools/serve.py --open</code>).</p>
<div class="today-grid"><div class="today-main">
<form id="t-add" class="t-add" autocomplete="off">
<input id="t-title" type="text" placeholder="Add a task and press Enter" aria-label="New task" maxlength="300">
<div class="t-add-more"><span class="prio-seg" id="t-prio" role="group" aria-label="Priority" data-value=""><button type="button" data-p="high">High</button><button type="button" data-p="medium">Medium</button><button type="button" data-p="low">Low</button></span>
<select id="t-est" class="sel sel-sm" aria-label="Estimated time">{est}</select>
<button type="button" class="dp-btn" id="t-when" data-kind="when" data-value="" aria-haspopup="dialog" title="Which day it shows up on your list">Today</button>
<button type="button" class="dp-btn" id="t-due" data-kind="due" data-value="" aria-haspopup="dialog" title="Deadline">No due date</button>
<input id="t-contact" type="text" placeholder="Who to reach out to" maxlength="120" aria-label="Who to reach out to">
<button class="btn" type="submit">Add</button></div></form>
<section id="t-due-sug" class="due-sug nocopy" hidden></section>
<section class="panel-box t-box"><div class="box-h"><h2>Today's list</h2><span class="muted small" id="t-total"></span><button class="mini" id="t-sortp" type="button" title="Order today's list by priority, then due date">Sort by priority</button></div>
<ol id="t-list" class="t-list"></ol>
<p class="muted small t-hint">Drag to rank, or Alt+↑/↓. Click a task for notes, dates and more.</p></section>
<details class="grp-box" id="t-sched-box"><summary><h2>Scheduled for later <span class="muted" id="t-sched-n"></span></h2></summary><section class="panel-box"><p class="muted small t-hint">Each task comes back to Today on its day. Changed your mind? Press <b>Bring to today</b>.</p><ol id="t-sched" class="t-list"></ol></section></details>
<details class="grp-box" id="t-park-box"><summary><h2>Parked <span class="muted" id="t-park-n"></span></h2></summary><section class="panel-box"><p class="muted small t-hint">Out of the way with no date. Bring them back when they matter again.</p><ol id="t-park" class="t-list"></ol></section></details>
<details class="grp-box" id="t-done-box"><summary><h2>Done <span class="muted" id="t-done-n"></span></h2></summary><section class="panel-box"><p class="muted small t-hint">Untick to reopen. Done items move to the archive the next day and are deleted after 7 days.</p><ol id="t-done" class="t-list"></ol></section></details>
<details class="grp-box" id="t-bin-box"><summary><h2>Recently deleted <span class="muted" id="t-bin-n"></span></h2></summary><section class="panel-box"><p class="muted small t-hint">Kept for 7 days, then cleaned up. Restore anything you deleted by mistake.</p><ol id="t-bin" class="t-list"></ol></section></details>
</div>
<aside class="today-side" aria-label="Supporting your day">
<section id="t-away" class="side-card away-card nocopy" hidden></section>
<section id="t-brief" class="side-card"></section>
<div id="t-people" class="side-stack nocopy"></div>
</aside></div>"""
    return shell("Today", body, active="today", built=built)


def page_health(built):
    p = M / "knowledge" / "map" / "health.json"
    h = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"date": "", "items": []}
    lab = {"warn": ("Fix", "s-ref plain"), "todo": ("To do", "s-build plain"), "info": ("Note", "s-none plain")}   # "plain": a dot, not a stage icon
    rows = "".join(f'<div class="row health-row">{pill(*lab[i["level"]])}<span class="tag">{esc(i["area"])}</span><span class="row-t health-msg">{esc(i["msg"])}</span></div>' for i in h["items"])
    body = f"""<div class="page-h"><div><h1>Health</h1><p class="lead">What Mantis noticed on its last check ({esc(h["date"])}). Cleanup of temporary files runs weekly by itself; anything that needs a decision is listed here.</p></div></div>
<section class="panel-box">{rows or '<p class="empty">All clear.</p>'}</section>
<section class="panel-box jobs-box" id="jobs"><div class="box-h"><h2>Background jobs</h2><span class="muted small" id="job-quota"></span></div>
{INBOX_STRIP.format(btn=job_btn("process-inbox", "Process inbox", cls="btn"))}
<div class="job-acts">{job_btn("rebuild", "Rebuild everything", ai=False)}{job_btn("daily-brief", "Prepare today's brief")}</div>
<p class="muted small job-note">Buttons marked ✦ use Claude on your normal subscription quota; the others are free. Jobs that hit a rule needing your decision stop and say "needs you" instead of guessing.</p>
<div id="job-list"></div></section>"""
    return shell("Health", body, active="health", built=built)


def page_review(features, built):
    names = {f["slug"]: f["title"] for f in features}
    groups = {}
    for o in OPEN:
        for s in (["~names"] if o["kind"] in ("name", "term") else o["features"] or [""]):
            groups.setdefault(s, []).append(o)
    order = [f["slug"] for f in features if f["slug"] in groups] + [s for s in ("", "~names") if s in groups]
    names["~names"] = "Names and terms to confirm"
    cls = {"Open": "s-ref", "Potential resolution": "s-build"}

    FIRST = ("What's missing", "Statement A", "Statement B", "Statement", "Claim")

    def context(o):
        """What the owner needs to answer: the question itself, the evidence so far, and the likely answer."""
        det = [(k, v) for k, v in o.get("detail", []) if not k.startswith("Evidence Strength")]
        EVID = ("Evidence so far", "Partial resolution", "Settled", "Update", "Overall status", "Resolution")
        main = [(k, v) for k, v in det if k.split(" (")[0] in FIRST]
        evid = [(k, v) for k, v in det if k.startswith(EVID)] if o["status"] != "Open" else []
        rest = [(k, v) for k, v in det if k.split(" (")[0] not in FIRST and (k, v) not in evid]
        strength = next((v for k, v in o.get("detail", []) if k.startswith("Evidence Strength")), "")
        html_ = "".join(f'<div class="oi-q"><b>{esc(k)}</b><p>{esc(v)}</p></div>' for k, v in main)
        if o["status"] != "Open":
            likely = o["status_full"].split("(", 1)[1].rstrip(")") if "(" in o["status_full"] else ""
            ev = "".join(f'<p><b>{esc(k)}:</b> {esc(v)}</p>' for k, v in evid)
            html_ += (f'<div class="oi-likely"><b>Likely answer</b>{f"<p>{esc(likely)}</p>" if likely else ""}{ev or ("" if likely else "<p>See the evidence below.</p>")}'
                      f'<button type="button" class="btn quick-confirm nocopy" data-q="{esc(o["id"])}">✓ Confirm and close</button>'
                      f'<span class="muted small"> or answer below if it is not right.</span></div>')
        if rest:
            html_ += '<details class="oi-more"><summary>Notes and evidence so far</summary>' + "".join(
                f'<p><b>{esc(k)}:</b> {esc(v)}</p>' for k, v in rest) + "</details>"
        if strength:
            html_ += f'<p class="muted small">Evidence strength: {esc(strength)}</p>'
        return html_ or f'<p>{esc(o["status_full"])}</p>'

    def row(o, flat=False):
        docs = "".join(f"<li>{esc(d['id'].replace('MANTIS-', ''))} {esc(d['title'])}</li>" for d in o["docs"])
        tops = [names.get(s, "No topic") for s in (o["features"] if o["kind"] not in ("name", "term") else ["~names"])]
        more = f'<span class="tag oi-where" title="{esc(", ".join(tops[3:]))}">+{len(tops) - 3} more</span>' if len(tops) > 3 else ""
        where = (f'<span class="oi-tags">{"".join(f"<span class=\"tag oi-where\">{esc(x)}</span>" for x in tops[:3])}{more}</span>') if flat else ""
        anchor = f'id="{esc(o["id"])}" ' if flat else ""   # only the one-list copy carries the id, so links land once
        return (f'<details class="bl oi" {anchor}data-qid="{esc(o["id"])}" data-kind="{o["kind"]}" data-status="{esc(o["status"])}"><summary>'
                f'<span class="bl-id">{esc(o["id"].replace("MANTIS-", ""))}</span><span class="oi-main"><span class="row-t">{esc(re.sub(r" ?[(]MANTIS-[A-Z]+-[0-9]+(?:[,;] ?MANTIS-[A-Z]+-[0-9]+)*[)]", "", o["topic"]))}</span>{where}</span>'
                f'{pill(o["status"], cls.get(o["status"], "s-none") + " plain") if o["status"] != "Open" else ""}<span class="muted small oi-date">{esc(o["raised"])}</span></summary>'
                f'<div class="doc">{context(o)}'
                f'{"<p class=oi-named><b>Named in:</b></p><ul>" + docs + "</ul>" if docs else ""}'
                f'<p class="muted small">Full entry: <code>python tools/entry.py show {esc(o["id"])}</code></p>'
                f'<div class="answer" data-id="{esc(o["id"])}" data-topic="{esc(o["topic"][:300])}"><p class="answer-sent" hidden>Answer sent. Mantis will process it in the next session.</p>'
                f'<div class="answer-form"><div class="seg verdict">{verdicts(o["kind"])}</div>'
                f'<textarea rows="3" placeholder="{esc(PLACEHOLDER.get(o["kind"], PLACEHOLDER["gap"]))}"></textarea>'
                f'<input class="who" type="text" placeholder="Who should answer it? (name or role)" hidden>'
                f'<button type="button" class="btn-line answer-discard" hidden>Discard this answer</button></div></div></div></details>')

    secs = "".join(f'<details class="grp-box oi-group" data-group="{esc(s)}"><summary><h2>{esc(names.get(s, "Not linked to a roadmap topic"))} '
                   f'<span class="muted oi-n">{len(groups[s])}</span></h2></summary><div class="panel-box">{"".join(row(o) for o in groups[s])}</div></details>' for s in order)
    uniq = sorted(OPEN, key=lambda o: (o.get("raised", ""), o["id"]), reverse=True)
    flat = f'<section class="oi-flat" id="oi-flat"><div class="panel-box">{"".join(row(o, flat=True) for o in uniq)}</div></section>'
    n_gap = sum(1 for o in OPEN if o["kind"] == "gap")
    n_pot = sum(1 for o in OPEN if o["status"] != "Open")
    body = f"""<div class="page-h"><div><h1>Open items</h1><p class="lead">{len(OPEN)} questions Mantis is tracking, newest first. Open one to answer it; answer several, then submit them together.</p></div></div>
<div class="answers-strip oi-banner nocopy" hidden><b>Your submitted answers are waiting to be recorded.</b> {job_btn("process-answers", "Process answers", cls="btn")}</div>
{f'<div class="oi-banner nocopy"><b>{n_pot} question{"s have" if n_pot != 1 else " has"} a likely answer.</b> Confirm or correct {"them" if n_pot != 1 else "it"} in a minute. <button type="button" class="btn" data-goto-filter="potential">Show {"them" if n_pot != 1 else "it"}</button></div>' if n_pot else ""}
<div class="toolbar"><div class="chips" id="f-oi"><button data-v="all" class="on">All</button><button data-v="potential">Waiting for your decision · {n_pot}</button><button data-v="gap">Gaps</button><button data-v="conflict">Conflicts</button><button data-v="names">Names and terms</button></div>
<div class="seg" id="oi-view" aria-label="Layout"><button data-v="flat" class="on">One list</button><button data-v="topic">By topic</button></div></div>
<div class="oi-topics-bar nocopy" id="oi-topics-bar" hidden><span class="muted small" id="oi-topics-n"></span><button type="button" class="mini" id="oi-expand">Expand all</button></div>
{flat if OPEN else '<p class="empty">Nothing open.</p>'}<div id="oi-topics" hidden>{secs}</div>
<div class="answer-bar" id="answer-bar" hidden><span id="answer-count"></span><button class="btn-ghost" id="answer-clear" type="button">Clear drafts</button><button class="btn" id="answer-submit" type="button">Submit answers</button></div>"""
    return shell("Open items", body, active="review", built=built)


def page_backlog(entries, built):
    val = {"Transformational": 0, "High": 1, "Medium": 2, "Low": 3}
    size = {"Small": 0, "Medium": 1, "Large": 2, "Very": 3}
    cls = {"In": "s-build", "Parked": "s-none", "Adopted": "s-done", "Rejected": "s-ref"}

    def card(e):
        return (f'<details class="bl" data-status="{esc(e["status"])}"><summary><span class="bl-id">{esc(e["id"].replace("MANTIS-", ""))}</span>'
                f'<span class="row-t">{esc(e["title"])}</span>{pill("In progress" if e["status"] == "In" else e["status"], cls.get(e["status"], "s-none") + " plain")}'
                f'<span class="muted small">{esc(e["size"])} · {esc(e["value"])} value</span></summary>'
                f'<div class="doc">{markdown.markdown(fix_lists(e["body"]), extensions=["tables", "sane_lists"])}</div></details>')

    key = lambda e: (val.get(e["value"], 4), size.get(e["size"], 4), e["id"])
    active = [e for e in entries if e["status"] == "In"]
    parked = sorted([e for e in entries if e["status"] == "Parked"], key=key)
    done = [e for e in entries if e["status"] == "Adopted"]
    rejected = [e for e in entries if e["status"] == "Rejected"]
    group = lambda title, xs, open_: (f'<details class="grp-box"{" open" if open_ else ""}><summary><h2>{title} <span class="muted">{len(xs)}</span></h2></summary>'
                                      f'<section class="panel-box">{"".join(card(e) for e in xs)}</section></details>') if xs else ""
    body = f"""<div class="page-h"><div><h1>Mantis backlog</h1><p class="lead">Ideas for improving Mantis itself. Open work first, then parked ideas by value and size. Finished ones are folded away.</p></div></div>
{group("In progress", active, True)}{group("Parked", parked, True)}{group("Done", done, False)}{group("Rejected", rejected, False)}"""
    return shell("Mantis backlog", body, active="backlog", built=built)


# ---------- Build ----------

def build():
    built = datetime.now().strftime("%d %b %Y, %H:%M")
    mp = M / "knowledge" / "map"
    if (mp / "entities.json").exists():
        GRAPH.update(json.loads((mp / "entities.json").read_text(encoding="utf-8")))
        nodes = json.loads((mp / "graph.json").read_text(encoding="utf-8"))["nodes"]
        GRAPH["titles"] = {n["id"]: n.get("title", "") for n in nodes if n["type"] == "document"}
    if (mp / "open-items.json").exists():
        OPEN[:] = json.loads((mp / "open-items.json").read_text(encoding="utf-8"))
    features, later, work, epics_by_id = load()
    TOPICS[:] = load_topics()
    fp = M / "knowledge" / "focus.json"
    if fp.exists():
        FOCUS.update(json.loads(fp.read_text(encoding="utf-8")))
    hp = M / "knowledge" / "map" / "health.json"
    BADGES["review"] = sum(1 for o in OPEN if o["status"] != "Open")
    BADGES["health"] = sum(1 for i in (json.loads(hp.read_text(encoding="utf-8"))["items"] if hp.exists() else []) if i["level"] == "warn")
    items = library_items(features, work)
    tmp = Path(tempfile.mkdtemp(prefix="mantis-site-"))  # outside OneDrive, unique per build
    (tmp / "features").mkdir()
    (tmp / "pages").mkdir()
    (tmp / "topics").mkdir()
    shutil.copytree(Path(__file__).resolve().parent / "site_assets", tmp / "assets")
    w = lambda rel, s: (tmp / rel).write_text(s, encoding="utf-8")
    w("index.html", page_home(features, later, work, items, built))
    w("roadmap.html", page_roadmap(features, later, built))
    w("work.html", page_work(work, features, built))
    w("library.html", page_library(items, built))
    w("backlog.html", page_backlog(backlog(), built))
    w("graph.html", page_graph(built))
    w("review.html", page_review(features, built))
    w("topics.html", page_topics(TOPICS, features, built))
    w("health.html", page_health(built))
    w("today.html", page_today(built))
    w("people.html", page_people(built))
    w("decisions.html", page_decisions(built))
    for t in TOPICS:
        w(f"topics/{t['slug']}.html", page_topic(t, TOPICS, built))
    bl = backlog()
    w("search.json", json.dumps(search_index(features, work, items, bl), ensure_ascii=False))
    for f in features:
        w(f"features/{f['slug']}.html", page_feature(f, features, epics_by_id, built))
    for x in work:
        if x["feature"] == "none":
            w(f"pages/work-{x['id']}.html", page_loose(x, work, built))
    for it in items:
        if it.get("md"):
            w(it["href"], page_single(it, built))
    w("version.txt", str(datetime.now().timestamp()))
    # Copy over the old site rather than swapping folders: OneDrive or the server may hold a lock.
    # Two builds can overlap (the server rebuilds on save while a session runs build_map.py):
    # retry briefly when the other one holds a file, instead of failing.
    import time
    for attempt in range(8):
        try:
            shutil.copytree(tmp, SITE, dirs_exist_ok=True)
            break
        except (PermissionError, shutil.Error):
            if attempt == 7:
                raise
            time.sleep(0.5)
    fresh = {p.relative_to(tmp) for p in tmp.rglob("*")}
    for p in sorted(SITE.rglob("*"), reverse=True):
        if p.relative_to(SITE) not in fresh:
            try:
                p.rmdir() if p.is_dir() else p.unlink()
            except OSError:
                pass   # held by the other build or the browser; the next build removes it
    shutil.rmtree(tmp, ignore_errors=True)
    leaks = [p.relative_to(SITE).as_posix() for p in SITE.rglob("*.html") if p.name not in ("backlog.html", "review.html", "health.html")
             and re.search(r"\b(?:DOC|GAP|ASM|CFL|DEC)-\d", re.sub(r"(?s)<template.*?</template>", "", p.read_text(encoding="utf-8")))]
    print(f"Site: {len(features)} topics, {len(work)} epics and stories, {len(items)} library items -> {SITE}"
          + (f"  WARNING, IDs left in: {leaks}" if leaks else ""))


if __name__ == "__main__":
    build()
