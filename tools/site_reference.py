"""Site pages for reference and housekeeping: Library (pages, diagrams, decisions), Graph, What's new, Health (with the backlog), search."""
import re
from site_common import *   # noqa: F401,F403  (shared state and helpers)


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
    return shell("Library", body, active="library", built=built)


def page_single(it, built):
    body = f"""<div class="crumbs"><a href="../library.html">Library</a><span>›</span><span>{esc(it["title"])}</span></div>
<div class="tab-panel">{copy_bar("Copy page", it.get("file"))}<article class="doc">{render(it["md"])}</article></div>"""
    return shell(it["title"], body, base="../", active="library", built=built)


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
        add("Mantis backlog", e["title"], "health.html#backlog", plain(e["body"], 1500), e["id"].replace("MANTIS-", ""))
    for o in OPEN:
        add("Open item", plain(o["topic"], 140), f"review.html#{o['id']}", plain(o["status_full"]), o["id"].replace("MANTIS-", ""))
    return idx


def page_decisions(built, embed=False):
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
    if embed:   # shown inside another page (MANTIS-IMP-068): no page header, no shell
        return re.sub(r'^<div class="page-h">.*?</div></div>\n?', "", body, count=1, flags=re.S)
    return shell("Decisions", body, active="decisions", built=built)


def page_changes(built):
    """What's new (MANTIS-IMP-043) and cards to refresh (MANTIS-IMP-044)."""
    from datetime import date as _d, timedelta as _td
    today = _d.fromisoformat(CHANGES["today"]) if CHANGES.get("today") else _d.today()
    since = (today - _td(days=30)).isoformat()
    evs = [e for e in CHANGES["events"] if e["date"] >= since]
    # The feed, grouped by day
    days = {}
    for e in evs:
        days.setdefault(e["date"], []).append(e)

    def day_label(d):
        dd = _d.fromisoformat(d)
        n = (today - dd).days
        return ("Today" if n == 0 else "Yesterday" if n == 1 else dd.strftime("%A")) + f'<span class="muted"> · {dd.strftime("%d %b").lstrip("0")}</span>' if n < 7 \
            else dd.strftime("%A %d %B").replace(" 0", " ")

    def row(e):
        label, group, cls = EV_KINDS.get(e["kind"], (e["kind"].capitalize(), "cards", "ev-card"))
        if e["kind"] == "page" and e.get("what"):
            label = f'{e["what"]} updated'
        card = (f'<a class="ev-card muted small" href="{esc(e["card_href"])}">{esc(e["card"])}</a>'
                if e.get("card") and e["card"] != e["title"] and e.get("card_href") else "")
        title = f'<a href="{esc(e["href"])}">{esc(e["title"])}</a>' if e.get("href") else esc(e["title"])
        detail = f'<span class="ev-d muted small">{esc(e["detail"])}</span>' if e.get("detail") else ""
        return (f'<li class="ev" data-kind="{esc(e["kind"])}" data-group="{group}" data-date="{e["date"]}">'
                f'<span class="ev-k {cls}"><span class="ev-ico" aria-hidden="true"></span>{esc(label)}</span>'
                f'<span class="ev-main"><span class="ev-t">{title}</span>{detail}</span>{card}</li>')

    def day_rows(es):
        """What needs a decision first. Five or more of one routine kind on a day fold into one row."""
        es = sorted(es, key=lambda e: EV_ORDER.index(e["kind"]) if e["kind"] in EV_ORDER else 99)
        out, done = [], set()
        for e in es:
            k = e["kind"]
            same = [x for x in es if x["kind"] == k]
            if k in EV_FOLD and len(same) >= 5:
                if k in done:
                    continue
                done.add(k)
                label, group, cls = EV_KINDS[k]
                out.append(f'<li class="ev ev-fold" data-kind="{k}" data-group="{group}" data-date="{e["date"]}" data-n="{len(same)}"><details>'
                           f'<summary><span class="ev-k {cls}"><span class="ev-ico" aria-hidden="true"></span>{esc(label)}</span>'
                           f'<span class="ev-main"><span class="ev-t">{esc(EV_FOLD[k].format(n=len(same)))}</span>'
                           f'<span class="ev-d muted small">Show them</span></span></summary>'
                           f'<ol class="ev-sub">{"".join(row(x) for x in same)}</ol></details></li>')
            else:
                out.append(row(e))
        return "".join(out)

    feed = "".join(f'<section class="ev-day" data-date="{d}"><h3><span>{day_label(d)}</span><span class="muted ev-n">{n_(len(es), "change")}</span></h3>'
                   f'<ol class="ev-list">{day_rows(es)}</ol></section>' for d, es in days.items())
    present = {EV_KINDS.get(e["kind"], ("", "cards", ""))[1] for e in evs}
    chips = '<button data-v="all" class="on">All</button>' + "".join(f'<button data-v="{g}">{esc(l)}</button>' for g, l in EV_GROUPS if g in present)
    body = f"""<div class="page-h"><div><h1>What's new</h1><p class="lead">Everything that changed in Mantis, newest first: sources, questions and answers, decisions, stage moves, and pages or Jira items updated.</p></div></div>
<div class="toolbar ev-bar nocopy"><div class="seg" id="ev-range" aria-label="Period"><button data-v="visit">Since your last visit</button><button data-v="7" class="on">7 days</button><button data-v="30">30 days</button></div>
<div class="chips" id="ev-kind" aria-label="Kind of change">{chips}</div></div>
<p class="muted small ev-sum" id="ev-sum" aria-live="polite"></p>
<div class="ev-feed" id="ev-feed" data-today="{today.isoformat()}">{feed or '<p class="empty">Nothing changed in the last 30 days.</p>'}</div>
<p class="empty" id="ev-none" hidden>Nothing of this kind in this period.</p>"""
    return shell("What's new", body, active="changes", built=built)


def page_diagrams(built, embed=False):
    """Registered knowledge assets (MANTIS-IMP-008): diagrams worth reusing, with what each shows."""
    clean = lambda v: re.sub(r"\s*(?:Source: )?\(?MANTIS-[A-Z]+-\d+(?:, (?:page|slide) \d+)?\)?[.;,]?", "", v).strip()
    tiles = []
    for a in sorted(ASSETS, key=lambda x: (x["type"], x["title"].lower())):
        if a["status"] == "Superseded" or not asset_src(a["id"]):
            continue
        src = asset_src(a["id"])
        where = ", ".join(esc(GRAPH.get("titles", {}).get(d, "")) for d in a["docs"] if GRAPH.get("titles", {}).get(d))
        used = len(a.get("referenced_by", []))
        meta = (f'<p class="muted small">From: {where}</p>' if where else "") + (f'<p class="muted small">Used on {used} page{"s" if used != 1 else ""}.</p>' if used else "")
        tiles.append(f'<article class="tile dia" data-type="{esc(a["type"])}"><a class="dia-img" href="{esc(src)}" target="_blank" rel="noopener" title="Open full size">'
                     f'<img src="{esc(src)}" alt="{esc(a["title"])}" loading="lazy"></a>'
                     f'<div class="dia-body"><span class="tag">{esc(a["type"].replace("-", " ").capitalize() or "Diagram")}</span><h3>{esc(a["title"])}</h3>'
                     f'<p>{esc(clean(a["description"]))}</p>'
                     f'{meta}</div></article>')
    types = sorted({a["type"] for a in ASSETS if a["type"]})
    chips = "".join(f'<button data-v="{esc(t)}">{esc(t.replace("-", " ").capitalize())}</button>' for t in types)
    body = f"""<div class="page-h"><div><h1>Diagrams</h1><p class="lead">Diagrams and other visuals from the sources that are worth reusing, each with what it shows. Pages reuse one of these before anyone draws a new diagram.</p></div></div>
{f'<div class="toolbar"><div class="chips" id="f-dia"><button data-v="all" class="on">All</button>{chips}</div></div>' if len(types) > 1 else ""}
<div class="dia-grid">{"".join(tiles) or '<p class="empty">No diagrams registered yet.</p>'}</div>"""
    if embed:   # shown inside another page (MANTIS-IMP-068): no page header, no shell
        return re.sub(r'^<div class="page-h">.*?</div></div>\n?', "", body, count=1, flags=re.S)
    return shell("Diagrams", body, active="diagrams", built=built)


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
<div id="job-list"></div></section>
<details class="grp-box backlog-box" id="backlog"><summary><h2>Mantis backlog</h2><span class="muted small">Ideas for Mantis itself</span></summary>{page_backlog(backlog(), built, embed=True)}</details>"""
    return shell("Health", body, active="health", built=built)


def page_backlog(entries, built, embed=False):
    val = {"Transformational": 0, "High": 1, "Medium": 2, "Low": 3}
    size = {"Small": 0, "Medium": 1, "Large": 2, "Very": 3}
    cls = {"In": "s-build", "Investigating": "s-build", "Proposed": "w-review", "Parked": "s-none", "Adopted": "s-done", "Rejected": "s-ref"}

    def card(e):
        return (f'<details class="bl" data-status="{esc(e["status"])}"><summary><span class="bl-id">{esc(e["id"].replace("MANTIS-", ""))}</span>'
                f'<span class="row-t">{esc(e["title"])}</span>{pill("In progress" if e["status"] == "In" else e["status"], cls.get(e["status"], "s-none") + " plain")}'
                f'<span class="muted small">{esc(e["phase"] + " · ") if e.get("phase") else ""}{esc(e["size"])} · {esc(e["value"])} value</span></summary>'
                f'<div class="doc">{markdown.markdown(fix_lists(e["body"]), extensions=["tables", "sane_lists"])}</div></details>')

    key = lambda e: (val.get(e["value"], 4), size.get(e["size"], 4), e["id"])
    active = [e for e in entries if e["status"] in ("In", "Investigating")]
    # Proposed ideas wait for the owner's go, in the order planned (Priority: Phase 1, 2, 3), then by value
    proposed = sorted([e for e in entries if e["status"] == "Proposed"], key=lambda e: (e.get("phase") or "Phase 9", key(e)))
    parked = sorted([e for e in entries if e["status"] == "Parked"], key=key)
    done = [e for e in entries if e["status"] == "Adopted"]
    rejected = [e for e in entries if e["status"] == "Rejected"]
    group = lambda title, xs, open_: (f'<details class="grp-box"{" open" if open_ else ""}><summary><h2>{title} <span class="muted">{len(xs)}</span></h2></summary>'
                                      f'<section class="panel-box">{"".join(card(e) for e in xs)}</section></details>') if xs else ""
    body = f"""<div class="page-h"><div><h1>Mantis backlog</h1><p class="lead">Ideas for improving Mantis itself. Open work first, then parked ideas by value and size. Finished ones are folded away.</p></div></div>
{group("In progress", active, True)}{group("Proposed, waiting for your go", proposed, True)}{group("Parked", parked, True)}{group("Done", done, False)}{group("Rejected", rejected, False)}"""
    if embed:   # shown inside another page (MANTIS-IMP-068): no page header, no shell
        return re.sub(r'^<div class="page-h">.*?</div></div>\n?', "", body, count=1, flags=re.S)
    return shell("Mantis backlog", body, active="backlog", built=built)
