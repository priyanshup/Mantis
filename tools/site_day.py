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


def card_hrefs(features):
    """Where each card lives, and the owner's ranking, for the parts app.js draws (the pull brief, Today's lead)."""
    hrefs = {f["slug"]: f"features/{f['slug']}.html" for f in features} | {t["slug"]: f"topics/{t['slug']}.html" for t in TOPICS}
    return {"href": hrefs, "rank": [s for s in FOCUS.get("following", []) if s in hrefs]}


def page_today(features, work, built):
    """Today (2026-10-31 redesign, after MANTIS-IMP-094): one headline, the day's tasks, what changed, and a quiet
    side column for meetings, people and leave. Every list has a fixed size; the rest is one click away."""
    mine = yours()
    likely = sum(1 for o in mine if o["status"] not in ("Open", "Unconfirmed"))
    q_line = (f'<a class="ri" href="questions.html#waiting"><span class="ri-v">{n_(likely, "question")} may already be answered</span>'
              f'<span class="ri-s">Check {"it" if likely == 1 else "them"}</span></a>') if likely else ""
    week = this_week(features)
    week_box = (f'<section class="rail-blk" id="this-week" hidden><h2>This week</h2>'
                + "".join(f'<a class="ri" href="{h}"><span class="ri-v">{esc(t)}</span></a>' for h, t, _ in week) + "</section>") if week else ""
    # The cards a task can be grouped under (the owner picks; Mantis never guesses): followed ones first
    followed = set(FOCUS.get("following", []))
    cards = sorted(([c["slug"], c["title"], int(c["slug"] in followed)] for c in features + TOPICS if not archived(c["slug"])),
                   key=lambda x: (-x[2], x[1].lower()))
    lists = "".join(f'<button type="button" data-l="{k}" hidden>{n} <span class="n" id="t-{k}-n"></span></button>'
                    for k, n in (("sched", "Later"), ("park", "Parked"), ("done", "Done"), ("bin", "Deleted")))
    body = f"""<div class="page-h today-h"><div><p class="eyebrow" id="t-date"></p><h1 id="t-head">Today</h1><p class="lead" id="t-sum"></p></div></div>
<p class="empty" id="t-offline" hidden>Your tasks are saved by the Mantis site server. Open the site at http://localhost:8000 (it starts with each Claude Code session, or run <code>python tools/serve.py --open</code>).</p>
<div class="carry nocopy" id="t-carry" hidden><span id="t-carry-t"></span><button type="button" class="btn-line" data-carry="review">Review</button><button type="button" class="btn" data-carry="keep">Keep all</button></div>
<div class="today-grid"><div class="today-main">
<section class="blk" aria-labelledby="do-h"><div class="blk-h"><h2 id="do-h">Do today</h2><span class="blk-acts"><button type="button" class="linkish" id="t-sortp" title="Forget the places you dragged tasks and groups to; rank by priority, due date, then shortest first" hidden>Reset to default order</button><button type="button" class="linkish" id="t-more" hidden></button></span></div>
<ol id="t-list" class="t-list" title="Drag to rank, or Alt+↑/↓. Click a task for notes and dates."><li>{SKEL}</li></ol>
<form id="t-add" class="t-add" autocomplete="off" data-cards='{esc(json.dumps(cards))}'><span class="pm" aria-hidden="true">+</span>
<input id="t-title" type="text" placeholder="Add a task" aria-label="New task" maxlength="300">
<div class="t-add-more"><button type="button" class="pick" id="t-prio" data-pick="prio" data-value="">Priority</button>
<button type="button" class="pick" id="t-est" data-pick="est" data-value="">Time</button>
<button type="button" class="pick dp-btn" id="t-when" data-kind="when" data-value="" aria-haspopup="dialog" title="Which day it shows up on your list">Today</button>
<button type="button" class="pick dp-btn" id="t-due" data-kind="due" data-value="" aria-haspopup="dialog" title="Deadline">Due</button>
<input id="t-contact" class="pick-in" type="text" placeholder="Ask" maxlength="120" aria-label="Who to reach out to">
<button type="button" class="pick" id="t-grp" data-pick="group" data-value="">Group</button>
<button class="key-sm t-go" type="submit">Add</button></div></form>
<div class="t-other nocopy" id="t-other" role="tablist" aria-label="Other task lists">{lists}</div>
<ol id="t-sched" class="t-list t-olist" hidden></ol><ol id="t-park" class="t-list t-olist" hidden></ol><ol id="t-done" class="t-list t-olist" hidden></ol><ol id="t-bin" class="t-list t-olist" hidden></ol>
<section id="t-due-sug" class="due-sug nocopy" hidden></section>
<div id="t-brief" class="do-sug" hidden></div></section>
<section class="blk" id="pull-box" aria-labelledby="pull-h" data-cards='{esc(json.dumps(card_hrefs(features)))}'><div class="blk-h"><h2 id="pull-h">Since your last pull</h2><button type="button" class="linkish" id="pull-more" hidden></button></div>
<div id="pull-body">{SKEL}</div></section>
</div>
<aside class="today-side rail" aria-label="Meetings, people and questions">
<section class="rail-blk" id="t-next" hidden><h2>Next up</h2><div id="t-next-b"></div></section>
<section class="rail-blk" id="t-people" hidden></section>
{f'<section class="rail-blk"><h2>Questions</h2>{q_line}</section>' if q_line else ""}
{week_box}
<section id="t-away" class="rail-blk away-card nocopy" hidden></section>
</aside></div>"""
    return shell("Today", body, active="today", built=built)


def page_meetings(built):
    """Meetings (MANTIS-IMP-094): each regular meeting with an agenda that builds itself, what was agreed last
    time, and a place to drop the notes or transcript afterwards. Drawn by app.js from GET /api/extra."""
    # 2026-10-31 redesign: the meetings on the left, one agenda in focus on the right; a one-off brief and the weekly
    # status sit in the header, so the page holds nothing but the meetings themselves. Both are text links: Prepare
    # brief is the page's one main button (DESIGN.md rule 1).
    body = """<div class="page-h"><div><h1>Meetings</h1></div><div class="ph-acts nocopy">
<details class="pop"><summary class="linkish">Brief me for someone</summary><div class="pop-b"><select id="mb-who" class="sel" aria-label="Meeting with"></select>
<button type="button" class="btn job ai" data-job="meeting-brief" data-arg-from="#mb-who" title="Uses Claude, on your normal quota">Brief me</button><div class="chips" id="mt-briefs"></div></div></details>
<button type="button" class="linkish job ai" data-job="status-update" title="Uses Claude, on your normal quota">Weekly status</button></div></div>
<div class="mt-grid"><div class="mt-side"><nav class="mt-nav nocopy" id="mt-nav" aria-label="Your meetings"></nav>
<details class="add-meet nocopy" id="add-meet"><summary class="linkish">Add a regular meeting</summary><div class="pop-form" id="pp-meetings"></div></details></div>
<div id="mt-list" class="mt-list">""" + SKEL + """</div></div>"""
    return shell("Meetings", body, active="meetings", built=built)


def health():
    p = M / "knowledge" / "map" / "health.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"date": "", "items": []}


def health_html(work):
    """What Mantis noticed, the health report and background jobs, folded into Sources: housekeeping, kept off
    Today (MANTIS-IMP-094). The Mantis backlog is about Mantis itself and lives in docs/project, not here."""
    h = health()
    lab = {"warn": "Fix", "todo": "To do", "info": "Note"}
    rows = "".join(f'<div class="row health-row"><span class="t-meta{" warn-text" if i["level"] == "warn" else ""}">{lab[i["level"]]}</span><span class="row-t health-msg">{esc(plain(i["msg"], 400))}</span><span class="t-meta">{esc(i["area"])}</span></div>' for i in h["items"])
    att = [a for a in attention(work) if a[0] != "sources.html#health"]   # health warnings are listed below already
    noticed = (f'<h3 class="ag-h">Mantis noticed</h3><div class="rows">' + "".join(row_link(h_, m, a) for h_, m, a in att) + "</div>") if att else ""
    return f"""<details class="fold fold-panel" id="health"><summary><h2>Health and jobs</h2></summary>
{noticed}<h3 class="ag-h">Checks, {esc(h["date"])}</h3><div class="rows">{rows or '<p class="empty">All clear.</p>'}</div>
<section class="jobs-box" id="jobs"><div class="blk-h"><h3 class="ag-h">Background jobs</h3><span class="t-meta" id="job-quota"></span></div>
<div class="job-acts">{job_btn("rebuild", "Rebuild everything", ai=False)}{job_btn("daily-brief", "Prepare today's brief")}</div>
<p class="muted small job-note">Buttons marked ✦ use Claude on your normal subscription quota; the others are free. Jobs that hit a rule needing your decision stop and say "needs you" instead of guessing.</p>
<div id="job-list"></div></section></details>"""


def page_sources(work, built):
    """Sources (2026-10-31 redesign, after MANTIS-IMP-094): what Mantis reads, one row per filter, and the inbox.
    Health, past pulls and names to confirm are one line each beside them; the pull itself sits in the header.
    Past pulls and Health and jobs stay out of sight until their side line opens them (each said once)."""
    h = health()
    warn = sum(1 for i in h["items"] if i["level"] == "warn")
    att = [a for a in attention(work) if a[0] != "sources.html#health"]
    tidy = sum(1 for o in OPEN if scope_of(o) == "tidy")
    body = f"""<div class="page-h"><div><h1>Sources</h1><p class="lead" id="pn-state">Checking…</p></div></div>
<div class="today-grid"><div class="today-main">
<section class="blk nocopy" id="unmapped" aria-labelledby="um-h" hidden><div class="blk-h"><h2 id="um-h">Tickets with no feature</h2></div>
<p class="muted small">A pull leaves them out until you say where they belong.</p><div id="um-list" class="rows"></div></section>
<section class="blk nocopy" aria-labelledby="flt-h"><div class="blk-h"><h2 id="flt-h">Filters</h2><button type="button" class="linkish" id="flt-add-btn">Add a filter</button></div>
<div id="flt" class="flt rows">{SKEL}</div></section>
<section class="blk nocopy" aria-labelledby="ib-h"><div class="blk-h"><h2 id="ib-h">Inbox</h2><span class="t-meta" id="ib-state"></span></div>
<div class="drop" id="drop" tabindex="0" role="button" aria-label="Add files to the inbox: drop them here or press Enter to choose">
<span>Drop notes, transcripts or documents. The next pull reads them first.</span><span class="btn-line">Choose files</span>
<input type="file" id="drop-file" multiple hidden accept=".md,.txt,.vtt,.srt,.docx,.pdf,.html,.htm,.xlsx,.pptx"></div>
<details class="paste-box"><summary class="linkish">Paste text instead</summary><textarea id="paste-text" rows="5" placeholder="Paste meeting notes, an email or a chat thread"></textarea>
<div class="mb-row"><input id="paste-name" type="text" placeholder="Name (optional)" aria-label="Name for the pasted text"><button type="button" class="btn" id="paste-save">Add to inbox</button></div></details></section>
<details class="fold fold-panel" id="history"><summary><h2>Past pulls</h2></summary><div id="pull-history">{SKEL}</div>
<p class="small hist-more"><a href="changes.html">Everything that changed, day by day</a></p></details>
{health_html(work)}
</div>
<aside class="rail" aria-label="Health and history">
<a class="ri" href="#health" data-open="health"><span class="ri-h">Health</span><span class="ri-v{" warn-text" if warn else ""}">{n_(warn, "thing") + " to fix" if warn else "All clear"}</span><span class="ri-s">{f"{len(att)} noticed · " if att else ""}checked {esc(h["date"])}</span></a>
<a class="ri" href="#history" data-open="history"><span class="ri-h">History</span><span class="ri-v">The last ten pulls</span></a>
{f'<a class="ri" href="questions.html#tidy"><span class="ri-h">Names and terms</span><span class="ri-v">{tidy} to confirm</span></a>' if tidy else ""}
</aside></div>"""
    return shell("Sources", body, active="sources", built=built)
