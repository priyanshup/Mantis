"""Site pages for the owner's day (MANTIS-IMP-094): Today, Meetings, Sources.

Static frames with the build-time parts filled in; the live parts (tasks, follow-ups, meetings and their
agendas, the pull brief, filters) are drawn by app.js from tools/serve.py, so they never wait for a rebuild."""
from datetime import date as _date, timedelta as _td
from site_common import *   # noqa: F401,F403  (shared state and helpers)


def scope_of(o):
    """Questions page side: 'tidy' for names and terms to confirm (housekeeping, not decisions), 'others' when
    someone else is named to answer an open question, else 'you'."""
    if o["kind"] in ("name", "term"):
        return "tidy"
    return "others" if o["status"] == "Open" and o.get("ask") else "you"


def qkey(o):
    return hashlib.sha1(o["id"].encode("utf-8")).hexdigest()[:10]


def topic_text(o):
    return re.sub(r" ?[(]MANTIS-[A-Z]+-[0-9]+(?:[,;] ?MANTIS-[A-Z]+-[0-9]+)*[)]", "", o["topic"])


def yours():
    """Questions waiting for the owner, the ones to decide first, then by priority, newest first."""
    mine = [o for o in OPEN if scope_of(o) == "you"]
    mine.sort(key=lambda o: (o.get("raised", ""), o["id"]), reverse=True)
    mine.sort(key=lambda o: (o["status"] == "Open", PRIO_RANK[o.get("priority", "")]))
    return mine


def attention(work):
    """What Mantis noticed that is not a question: decision readiness, decisions whose basis moved, drafts to
    review, outputs behind their card, summaries behind their sources, health warnings. [(href, text, action)]"""
    att = []
    for slug, msg, act in READY.get("attention", []):
        if not archived(slug):
            att.append((f"features/{slug}.html", msg, act))
    for d in READY.get("decisions", []):
        what = "; ".join(("a source it rests on was edited" if "-DOC-" in x else f"a question it rests on is now \"{now.split(' (')[0]}\"")
                         for x, _, now in d["changes"][:2])
        text = re.sub(r"\s*\([^)]*\)", "", d["decision"])
        short = text if len(text) <= 90 else text[:90].rsplit(" ", 1)[0].rstrip(",;:") + "…"
        att.append(("library.html#decisions", f"Decision \"{short}\" may need a look: {what}.", "Review"))
    for x in work:
        if x["status"] in ("draft", "review") and x["file"] not in FOCUS.get("archived_work", []) and not archived(x["feature"]):
            att.append((x["href"], f'{"Epic" if x["kind"] == "epic" else "Story"} "{x["title"]}" is {WORK[x["status"]][0].lower()}', "Review"))
    for b in CHANGES.get("behind", []):
        att.append((b["href"], f'{b["kind"]} "{b["title"]}" may be out of date. {b["why"]}.', "Update"))
    for r in CHANGES.get("refresh", []):
        att.append((r["href"], f'{r["title"]}: {r["why"]}.', "Refresh"))
    hp = M / "knowledge" / "map" / "health.json"
    for i in (json.loads(hp.read_text(encoding="utf-8"))["items"] if hp.exists() else []):
        if i["level"] == "warn":
            att.append(("sources.html#health", f'{i["area"]}: {plain(i["msg"], 220)}', "Fix"))
    return att


def this_week(features):
    """Monday's look back and ahead (a weekly review in five lines): only the lines that have something."""
    today = _date.fromisoformat(CHANGES["today"]) if CHANGES.get("today") else _date.today()
    rows = []
    stale = [o for o in OPEN if o.get("raised") and (today - _date.fromisoformat(o["raised"][:10])).days > 14]
    if stale:
        rows.append(("questions.html", f"{n_(len(stale), 'question')} open for more than two weeks", "Review"))
    try:
        import followups
        old = [f for g in followups.grouped(include_steps=False).values() for f in g["items"]
               if (f.get("chase") and f["chase"] < today.isoformat()) or (today - _date.fromisoformat(f["created"])).days > 7]
        if old:
            rows.append(("index.html#followups", f"{n_(len(old), 'follow-up')} open for more than a week or past the chase date", "Chase"))
    except Exception:
        pass
    week = (today - _td(days=7)).isoformat()
    moved = [e for e in CHANGES.get("events", []) if e["kind"] == "stage" and e["date"] >= week]
    if moved:
        rows.append(("features.html#roadmap", "Moved stage: " + ", ".join(sorted({e.get("card") or e["title"] for e in moved})[:4]), "Look"))
    tl = CHANGES.get("timeline") or {}
    ahead = [m for m in tl.get("upcoming", []) if m["date"] <= (today + _td(days=7)).isoformat()]
    if ahead:
        rows.append(("features.html#roadmap", f"Coming up this week: " + "; ".join(f'{m["label"]} ({_date.fromisoformat(m["date"]).strftime("%a")})' for m in ahead[:3]), "Plan"))
    followed = set(FOCUS.get("following", []))
    quiet = [r["title"] for r in tl.get("rows", []) if Path(r.get("href", "")).stem in followed
             and (not r.get("last") or (today - _date.fromisoformat(r["last"])).days > 21)]
    if quiet:
        rows.append(("features.html", "Quiet for three weeks: " + ", ".join(quiet[:4]), "Check"))
    return rows


def row_link(href, text, act=""):
    return f'<a class="row att" href="{href}"><span class="row-t">{esc(text)}</span>{f"<span class=\"tag\">{esc(act)}</span>" if act else ""}</a>'


def page_today(features, work, built):
    """Today (MANTIS-IMP-094): what changed, what is on, what to do; then what waits on you and on others."""
    mine = yours()
    top = "".join(f'<a class="row q-row" href="questions.html#k={qkey(o)}"><span class="row-t">{esc(topic_text(o))}</span>'
                  f'{pill("Decide", "s-build plain") if o["status"] not in ("Open", "Unconfirmed") else pill("Possible conflict", "s-ref plain") if o["status"] == "Unconfirmed" else ""}</a>'
                  for o in mine[:3])
    decide = sum(1 for o in mine if o["status"] != "Open")
    needs = (f'<section class="side-card"><div class="sc-h"><h2>Needs your answer</h2><span class="sc-n" title="To decide: likely answers and possible conflicts">{decide or ""}</span></div>'
             + (f'{top}<a class="linkish small" href="questions.html">All {len(mine)} on Questions</a>' if mine else '<p class="muted small">Nothing waits for you.</p>')
             + "</section>")
    week = this_week(features)
    week_box = (f'<section class="panel-box week-box" id="this-week" hidden><div class="box-h"><h2>This week</h2>'
                f'<span class="muted small">Your Monday look back and ahead</span></div>{"".join(row_link(*r) for r in week)}</section>') if week else ""
    est = "".join(f'<option value="{v}">{l}</option>' for v, l in (("0", "Time?"), ("15", "15 min"), ("30", "30 min"), ("60", "1 hour"),
                                                                    ("120", "2 hours"), ("240", "Half day"), ("480", "Full day")))
    body = f"""<div class="page-h today-h"><div><p class="eyebrow" id="hello">Hello</p><h1 id="t-date">Today</h1><p class="lead" id="t-sum">Loading your day…</p></div>
<button type="button" class="btn-line" id="away-btn">Going away?</button></div>
<p class="empty" id="t-offline" hidden>Your tasks are saved by the Mantis site server. Open the site at http://localhost:8000 (it starts with each Claude Code session, or run <code>python tools/serve.py --open</code>).</p>
<div class="today-grid"><div class="today-main">
<section class="panel-box pull-box" id="pull-box" aria-labelledby="pull-h"><div class="box-h"><h2 id="pull-h">Since last pull</h2><span class="muted small" id="pull-when"></span>
{job_btn("pull", "Pull now", cls="btn")}</div><div id="pull-body"><p class="muted">Loading…</p></div></section>
<section class="panel-box" id="t-meet" hidden></section>
<section class="panel-box do-box" aria-labelledby="do-h"><div class="box-h"><h2 id="do-h">Do today</h2><span class="muted small" id="t-total"></span>
<button class="mini" id="t-sortp" type="button" title="Order today's list by priority, then due date">Sort by priority</button></div>
<form id="t-add" class="t-add" autocomplete="off">
<input id="t-title" type="text" placeholder="Add a task and press Enter" aria-label="New task" maxlength="300">
<div class="t-add-more"><span class="prio-seg" id="t-prio" role="group" aria-label="Priority" data-value=""><button type="button" data-p="high">High</button><button type="button" data-p="medium">Medium</button><button type="button" data-p="low">Low</button></span>
<select id="t-est" class="sel sel-sm" aria-label="Estimated time">{est}</select>
<button type="button" class="dp-btn" id="t-when" data-kind="when" data-value="" aria-haspopup="dialog" title="Which day it shows up on your list">Today</button>
<button type="button" class="dp-btn" id="t-due" data-kind="due" data-value="" aria-haspopup="dialog" title="Deadline">No due date</button>
<input id="t-contact" type="text" placeholder="Who to reach out to" maxlength="120" aria-label="Who to reach out to">
<button class="btn" type="submit">Add</button></div></form>
<ol id="t-list" class="t-list"></ol>
<p class="muted small t-hint">Drag to rank, or Alt+↑/↓. Click a task for notes, dates and more.</p>
<div id="t-brief" class="do-sug"></div>
<section id="t-due-sug" class="due-sug nocopy" hidden></section></section>
{week_box}
<details class="grp-box" id="t-sched-box"><summary><h2>Scheduled for later <span class="muted" id="t-sched-n"></span></h2></summary><section class="panel-box"><p class="muted small t-hint">Each task comes back to Today on its day. Changed your mind? Press <b>Bring to today</b>.</p><ol id="t-sched" class="t-list"></ol></section></details>
<details class="grp-box" id="t-park-box"><summary><h2>Parked <span class="muted" id="t-park-n"></span></h2></summary><section class="panel-box"><p class="muted small t-hint">Out of the way with no date. Bring them back when they matter again.</p><ol id="t-park" class="t-list"></ol></section></details>
<details class="grp-box" id="t-done-box"><summary><h2>Done <span class="muted" id="t-done-n"></span></h2></summary><section class="panel-box"><p class="muted small t-hint">Untick to reopen. Done items move to the archive the next day and are deleted after 7 days.</p><ol id="t-done" class="t-list"></ol></section></details>
<details class="grp-box" id="t-bin-box"><summary><h2>Recently deleted <span class="muted" id="t-bin-n"></span></h2></summary><section class="panel-box"><p class="muted small t-hint">Kept for 7 days, then cleaned up. Restore anything you deleted by mistake.</p><ol id="t-bin" class="t-list"></ol></section></details>
</div>
<aside class="today-side" aria-label="Waiting on you and on others">
{needs}
<div id="t-people" class="side-stack nocopy"></div>
<section id="t-away" class="side-card away-card nocopy" hidden></section>
</aside></div>"""
    return shell("Today", body, active="today", built=built)


def page_meetings(built):
    """Meetings (MANTIS-IMP-094): each regular meeting with an agenda that builds itself, what was agreed last
    time, and a place to drop the notes or transcript afterwards. Drawn by app.js from GET /api/extra."""
    body = """<div class="page-h"><div><h1>Meetings</h1><p class="lead">Your regular meetings. Each agenda builds itself from what is open with the people in it and what changed on its subjects, so you walk in prepared.</p></div>
<details class="add-meet nocopy"><summary class="btn-line">Add a regular meeting</summary><div class="pop-form" id="pp-meetings"></div></details></div>
<div id="mt-list" class="mt-list"><p class="muted">Loading your meetings…</p></div>
<section class="panel-box oneoff nocopy" aria-labelledby="oo-h"><div class="box-h"><h2 id="oo-h">Meeting someone else?</h2><span class="muted small">A brief for one conversation</span></div>
<div class="mb-row"><select id="mb-who" class="sel" aria-label="Meeting with"></select><button type="button" class="btn job ai" data-job="meeting-brief" data-arg-from="#mb-who" title="Uses Claude, on your normal quota">Brief me</button>
<button type="button" class="btn-line job ai" data-job="status-update" title="Uses Claude, on your normal quota">Write this week's status update</button></div>
<div class="chips" id="mt-briefs"></div></section>"""
    return shell("Meetings", body, active="meetings", built=built)


def health_html(work):
    """What Mantis noticed, the health report, background jobs and the Mantis backlog, folded into Sources:
    housekeeping, kept off Today (MANTIS-IMP-094)."""
    from site_reference import page_backlog
    p = M / "knowledge" / "map" / "health.json"
    h = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"date": "", "items": []}
    lab = {"warn": ("Fix", "s-ref plain"), "todo": ("To do", "s-build plain"), "info": ("Note", "s-none plain")}
    rows = "".join(f'<div class="row health-row">{pill(*lab[i["level"]])}<span class="tag">{esc(i["area"])}</span><span class="row-t health-msg">{esc(i["msg"])}</span></div>' for i in h["items"])
    warn = sum(1 for i in h["items"] if i["level"] == "warn")
    att = [a for a in attention(work) if a[0] != "sources.html#health"]   # health warnings are listed below already
    noticed = (f'<section class="panel-box"><div class="box-h"><h2>Mantis noticed</h2><span class="muted small">Plans, drafts and summaries to look at when you have time</span></div>'
               + "".join(row_link(h_, m, a) for h_, m, a in att) + "</section>") if att else ""
    return f"""<details class="grp-box" id="health"><summary><h2>Health and jobs</h2><span class="muted small">Last check {esc(h["date"])}{f" · {n_(warn, 'thing')} to fix" if warn else " · all clear"}{f" · {len(att)} noticed" if att else ""}</span></summary>
{noticed}<section class="panel-box">{rows or '<p class="empty">All clear.</p>'}</section>
<section class="panel-box jobs-box" id="jobs"><div class="box-h"><h2>Background jobs</h2><span class="muted small" id="job-quota"></span></div>
<div class="job-acts">{job_btn("rebuild", "Rebuild everything", ai=False)}{job_btn("daily-brief", "Prepare today's brief")}</div>
<p class="muted small job-note">Buttons marked ✦ use Claude on your normal subscription quota; the others are free. Jobs that hit a rule needing your decision stop and say "needs you" instead of guessing.</p>
<div id="job-list"></div></section>
<details class="grp-box backlog-box" id="backlog"><summary><h2>Mantis backlog</h2><span class="muted small">Ideas for Mantis itself</span></summary>{page_backlog(backlog(), "", embed=True)}</details></details>"""


def page_sources(work, built):
    """Sources (MANTIS-IMP-094): what Mantis reads and when it last did. The filters, the pull, the inbox,
    past pulls, then health and jobs folded away. Filters and pulls are drawn by app.js."""
    body = f"""<div class="page-h"><div><h1>Sources</h1><p class="lead">What Mantis reads, and when it last did. A pull runs only when you start it.</p></div></div>
<section class="panel-box pull-now nocopy" aria-labelledby="pn-h"><div class="pn-t"><h2 id="pn-h">Pull</h2><p class="muted" id="pn-state">Checking…</p></div>
{job_btn("pull", "Pull now", cls="btn")}</section>
<section class="panel-box nocopy" id="unmapped" aria-labelledby="um-h" hidden><div class="box-h"><h2 id="um-h">Tickets with no feature</h2>
<span class="muted small">A pull does not digest them until you say where they belong</span></div><div id="um-list"></div></section>
<section class="panel-box nocopy" aria-labelledby="flt-h"><div class="box-h"><h2 id="flt-h">Jira and Confluence filters</h2><span class="muted small">A pull reads only the active ones</span>
<button type="button" class="btn-line" id="flt-add-btn">Add a filter</button></div>
<div id="flt" class="flt"><p class="muted small">Loading filters…</p></div>
<p class="muted small flt-note">Jira: JQL that picks the root issues (usually Features); their children are followed. Confluence: a page link or ID for everything under it, or CQL. Pages Mantis already holds are always checked.</p></section>
<section class="panel-box nocopy" aria-labelledby="ib-h"><div class="box-h"><h2 id="ib-h">Inbox</h2><span class="muted small" id="ib-state"></span></div>
<div class="drop" id="drop" tabindex="0" role="button" aria-label="Add files to the inbox: drop them here or press Enter to choose">
<p><b>Drop notes, transcripts or documents here</b><span class="muted small">Word, PDF, text, transcripts, web pages, spreadsheets · or <span class="linkish">choose files</span></span></p>
<input type="file" id="drop-file" multiple hidden accept=".md,.txt,.vtt,.srt,.docx,.pdf,.html,.htm,.xlsx,.pptx"></div>
<details class="paste-box"><summary>Or paste text</summary><textarea id="paste-text" rows="5" placeholder="Paste meeting notes, an email or a chat thread"></textarea>
<div class="mb-row"><input id="paste-name" type="text" placeholder="Name (optional)" aria-label="Name for the pasted text"><button type="button" class="btn" id="paste-save">Add to inbox</button></div></details>
<p class="muted small">The next pull digests everything waiting here first.</p></section>
<details class="grp-box" id="history"><summary><h2>Past pulls</h2><span class="muted small">The last ten briefs</span></summary><div id="pull-history" class="panel-box"><p class="muted small">Loading…</p></div>
<p class="small hist-more"><a href="changes.html">Everything that changed, day by day →</a></p></details>
{health_html(work)}"""
    return shell("Sources", body, active="sources", built=built)
