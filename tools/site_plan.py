"""Site pages for planning: Features (Following, Roadmap with its Timeline view, Ideas, All), feature and topic pages, Epics & stories."""
import re
from site_common import *   # noqa: F401,F403  (shared state and helpers)


# ---------- Pages ----------

def focus_html(features):
    """Following: the cards the owner follows, in their own order, with what each one waits on. Drag to rank."""
    by_slug = {c["slug"]: (c, c in features) for c in features + TOPICS}
    mine = [by_slug[s] for s in FOCUS["following"] if s in by_slug]
    waiting_of = lambda slug: sum(1 for o in OPEN if o["status"] != "Open" and slug in o["features"])
    ready = {r["slug"]: r for r in READY.get("features", [])}

    def focus_row(i, c, feat):
        sig = []
        if waiting_of(c["slug"]):
            sig.append(f'<span class="pill w-jira plain" title="Open questions with a likely answer">{waiting_of(c["slug"])} to decide</span>')
        if c.get("new_docs"):
            sig.append(f'<span class="pill w-review plain" title="Sources not yet in the summary">{len(c["new_docs"])} new</span>')
        sig.append(f'<span class="muted small f-open">{c["open"]} open</span>' if c.get("open") else '<span class="f-open"></span>')
        sig.append(pill(*STATUS[c["status"]]) if feat else '<span class="tag">Topic</span>')
        r = ready.get(c["slug"])
        why = f'<span class="muted small f-why">{esc(READY["states"].get(r["state"], r["state"]))}: {esc(r["why"])}</span>' if r and r["state"] not in ("ready", "measuring", "reviewed") else ""
        return (f'<li class="f-row" draggable="true" data-slug="{c["slug"]}"><span class="t-grip" title="Drag to rank">⋮⋮</span><span class="f-rank">{i}</span>'
                f'<span class="f-main"><a class="row-t" href="{"features" if feat else "topics"}/{c["slug"]}.html">{esc(c["title"])}</a>{why}</span><span class="f-sig">{"".join(sig)}</span>'
                f'<span class="f-move nocopy"><button type="button" data-m="-1" title="Move up" aria-label="Move up">↑</button><button type="button" data-m="1" title="Move down" aria-label="Move down">↓</button></span></li>')

    return (('<input type="search" id="f-filter" placeholder="Filter…" aria-label="Filter what you follow">' if len(mine) > 8 else "")
            + '<ol class="focus-list" id="focus-list">' + "".join(focus_row(i + 1, c, f) for i, (c, f) in enumerate(mine)) + "</ol>"
            + '<p class="muted small f-hint">Drag or use ↑ ↓ to rank: put what you will tackle first at the top.</p>') if mine \
        else '<p class="empty">You follow nothing yet. Open <b>All</b> and press ☆ Follow on the subjects you own.</p>'


def page_features(features, later, built):
    """Features (MANTIS-IMP-094): Following, Roadmap, Ideas and All under one switch. Following is the ranked
    focus list, Roadmap the board, list and timeline, Ideas and All the cards with Follow and Roadmap buttons."""
    rd = roadmap_html(features, later)
    cards = [(f, True) for f in features] + [(t, False) for t in TOPICS]
    n_f = sum(1 for s in FOCUS["following"] if not archived(s))
    n_r = sum(1 for c, f in cards if on_roadmap(c, f))
    n_i = sum(1 for c, f in cards if not f and not on_roadmap(c, f) and not archived(c["slug"]))
    n_a = sum(1 for c, f in cards if archived(c["slug"]))
    n_epics, n_stories = len({e["id"] for f in features for e in f["epics"]}), sum(len(f["stories"]) for f in features)
    body = f"""<div class="page-h"><div><h1>Features</h1><p class="lead">Every feature and idea Mantis tracks. Follow what you own; it comes first everywhere.</p></div>
<a class="btn-line" href="work.html">Epics &amp; stories <span class="muted">{n_epics + n_stories}</span></a></div>
<div class="scope-bar"><div class="seg seg-lg" id="ttab" role="tablist" aria-label="Which features"><button data-v="focus" class="on" role="tab">Following <span class="muted">{n_f}</span></button>
<button data-v="roadmap" role="tab">Roadmap <span class="muted">{n_r}</span></button><button data-v="ideas" role="tab">Ideas <span class="muted">{n_i}</span></button>
<button data-v="all" role="tab">All <span class="muted">{len(cards) - n_a}</span></button></div>
<button type="button" class="linkish small" data-arch>Archived · {n_a}</button></div>
<section data-scope-panel="focus" class="panel-box">{focus_html(features)}</section>
<section data-scope-panel="roadmap" hidden>{rd}</section>
<section data-scope-panel="tiles" hidden><div class="toolbar"><input id="tq" type="search" placeholder="Filter…" aria-label="Filter features and ideas"><div class="bulk nocopy" id="t-bulk" aria-label="Change several at once"></div></div>
<p class="empty" id="t-empty" hidden>Nothing here yet.</p>
<div class="later topic-grid">{"".join(tile(c, f) for c, f in cards)}</div></section>"""
    return shell("Features", body, active="features", built=built)


def tile(c, feat):
    url = ("features/" if feat else "topics/") + c["slug"] + ".html"
    fol, road = c["slug"] in FOCUS["following"], on_roadmap(c, feat)
    kind = "" if feat else '<span class="tag">Idea</span>'
    arc = archived(c["slug"])
    return (f'<div class="tile topic-tile" data-slug="{c["slug"]}" data-following="{int(fol)}" data-roadmap="{int(road)}" data-idea="{int(not feat and not road)}" data-archived="{int(arc)}">'
            f'<h3><a href="{url}">{esc(c["title"])}</a></h3>{kind}<p>{esc(c["summary"])}</p>'
            f'<div class="facts"><span><b>{len(c["docs"])}</b> {"source" if len(c["docs"]) == 1 else "sources"}</span>' + (f'<span><b>{c["open"]}</b> open {"question" if c["open"] == 1 else "questions"}</span>' if c.get("open") else "")
            + (f'<span class="warn-text">{len(c["new_docs"])} new since summary</span>' if c.get("new_docs") else '<span>Summary current</span>') + '</div>'
            f'<div class="tile-acts nocopy"><button type="button" class="act follow{" on" if fol else ""}" data-a="follow" aria-pressed="{str(fol).lower()}">{"★ Following" if fol else "☆ Follow"}</button>'
            f'<button type="button" class="act road{" on" if road else ""}" data-a="roadmap" aria-pressed="{str(road).lower()}">{"✓ On roadmap" if road else "+ Roadmap"}</button>'
            f'<button type="button" class="act arc" data-a="archive" title="Hide this card everywhere; restore it from Archived">{"Restore" if arc else "Archive"}</button></div></div>')


def roadmap_html(features, later):
    data = [{k: f[k] for k in ("slug", "title", "type", "status", "status_note", "priority", "jira", "estimate", "updated", "summary", "open")}
            | {"epics": len(f["epics"]), "page": bool(f["page"]), "stories": len(f["stories"]),
               "storiesDone": sum(1 for s in f["stories"] if s["status"] in ("in-jira", "done"))}
            for f in features if on_roadmap(f, True)]
    for f in data:
        f["url"] = f"features/{f['slug']}.html"
    for t in TOPICS:
        if on_roadmap(t, False):
            fm = read(t["card"])[0]
            data.append({"slug": t["slug"], "url": f"topics/{t['slug']}.html", "title": t["title"], "type": "topic",
                         "status": fm.get("status", "discovery") if fm.get("status") in STATUS else "discovery", "status_note": "",
                         "priority": fm.get("priority", "") if fm.get("priority") in ("P1", "P2", "P3") else "", "jira": "none",
                         "estimate": "", "updated": t["updated"], "summary": t["summary"], "open": t["open"], "epics": 0,
                         "page": False, "stories": 0, "storiesDone": 0})
    data += [{"slug": "", "title": l["title"], "type": "feature", "status": "none", "status_note": "", "priority": "", "jira": "",
              "estimate": "", "updated": "", "summary": l["note"], "open": 0, "epics": 0, "page": False, "stories": 0, "storiesDone": 0} for l in later]
    labels = {k: v[0] for k, v in STATUS.items()}
    chips = "".join(f'<button data-v="{k}">{v[0]}</button>' for k, v in STATUS.items())
    return f"""<div class="toolbar rd-bar"><div class="seg" id="view" aria-label="Layout"><button data-v="board" class="on">Board</button><button data-v="list">List</button><button data-v="timeline">Timeline</button></div>
<div class="rd-tools" id="rd-tools"><input id="q" type="search" placeholder="Filter…" aria-label="Filter the roadmap">
<div class="chips" id="f-status"><button data-v="all" class="on">All</button>{chips}</div>
<div class="chips" id="f-prio"><button data-v="all" class="on">Any priority</button><button data-v="P1">P1</button><button data-v="P2">P2</button><button data-v="P3">P3</button></div></div></div>
<div id="board"></div><div id="list" hidden></div><div id="tl-view" hidden>{page_timeline("", embed=True)}</div>
<script id="data" type="application/json">{json.dumps({"items": data, "labels": labels})}</script>"""


def page_feature(f, features, epics_by_id, built):
    label, cls = STATUS[f["status"]]
    switch = "".join(f'<option value="{x["slug"]}.html"{" selected" if x is f else ""}>{esc(x["title"])} · {STATUS[x["status"]][0]}</option>' for x in features if x is f or not archived(x["slug"]))
    meta = [prio_pill(f["priority"]), pill(label, cls)]
    if f["type"] == "workstream":
        meta.append('<span class="tag">Platform workstream</span>')
    if f["jira"] and f["jira"] != "none":
        meta.append(f'<button class="pill p-jira copy-text" data-text="{esc(f["jira"])}" title="Copy the Jira key">Jira {esc(f["jira"])}</button>')
    if f["estimate"]:
        meta.append(f'<span class="muted small">2027 estimate: {esc(f["estimate"])}</span>')
    meta.append(fresh(f))
    if archived(f["slug"]):
        meta.insert(0, '<span class="tag">Archived</span>')
    note = f'<p class="muted">{esc(f["status_note"])}</p>' if f["status_note"] else ""
    t = f["title"]
    epics = f["epics"]
    qs = feature_questions(f["slug"])
    tickets = jira_tickets(f["slug"])
    first_draft = "page" if f["page_md"] else (f'epic-{epics[0]["anchor"]}' if epics else "page")
    tabs = (f'<a href="#overview" data-match="overview">Overview</a>'
            f'<a href="#questions" data-match="questions">Questions{f" <span class=\"tab-n\">{len(qs)}</span>" if qs else ""}</a>'
            f'<a href="#jira" data-match="jira">Jira{f" <span class=\"tab-n\">{len(tickets)}</span>" if tickets else ""}</a>'
            f'<a href="#{first_draft}" data-match="page epic- story-">Drafts</a>')
    # Drafts: the Confluence page, the epics and the stories, one at a time, with a switcher above each
    drafts = [("page", "Confluence page", f["page_status"])] + [(f"epic-{e['anchor']}", f"Epic: {e['title']}", e["status"]) for e in epics]
    switcher = lambda here: (f'<div class="epic-switch nocopy" aria-label="Drafts">' + "".join(
        f'<a class="chip{" on" if k == here else ""}" href="#{k}">{esc(label)}</a>' for k, label, _ in drafts) + "</div>") if len(drafts) > 1 else ""
    panels = [("overview", copy_bar("Copy one-pager"), render(f["card_md"])),
              ("questions", "", questions_html(qs, "../")),
              ("jira", "", tickets_html(tickets, f.get("jira", ""))),
              ("page", (copy_bar("Copy page", f["page"]) if f["page_md"] else ""),
               switcher("page") + (render(f["page_md"]) if f["page_md"] else empty("Confluence page", f"Write the Confluence page for {t}")))]
    for e in epics:
        panels.append((f"epic-{e['anchor']}", copy_bar("Copy epic", e["file"]), switcher(f"epic-{e['anchor']}") + render(e["md"], breaks=True, sections=False)))
    for s in f["stories"]:
        ep = f'<p class="muted small nocopy">Story{" in epic " + esc(s["epic_title"]) if s["epic_title"] else ", not in an epic"} · {WORK.get(s["status"], (s["status"],))[0]}</p>'
        panels.append((f"story-{s['anchor']}", copy_bar("Copy story", s["file"]), ep + render(s["md"], breaks=True, sections=False)))
    ph = "".join(f'<div class="tab-panel" id="p-{k}" hidden>{bar}<article class="doc">{body}</article></div>' for k, bar, body in panels)
    done = sum(1 for s in f["stories"] if s["status"] in ("in-jira", "done"))
    nav = (f'<a class="story" href="#page" data-anchor="page"><span><span class="k-ico">▤</span>Confluence page</span>{work_pill(f["page_status"]) if f["page_md"] else "<span class=\"muted small\">not written</span>"}</a>'
           + "".join(f'<a class="story" href="#epic-{e["anchor"]}" data-anchor="epic-{e["anchor"]}"><span><span class="k-ico k-epic">◆</span>{esc(e["title"])}</span>{work_pill(e["status"])}</a>' for e in epics)
           + (story_list(f["stories"], epics_by_id) or '<p class="muted small side-empty">No stories yet.</p>'))
    body = f"""
<div class="crumbs"><a href="../features.html">Features</a><span>›</span>
<select id="switch" aria-label="Go to another feature">{switch}</select></div>
<div class="feat-h"><h1>{esc(t)}</h1><div class="meta">{"".join(m for m in meta if m)}</div>{note}
<p class="muted small">Updated {esc(f["updated"])}</p>
<div class="card-acts">{job_btn("refresh-card", "Refresh summary", arg=f["slug"], cls="mini")}</div></div>
<div class="feat">
<div class="feat-main"><nav class="tabs" aria-label="This feature">{tabs}</nav>{ph}</div>
<aside class="side"><div class="side-h"><h2>Drafts</h2><span class="muted small">{done}/{len(f["stories"])} stories in Jira</span></div>{nav}{feature_entities(f["slug"])}</aside>
</div>"""
    return shell(t, body, base="../", active="features", built=built)


def feature_questions(slug):
    from site_day import scope_of, yours
    mine = [o for o in yours() if slug in o.get("features", [])]
    return mine + [o for o in OPEN if slug in o.get("features", []) and scope_of(o) == "others"]


def questions_html(qs, base):
    """A feature's open questions, each linking to where it is answered (the Questions page)."""
    from site_day import scope_of, qkey, topic_text
    if not qs:
        return '<p class="empty">No open questions on this feature.</p>'
    row = lambda o: (f'<a class="row" href="{base}questions.html#k={qkey(o)}"><span class="row-t">{esc(topic_text(o))}</span>'
                     + (f'<span class="muted small">Ask {esc(o["ask"]["name"].split()[0])}</span>' if scope_of(o) == "others" else
                        pill("Decide", "s-build plain") if o["status"] not in ("Open", "Unconfirmed") else pill("Possible conflict", "s-ref plain") if o["status"] == "Unconfirmed" else "")
                     + "</a>")
    you = [o for o in qs if scope_of(o) == "you"]
    oth = [o for o in qs if scope_of(o) == "others"]
    return ((f'<h2>For you <span class="muted">{len(you)}</span></h2>' + "".join(row(o) for o in you) if you else "")
            + (f'<h2>Waiting on others <span class="muted">{len(oth)}</span></h2>' + "".join(row(o) for o in oth) if oth else ""))


def jira_site():
    env = M / "config" / ".env"
    m = re.search(r"(?m)^JIRA_URL\s*=\s*(\S+)", env.read_text(encoding="utf-8")) if env.exists() else None
    return m.group(1).rstrip("/") if m else ""


def jira_tickets(slug):
    """Tickets under this card's Jira Feature or items, from the local mirror (no call to Jira)."""
    try:
        import atl_store, atl_updates, atl_client
        idx, conf = atl_store.load_index("jira"), atl_client.load_config()
    except Exception:
        return []
    rows = [dict(v, key=k) for k, v in idx.items() if atl_updates.card_of(k, idx, conf) == slug]
    return sorted(rows, key=lambda r: r.get("updated", ""), reverse=True)


def tickets_html(rows, key):
    if not rows:
        return '<p class="empty">No Jira tickets mapped to this feature yet. A pull maps them once the feature has a Jira key.</p>'
    site = jira_site()
    order = {"Feature": 0, "Epic": 1}
    rows = sorted(rows, key=lambda r: order.get(r.get("type"), 2))   # Features, then Epics, then the rest; newest first within each (stable)
    link = lambda k: f'<a href="{site}/browse/{k}" target="_blank" rel="noopener">{k}</a>' if site else k
    head = '<thead><tr><th>Key</th><th>Type</th><th>Status</th><th>Summary</th><th>Updated</th></tr></thead>'
    body = "".join(f'<tr><td class="nowrap">{link(esc(r["key"]))}</td><td>{esc(r.get("type", ""))}</td><td class="nowrap">{esc(r.get("status", ""))}</td>'
                   f'<td>{esc(r.get("summary", ""))}</td><td class="nowrap muted">{esc(r.get("updated", "")[:10])}</td></tr>' for r in rows[:80])
    more = f'<p class="muted small">{len(rows) - 80} more in Jira.</p>' if len(rows) > 80 else ""
    return f'<p class="muted small nocopy">From the Jira mirror, as of the last pull. {n_(len(rows), "ticket")}.</p><div class="tbl"><table>{head}<tbody>{body}</tbody></table></div>{more}'


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
    return shell("Epics & stories", body, active="features", built=built)


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
    return shell(x["title"], body, base="../", active="features", built=built)


def page_topic(t, topics, built):
    switch = "".join(f'<option value="{x["slug"]}.html"{" selected" if x is t else ""}>{esc(x["title"])}</option>' for x in topics if x is t or not archived(x["slug"]))
    body = f"""
<div class="crumbs"><a href="../features.html#all">Features</a><span>›</span>
<select id="switch" aria-label="Go to another topic">{switch}</select></div>
<div class="feat-h"><h1>{esc(t["title"])}</h1><div class="meta"><span class="tag">Topic</span>{'<span class="tag">Archived</span>' if archived(t["slug"]) else ""}{fresh(t)}<span class="muted small">{n_(len(t["docs"]), "source")}{f" · {n_(t['open'], 'open question')}" if t["open"] else ""}</span></div>
<div class="card-acts">{job_btn("refresh-card", "Refresh summary", arg=t["slug"], cls="mini")}{job_btn("rebuild", "Rebuild", ai=False, cls="mini")}</div></div>
<div class="feat">
<div class="feat-main"><div class="tab-panel" id="p-overview">{copy_bar("Copy summary")}<article class="doc">{render(t["card_md"])}</article></div></div>
<aside class="side">{feature_entities(t["slug"], 14, "topic") or '<p class="empty">No people or systems named yet.</p>'}</aside>
</div>"""
    return shell(t["title"], body, base="../", active="features", built=built)


def page_timeline(built, embed=False):
    """Timeline (MANTIS-IMP-052): each roadmap feature over 8 weeks back and 10 ahead. Past: when sources,
    decisions and stage moves arrived. Ahead: dated steps, chase dates and regular meetings. Time away spans all rows."""
    from datetime import date as _d, timedelta as _td
    tl = CHANGES.get("timeline") or {}
    if not tl.get("rows"):
        return shell("Timeline", '<div class="page-h"><div><h1>Timeline</h1></div></div><p class="empty">No roadmap features yet.</p>', active="timeline", built=built)
    start, end, today = (_d.fromisoformat(tl[k]) for k in ("start", "end", "today"))
    span = (end - start).days
    pct = lambda iso: max(0.0, min(100.0, (_d.fromisoformat(iso[:10]) - start).days / span * 100))
    weeks = [start + _td(weeks=i) for i in range(tl["weeks"])]
    months, last = [], None
    for i, w in enumerate(weeks):
        if w.month != last:
            months.append((i, w.strftime("%b")))
            last = w.month
    head = "".join(f'<span class="tl-m" style="left:{i / len(weeks) * 100:.3f}%">{m}</span>' for i, m in months)
    ticks = "".join(f'<span class="tl-w" style="left:{i / len(weeks) * 100:.3f}%">{w.day}</span>' for i, w in enumerate(weeks))
    grid = "".join(f'<span class="tl-g" style="left:{i / len(weeks) * 100:.3f}%"></span>' for i in range(1, len(weeks)))
    now = f'<span class="tl-now" style="left:{pct(today.isoformat()):.3f}%" aria-hidden="true"></span>'
    away = "".join(f'<span class="tl-away" style="left:{pct(a["start"]):.3f}%;width:{max(0.6, pct(a["end"]) - pct(a["start"]) + 100 / span):.3f}%" title="{esc(a["label"])}: {esc(a["start"])} to {esc(a["end"])}"></span>'
                   for a in tl["away"])
    nice = lambda iso: _d.fromisoformat(iso).strftime("%a %d %b").replace(" 0", " ")

    def marks(r):
        out = []
        weeks_src = {}
        for m in r["marks"]:
            if m["kind"] == "source":   # sources fold into one dot per week, sized by count
                wk = (_d.fromisoformat(m["date"]) - start).days // 7
                weeks_src.setdefault(wk, []).append(m)
        for wk, ms in weeks_src.items():
            n = len(ms)
            tip = f'{n} source{"s" if n != 1 else ""} added to Mantis in the week of {nice((start + _td(weeks=wk)).isoformat())}: ' + "; ".join(m["label"] for m in ms[:4]) + ("…" if n > 4 else "")
            out.append(f'<span class="tl-k tl-src{" tl-many" if n > 2 else ""}" style="left:{(wk + .5) / len(weeks) * 100:.3f}%" title="{esc(tip)}" aria-label="{esc(tip)}">{n if n > 1 else ""}</span>')
        for m in r["marks"]:
            if m["kind"] == "source":
                continue
            label = f'{TL_KINDS.get(m["kind"], m["kind"])}, {nice(m["date"])}: {m["label"]}'
            out.append(f'<span class="tl-k tl-{m["kind"]}" style="left:{pct(m["date"]):.3f}%" title="{esc(label)}" aria-label="{esc(label)}"></span>')
        return "".join(out)

    def row(r):
        days = (today - _d.fromisoformat(r["last"])).days if r["last"] else None
        quiet = f'active {"today" if days == 0 else "yesterday" if days == 1 else f"{days} days ago"}' if days is not None else "quiet in this window"
        return (f'<div class="tl-row"><div class="tl-label"><a href="{esc(r["href"])}">{esc(r["title"])}</a>'
                f'<span class="tl-meta">{pill(*STATUS.get(r["status"], ("?", "s-none")))}<span class="muted small">{esc(quiet)}</span></span></div>'
                f'<div class="tl-track">{marks(r)}</div></div>')

    legend = "".join(f'<span class="tl-leg"><span class="tl-k tl-{k}" aria-hidden="true"></span>{esc(v)}</span>'
                     for k, v in (("src", "Added to Mantis (one dot a week)"), ("decision", "Decision"), ("stage", "Stage changed"),
                                  ("possible", "Possible conflict"), ("due", "Step due"), ("chase", "Chase"), ("meeting", "Meeting")))
    legend += '<span class="tl-leg"><span class="tl-away-key" aria-hidden="true"></span>You are away</span>' if tl["away"] else ""
    up = "".join(f'<a class="row" href="{esc(m["href"])}"><span class="tl-up-d">{esc(nice(m["date"]))}</span><span class="tl-k tl-{m["kind"]}" aria-hidden="true"></span>'
                 f'<span class="row-t">{esc(m["label"])}</span><span class="muted small">{esc(m["card"])}</span></a>' for m in tl["upcoming"])
    up += "".join(f'<div class="row"><span class="tl-up-d">{esc(nice(a["start"]))}</span><span class="tl-away-key" aria-hidden="true"></span>'
                  f'<span class="row-t">{esc(a["label"])} until {esc(nice(a["end"]))}</span></div>' for a in tl["away"] if a["end"] >= tl["today"])
    nodates = not any(m["kind"] in ("due", "chase") for r in tl["rows"] for m in r["marks"])
    body = f"""<div class="page-h"><div><h1>Timeline</h1><p class="lead">Your roadmap over the last 8 weeks and the next 10: what moved, and what is dated ahead. Features you follow come first. Sources show the week they were added to Mantis, not when they were written.</p></div></div>
<div class="tl-legend nocopy">{legend}</div>
<section class="tl panel-box" aria-label="Timeline, {esc(nice(tl['start']))} to {esc(nice(tl['end']))}">
<div class="tl-scroll"><div class="tl-inner">
<div class="tl-row tl-head"><div class="tl-label"></div><div class="tl-track">{head}{ticks}</div></div>
<div class="tl-body"><div class="tl-overlay" aria-hidden="true"><div class="tl-label"></div><div class="tl-track">{grid}{away}{now}</div></div>
{"".join(row(r) for r in tl["rows"])}</div></div></div></section>
<section class="panel-box tl-up"><div class="box-h"><h2>Coming up</h2><span class="muted small">Dated steps, chases, meetings and time away</span></div>
{up or '<p class="empty">Nothing dated ahead.</p>'}
{'<p class="muted small tl-hint">No next step has a due date yet. Add a Due column to a card&#39;s Next steps table and it appears here.</p>' if nodates else ""}</section>"""
    if embed:   # shown inside another page (MANTIS-IMP-068): no page header, no shell
        return re.sub(r'^<div class="page-h">.*?</div></div>\n?', "", body, count=1, flags=re.S)
    return shell("Timeline", body, active="timeline", built=built)
