"""The People page and the side panel's people list."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import hashlib
import json
import re
from datetime import datetime
from pagebuild.frame import job_btn, shell
from pagebuild.loaders import can_answer, draft_button
from pagebuild.markup import plain
from pagebuild.paths import M
from pagebuild.registry import DRAFTS, OPEN
from pagebuild.text import esc


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
                     f'<span class="pp-n nocopy" hidden></span></h3>{rows}{can_answer(p["name"])}'
                     f'<div class="pp-live nocopy"></div>'
                     f'<div class="tile-acts nocopy">{job_btn("meeting-brief", "Brief me", arg=p["name"], cls="act")}{draft_button(p["name"]) if p["name"] in DRAFTS else ""}'
                     f'<button type="button" class="act pp-add" data-person="{esc(p["name"])}">+ Follow-up</button></div></article>')
    body = f"""<div class="page-h"><div><h1>People</h1><p class="lead">Everyone you work with: role, how to reach them, how they like to be briefed, and what is open with them. Any name on the site opens the same details in a side panel.</p></div>
<div class="toolbar"><input type="search" id="pp-filter" placeholder="Filter people…" aria-label="Filter people"></div></div>
<script type="application/json" id="draft-data">{json.dumps(DRAFTS, ensure_ascii=False).replace("</", "<\\/")}</script>
<div class="later people-grid">{"".join(cards) or '<p class="empty">No people yet. Add them to mantis/knowledge/people.md.</p>'}</div>"""
    return shell("People", body, active="people", built=built, kind="people")


def people_data():
    """Everyone, for the side panel (MANTIS-IMP-094): the knowledge-base fields with citations kept off the page,
    the questions each can answer, and the drafts behind Draft a message. Live parts come from GET /api/extra."""
    import people as people_mod
    out = []
    for p in people_mod.load():
        f = lambda v: (re.sub(r"\s*\([^()]*(?:MANTIS-|User knowledge|Confluence|Owner)[^()]*\)", "", v or "").replace("*proposed:*", "").strip(),
                       (v or "").strip().startswith("*proposed:*"))
        can = [{"q": plain(re.sub(r" ?[(]MANTIS-[^)]*[)]", "", o["topic"]), 140), "k": hashlib.sha1(o["id"].encode("utf-8")).hexdigest()[:10],
                "named": o["ask"]["how"] == "named"} for o in OPEN if (o.get("ask") or {}).get("name") == p["name"]]
        out.append({"name": p["name"], "slug": p["slug"], "aliases": p["aliases"],
                    **{k: f(p[k])[0] for k in ("role", "team", "channel", "briefing", "notes")},
                    "proposed": [k for k in ("briefing", "notes") if f(p[k])[1]], "can": can, "draft": DRAFTS.get(p["name"])})
    return out


def auto_closed(days=30):
    """Open questions a source closed automatically in the last `days` days, newest first (MANTIS-IMP-094)."""
    since = (datetime.now().date().toordinal() - days)
    out = []
    for p in (M / "knowledge" / "registers" / "gaps").glob("MANTIS-GAP-*.md"):
        t = p.read_text(encoding="utf-8")
        m = re.search(r"(?m)^- \*\*Status:\*\* Closed \(auto, (\d{4}-\d{2}-\d{2}): (.*?); source (MANTIS-DOC-\d{4})\)", t)
        if m and datetime.strptime(m.group(1), "%Y-%m-%d").date().toordinal() >= since:
            topic = re.search(r"(?m)^- \*\*Topic:\*\*\s*(.+)$", t)
            out.append({"id": p.stem, "date": m.group(1), "why": m.group(2), "topic": (topic.group(1) if topic else "").strip()})
    return sorted(out, key=lambda x: x["date"], reverse=True)
