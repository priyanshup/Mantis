"""The epic and story pages (a feature's work, and work that belongs to no feature)."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import json
from pagebuild.frame import copy_bar, shell
from pagebuild.labels import WORK, work_pill
from pagebuild.markup import render
from pagebuild.registry import FOCUS, archived
from pagebuild.text import esc


def page_work(work, features, built):
    data = [{k: x[k] for k in ("kind", "title", "status", "feature", "feature_title", "epic_title", "jira", "updated")}
            | {"href": x["href"], "file": x["file"], "mine": x["feature"] in FOCUS["following"],
               "own": x["file"] in FOCUS.get("archived_work", []), "archived": archived(x["feature"]) or x["file"] in FOCUS.get("archived_work", [])} for x in work]
    feats = "".join(f'<option value="{f["slug"]}">{esc(f["title"])}</option>' for f in features if (f["epics"] or f["stories"]) and not archived(f["slug"]))
    body = f"""<div class="crumbs"><a href="features.html">Features</a><span>›</span><span>Epics &amp; stories</span></div>
<div class="page-h"><div><h1>Epics &amp; stories</h1><p class="lead">Everything written for Jira, by status, across all features. Includes generic epics and stories that stand alone.</p></div>
<div class="seg" id="view"><button data-v="board" class="on">Board</button><button data-v="list">List</button></div></div>
<div class="toolbar"><input id="q" type="search" placeholder="Filter…" aria-label="Filter epics and stories">
<div class="chips" id="f-kind"><button data-v="all" class="on">All</button><button data-v="epic">Epics</button><button data-v="story">Stories</button></div>
<select id="f-feature" class="sel" aria-label="Filter by feature"><option value="all">All features</option><option value="mine">Following</option><optgroup label="Feature">{feats}<option value="none">No feature</option></optgroup><option value="archived">Archived</option></select></div>
<div id="board"></div><div id="list" hidden></div>
<script id="work" type="application/json">{json.dumps({"items": data, "labels": {k: v[0] for k, v in WORK.items()}})}</script>"""
    return shell("Epics & stories", body, active="features", built=built, kind="work")


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
    return shell(x["title"], body, base="../", active="features", built=built, kind="document")
