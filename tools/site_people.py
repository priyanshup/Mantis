"""Site pages about people and questions: Open items and People."""
from site_common import *   # noqa: F401,F403  (shared state and helpers)


def page_people(built):
    """Everyone in knowledge/people.md (MANTIS-IMP-022). Follow-ups, meetings and briefs are filled live by app.js."""
    import people as people_mod
    cards = []
    for p in people_mod.load():
        f = p["fields"]
        def clean(v):   # citations stay in the knowledge base; the page shows them on hover only
            cites = re.findall(r"\(([^()]*(?:MANTIS-|User knowledge|Confluence|Owner)[^()]*)\)", v)
            text = re.sub(r"\s*\([^()]*(?:MANTIS-|User knowledge|Confluence|Owner)[^()]*\)", "", v).strip()
            proposed = text.startswith("*proposed:*")
            text = esc(text.replace("*proposed:*", "").strip())
            cite = re.sub(r"MANTIS-[A-Z]+-\d+", "a source document", "; ".join(cites))
            return (('<span class="tag">Proposed</span> ' if proposed else "") + text, cite)
        rows = ""
        for k, v in (("role", p["role"]), ("team", p["team"]), ("channel", p["channel"]), ("briefing style", p["briefing"]), ("notes", p["notes"])):
            if v:
                text, cite = clean(v)
                rows += f'<div class="pp-f"><span class="muted small">{esc(k.capitalize())}</span><span{f" title=\"Source: {esc(cite)}\"" if cite else ""}>{text}</span></div>'
        cards.append(f'<article class="tile person" id="{esc(p["slug"])}" data-name="{esc(p["name"])}"><h3><span>{esc(p["name"])}</span>'
                     f'<span class="pp-n nocopy" hidden></span></h3>{rows}{can_answer(p["name"])}'
                     f'<div class="pp-live nocopy"></div>'
                     f'<div class="tile-acts nocopy">{job_btn("meeting-brief", "Brief me", arg=p["name"], cls="act")}{draft_button(p["name"]) if p["name"] in DRAFTS else ""}'
                     f'<button type="button" class="act pp-add" data-person="{esc(p["name"])}">+ Follow-up</button></div></article>')
    body = f"""<div class="page-h"><div><h1>People</h1><p class="lead">Everyone you work with: role, how to reach them, how they like to be briefed, and what is open with them. Edit details in the knowledge base (people file); follow-ups and briefs update live.</p></div>
<div class="toolbar"><input type="search" id="pp-filter" placeholder="Filter people…" aria-label="Filter people"></div></div>
<section class="panel-box pp-meet nocopy"><div class="box-h"><h2>Your regular meetings</h2><span class="muted small">Briefs and deadline suggestions use these</span></div><div id="pp-meetings"><p class="muted small">Loading…</p></div></section>
<script type="application/json" id="draft-data">{json.dumps(DRAFTS, ensure_ascii=False).replace("</", "<\\/")}</script>
<div class="later people-grid">{"".join(cards) or '<p class="empty">No people yet. Add them to mantis/knowledge/people.md.</p>'}</div>"""
    return shell("People", body, active="people", built=built)


def page_review(features, built):
    names = {f["slug"]: f["title"] for f in features}
    groups = {}
    for o in OPEN:
        for s in (["~names"] if o["kind"] in ("name", "term") else o["features"] or [""]):
            groups.setdefault(s, []).append(o)
    order = [f["slug"] for f in features if f["slug"] in groups] + [s for s in ("", "~names") if s in groups]
    names["~names"] = "Names and terms to confirm"
    cls = {"Open": "s-ref", "Potential resolution": "s-build", "Unconfirmed": "s-ref"}

    FIRST = ("What's missing", "Statement A", "Statement B", "Statement", "Claim")

    def context(o):
        """What the owner needs to answer: the question itself, the evidence so far, and the likely answer."""
        det = [(k, v) for k, v in o.get("detail", []) if not k.startswith("Evidence Strength")]
        EVID = ("Evidence so far", "Partial resolution", "Settled", "Update", "Overall status", "Resolution")
        main = [(k, v) for k, v in det if k.split(" (")[0] in FIRST]
        likely_ans = o["status"] not in ("Open", "Unconfirmed")   # a possible conflict has no "likely answer" to confirm
        evid = [(k, v) for k, v in det if k.startswith(EVID)] if likely_ans else []
        rest = [(k, v) for k, v in det if k.split(" (")[0] not in FIRST and (k, v) not in evid]
        strength = next((v for k, v in o.get("detail", []) if k.startswith("Evidence Strength")), "")
        html_ = "".join(f'<div class="oi-q"><b>{esc(k)}</b><p>{esc(v)}</p></div>' for k, v in main)
        if likely_ans:
            likely = o["status_full"].split("(", 1)[1].rstrip(")") if "(" in o["status_full"] else ""
            ev = "".join(f'<p><b>{esc(k)}:</b> {esc(v)}</p>' for k, v in evid)
            html_ += (f'<div class="oi-likely"><b>Likely answer</b>{f"<p>{esc(likely)}</p>" if likely else ""}{ev or ("" if likely else "<p>See the evidence below.</p>")}'
                      f'<button type="button" class="btn quick-confirm nocopy" data-q="{esc(o["id"])}">✓ Confirm and close</button>'
                      f'<span class="muted small"> or answer below if it is not right.</span></div>')
        if rest:
            html_ += '<details class="oi-more"><summary>Notes and evidence so far</summary>' + "".join(
                f'<p><b>{esc(k)}:</b> {esc(v)}</p>' for k, v in rest) + "</details>"
        if strength:
            html_ += f'<p class="muted small">Evidence strength: {esc(strength)}</p>'
        return html_ or f'<p>{esc(o["status_full"])}</p>'

    def row(o, flat=False):
        docs = "".join(f"<li>{esc(d['id'].replace('MANTIS-', ''))} {esc(d['title'])}</li>" for d in o["docs"])
        tops = [names.get(s, "No topic") for s in (o["features"] if o["kind"] not in ("name", "term") else ["~names"])]
        more = f'<span class="tag oi-where" title="{esc(", ".join(tops[3:]))}">+{len(tops) - 3} more</span>' if len(tops) > 3 else ""
        where = (f'<span class="oi-tags">{"".join(f"<span class=\"tag oi-where\">{esc(x)}</span>" for x in tops[:3])}{more}</span>') if flat else ""
        anchor = f'id="{esc(o["id"])}" ' if flat else ""   # only the one-list copy carries the id, so links land once
        return (f'<details class="bl oi" {anchor}data-qid="{esc(o["id"])}" data-k="{hashlib.sha1(o["id"].encode("utf-8")).hexdigest()[:10]}" data-kind="{o["kind"]}" data-status="{esc(o["status"])}" data-priority="{esc(o.get("priority", ""))}" data-ask="{esc((o.get("ask") or {}).get("name", ""))}"><summary>'
                f'<span class="bl-id">{esc(o["id"].replace("MANTIS-", ""))}</span><span class="oi-main"><span class="row-t">{esc(re.sub(r" ?[(]MANTIS-[A-Z]+-[0-9]+(?:[,;] ?MANTIS-[A-Z]+-[0-9]+)*[)]", "", o["topic"]))}</span>{where}{ask_chip(o)}</span>'
                f'{pill(o["priority"] + " priority", PRIO_CLS[o["priority"]] + " plain") if o.get("priority") else ""}'
                f'{pill("Possible conflict" if o["status"] == "Unconfirmed" else o["status"], cls.get(o["status"], "s-none") + " plain") if o["status"] != "Open" else ""}<span class="muted small oi-date">{esc(o["raised"])}</span></summary>'
                f'<div class="doc">{context(o)}'
                f'{"<p class=oi-named><b>Named in:</b></p><ul>" + docs + "</ul>" if docs else ""}'
                f'<p class="muted small">Full entry: <code>python tools/entry.py show {esc(o["id"])}</code></p>'
                f'<div class="answer" data-id="{esc(o["id"])}" data-topic="{esc(o["topic"][:300])}"><p class="answer-sent" hidden>Answer sent. Mantis will process it in the next session.</p>'
                f'<div class="answer-form"><div class="seg verdict">{verdicts("possible" if o["status"] == "Unconfirmed" else o["kind"])}</div>'
                f'<textarea rows="3" placeholder="{esc(PLACEHOLDER.get("possible" if o["status"] == "Unconfirmed" else o["kind"], PLACEHOLDER["gap"]))}" data-ph-later="When or how it will be decided, e.g. after the spike, at the next steering meeting (optional)"></textarea>'
                f'<input class="who" type="text" placeholder="Who should answer it? (name or role)" hidden>'
                f'<button type="button" class="btn-line answer-discard" hidden>Discard this answer</button></div></div></div></details>')

    secs = "".join(f'<details class="grp-box oi-group" data-group="{esc(s)}"><summary><h2>{esc(names.get(s, "Not linked to a roadmap topic"))} '
                   f'<span class="muted oi-n">{len(groups[s])}</span></h2></summary><div class="panel-box">{"".join(row(o) for o in groups[s])}</div></details>' for s in order)
    uniq = sorted(OPEN, key=lambda o: (o.get("raised", ""), o["id"]), reverse=True)
    uniq.sort(key=lambda o: PRIO_RANK[o.get("priority", "")])   # MANTIS-IMP-001: Critical and High first, newest first within each
    flat = f'<section class="oi-flat" id="oi-flat"><div class="panel-box">{"".join(row(o, flat=True) for o in uniq)}</div></section>'
    n_gap = sum(1 for o in OPEN if o["kind"] == "gap")
    n_pot = sum(1 for o in OPEN if o["status"] not in ("Open", "Unconfirmed"))
    n_top = sum(1 for o in OPEN if o.get("priority") in ("Critical", "High"))
    n_pos = sum(1 for o in OPEN if o["status"] == "Unconfirmed")
    whos = {}
    for o in OPEN:
        if o.get("ask"):
            whos[o["ask"]["name"]] = whos.get(o["ask"]["name"], 0) + 1
    who_sel = ('<select id="oi-who" class="sel sel-sm" aria-label="Who can answer"><option value="">Anyone can answer</option>'
               + "".join(f'<option value="{esc(n)}">{esc(n)} · {c}</option>' for n, c in sorted(whos.items(), key=lambda x: (-x[1], x[0]))) + "</select>") if whos else ""
    body = f"""<div class="page-h"><div><h1>Open items</h1><p class="lead">{len(OPEN)} questions Mantis is tracking, {"highest priority first, then " if n_top else ""}newest first. Open one to answer it; answer several, then submit them together.</p></div></div>
<div class="answers-strip oi-banner nocopy" hidden><b>Your submitted answers are waiting to be recorded.</b> {job_btn("process-answers", "Process answers", cls="btn")}</div>
{f'<div class="oi-banner nocopy"><b>{n_pos} possible conflict{"s" if n_pos != 1 else ""} to check.</b> Two sources may disagree; tell Mantis whether they do. <button type="button" class="btn" data-goto-filter="possible">Show {"them" if n_pos != 1 else "it"}</button></div>' if n_pos else ""}
{f'<div class="oi-banner nocopy"><b>{n_pot} question{"s have" if n_pot != 1 else " has"} a likely answer.</b> Confirm or correct {"them" if n_pot != 1 else "it"} in a minute. <button type="button" class="btn" data-goto-filter="potential">Show {"them" if n_pot != 1 else "it"}</button></div>' if n_pot else ""}
<div class="toolbar"><div class="chips" id="f-oi"><button data-v="all" class="on">All</button><button data-v="potential">Waiting for your decision · {n_pot}</button>{f'<button data-v="possible">Possible conflicts · {n_pos}</button>' if n_pos else ""}{f'<button data-v="priority">High priority · {n_top}</button>' if n_top else ""}<button data-v="gap">Gaps</button><button data-v="conflict">Conflicts</button><button data-v="names">Names and terms</button></div>{who_sel}{'<button type="button" class="btn-line nocopy" id="oi-draft" hidden>Draft a message</button>' if who_sel else ""}
<div class="seg" id="oi-view" aria-label="Layout"><button data-v="flat" class="on">One list</button><button data-v="topic">By topic</button></div></div>
<div class="oi-topics-bar nocopy" id="oi-topics-bar" hidden><span class="muted small" id="oi-topics-n"></span><button type="button" class="mini" id="oi-expand">Expand all</button></div>
<script type="application/json" id="draft-data">{json.dumps(DRAFTS, ensure_ascii=False).replace("</", "<\\/")}</script>
{flat if OPEN else '<p class="empty">Nothing open.</p>'}<div id="oi-topics" hidden>{secs}</div>
<div class="answer-bar" id="answer-bar" hidden><span id="answer-count"></span><button class="btn-ghost" id="answer-clear" type="button">Clear drafts</button><button class="btn" id="answer-submit" type="button">Submit answers</button></div>"""
    return shell("Open items", body, active="review", built=built)
