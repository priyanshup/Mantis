"""The front end (2026-11-11): the approved mock's own screens, run on live data.

The six tabs are one page (index.html) that renders from the mock's scripts in assets/app/. What does not change while the
site runs (features, open questions, recent documents, health) is written here as assets/app/static.json at build time;
what does (tasks, meetings, follow-ups, Growth, filters, the pull brief) is fetched from tools/serve.py by assets/app/boot.js.
The old pages stay at their addresses; the old Today is classic.html.
"""
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import layout
import site_chrome
from pagebuild.paths import M
from pagebuild.registry import FOCUS, OPEN, TOPICS, archived

STAGE = {"discovery": 0, "refinement": 1, "build": 2}


def _plain(s, n=320):
    s = re.sub(r"\*\*|`|\[([^\]]*)\]\([^)]*\)", lambda m: m.group(1) or "", str(s or ""))
    s = re.sub(r" ?[(]MANTIS-[A-Z]+-[0-9]+(?:[,;] ?MANTIS-[A-Z]+-[0-9]+)*[)]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[: n - 1].rstrip() + "…" if len(s) > n else s


def _short(t):
    return re.sub(r"\s*\([^)]*\)\s*$", "", str(t)).split(":")[0]


def _story(md):
    """A story or epic file's text split into the labelled parts the reader shows (no Mantis IDs, no comments)."""
    body = re.sub(r"<!--.*?-->", "", md or "", flags=re.S)
    body = re.sub(r"^---\n.*?\n---\n", "", body, flags=re.S)
    parts = {}
    marks = ["Background and problem statement", "Acceptance criteria", "Edge cases", "Out of scope", "Open questions"]
    pat = r"\*\*(" + "|".join(re.escape(m) for m in marks) + r")\*\*\n(.*?)(?=\n\*\*(?:" + "|".join(re.escape(m) for m in marks) + r")\*\*|\nEpic:|\Z)"
    for m in re.finditer(pat, body, re.S):
        parts[m.group(1)] = m.group(2).strip()
    head = body.split("**Background")[0]
    story = " ".join(l.strip() for l in head.splitlines() if l.strip().startswith(("As a", "I want", "So that")))
    bl = lambda s: [l.lstrip("- ").strip() for l in (s or "").splitlines() if l.strip().startswith("-")]
    return {"story": story, "bg": _plain(parts.get("Background and problem statement", ""), 900), "ac": bl(parts.get("Acceptance criteria")),
            "edge": bl(parts.get("Edge cases")), "oos": bl(parts.get("Out of scope")), "oq": bl(parts.get("Open questions"))}


def features_json(features):
    follow = set(FOCUS.get("following", []))
    out = []
    for f in features:
        stories = [{"key": s.get("jira") or "", "title": s["title"], **_story(s.get("md", ""))} for s in f.get("stories", [])]
        epics = [{"key": e.get("jira") or "", "title": e["title"], **_story(e.get("md", ""))} for e in f.get("epics", [])]
        out.append({"slug": f["slug"], "title": f["title"], "stage": STAGE.get(f.get("status", ""), 0), "status": f.get("status", ""), "priority": f.get("priority", "") if f.get("priority") in ("P1", "P2", "P3") else "",
                    "sources": len(f.get("docs", [])), "summary": _plain(f.get("summary", ""), 600), "jira": f.get("jira") or "", "estimate": f.get("estimate") or "",
                    "following": f["slug"] in follow, "archived": bool(archived(f["slug"])), "stories": stories, "epics": epics, "page": (f.get("page_md") or "")[:9000],
                    "preps": [{"title": p["title"], "updated": p["updated"], "md": p["md"][:9000]} for p in f.get("preps", [])]})
    out.sort(key=lambda x: (not x["following"], x["priority"] or "P9", x["title"].lower()))
    return out


def topics_json():
    follow = set(FOCUS.get("following", []))
    return sorted(({"slug": t["slug"], "title": t["title"], "sources": len(t.get("docs", [])), "following": t["slug"] in follow, "archived": bool(archived(t["slug"]))} for t in TOPICS),
                  key=lambda x: (x["archived"], not x["following"], x["title"].lower()))


def questions_json(features):
    from pagebuild.day import scope_of, topic_text
    names = {f["slug"]: f["title"] for f in features} | {t["slug"]: t["title"] for t in TOPICS}
    out = []
    for o in OPEN:
        scope = scope_of(o)
        if scope == "tidy":
            continue
        who = "You" if scope == "you" else ((o.get("ask") or {}).get("name") or "No one named yet")
        feats = [names[s] for s in o.get("features", []) if s in names]
        det = [(k, v) for k, v in o.get("detail", []) if not k.startswith("Evidence Strength")]
        ctx = _plain(det[0][1], 300) if det else _plain(o.get("status_full", ""), 300)
        pri = o.get("priority", "")
        out.append({"id": o["id"], "k": hashlib.sha1(o["id"].encode("utf-8")).hexdigest()[:10], "q": topic_text(o), "who": who,
                    "feat": _short(feats[0]) if feats else "General", "pri": "High" if pri in ("Critical", "High") else (pri or "None"),
                    "status": o["status"], "ctx": ctx, "src": [d["title"] for d in o.get("docs", [])][:3], "scope": scope})
    return out


def recent_json(features, n=6):
    d = M / "02_digests"
    owner = {}
    for f in features:
        for doc in f.get("docs", []):
            owner.setdefault(doc, f["title"])
    rows = []
    for p in sorted(d.glob("MANTIS-DOC-*.md"), reverse=True)[:n]:
        txt = p.read_text(encoding="utf-8", errors="ignore")[:1500]
        t = re.search(r'^original_title:\s*"?(.*?)"?\s*$', txt, re.M)
        title = (t.group(1) if t else p.stem)
        kind = "Jira and Confluence" if title.lower().startswith("jira and confluence") else "Meeting notes" if re.search(r"sync|meeting|connect|refinement|grooming|1-1", title, re.I) else "Document"
        rows.append({"title": _plain(title, 90), "kind": kind, "feat": _short(owner.get(p.stem, "")) or "General", "date": datetime.fromtimestamp(p.stat().st_mtime).strftime("%d %b").lstrip("0")})
    return rows


def health_json():
    p = M / "knowledge" / "map" / "health.md"
    if not p.exists():
        return []
    return [_plain(re.sub(r"^- \*\*Fix\*\* \([^)]*\):\s*", "", l), 140) for l in p.read_text(encoding="utf-8").splitlines() if l.startswith("- **Fix**")]


def static_json(features, built):
    docs = len(list((M / "02_digests").glob("MANTIS-DOC-*.md")))
    return json.dumps({"built": built, "docs": docs, "features": features_json(features), "topics": len([t for t in TOPICS if not archived(t["slug"])]), "topicsList": topics_json(),
                       "questions": questions_json(features), "recent": recent_json(features), "health": health_json()}, ensure_ascii=False)


# Load order matters: a later file may extend or wrap an earlier one. Define each function once (tools/stylelint.py checks).
SCRIPTS = ["ui.js", "platform.js", "screens-base.js", "screens-questions-growth.js", "tasks-add-edit-inbox.js", "controls-kit.js", "agenda-calendar.js", "week-view.js", "today-features-layout.js", "snooze-history.js", "groups-refill.js", "group-ranking.js", "widgets-today.js", "widgets-sources.js", "widgets-growth.js", "widgets-meetings-questions.js", "widgets-features.js", "feature-meetings.js", "feature-filters.js", "feature-inbox.js", "feature-capture.js", "feature-growth.js", "live-data.js", "feature-reader.js", "behaviour-core.js", "behaviour-questions-growth.js", "behaviour-tasks-palette.js", "behaviour-controls.js", "behaviour-agenda.js", "motion-delight.js", "motion-indicators-peek.js", "behaviour-plan-settle.js", "behaviour-group-reorder.js", "save-live.js", "start.js", "tooltips.js"]


def _layout():
    """site_config/layout.json as the page receives it (without its notes)."""
    lay = layout.load()
    lay.pop("_readme", None)
    return json.dumps(lay, separators=(",", ":"))


def page_app(built):
    icon = lambda d: f'<svg viewBox="0 0 24 24">{d}</svg>'
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
{site_chrome.head_links('', fonts=site_chrome.FONTS[:2])}
<title>Mantis</title>
{site_chrome.stylesheets('', 'assets/app/app.css')}</head>
<body>
<header class="top"><div class="top-in">
<a class="brand" href="#today" aria-label="Mantis, go to Today"><img src="assets/mark.svg?v=4" alt=""><span>Mantis</span></a>
<nav id="nav" aria-label="Sections"></nav>
<div class="tools">
<button class="ic" id="b-find" aria-label="Search and commands, Control K" title="Search">{icon('<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>')}</button>
<button class="ic" id="b-inbox" aria-label="Inbox" title="Inbox">{icon('<path d="M4 13l2.2-7.2A2 2 0 0 1 8.1 4.4h7.8a2 2 0 0 1 1.9 1.4L20 13M4 13v5a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-5M4 13h4.5a1 1 0 0 1 1 .8 2.6 2.6 0 0 0 5 0 1 1 0 0 1 1-.8H20"/>')}<span class="badge" id="ibadge" hidden>1</span></button>
<button class="ic" id="b-people" aria-label="People">{icon('<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.6-3.6 3.2-5.5 6.5-5.5s5.9 1.9 6.5 5.5"/><path d="M16 4.8a3.5 3.5 0 0 1 0 6.4M18.5 14.8c1.7.7 2.8 2.4 3 5.2"/>')}</button>
<button class="ic" id="b-lib" aria-label="Library">{icon('<path d="M5 4h4v16H5zM11 4h4v16h-4zM17.2 5.2l3.4 1-3.8 14-3.4-1z"/>')}</button>
{site_chrome.theme_toggle('id="b-theme" aria-label="Switch theme" title="Theme"')}
<button class="ic burger" id="b-menu" aria-label="Menu" aria-expanded="false" title="Menu"><svg viewBox="0 0 24 24"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button>
</div></div></header>
<div class="menu" id="menu" hidden></div>
<main id="main" aria-busy="true"><div class="boot" role="status"><span class="boot-bar"></span><span class="boot-bar"></span><span class="boot-bar short"></span><span class="sr">Loading Mantis</span></div></main>
<div id="layer"></div>
<div class="lab" hidden><button data-mode="normal" aria-pressed="true">Normal</button></div>
<script>window.APP_LAYOUT={_layout()};window.APP_SCRIPTS={json.dumps(SCRIPTS)};</script>
<script src="assets/app/boot.js"></script>
</body></html>
"""
