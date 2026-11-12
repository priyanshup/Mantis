"""The library page, the single-document page and the search index."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import hashlib
import re
from pagebuild.decisions import page_decisions
from pagebuild.diagrams import page_diagrams
from pagebuild.frame import copy_bar, shell
from pagebuild.labels import STATUS, work_pill
from pagebuild.markup import plain, render
from pagebuild.paths import M
from pagebuild.registry import ASSETS, GRAPH, OPEN, TOPICS, on_roadmap
from pagebuild.text import ID, esc, n_


def page_library(items, built):
    rows = "".join(f'<a class="row lib" data-kind="{esc(it["kind"])}" href="{it["href"]}"><span class="row-t">{esc(it["title"])}</span>'
                   f'<span class="tag">{esc(it["kind"])}</span><span class="muted">{esc(it["where"])}</span>{work_pill(it["status"]) if it["status"] else ""}</a>' for it in items)
    kinds = sorted({it["kind"] for it in items})
    # One place for everything reusable (MANTIS-IMP-068): pages, epics and stories, then diagrams and decisions
    n_dia = sum(1 for a in ASSETS if a["status"] != "Superseded")
    n_dec = len(list((M / "knowledge" / "registers" / "decisions").glob("MANTIS-DEC-*.md")))
    chips = ('<button data-v="all" class="on">All</button>' + "".join(f'<button data-v="{esc(k)}">{esc(k[:-1] + "ies" if k.endswith("y") else k + "s")}</button>' for k in kinds)
             + f'<button data-v="diagrams">Diagrams · {n_dia}</button><button data-v="decisions">Decisions · {n_dec}</button>')
    body = f"""<div class="page-h"><div><h1>Library</h1><p class="lead">Everything Mantis keeps for reuse: pages, epics and stories ready to copy, diagrams from the sources, and the decisions made along the way.</p></div></div>
<div class="toolbar"><div class="chips" id="f-lib">{chips}</div></div>
<section class="panel-box lib-sec" data-libsec="written">{rows or '<p class="empty">Nothing written yet.</p>'}</section>
<section class="lib-sec" data-libsec="diagrams" id="diagrams"><h2 class="lib-h">Diagrams</h2>{page_diagrams(built, embed=True)}</section>
<section class="lib-sec" data-libsec="decisions" id="decisions"><h2 class="lib-h">Decisions</h2>{page_decisions(built, embed=True)}</section>"""
    return shell("Library", body, built=built, kind="library")


def page_single(it, built):
    body = f"""<div class="crumbs"><a href="../library.html">Library</a><span>›</span><span>{esc(it["title"])}</span></div>
<div class="tab-panel">{copy_bar("Copy page", it.get("file"))}<article class="doc">{render(it["md"])}</article></div>"""
    return shell(it["title"], body, base="../", built=built, kind="document")


def search_index(features, work, items, entries):
    """One record per thing worth finding (IMP-006). Built at no token cost; searched in the browser."""
    idx = []
    add = lambda kind, title, url, text="", where="": idx.append({"k": kind, "t": title, "u": url, "w": where, "x": text})
    for t in TOPICS:
        add("Idea" if not on_roadmap(t, False) else "Feature", t["title"], f"topics/{t['slug']}.html", plain(t["card_md"]), n_(len(t['docs']), "source"))
    for f in features:
        u = f"features/{f['slug']}.html"
        add("Feature", f["title"], u + "#overview", plain(f["card_md"]), STATUS[f["status"]][0])
        if f["page_md"]:
            add("Confluence page", f["title"], u + "#page", plain(f["page_md"]), f["title"])
    for x in work:
        add("Epic" if x["kind"] == "epic" else "Story", x["title"], x["href"], plain(x["md"]), x["feature_title"] or "No topic")
    for it in items:
        if it.get("md"):
            add(it["kind"], it["title"], it["href"], plain(it["md"]))
    import people as people_mod   # a person opens their side panel (the link is a fallback to the People page)
    for p in people_mod.load():
        add("Person", p["name"], f"people.html#{p['slug']}", " ".join(x for x in (p["role"], p["team"]) if x), plain(p["role"], 80))
        idx[-1]["a"] = "|".join(p["aliases"])
        idx[-1]["p"] = p["name"]
    titles = GRAPH.get("titles", {})
    for p in sorted((M / "02_digests").glob("MANTIS-DOC-*.md"), reverse=True):
        m = re.search(r"(?ms)^## Summary\s*\n(.*?)(?=^## |\Z)", p.read_text(encoding="utf-8"))
        title = re.sub(ID, "", titles.get(p.stem, "")).strip()
        if title:
            add("Source", title, "", plain(m.group(1), 900) if m else "")
    for e in entries:
        add("Mantis backlog", e["title"], "sources.html#backlog", plain(e["body"], 1500), e["id"].replace("MANTIS-", ""))
    for o in OPEN:
        add("Question", plain(o["topic"], 140), f"questions.html#k={hashlib.sha1(o['id'].encode('utf-8')).hexdigest()[:10]}", plain(o["status_full"]), o["id"].replace("MANTIS-", ""))
    return idx
