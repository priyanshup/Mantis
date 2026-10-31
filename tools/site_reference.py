"""Site pages for reference and housekeeping: Library (pages, diagrams, decisions), What's new, search. Health lives on Sources (site_day.py)."""
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
    return shell("Library", body, built=built)


def page_single(it, built):
    body = f"""<div class="crumbs"><a href="../library.html">Library</a><span>›</span><span>{esc(it["title"])}</span></div>
<div class="tab-panel">{copy_bar("Copy page", it.get("file"))}<article class="doc">{render(it["md"])}</article></div>"""
    return shell(it["title"], body, base="../", built=built)


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
    return shell("What's new", body, active="sources", built=built)


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


