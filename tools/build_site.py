"""Build the read-only Mantis website from the Markdown files.

    python tools/build_site.py      (build_map.py also calls this, so a normal rebuild covers it)
    python tools/serve.py           (serves it at http://localhost:8000 and rebuilds on change)

Markdown stays the only source. This script writes the site to %LOCALAPPDATA%/Mantis/site
(outside OneDrive) and nothing else. Every page is cleaned for pasting into Confluence or Jira: Mantis IDs, source columns, repo paths and
HTML comments are removed. Needs the `markdown` package (pip install markdown).
Reads mantis/knowledge/map/features.json and work.json, which build_map.py writes.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import json, re
from datetime import datetime
from pathlib import Path

from pagebuild.changes import page_changes
from pagebuild.feature import page_feature
from pagebuild.frame import MOVED, redirect
from pagebuild.library import page_library, page_single, search_index
from pagebuild.loaders import draft_data, library_items, load, load_topics
from pagebuild.paths import M, SITE
from pagebuild.people import page_people, people_data
from pagebuild.registry import ASSETS, CHANGES, DRAFTS, FOCUS, GRAPH, OPEN, READY, TOPICS
from pagebuild.topic import page_topic
from pagebuild.work import page_loose, page_work
from site_app import page_app, static_json


# ---------- Build ----------

def build_assets(out):
    """Scripts, styles and tokens. Cheap, so they are rebuilt on every build."""
    # Pages are built in memory; only files whose content changed are written (MANTIS-IMP-016).
    assets = Path(__file__).resolve().parent / "site_assets"
    for p in assets.rglob("*"):
        if p.is_file() and p.parent.name != "js" and "pages" not in p.relative_to(assets).parts:
            out["assets/" + p.relative_to(assets).as_posix()] = p.read_bytes()
    import site_pages
    for t in site_pages.config()["types"]:   # one script and one stylesheet per page type
        out[f"assets/pages/{t}.js"], out[f"assets/pages/{t}.css"] = site_pages.bundle_js(t), site_pages.bundle_css(t)
    import theme
    for problem in theme.check():   # checked on every build (MANTIS-IMP-107)
        print("Theme:", problem)
    out["assets/tokens.css"] = theme.css().encode("utf-8")   # the one source of colour, type, shape and motion
    import layout, stylelint
    for problem in layout.check():
        print("Layout:", problem)
    stylelint.main()   # prints one line; problems are listed under it


def render_pages(out, built):
    """Every page that is drawn from the knowledge. Returns the counts for the summary line."""
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
    items = library_items(features, work)
    w = lambda rel, s: out.__setitem__(rel, s.encode("utf-8"))
    # The six tabs are index.html alone (MANTIS-IMP-107); the old tab addresses redirect (MOVED). Then the pages the tabs lead to
    w("index.html", page_app(built))
    out["assets/app/static.json"] = static_json(features, built).encode("utf-8")
    w("work.html", page_work(work, features, built))
    w("library.html", page_library(items, built))
    w("people.html", page_people(built))
    w("people.json", json.dumps(people_data(), ensure_ascii=False))   # the side panel's People list
    w("library.json", json.dumps([{k: it[k] for k in ("kind", "title", "href", "where", "status")} for it in items], ensure_ascii=False))
    for a in ASSETS:   # copy each registered image once; pages point at /diagrams/<file>
        f = M / "knowledge" / "assets" / a.get("file", "")
        if a.get("file") and f.is_file():
            out[f"diagrams/{f.name}"] = f.read_bytes()
    w("changes.html", page_changes(built))
    for t in TOPICS:
        w(f"topics/{t['slug']}.html", page_topic(t, TOPICS, built))
    # The Mantis backlog is about Mantis itself (docs/project), so search finds only the owner's work (2026-10-31)
    w("search.json", json.dumps(search_index(features, work, items, []), ensure_ascii=False))
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
    return {"features": len(features), "work": len(work), "items": len(items)}


def build():
    import sitecache
    built = datetime.now().strftime("%d %b %Y, %H:%M")
    out = {}
    build_assets(out)
    # Incremental (sitecache.py): when no input changed, the pages already in the site folder are kept, not drawn again.
    sig, state = sitecache.fingerprint(), sitecache.load()
    reuse = sitecache.reusable(state, sig, SITE)
    if reuse:
        counts, page_files = state["counts"], state["files"]
        for rel in page_files:
            out[rel] = None   # None = keep the file that is there
    else:
        before = set(out)
        counts = render_pages(out, built)
        page_files = sorted(set(out) - before)
    # Write only what changed. The "Built" stamp in the footer and in static.json is ignored when comparing, so a
    # rebuild that changes nothing writes nothing and open tabs do not reload. Two builds can
    # overlap (the server rebuilds on save while a session runs build_map.py): a file held by the
    # other build or the browser is retried briefly, then left for the next build.
    import time
    stamp = re.compile(rb"Built [^<\"]*?(?=</span></footer>)|\"built\": \"[^\"]*\"")   # the footer stamp and static.json's built time
    written = 0
    for rel, data in out.items():
        if data is None:
            continue
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
    leaks = [rel for rel, data in out.items() if data is not None and rel.endswith(".html") and Path(rel).name not in ("questions.html", "sources.html")
             and re.search(r"\b(?:DOC|GAP|ASM|CFL|DEC|AST)-\d", re.sub(r"(?s)<template.*?</template>", "", data.decode("utf-8")))]
    if not reuse:
        sitecache.save(sig, page_files, counts)
    print(f"Site: {counts['features']} topics, {counts['work']} epics and stories, {counts['items']} library items -> {SITE} ("
          + (f"pages unchanged, {len(page_files)} reused; " if reuse else "pages drawn; ") + f"{written} file(s) changed)"
          + (f"  WARNING, IDs left in: {leaks}" if leaks else ""))


if __name__ == "__main__":
    import buildlock   # never interleave with a full rebuild (MANTIS-IMP-063)
    buildlock.acquire()
    build()
