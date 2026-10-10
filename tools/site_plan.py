"""Site pages for planning: Home, Roadmap (with its Timeline view), feature and topic pages, Topics, Epics & stories, Today."""
import re
from site_common import *   # noqa: F401,F403  (shared state and helpers)


# ---------- Pages ----------

def page_home(features, later, work, items, built):
    counts = {k: sum(1 for f in features if f["status"] == k) for k in STATUS}
    counts["none"] = len(later)
    tiles = "".join(f'<a class="stat {STATUS[k][1]}" href="roadmap.html#status={k}"><b>{counts[k]}</b><span>{STATUS[k][0]}</span></a>' for k in STATUS)
    recent = sorted(features, key=lambda f: f["updated"], reverse=True)[:5]
    rec = "".join(f'<a class="row" href="features/{f["slug"]}.html"><span class="row-t">{esc(f["title"])}</span>'
                  f'{prio_pill(f["priority"])}{pill(*STATUS[f["status"]])}<span class="muted">{esc(f["updated"])}</span></a>' for f in recent)
    # Needs attention: one list of everything waiting on the owner, most useful first.
    att = []
    waiting = sum(1 for o in OPEN if o["status"] not in ("Open", "Unconfirmed"))
    possible = sum(1 for o in OPEN if o["status"] == "Unconfirmed")
    names = sum(1 for o in OPEN if o["kind"] in ("name", "term"))
    if possible:
        att.append(("review.html#possible", f"{n_(possible, 'possible conflict')} between sources: say whether they really disagree", "Check"))
    if waiting:
        att.append(("review.html", f"{waiting} open question{'s' if waiting != 1 else ''} with a likely answer, waiting for your decision", "Decide"))
    if names:
        att.append(("review.html", f"{n_(names, 'name or term', 'names and terms')} to confirm", "Answer"))
    # Decision readiness (MANTIS-IMP-074 to 076): overdue reviews, missing plans, unvalidated problems in refinement or build
    for slug, msg, act in READY.get("attention", []):
        if not archived(slug):
            att.append((f"features/{slug}.html", msg, act))
    # Decisions whose basis changed (MANTIS-IMP-080): what changed, and what is built on them; never reversed by code
    for d in READY.get("decisions", []):
        what = "; ".join(("a source it rests on was edited" if "-DOC-" in x else f"a question it rests on is now \"{now.split(' (')[0]}\"")
                         for x, _, now in d["changes"][:2])
        built = (f" Built on it: {', '.join(d['cards'])}" + (f" and {len(d['outputs'])} page(s) or epic(s)" if d["outputs"] else "") + ".") if d["cards"] else ""
        text = re.sub(r"\s*\([^)]*\)", "", d["decision"])   # asides in brackets make the line harder to read
        short = text if len(text) <= 90 else text[:90].rsplit(" ", 1)[0].rstrip(",;:") + "…"
        att.append((f"library.html#decisions", f"Decision \"{short}\" may need a look: {what}.{built}", "Review"))
    for x in work:
        if x["status"] in ("draft", "review") and x["file"] not in FOCUS.get("archived_work", []) and not archived(x["feature"]):
            att.append((x["href"], f'{"Epic" if x["kind"] == "epic" else "Story"} "{x["title"]}" is {WORK[x["status"]][0].lower()}', "Review"))
    # Pages, epics and stories whose card changed after they were written (MANTIS-IMP-070)
    for b in CHANGES.get("behind", []):
        att.append((b["href"], f'{b["kind"]} "{b["title"]}" may be out of date. {b["why"]}.', "Update"))
    # Summaries behind their sources, with the reason, cards you follow first (MANTIS-IMP-069: Home is the one action list)
    for r in CHANGES.get("refresh", []):
        att.append((r["href"], f'{r["title"]}: {r["why"]}.', "Refresh"))
    cards_md = (M / "knowledge" / "map" / "cards.md").read_text(encoding="utf-8") if (M / "knowledge" / "map" / "cards.md").exists() else ""
    sugg = re.findall(r"(?m)^- (\S+): (\d+) documents$", cards_md)
    if sugg:
        att.append(("topics.html", "Subjects in 3+ sources with no card: " + ", ".join(f"{t} ({n})" for t, n in sugg[:5]) + ". Ask Mantis for a topic card.", "Add"))
    from datetime import date as _d
    old_q = [o for o in OPEN if o.get("raised") and (_d.today() - _d.fromisoformat(o["raised"][:10])).days > 60]
    if old_q:
        att.append(("review.html", f"{n_(len(old_q), 'open question')} older than 60 days: worth the monthly review", "Review"))
    hp = M / "knowledge" / "map" / "health.json"
    for i in (json.loads(hp.read_text(encoding="utf-8"))["items"] if hp.exists() else []):
        if i["level"] == "warn" or i["area"] == "Inbox":
            att.append(("health.html", f'{i["area"]}: {plain(i["msg"], 220)}', "Fix" if i["level"] == "warn" else "Check"))
    wk = "".join(f'<a class="row att" href="{h}"><span class="row-t">{esc(m)}</span><span class="tag">{esc(a)}</span></a>' for h, m, a in att[:9]) \
        or '<p class="empty">Nothing needs you right now.</p>'
    # My focus, in the owner's own order (focus.json "following"), with the signals that help pick what to do first.
    by_slug = {c["slug"]: (c, c in features) for c in features + TOPICS}
    mine = [by_slug[s] for s in FOCUS["following"] if s in by_slug]
    waiting_of = lambda slug: sum(1 for o in OPEN if o["status"] != "Open" and slug in o["features"])

    def focus_row(i, c, feat):
        sig = []
        if waiting_of(c["slug"]):
            sig.append(f'<span class="pill w-jira" title="Open questions with a likely answer">{waiting_of(c["slug"])} to decide</span>')
        if c.get("new_docs"):
            sig.append(f'<span class="pill w-review" title="Sources not yet in the summary">{len(c["new_docs"])} new</span>')
        sig.append(f'<span class="muted small f-open">{c["open"]} open</span>' if c.get("open") else '<span class="f-open"></span>')
        sig.append(pill(*STATUS[c["status"]]) if feat else '<span class="tag">Topic</span>')
        return (f'<li class="f-row" draggable="true" data-slug="{c["slug"]}"><span class="t-grip" title="Drag to rank">⋮⋮</span><span class="f-rank">{i}</span>'
                f'<a class="row-t" href="{"features" if feat else "topics"}/{c["slug"]}.html">{esc(c["title"])}</a><span class="f-sig">{"".join(sig)}</span>'
                f'<span class="f-move nocopy"><button type="button" data-m="-1" title="Move up">↑</button><button type="button" data-m="1" title="Move down">↓</button></span></li>')

    foc = (('<input type="search" id="f-filter" placeholder="Filter my focus…" aria-label="Filter my focus">' if len(mine) > 8 else "")
           + '<ol class="focus-list" id="focus-list">' + "".join(focus_row(i + 1, c, f) for i, (c, f) in enumerate(mine)) + "</ol>"
           + '<p class="muted small f-hint">Drag or use ↑ ↓ to rank: put what you will tackle first at the top.</p>') if mine \
        else '<p class="empty">You follow nothing yet. On <a href="topics.html">Topics</a>, press ☆ Follow on the subjects you own.</p>'
    # Decisions and outcomes: each roadmap feature's state, judged by evidence rather than filled fields
    tone = {"review-overdue": "w-review", "live-no-review": "w-review", "no-plan": "w-review", "unvalidated": "s-none",
            "incomplete": "s-none", "not-framed": "s-none", "ready": "s-build", "measuring": "s-done",
            "reviewed-no-data": "w-review", "reviewed": "s-done"}
    rd_rows = [r for r in READY.get("features", []) if not archived(r["slug"])]
    rd = "".join(f'<a class="row rd-row" href="features/{r["slug"]}.html"><span class="row-t">{esc(r["title"])}'
                 f'<span class="muted small rd-why">{esc(r["why"])}</span></span>'
                 f'{pill(READY["states"].get(r["state"], r["state"]), tone.get(r["state"], "s-none") + " plain")}</a>' for r in rd_rows)
    ready_box = (f'<section class="panel-box"><div class="box-h"><h2>Decisions and outcomes</h2>'
                 f'<span class="muted small">By evidence, not filled fields</span></div>{rd}</section>') if rd_rows else ""
    body = f"""
<section class="hero hero-compact"><div><p class="hello" id="hello">Hello</p><h1>What needs you today</h1></div>
<a class="btn" href="today.html">Open today's list →</a></section>
<a class="since-strip nocopy" id="since-strip" href="changes.html" hidden><span class="since-t"></span><span class="since-go">What's new →</span></a>
<script type="application/json" id="changes-counts">{changes_counts_json()}</script>
{INBOX_STRIP.format(btn=job_btn("process-inbox", "Process inbox", cls="btn"))}
<section class="stats">{tiles}</section>
<div class="grid2">
<div class="stack"><section class="panel-box"><div class="box-h"><h2>Needs attention <span class="muted">{len(att)}</span></h2><a href="health.html">Health →</a></div>{wk}</section>
<a class="link-card" href="topics.html"><b>Topics</b><span>{n_(len(TOPICS), "subject")} beyond the roadmap, each summarised on one page</span></a>
<a class="link-card" href="work.html"><b>Epics &amp; stories</b><span>{n_(sum(1 for x in work if x["kind"] == "epic"), "epic")}, {n_(sum(1 for x in work if x["kind"] == "story"), "story", "stories")}, by status</span></a>
<a class="link-card" href="library.html"><b>Library</b><span>{n_(len(items), "page")}, epics and stories ready to copy</span></a></div>
<div class="stack"><section class="panel-box"><div class="box-h"><h2>My focus <span class="muted">{len(mine)}</span></h2><a href="topics.html">Choose topics →</a></div>{foc}</section>
{ready_box}</div>
</div>"""
    return shell("Home", body, active="home", built=built)


def page_roadmap(features, later, built):
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
    body = f"""
<div class="page-h"><div><h1>Roadmap</h1><p class="lead">Your roadmap: the roadmap features plus any topic you added. Add or remove items on the <a href="topics.html">Topics</a> page.</p></div>
<div class="seg" id="view"><button data-v="board" class="on">Board</button><button data-v="list">List</button><button data-v="timeline">Timeline</button></div></div>
<div class="toolbar" id="rd-tools">
<input id="q" type="search" placeholder="Search topics…" aria-label="Search topics">
<div class="chips" id="f-status"><button data-v="all" class="on">All</button>{chips}</div>
<div class="chips" id="f-prio"><button data-v="all" class="on">Any priority</button><button data-v="P1">P1</button><button data-v="P2">P2</button><button data-v="P3">P3</button></div>
</div>
<div id="board"></div><div id="list" hidden></div><div id="tl-view" hidden>{page_timeline(built, embed=True)}</div>
<script id="data" type="application/json">{json.dumps({"items": data, "labels": labels})}</script>"""
    return shell("Roadmap", body, active="roadmap", built=built)


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
    epic_tab = f'#epic-{epics[0]["anchor"]}' if epics else "#epic-none"
    epic_label = '<span class="k-ico k-epic">◆</span>' + ("Epic" if len(epics) <= 1 else f"Epics ({len(epics)})")
    tabs = (f'<a href="#overview" data-match="overview">One-pager</a>'
            f'<a href="#page" data-match="page">Confluence page{" " + work_pill(f["page_status"]) if f["page_status"] else ""}</a>'
            f'<a href="{epic_tab}" data-match="epic-">{epic_label}{" " + work_pill(epics[0]["status"]) if len(epics) == 1 else ""}</a>')
    panels = [("overview", copy_bar("Copy one-pager"), render(f["card_md"])),
              ("page", copy_bar("Copy page", f["page"]) if f["page_md"] else "",
               render(f["page_md"]) if f["page_md"] else empty("Confluence page", f"Write the Confluence page for {t}"))]
    if not epics:
        panels.append(("epic-none", "", empty("epic", f"Write the epic for {t}")))
    for e in epics:
        others = "".join(f'<a class="chip{" on" if o is e else ""}" href="#epic-{o["anchor"]}">{esc(o["title"])}</a>' for o in epics) if len(epics) > 1 else ""
        head = f'<div class="epic-switch nocopy">{others}</div>' if others else ""
        panels.append((f"epic-{e['anchor']}", copy_bar("Copy epic", e["file"]), head + render(e["md"], breaks=True, sections=False)))
    for s in f["stories"]:
        ep = f'<p class="muted small nocopy">Story{" in epic " + esc(s["epic_title"]) if s["epic_title"] else ", not in an epic"} · {WORK.get(s["status"], (s["status"],))[0]}</p>'
        panels.append((f"story-{s['anchor']}", copy_bar("Copy story", s["file"]), ep + render(s["md"], breaks=True, sections=False)))
    ph = "".join(f'<div class="tab-panel" id="p-{k}" hidden>{bar}<article class="doc">{body}</article></div>' for k, bar, body in panels)
    done = sum(1 for s in f["stories"] if s["status"] in ("in-jira", "done"))
    stories = story_list(f["stories"], epics_by_id) or empty("stories", f"Write the user stories for {t}")
    body = f"""
<div class="crumbs"><a href="../roadmap.html">Roadmap</a><span>›</span>
<select id="switch" aria-label="Go to another topic">{switch}</select></div>
<div class="feat-h"><h1>{esc(t)}</h1><div class="meta">{"".join(m for m in meta if m)}</div>{note}
<p class="muted small">Updated {esc(f["updated"])}{f" · {f['open']} open question" + ("s" if f["open"] != 1 else "") if f["open"] else ""}</p>
<div class="card-acts">{job_btn("refresh-card", "Refresh summary", arg=f["slug"], cls="mini")}{job_btn("rebuild", "Rebuild", ai=False, cls="mini")}</div></div>
<div class="feat">
<div class="feat-main"><nav class="tabs">{tabs}</nav>{ph}</div>
<aside class="side"><div class="side-h"><h2>Stories</h2><span class="muted small">{done}/{len(f["stories"])} in Jira</span></div>{stories}{feature_entities(f["slug"])}</aside>
</div>"""
    return shell(t, body, base="../", active="roadmap", built=built)


def page_work(work, features, built):
    data = [{k: x[k] for k in ("kind", "title", "status", "feature", "feature_title", "epic_title", "jira", "updated")}
            | {"href": x["href"], "file": x["file"], "mine": x["feature"] in FOCUS["following"],
               "own": x["file"] in FOCUS.get("archived_work", []), "archived": archived(x["feature"]) or x["file"] in FOCUS.get("archived_work", [])} for x in work]
    feats = "".join(f'<option value="{f["slug"]}">{esc(f["title"])}</option>' for f in features if (f["epics"] or f["stories"]) and not archived(f["slug"]))
    body = f"""<div class="page-h"><div><h1>Epics &amp; stories</h1><p class="lead">Everything written for Jira, by status. Includes generic epics and stories that stand alone.</p></div>
<div class="seg" id="view"><button data-v="board" class="on">Board</button><button data-v="list">List</button></div></div>
<div class="toolbar"><input id="q" type="search" placeholder="Search epics and stories…" aria-label="Search epics and stories">
<div class="chips" id="f-kind"><button data-v="all" class="on">All</button><button data-v="epic">Epics</button><button data-v="story">Stories</button></div>
<select id="f-feature" class="sel" aria-label="Filter by topic"><option value="all">All topics</option><option value="mine">My focus</option><optgroup label="Topic">{feats}<option value="none">No topic</option></optgroup><option value="archived">Archived</option></select></div>
<div id="board"></div><div id="list" hidden></div>
<script id="work" type="application/json">{json.dumps({"items": data, "labels": {k: v[0] for k, v in WORK.items()}})}</script>"""
    return shell("Epics & stories", body, active="work", built=built)


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
    return shell(x["title"], body, base="../", active="work", built=built)


def page_topics(topics, features, built):
    cards = [(f, True) for f in features] + [(t, False) for t in topics]

    def tile(c, feat):
        url = ("features/" if feat else "topics/") + c["slug"] + ".html"
        fol, road = c["slug"] in FOCUS["following"], on_roadmap(c, feat)
        kind = "" if feat else '<span class="tag">Topic</span>'
        arc = archived(c["slug"])
        return (f'<div class="tile topic-tile" data-slug="{c["slug"]}" data-following="{int(fol)}" data-roadmap="{int(road)}" data-archived="{int(arc)}">'
                f'<h3><a href="{url}">{esc(c["title"])}</a></h3>{kind}<p>{esc(c["summary"])}</p>'
                f'<div class="facts"><span><b>{len(c["docs"])}</b> {"source" if len(c["docs"]) == 1 else "sources"}</span>' + (f'<span><b>{c["open"]}</b> open {"question" if c["open"] == 1 else "questions"}</span>' if c.get("open") else "")
                + (f'<span class="warn-text">{len(c["new_docs"])} new since summary</span>' if c.get("new_docs") else '<span>Summary current</span>') + '</div>'
                f'<div class="tile-acts nocopy"><button type="button" class="act follow{" on" if fol else ""}" data-a="follow" aria-pressed="{str(fol).lower()}">{"★ Following" if fol else "☆ Follow"}</button>'
                f'<button type="button" class="act road{" on" if road else ""}" data-a="roadmap" aria-pressed="{str(road).lower()}">{"✓ On roadmap" if road else "+ Roadmap"}</button>'
                f'<button type="button" class="act arc" data-a="archive" title="Hide this card everywhere; restore it from the Archived tab">{"Restore" if arc else "Archive"}</button></div></div>')

    n_f = sum(1 for c, f in cards if c["slug"] in FOCUS["following"] and not archived(c["slug"]))
    n_r = sum(1 for c, f in cards if on_roadmap(c, f))
    n_a = sum(1 for c, f in cards if archived(c["slug"]))
    body = f"""<div class="page-h"><div><h1>Topics</h1><p class="lead">One summary page per subject, each kept up to date from its sources. Follow the ones you are responsible for, and choose which belong on your roadmap.</p></div></div>
<div class="toolbar"><div class="seg" id="ttab"><button data-v="focus" class="on">My focus <span class="muted">{n_f}</span></button><button data-v="roadmap">On roadmap <span class="muted">{n_r}</span></button><button data-v="all">All <span class="muted">{len(cards) - n_a}</span></button><button data-v="archived">Archived <span class="muted">{n_a}</span></button></div>
<input id="tq" type="search" placeholder="Filter…" aria-label="Filter topics"><div class="bulk nocopy" id="t-bulk" aria-label="Change several at once"></div></div>
<p class="empty" id="t-empty" hidden>Nothing here yet. Open <b>All</b> and press ☆ Follow on the subjects you own.</p>
<div class="later topic-grid">{"".join(tile(c, f) for c, f in cards)}</div>"""
    return shell("Topics", body, active="topics", built=built)


def page_topic(t, topics, built):
    switch = "".join(f'<option value="{x["slug"]}.html"{" selected" if x is t else ""}>{esc(x["title"])}</option>' for x in topics if x is t or not archived(x["slug"]))
    body = f"""
<div class="crumbs"><a href="../topics.html">Topics</a><span>›</span>
<select id="switch" aria-label="Go to another topic">{switch}</select></div>
<div class="feat-h"><h1>{esc(t["title"])}</h1><div class="meta"><span class="tag">Topic</span>{'<span class="tag">Archived</span>' if archived(t["slug"]) else ""}{fresh(t)}<span class="muted small">{n_(len(t["docs"]), "source")}{f" · {n_(t['open'], 'open question')}" if t["open"] else ""}</span></div>
<div class="card-acts">{job_btn("refresh-card", "Refresh summary", arg=t["slug"], cls="mini")}{job_btn("rebuild", "Rebuild", ai=False, cls="mini")}</div></div>
<div class="feat">
<div class="feat-main"><div class="tab-panel" id="p-overview">{copy_bar("Copy summary")}<article class="doc">{render(t["card_md"])}</article></div></div>
<aside class="side">{feature_entities(t["slug"], 14, "topic") or '<p class="empty">No people or systems named yet.</p>'}</aside>
</div>"""
    return shell(t["title"], body, base="../", active="topics", built=built)


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


def page_today(built):
    """The owner's task list. A static shell; app.js loads and saves the tasks through tools/serve.py."""
    est = "".join(f'<option value="{v}">{l}</option>' for v, l in (("0", "Time?"), ("15", "15 min"), ("30", "30 min"), ("60", "1 hour"),
                                                                    ("120", "2 hours"), ("240", "Half day"), ("480", "Full day")))
    body = f"""<div class="page-h today-h"><div><p class="hello" id="hello">Hello</p><h1 id="t-date">Today</h1><p class="lead" id="t-sum">Loading your tasks…</p></div></div>
<p class="empty" id="t-offline" hidden>Your tasks are saved by the Mantis site server. Open the site at http://localhost:8000 (it starts with each Claude Code session, or run <code>python tools/serve.py --open</code>).</p>
<div class="today-grid"><div class="today-main">
<form id="t-add" class="t-add" autocomplete="off">
<input id="t-title" type="text" placeholder="Add a task and press Enter" aria-label="New task" maxlength="300">
<div class="t-add-more"><span class="prio-seg" id="t-prio" role="group" aria-label="Priority" data-value=""><button type="button" data-p="high">High</button><button type="button" data-p="medium">Medium</button><button type="button" data-p="low">Low</button></span>
<select id="t-est" class="sel sel-sm" aria-label="Estimated time">{est}</select>
<button type="button" class="dp-btn" id="t-when" data-kind="when" data-value="" aria-haspopup="dialog" title="Which day it shows up on your list">Today</button>
<button type="button" class="dp-btn" id="t-due" data-kind="due" data-value="" aria-haspopup="dialog" title="Deadline">No due date</button>
<input id="t-contact" type="text" placeholder="Who to reach out to" maxlength="120" aria-label="Who to reach out to">
<button class="btn" type="submit">Add</button></div></form>
<section id="t-due-sug" class="due-sug nocopy" hidden></section>
<section class="panel-box t-box"><div class="box-h"><h2>Today's list</h2><span class="muted small" id="t-total"></span><button class="mini" id="t-sortp" type="button" title="Order today's list by priority, then due date">Sort by priority</button></div>
<ol id="t-list" class="t-list"></ol>
<p class="muted small t-hint">Drag to rank, or Alt+↑/↓. Click a task for notes, dates and more.</p></section>
<details class="grp-box" id="t-sched-box"><summary><h2>Scheduled for later <span class="muted" id="t-sched-n"></span></h2></summary><section class="panel-box"><p class="muted small t-hint">Each task comes back to Today on its day. Changed your mind? Press <b>Bring to today</b>.</p><ol id="t-sched" class="t-list"></ol></section></details>
<details class="grp-box" id="t-park-box"><summary><h2>Parked <span class="muted" id="t-park-n"></span></h2></summary><section class="panel-box"><p class="muted small t-hint">Out of the way with no date. Bring them back when they matter again.</p><ol id="t-park" class="t-list"></ol></section></details>
<details class="grp-box" id="t-done-box"><summary><h2>Done <span class="muted" id="t-done-n"></span></h2></summary><section class="panel-box"><p class="muted small t-hint">Untick to reopen. Done items move to the archive the next day and are deleted after 7 days.</p><ol id="t-done" class="t-list"></ol></section></details>
<details class="grp-box" id="t-bin-box"><summary><h2>Recently deleted <span class="muted" id="t-bin-n"></span></h2></summary><section class="panel-box"><p class="muted small t-hint">Kept for 7 days, then cleaned up. Restore anything you deleted by mistake.</p><ol id="t-bin" class="t-list"></ol></section></details>
</div>
<aside class="today-side" aria-label="Supporting your day">
<section id="t-away" class="side-card away-card nocopy" hidden></section>
<section id="t-brief" class="side-card"></section>
<div id="t-people" class="side-stack nocopy"></div>
</aside></div>"""
    return shell("Today", body, active="today", built=built)
