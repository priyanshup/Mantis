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
    body = f"""<div class="page-h"><div><h1>People</h1><p class="lead">Everyone you work with: role, how to reach them, how they like to be briefed, and what is open with them. Any name on the site opens the same details in a side panel.</p></div>
<div class="toolbar"><input type="search" id="pp-filter" placeholder="Filter people…" aria-label="Filter people"></div></div>
<script type="application/json" id="draft-data">{json.dumps(DRAFTS, ensure_ascii=False).replace("</", "<\\/")}</script>
<div class="later people-grid">{"".join(cards) or '<p class="empty">No people yet. Add them to mantis/knowledge/people.md.</p>'}</div>"""
    return shell("People", body, active="people", built=built)


def people_data():
    """Everyone, for the side panel (MANTIS-IMP-094): the knowledge-base fields with citations kept off the page,
    the questions each can answer, and the drafts behind Draft a message. Live parts come from GET /api/extra."""
    import people as people_mod
    out = []
    for p in people_mod.load():
        f = lambda v: (re.sub(r"\s*\([^()]*(?:MANTIS-|User knowledge|Confluence|Owner)[^()]*\)", "", v or "").replace("*proposed:*", "").strip(),
                       (v or "").strip().startswith("*proposed:*"))
        can = [{"q": plain(re.sub(r" ?[(]MANTIS-[^)]*[)]", "", o["topic"]), 140), "k": hashlib.sha1(o["id"].encode("utf-8")).hexdigest()[:10],
                "named": o["ask"]["how"] == "named"} for o in OPEN if (o.get("ask") or {}).get("name") == p["name"]]
        out.append({"name": p["name"], "slug": p["slug"], "aliases": p["aliases"],
                    **{k: f(p[k])[0] for k in ("role", "team", "channel", "briefing", "notes")},
                    "proposed": [k for k in ("briefing", "notes") if f(p[k])[1]], "can": can, "draft": DRAFTS.get(p["name"])})
    return out


def auto_closed(days=30):
    """Open questions a source closed automatically in the last `days` days, newest first (MANTIS-IMP-094)."""
    since = (datetime.now().date().toordinal() - days)
    out = []
    for p in (M / "knowledge" / "registers" / "gaps").glob("MANTIS-GAP-*.md"):
        t = p.read_text(encoding="utf-8")
        m = re.search(r"(?m)^- \*\*Status:\*\* Closed \(auto, (\d{4}-\d{2}-\d{2}): (.*?); source (MANTIS-DOC-\d{4})\)", t)
        if m and datetime.strptime(m.group(1), "%Y-%m-%d").date().toordinal() >= since:
            topic = re.search(r"(?m)^- \*\*Topic:\*\*\s*(.+)$", t)
            out.append({"id": p.stem, "date": m.group(1), "why": m.group(2), "topic": (topic.group(1) if topic else "").strip()})
    return sorted(out, key=lambda x: x["date"], reverse=True)


def page_review(features, built):
    from site_day import scope_of, yours
    names = {f["slug"]: f["title"] for f in features} | {t["slug"]: t["title"] for t in TOPICS}

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
        def said(v):   # the statement, then where it comes from on its own small line; no Mantis IDs or Markdown
            parts = re.split(r"\s*[—–-]{0,2}\s*\*\*Sources?:?\*\*:?\s*", v, maxsplit=1)
            text, src = plain(parts[0], 1200), plain(parts[1] if len(parts) > 1 else "", 300).strip(" ;.")
            return f'<p>{esc(text)}</p>' + (f'<small class="oi-src">{esc(src)}</small>' if src else "")
        html_ = "".join(f'<div class="oi-q"><b>{esc(k)}</b>{said(v)}</div>' for k, v in main)
        if likely_ans:
            likely = o["status_full"].split("(", 1)[1].rstrip(")") if "(" in o["status_full"] else ""
            ev = "".join(f'<p><b>{esc(plain(k, 200))}:</b> {esc(plain(v, 2000))}</p>' for k, v in evid)
            html_ += (f'<div class="oi-likely"><b>Likely answer</b>{f"<p>{esc(plain(likely, 1200))}</p>" if likely else ""}{ev or ("" if likely else "<p>See the evidence below.</p>")}'
                      f'<button type="button" class="btn quick-confirm nocopy" data-q="{esc(o["id"])}">✓ Confirm and close</button>'
                      f'<span class="muted small"> or answer below if it is not right.</span></div>')
        if rest:
            html_ += '<details class="oi-more"><summary>Notes and evidence so far</summary>' + "".join(
                f'<p><b>{esc(plain(k, 200))}:</b> {esc(plain(v, 2000))}</p>' for k, v in rest) + "</details>"
        if strength:
            html_ += f'<p class="muted small">Evidence strength: {esc(strength)}</p>'
        return html_ or f'<p>{esc(o["status_full"])}</p>'

    def row(o):
        """One line per question (2026-10-31 redesign): the question, an exception worth seeing (a likely answer,
        a high priority), and its main feature. IDs, dates and the other features open with it."""
        docs = "".join(f"<li>{esc(d['title'])}</li>" for d in o["docs"])
        tops = [names.get(s, "") for s in o["features"]] if o["kind"] not in ("name", "term") else []
        tops = [t for t in tops if t]
        # the feature the question is most about first: the one whose name shares the most words with it
        words = lambda t: {w for w in re.findall(r"[a-z]{4,}", t.lower())}
        tops.sort(key=lambda t: -len(words(t) & words(o["topic"])))
        flag = ("Likely answer" if o["status"].lower().startswith("potential") else "")
        prio = o.get("priority", "") if o.get("priority") in ("Critical", "High") else ""
        short = lambda t: re.sub(r"\s*\([^)]*\)\s*$", "", t).split(":")[0]
        # The row's feature tag fits whole: a long name keeps the part before " and " when that is two words or more
        # ("Customer groups and group pricing" -> "Customer groups"); the full names stay in the tooltip
        def tag(t):
            t = short(t); head = t.split(" and ")[0]
            return head if len(t) > 26 and " and " in t and len(head.split()) >= 2 else t
        return (f'<details class="bl oi" id="{esc(o["id"])}" data-qid="{esc(o["id"])}" data-k="{hashlib.sha1(o["id"].encode("utf-8")).hexdigest()[:10]}" data-scope="{scope_of(o)}" data-kind="{o["kind"]}" data-status="{esc(o["status"])}" data-priority="{esc(o.get("priority", ""))}" data-ask="{esc((o.get("ask") or {}).get("name", ""))}"><summary>'
                f'<span class="row-t">{esc(re.sub(r" ?[(]MANTIS-[A-Z]+-[0-9]+(?:[,;] ?MANTIS-[A-Z]+-[0-9]+)*[)]", "", o["topic"]))}</span>'
                f'{f"<span class=\"t-meta flag-info\">{flag}</span>" if flag else ""}{f"<span class=\"t-meta warn-text\">{prio}</span>" if prio else ""}'
                f'<span class="t-meta oi-where" title="{esc(", ".join(tops))}">{esc(tag(tops[0])) if tops else ""}</span></summary>'
                f'<div class="doc oi-body">{context(o)}'
                f'<p class="muted small oi-meta">{"Possible conflict · " if o["status"] == "Unconfirmed" else ""}Raised {esc(o["raised"])}'
                f'{" · " + esc(", ".join(short(t) for t in tops[:3])) if tops else ""}{f" and {len(tops) - 3} more" if len(tops) > 3 else ""}</p>'
                f'{"<details class=oi-more><summary>Named in " + n_(len(o["docs"]), "source") + "</summary><ul>" + docs + "</ul></details>" if docs else ""}'
                f'<div class="answer" data-id="{esc(o["id"])}" data-topic="{esc(o["topic"][:300])}"><p class="answer-sent" hidden>Answer sent. Mantis will process it in the next session.</p>'
                f'<div class="answer-form"><div class="seg verdict">{verdicts("possible" if o["status"] == "Unconfirmed" else o["kind"])}</div>'
                f'<textarea rows="3" placeholder="{esc(PLACEHOLDER.get("possible" if o["status"] == "Unconfirmed" else o["kind"], PLACEHOLDER["gap"]))}" data-ph-later="When or how it will be decided, e.g. after the spike, at the next steering meeting (optional)"></textarea>'
                f'<input class="who" type="text" placeholder="Who should answer it? (name or role)" hidden>'
                f'<button type="button" class="btn-line answer-discard" hidden>Discard this answer</button></div></div></div></details>')

    # Grouped by who can answer (2026-10-31 redesign): the next step on a question is asking that person, so each
    # group carries the message to send. Each question is listed once; tidy-up (names and terms) is reached from
    # Sources and has no tab of its own.
    others = sorted((o for o in OPEN if scope_of(o) == "others"), key=lambda o: (o.get("raised", ""), o["id"]), reverse=True)
    others.sort(key=lambda o: ((o.get("ask") or {}).get("how") != "named", PRIO_RANK[o.get("priority", "")]))
    tidy = [o for o in OPEN if scope_of(o) == "tidy"]
    closed = auto_closed()
    NOONE = "No one named yet"

    def grouped(scope, items):
        by = {}
        for o in items:
            by.setdefault((o.get("ask") or {}).get("name") or (NOONE if scope != "tidy" else "Names and terms to confirm"), []).append(o)
        order = sorted(by, key=lambda p: (p in (NOONE,), -len(by[p]), p))
        return "".join(f'<section class="q-grp" data-scope="{scope}"><div class="blk-h"><h2>{esc(p)} <span class="n oi-n">{len(by[p])}</span></h2>'
                       f'{draft_button(p, "linkish") if p in DRAFTS else ""}</div><div class="rows">{"".join(row(o) for o in by[p])}</div></section>' for p in order)

    closed_rows = "".join(f'<div class="row closed-row" data-closed="{esc(x["id"])}"><span class="row-t">{esc(re.sub(r" ?[(]MANTIS-[^)]*[)]", "", x["topic"]))}'
                          f'<span class="muted small">{esc(x["date"])} · {esc(plain(x["why"], 220))}</span></span>'
                          f'<button type="button" class="linkish" data-reopen="{esc(x["id"])}">Undo</button></div>' for x in closed)
    kinds = [("all", "Everything"), ("potential", "Likely answer"), ("possible", "Possible conflicts"), ("gap", "Gaps"), ("conflict", "Conflicts")]
    body = f"""<div class="page-h"><div><h1>Questions</h1></div><div class="ph-acts nocopy"><button type="button" class="btn" id="q-focus">Answer one by one</button></div></div>
<div class="answers-strip oi-banner nocopy" hidden><b>Your submitted answers wait for the next pull.</b> Press Pull at the top when you are ready.</div>
<div class="tabs-row"><div class="tabs-u" id="q-scope" role="tablist" aria-label="Questions"><button data-v="you" class="on" role="tab">For you <span class="n">{len(yours())}</span></button><button data-v="others" role="tab">Waiting <span class="n">{len(others)}</span></button>
{f'<button data-v="closed" role="tab">Answered <span class="n">{len(closed)}</span></button>' if closed else ""}<button data-v="tidy" role="tab" hidden>Names and terms <span class="n">{len(tidy)}</span></button></div>
<details class="pop nocopy" id="f-oi-pop"><summary class="btn-line" id="f-oi-l">Filter</summary><div class="pop-b"><p class="grp-l">Show</p>
<div class="chipset" id="f-oi">{"".join(f'<button type="button" data-v="{v}"{" class=\"on\"" if v == "all" else ""}>{l}</button>' for v, l in kinds)}</div></div></details></div>
<script type="application/json" id="draft-data">{json.dumps(DRAFTS, ensure_ascii=False).replace("</", "<\\/")}</script>
<p class="empty" id="q-empty" hidden>Nothing here. When a question needs you, it shows up here and on the Questions tab badge.</p>
<div id="q-lists" class="stack">{grouped("you", yours())}{grouped("others", others)}{grouped("tidy", tidy)}</div>
<section id="q-closed" hidden><p class="muted small closed-note">A new source answered these clearly, so Mantis closed them and cited the source. Undo opens one again.</p>
<div class="rows">{closed_rows}</div></section>
<div class="answer-bar" id="answer-bar" hidden><span id="answer-count"></span><button class="btn-ghost" id="answer-clear" type="button">Clear drafts</button><button class="btn" id="answer-submit" type="button">Submit answers</button></div>
<div class="q-focusbar nocopy" id="q-focusbar" hidden><button type="button" class="btn-line" id="q-prev" title="Previous question (K)">← Back</button>
<button type="button" class="btn-line" id="q-next" title="Next question (J)">Next →</button><span class="t-meta">Keys 1 2 3 choose · J K move</span><button type="button" class="linkish" id="q-unfocus" title="Esc">Leave</button></div>"""
    return shell("Questions", body, active="questions", built=built)
