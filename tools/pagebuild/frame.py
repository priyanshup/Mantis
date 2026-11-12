"""The pieces of a page around its content: the shell call, copy bar, Jira and sync panels, redirects and small widgets."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import edit_common
import json
import markdown
from pagebuild.markup import render
from pagebuild.paths import M
from pagebuild.registry import CHANGES
from pagebuild.text import esc, fix_lists, front_matter, n_


# Old addresses keep working: each becomes a redirect to where the content lives now (its #anchor kept)
# Retired pages and where they go. The six tab pages now live only in index.html (MANTIS-IMP-107); a link with a key,
# such as questions.html#k=48c3, still lands on that question because the redirect hands the old fragment on.
MOVED = {"today.html": "index.html#today", "classic.html": "index.html#today", "meetings.html": "index.html#meetings",
         "features.html": "index.html#features", "roadmap.html": "index.html#features", "topics.html": "index.html#features",
         "timeline.html": "index.html#features", "graph.html": "index.html#features",
         "questions.html": "index.html#questions", "review.html": "index.html#questions",
         "sources.html": "index.html#sources", "health.html": "index.html#sources", "backlog.html": "index.html#sources",
         "growth.html": "index.html#growth",
         "diagrams.html": "library.html#diagrams", "decisions.html": "library.html#decisions"}


def redirect(to):
    page, _, frag = to.partition("#")
    if page == "index.html":   # a tab: keep the old fragment (#k=..., #m-...) for the tab to use, then go
        go = f'try{{sessionStorage.setItem("mantis-deep",location.hash)}}catch(e){{}}location.replace({json.dumps(to)})'
    else:
        go = f'location.replace({json.dumps(page)} + (location.hash || {json.dumps("#" + frag if frag else "")}))'
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Moved</title><script>{go}</script>'
            f'<meta http-equiv="refresh" content="0; url={to}"></head><body><p>This page moved: <a href="{to}">{to}</a>.</p></body></html>')


def shell(title, body, base="", active="", built="", kind=None):
    """A content page: its page type (site_config/pages.json) picks the styles and scripts; site_shell.py draws the frame."""
    import site_shell
    return site_shell.shell(kind, title, body, base, active, built)


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
