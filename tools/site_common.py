"""Shared parts of the Mantis site (MANTIS-IMP-064): state loaded once per build, Markdown rendering,
the page shell and header, copy and sync panels, small helpers. Page modules import everything from here."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import hashlib, html, json, os, re, shutil, tempfile
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
    "build": ("In build", "s-build"), "live": ("Live", "s-done"),
}


WORK = {  # epic, story and page status -> (label, css class)
    "draft": ("Draft", "w-draft"), "review": ("In review", "w-review"), "in-jira": ("In Jira", "w-jira"),
    "done": ("Done", "w-done"), "published": ("Published", "w-done"),
}


ID = r"(?:MANTIS-)?(?:DOC|GAP|ASM|CFL|DEC|IMP)-\d+|\bAD-\d{3}\b"


DROP_COLS = {"source", "sources", "doc", "docs", "source document", "source documents", "evidence", "id"}


# ---------- Markdown cleaning ----------

def front_matter(text):
    """(front matter, body), every value as written: the site shows lists as text (tools/frontmatter.py)."""
    import frontmatter
    return frontmatter.split(text, lists=False)


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
    # ![what it shows](asset:MANTIS-AST-001) in a page shows that registered diagram (MANTIS-IMP-008)
    body = re.sub(r'src="asset:(MANTIS-AST-\d+)"', lambda m: f'src="{asset_src(m.group(1))}" class="asset-img"', body)
    # A card's work type, in its "Work type:" line and its Sources table, shows as the coloured tag
    body = re.sub(r"<strong>Work type:</strong> (Business \+ technical|Business|Technical)( \([^)]*\))?\.",
                  lambda m: f'<span class="muted small">Work type</span> {work_tag(WORK_OF_LABEL[m.group(1)])}<span class="muted small">{m.group(2) or ""}</span>', body)
    body = re.sub(r"<td>(Business \+ technical|Business|Technical)</td>", lambda m: f"<td>{work_tag(WORK_OF_LABEL[m.group(1)])}</td>", body)
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


WORK_TIP = {"business": "Business work: the requirements come from users and the business",
            "technical": "Technical work: the requirements come from engineering",
            "both": "Business and technical work: requirements come from both sides"}
WORK_OF_LABEL = {"Business": "business", "Technical": "technical", "Business + technical": "both"}


def work_tag(w):
    """The coloured business / technical tag (a card dict or its "work" value); "both" is one split tag."""
    w = w.get("work", "") if isinstance(w, dict) else (w or "")
    if w == "both":
        return f'<span class="wtag wtag-both" title="{WORK_TIP[w]}"><span class="wh wh-b">Business</span><span class="wh wh-t">Technical</span></span>'
    return f'<span class="wtag wtag-{w}" title="{WORK_TIP[w]}">{w.capitalize()}</span>' if w in WORK_TIP else ""


def work_pill(status):
    label, cls = WORK.get(status or "", (status.title() if status else "No status", "w-draft"))
    return pill(label, cls)


# Five tabs, one per recurring moment (MANTIS-IMP-094): every one always visible, no overflow menu (HIG tab bars:
# "Avoid overflow tabs"; single-word labels). People and the library open in a side panel from any page.
NAV = (("today", "index.html", "Today"), ("meetings", "meetings.html", "Meetings"), ("features", "features.html", "Features"),
       ("questions", "questions.html", "Questions"), ("sources", "sources.html", "Sources"))
ICON = {   # 24px outline symbols for the compact tab bar, one visual language, drawn with currentColor
    "today": '<path d="M4 7.5A2.5 2.5 0 0 1 6.5 5h11A2.5 2.5 0 0 1 20 7.5v10a2.5 2.5 0 0 1-2.5 2.5h-11A2.5 2.5 0 0 1 4 17.5zM4 10h16M8.5 3v4M15.5 3v4"/><path d="M9 14.5l2 2 4-4"/>',
    "meetings": '<circle cx="9" cy="8.5" r="3"/><path d="M3.5 19c.6-3 2.8-4.8 5.5-4.8s4.9 1.8 5.5 4.8"/><circle cx="16.5" cy="9.5" r="2.4"/><path d="M15.6 14.3c2.4-.3 4.3 1.3 4.9 3.9"/>',
    "features": '<path d="M12 3.5 20.5 8 12 12.5 3.5 8z"/><path d="m3.5 12 8.5 4.5 8.5-4.5"/><path d="m3.5 16 8.5 4.5 8.5-4.5"/>',
    "questions": '<path d="M5 5.5h14a1.5 1.5 0 0 1 1.5 1.5v9a1.5 1.5 0 0 1-1.5 1.5h-7l-4.5 3.5V17.5H5A1.5 1.5 0 0 1 3.5 16V7A1.5 1.5 0 0 1 5 5.5z"/><path d="M10 9.6a2 2 0 1 1 2.7 1.9c-.5.2-.7.6-.7 1.1v.3"/><path d="M12 15.2h.01"/>',
    "sources": '<path d="M12 3.5v11m0 0-4-4m4 4 4-4"/><path d="M4.5 14.5v3a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-3"/>',
}


def icon(k, cls="ico"):
    return (f'<svg class="{cls}" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.7" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICON[k]}</svg>')


# Old addresses keep working: each becomes a redirect to where the content lives now (its #anchor kept)
MOVED = {"today.html": "index.html", "roadmap.html": "features.html#roadmap", "topics.html": "features.html#all",
         "timeline.html": "features.html#roadmap", "review.html": "questions.html", "health.html": "sources.html#health",
         "backlog.html": "sources.html#health", "graph.html": "features.html",
         "diagrams.html": "library.html#diagrams", "decisions.html": "library.html#decisions"}


def redirect(to):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Moved</title>'
            f'<script>location.replace({json.dumps(to.split("#")[0])} + (location.hash || {json.dumps("#" + to.split("#")[1] if "#" in to else "")}))</script>'
            f'<meta http-equiv="refresh" content="0; url={to}"></head><body><p>This page moved: <a href="{to}">{to}</a>.</p></body></html>')


def shell(title, body, base="", active="", built=""):
    badge = lambda k: f'<span class="badge" aria-label="{BADGES[k]} waiting for you">{BADGES[k]}</span>' if BADGES.get(k) else ""
    cur = lambda key: ' class="on" aria-current="page"' if key == active else ""
    nav = "".join(f'<a href="{base}{href}"{cur(key)}>{name}{badge(key)}</a>' for key, href, name in NAV)
    tabbar = "".join(f'<a href="{base}{href}"{cur(key)}>{icon(key)}<span>{name}</span>{badge(key)}</a>' for key, href, name in NAV)
    # One header for every page (2026-10-31 redesign): five tabs, one box that finds or asks (Ctrl K), the pull with
    # its last time, and a two-state theme switch. People and the library open from the search box.
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#e4e3df" media="(prefers-color-scheme: light)"><meta name="theme-color" content="#0b0b0c" media="(prefers-color-scheme: dark)">
<title>{esc(title)} · Mantis</title>
<link rel="icon" type="image/svg+xml" href="{base}assets/mark.svg?v=4"><link rel="icon" type="image/png" sizes="192x192" href="{base}assets/mark.png?v=4"><link rel="apple-touch-icon" href="{base}assets/mark.png?v=4">
<script>try{{var m=localStorage.getItem("mantis-theme");if(m==="light"||m==="dark")document.documentElement.dataset.theme=m}}catch(e){{}}</script>
<link rel="preload" href="{base}assets/fonts/Inter-400-600.woff2" as="font" type="font/woff2" crossorigin><link rel="preload" href="{base}assets/fonts/ZalandoSansExpanded-600-850.woff2" as="font" type="font/woff2" crossorigin><link rel="preload" href="{base}assets/fonts/IBMPlexMono-400.woff2" as="font" type="font/woff2" crossorigin><link rel="preload" href="{base}assets/fonts/IBMPlexMono-500.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{base}assets/style.css"></head>
<body>
<header class="top"><div class="wrap top-in">
<a class="brand" href="{base}index.html"><img class="mark" src="{base}assets/mark.svg?v=4" alt="" width="26" height="26"><span>Mantis</span></a>
<nav class="mainnav" id="mainnav" aria-label="Main">{nav}</nav>
<button type="button" class="kbar" id="kbar" aria-haspopup="dialog" aria-controls="palette"><span>Search or ask</span><kbd>Ctrl K</kbd></button>
<div class="pullpill nocopy"><span class="pp-when" id="pull-ago" title="Last pull"></span><button type="button" class="key-sm job" data-job="pull" title="Read what changed in Jira, Confluence and your inbox">Pull</button></div>
<button type="button" id="theme" class="theme-sw" role="switch" aria-checked="false" aria-label="Dark theme"></button></div><div id="busy" aria-hidden="true"></div></header>
<main class="wrap">{body}</main>
<footer class="wrap foot"><span>Mantis</span><span>Built {esc(built)}</span></footer>
<nav class="tabbar" aria-label="Main">{tabbar}</nav>
<div id="palette" class="palette" role="dialog" aria-modal="true" aria-label="Search or ask" hidden><div class="pal">
<div class="pal-in"><input id="gsearch" type="search" placeholder="Find a person, feature or document, or ask a question" aria-label="Search or ask" autocomplete="off" data-base="{base}"><kbd>Esc</kbd></div>
<div id="gresults" class="gresults"></div>
<div class="pal-ft"><span>↑↓ move</span><span>Enter open</span><button type="button" class="linkish" data-dopen="people">People</button><button type="button" class="linkish" data-dopen="library">Library</button></div></div></div>
<aside id="drawer" class="drawer" role="dialog" aria-modal="false" aria-label="People and library" data-base="{base}" hidden></aside>
<div id="toast" role="status"></div>
<script src="{base}assets/app.js"></script>
</body></html>
"""


# Where live content is still on its way: three rows that shimmer, the shape of what is coming (2026-10-31)
SKEL = '<div class="skel" role="status" aria-label="Loading"><i></i><i></i><i></i></div>'


def copy_bar(label, edit=""):
    """Panel header: copy button, plus an Edit button when `edit` (the output file, relative to mantis/) is given."""
    btn = f'<button class="btn-line edit-btn" type="button">Edit</button>' if edit else ""
    return (f'<div class="panel-bar nocopy"><span class="muted small bar-note">Formatted for Confluence and Jira</span>'
            f'<span class="bar-btns">{btn}<button class="btn copy-all">{esc(label)}</button></span></div>' + behind_note(edit)
            + edit_source(edit) + sync_panel(edit) + jira_panel(edit))


def behind_note(rel):
    """A page, epic or story whose card changed after it was written (MANTIS-IMP-070): say so, and what changed."""
    b = next((x for x in CHANGES.get("behind", []) if x["file"] == rel), None) if rel else None
    if not b:
        return ""
    return (f'<div class="sync behind-note nocopy"><span class="sync-ico" aria-hidden="true"></span><span><b>May be out of date.</b> '
            f'{esc(b["why"])}. The next processing run updates it; or ask Mantis to update it now.</span></div>')


def jira_panel(rel):
    """Jira (MANTIS-IMP-045): copy an epic or story field by field, and after the first time, see which fields
    changed since the owner last updated Jira, with the labelled parts that changed inside each."""
    if not rel or not rel.startswith(("outputs/epics/", "outputs/user-stories/")):
        return ""
    f = M / rel
    front, _, body = edit_common.split(f.read_text(encoding="utf-8"))
    title = front_matter(f.read_text(encoding="utf-8"))[0].get("title", "") or f.stem.replace("-", " ").capitalize()
    fields = edit_common.jira_fields(body, title)
    snap = M / "outputs" / ".published" / (rel[len("outputs/"):] + ".json")
    pub = json.loads(snap.read_text(encoding="utf-8")) if snap.exists() else None
    norm = lambda t: " ".join((t or "").split())
    old = dict(pub.get("fields", [])) if pub else {}
    changed = [k for k, v in fields if pub and norm(old.get(k)) != norm(v)]

    def src(k, v):   # what a Copy button puts on the clipboard: rendered for Jira's editor, hidden on the page
        return f'<div class="jf-src" data-f="{esc(k)}" hidden>{esc(v) if k == "Summary" else render(v, breaks=True, sections=False)}</div>'

    def what_changed(k, v):
        if k == "Summary" or k not in changed:
            return ""
        a, b = edit_common.parts(old.get(k, "")), edit_common.parts(v)
        names = [n for n in b if norm(a.get(n)) != norm(b[n])] + [f"{n} (removed)" for n in a if n not in b]
        names = ["opening lines" if n == "(opening)" else n for n in names]
        return f'<span class="muted small jf-what">{esc(", ".join(names))}</span>' if names and len(names) < len(b) + len(a) else ""

    btns = "".join(f'<span class="jf{" jf-changed" if k in changed else ""}"><button type="button" class="mini copy-field" data-f="{esc(k)}">Copy {esc(k.lower())}</button>'
                   f'{"<span class=\"pill w-review plain\">Changed</span>" if k in changed else ""}{what_changed(k, v)}</span>' for k, v in fields)
    mark = f'<button type="button" class="btn-line" data-publish="mantis/{esc(rel)}" data-to="Jira">{"I updated Jira" if pub else "I put this in Jira"}</button>'
    if not pub:
        state = '<span><b>Jira fields.</b> Copy each field into its box in Jira. After you paste, press the button: next time Mantis shows only the fields that changed.</span>'
    elif not changed:
        state = f'<span>Same as what you put in Jira on {esc(pub.get("date", ""))}.</span>'
    else:
        state = (f'<span><b>{n_(len(changed), "field")} changed</b> since you updated Jira on {esc(pub.get("date", ""))}: '
                 f'{esc(", ".join(changed))}. Update only {"that one" if len(changed) == 1 else "those"}.</span>')
    cls = "changed-j" if changed else ("ok" if pub else "")
    return (f'<div class="sync jira {cls} nocopy"><span class="sync-ico" aria-hidden="true"></span>{state}{mark}'
            f'<div class="jf-row">{btns}</div>{"".join(src(k, v) for k, v in fields)}</div>')


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


GRAPH = {}  # filled by build() from map/entities.json


def plain(md, limit=6000):
    """Markdown to searchable plain text, with Mantis IDs and repo paths removed."""
    t = clean(md)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"[#*_`>|]+", " ", t)
    t = re.sub(r"-{3,}", " ", t)
    return re.sub(r"\s+", " ", t).strip()[:limit]


OPEN = []  # filled by build() from map/open-items.json


TOPICS = []  # filled by build() from map/topics.json


FOCUS = {"following": [], "on_roadmap": [], "off_roadmap": [], "archived": []}  # the owner's choices, mantis/knowledge/focus.json


def archived(slug):
    """An archived card is hidden from focus, roadmap, lists and filters; its page, sources and search stay."""
    return slug in FOCUS.get("archived", [])


BADGES = {}  # nav counts, filled by build()


VERDICT_SETS = {
    # A possible conflict found by the contradiction check (MANTIS-IMP-047): the owner says what it is
    "possible": (("real", "Yes, they conflict"), ("changed", "The plan changed"), ("notconflict", "Not a conflict")),
    "name": (("same", "Same thing"), ("different", "Different things"), ("someone", "Someone else must answer")),
    "term": (("answers", "I know what it is"), ("someone", "Someone else must answer")),
}


PLACEHOLDER = {"gap": "Your answer: facts, decision, or what you know so far",
               "possible": "Optional: which one is right now, or why they don't clash",
               "name": "Optional: which name Mantis should use, or how they differ",
               "term": "What it stands for and what it is (a system, team, process...)"}


def ask_chip(o):
    """Who can answer (MANTIS-IMP-046). A name from a note is a fact; anything worked out is a question mark."""
    a = o.get("ask")
    if not a:
        return ""
    first = a["name"].split()[0] if " " in a["name"] and a["name"][0].isupper() else a["name"]
    if a["how"] == "named":
        return f'<span class="tag ask" title="{esc(a["why"])}">Ask {esc(first)}</span>'
    return f'<span class="tag ask maybe" title="{esc(a["why"])}: a suggestion, not confirmed">Maybe {esc(first)}?</span>'


def verdicts(kind):
    opts = VERDICT_SETS.get(kind, (("answers", "Answers it"), ("partly", "Partly answers it"), ("later", "Not decided yet"), ("someone", "Someone else must answer")))
    return "".join(f'<button type="button" data-v="{v}">{esc(l)}</button>' for v, l in opts)


def on_roadmap(c, is_feature):
    if archived(c["slug"]):
        return False
    return (c["slug"] not in FOCUS["off_roadmap"]) if is_feature else (c["slug"] in FOCUS["on_roadmap"])


DRAFTS = {}


def draft_data():
    """Per person, the open questions they can answer, phrased for a message (MANTIS-IMP-048)."""
    import people as people_mod
    chan = {p["name"]: p["channel"] for p in people_mod.load()}
    titles = {f["slug"]: f["title"] for f in json.loads((M / "knowledge" / "map" / "features.json").read_text(encoding="utf-8"))} \
        if (M / "knowledge" / "map" / "features.json").exists() else {}
    titles.update({t["slug"]: t["title"] for t in TOPICS})
    strip = lambda s: re.sub(r"\s*No inference has been made\.?", "", re.sub(r"\s*\(?MANTIS-[A-Z]+-\d+[^)]*\)?", "", s or "")).strip()
    out = {}
    for o in OPEN:
        a = o.get("ask")
        if not a or o["kind"] in ("name", "term"):
            continue
        main = next((v for k, v in o.get("detail", []) if k.split(" (")[0] in ("What's missing", "Statement", "Statement A", "Claim")), "")
        ctx = re.split(r"(?<=[.!?])\s", strip(main))[0] if main else ""
        out.setdefault(a["name"], {"first": a["name"].split()[0], "channel": chan.get(a["name"], ""), "questions": []})["questions"].append(
            {"q": strip(o["topic"]), "ctx": ctx if len(ctx) <= 200 else ctx[:199].rsplit(" ", 1)[0].rstrip(",;:") + "…", "card": titles.get((o.get("features") or [""])[0], ""), "named": a["how"] == "named"})
    for v in out.values():
        v["questions"].sort(key=lambda q: not q["named"])
    return out


def draft_button(name, cls="act"):
    return f'<button type="button" class="{cls} nocopy" data-draft="{esc(name)}">Draft a message</button>'


def can_answer(name):
    """Open questions this person can answer (MANTIS-IMP-046): named ones and suggestions in separate groups."""
    k = lambda o: hashlib.sha1(o["id"].encode("utf-8")).hexdigest()[:10]
    mine = [o for o in OPEN if (o.get("ask") or {}).get("name") == name]
    out = ""
    for label, group in (("Can answer", [o for o in mine if o["ask"]["how"] == "named"]),
                         ("Might answer", [o for o in mine if o["ask"]["how"] != "named"])):
        if not group:
            continue
        rows = "".join(f'<li><a href="questions.html#k={k(o)}">{esc(plain(re.sub(r" ?[(]MANTIS-[^)]*[)]", "", o["topic"]), 100))}</a></li>' for o in group[:3])
        more = f'<a class="small" href="questions.html#who={quote(name)}">All {len(mine)} on Open items →</a>' if len(group) > 3 else ""
        tip = "" if label == "Can answer" else ' title="Suggested from the sources: not confirmed"'
        out += f'<div class="pp-f pp-ask"><span class="muted small"{tip}>{label}</span><div><ul class="pp-q">{rows}</ul>{more}</div></div>'
    return out


CHANGES = {"events": [], "refresh": [], "today": ""}   # map/changes.json (tools/changes.py)
READY = {"states": {}, "features": [], "attention": []}   # map/readiness.json (tools/readiness.py, MANTIS-IMP-074 to 076)


# kind: (label, filter group, colour class). Every kind shows its icon and its word, never colour alone.
EV_KINDS = {"source": ("New source", "sources", "ev-src"), "question": ("New question", "questions", "ev-q"),
            "assumption": ("New assumption", "questions", "ev-q"), "likely": ("Likely answer", "answers", "ev-a"),
            "answer": ("Answered", "answers", "ev-a"), "closed": ("Closed", "answers", "ev-a"),
            "conflict": ("New conflict", "conflicts", "ev-c"),
            "possible": ("Possible conflict", "conflicts", "ev-c"), "decision": ("Decision", "decisions", "ev-dec"),
            "stage": ("Stage changed", "work", "ev-w"), "page": ("Updated", "work", "ev-w"), "jira": ("In Jira", "work", "ev-w"),
            "summary": ("Summary refreshed", "cards", "ev-card"), "diagram": ("New diagram", "cards", "ev-dia")}


EV_ORDER = ("possible", "conflict", "likely", "answer", "closed", "decision", "stage", "jira", "question", "assumption", "source", "page", "diagram", "summary")


EV_FOLD = {"summary": "{n} card summaries refreshed", "source": "{n} new sources", "question": "{n} new questions",
           "page": "{n} pages, epics and stories updated", "answer": "{n} answers recorded"}


EV_GROUPS = (("sources", "Sources"), ("questions", "Questions"), ("answers", "Answers"), ("conflicts", "Conflicts"),
             ("decisions", "Decisions"), ("work", "Pages and Jira"), ("cards", "Cards and diagrams"))


TL_KINDS = {"source": "New source", "decision": "Decision", "stage": "Stage changed", "possible": "Possible conflict",
            "conflict": "Conflict", "due": "Due", "done": "Done", "chase": "Chase", "meeting": "Meeting"}


ASSETS = []   # registered knowledge assets, from map/assets.json (MANTIS-IMP-008)


def asset_src(aid):
    a = next((x for x in ASSETS if x["id"] == aid), None)
    return f"/diagrams/{Path(a['file']).name}" if a and a.get("file") else ""


PRIO_RANK = {"Critical": 0, "High": 1, "": 2, "Medium": 3, "Low": 4}


PRIO_CLS = {"Critical": "s-ref pr-critical", "High": "s-ref", "Medium": "s-none", "Low": "s-none"}


# Everything here, underscores included, is shared with the page modules (from site_common import *).
__all__ = [n for n in dir() if not n.startswith("__")]
