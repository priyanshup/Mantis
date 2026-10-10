"""Build the read-only Mantis website from the Markdown files.

    python tools/build_site.py      (build_map.py also calls this, so a normal rebuild covers it)
    python tools/serve.py           (serves it at http://localhost:8000 and rebuilds on change)

Markdown stays the only source. This script writes the site to %LOCALAPPDATA%/Mantis/site
(outside OneDrive) and nothing else. Every page is cleaned for pasting into Confluence or Jira: Mantis IDs, source columns, repo paths and
HTML comments are removed. Needs the `markdown` package (pip install markdown).
Reads mantis/knowledge/map/features.json and work.json, which build_map.py writes.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import hashlib, html, json, os, re, shutil, tempfile
from urllib.parse import quote
from datetime import datetime
from pathlib import Path

import markdown

import edit_common
from site_common import *   # noqa: F401,F403  (shared state, helpers, shell)
from site_plan import *     # noqa: F401,F403
from site_people import *   # noqa: F401,F403
from site_reference import *   # noqa: F401,F403


# ---------- Build ----------

def app_js():
    """The site script, joined from site_assets/js/*.js in name order (MANTIS-IMP-064). The parts are pieces of
    one script (it opens in 00-core.js and closes in 90-reload-end.js), split by page area for editing."""
    parts = sorted((Path(__file__).resolve().parent / "site_assets" / "js").glob("*.js"))
    return b"".join(p.read_bytes() for p in parts)


def build():
    built = datetime.now().strftime("%d %b %Y, %H:%M")
    mp = M / "knowledge" / "map"
    if (mp / "entities.json").exists():
        GRAPH.update(json.loads((mp / "entities.json").read_text(encoding="utf-8")))
        GRAPH["titles"] = json.loads((mp / "titles.json").read_text(encoding="utf-8")) if (mp / "titles.json").exists() else {}
    if (mp / "changes.json").exists():
        CHANGES.update(json.loads((mp / "changes.json").read_text(encoding="utf-8")))
    if (mp / "readiness.json").exists():
        READY.update(json.loads((mp / "readiness.json").read_text(encoding="utf-8")))
    if (mp / "decision-watch.json").exists():
        READY["decisions"] = json.loads((mp / "decision-watch.json").read_text(encoding="utf-8")).get("flagged", [])
    if (mp / "assets.json").exists():
        ASSETS[:] = json.loads((mp / "assets.json").read_text(encoding="utf-8")).get("assets", [])
    if (mp / "open-items.json").exists():
        OPEN[:] = json.loads((mp / "open-items.json").read_text(encoding="utf-8"))
    features, later, work, epics_by_id = load()
    DRAFTS.clear()
    TOPICS[:] = load_topics()
    DRAFTS.update(draft_data())   # who can answer what, for Draft a message (needs OPEN and TOPICS)
    fp = M / "knowledge" / "focus.json"
    if fp.exists():
        FOCUS.update(json.loads(fp.read_text(encoding="utf-8")))
    hp = M / "knowledge" / "map" / "health.json"
    BADGES["review"] = sum(1 for o in OPEN if o["status"] != "Open")
    BADGES["health"] = sum(1 for i in (json.loads(hp.read_text(encoding="utf-8"))["items"] if hp.exists() else []) if i["level"] == "warn")
    items = library_items(features, work)
    # Pages are built in memory; only files whose content changed are written (MANTIS-IMP-016).
    out = {}
    assets = Path(__file__).resolve().parent / "site_assets"
    for p in assets.rglob("*"):
        if p.is_file() and p.parent.name != "js":
            out["assets/" + p.relative_to(assets).as_posix()] = p.read_bytes()
    out["assets/app.js"] = app_js()
    w = lambda rel, s: out.__setitem__(rel, s.encode("utf-8"))
    w("index.html", page_home(features, later, work, items, built))
    w("roadmap.html", page_roadmap(features, later, built))
    w("work.html", page_work(work, features, built))
    w("library.html", page_library(items, built))
    w("graph.html", page_graph(built))
    w("review.html", page_review(features, built))
    w("topics.html", page_topics(TOPICS, features, built))
    w("health.html", page_health(built))
    w("today.html", page_today(built))
    w("people.html", page_people(built))
    for a in ASSETS:   # copy each registered image once; pages point at /diagrams/<file>
        f = M / "knowledge" / "assets" / a.get("file", "")
        if a.get("file") and f.is_file():
            out[f"diagrams/{f.name}"] = f.read_bytes()
    w("changes.html", page_changes(built))
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
    for rel, to in MOVED.items():   # MANTIS-IMP-068
        w(rel, redirect(to))
    # Write only what changed. The "Built" stamp in the footer is ignored when comparing, so a
    # rebuild that changes nothing writes nothing and open tabs do not reload. Two builds can
    # overlap (the server rebuilds on save while a session runs build_map.py): a file held by the
    # other build or the browser is retried briefly, then left for the next build.
    import time
    stamp = re.compile(rb"Built [^<]*?\.</span></footer>")
    written = 0
    for rel, data in out.items():
        p = SITE / rel
        try:
            if p.exists() and stamp.sub(b"", p.read_bytes()) == stamp.sub(b"", data):
                continue
        except OSError:
            pass
        p.parent.mkdir(parents=True, exist_ok=True)
        for attempt in range(8):
            try:
                p.write_bytes(data)
                written += 1
                break
            except PermissionError:
                if attempt == 7:
                    raise
                time.sleep(0.5)
    removed = 0
    if SITE.exists():
        for p in sorted(SITE.rglob("*"), reverse=True):
            rel = p.relative_to(SITE).as_posix()
            if rel == "version.txt" or rel in out or (p.is_dir() and any(k.startswith(rel + "/") for k in out)):
                continue
            try:
                p.rmdir() if p.is_dir() else p.unlink()
                removed += 1
            except OSError:
                pass   # held by the other build or the browser; the next build removes it
    if written or removed or not (SITE / "version.txt").exists():
        (SITE / "version.txt").write_text(str(datetime.now().timestamp()), encoding="utf-8")
    leaks = [rel for rel, data in out.items() if rel.endswith(".html") and Path(rel).name not in ("backlog.html", "review.html", "health.html")
             and re.search(r"\b(?:DOC|GAP|ASM|CFL|DEC|AST)-\d", re.sub(r"(?s)<template.*?</template>", "", data.decode("utf-8")))]
    print(f"Site: {len(features)} topics, {len(work)} epics and stories, {len(items)} library items -> {SITE} ({written} file(s) changed)"
          + (f"  WARNING, IDs left in: {leaks}" if leaks else ""))


if __name__ == "__main__":
    import buildlock   # never interleave with a full rebuild (MANTIS-IMP-063)
    buildlock.acquire()
    build()
