"""Site pages for planning: Features (Following, Roadmap with its Timeline view, Ideas, All), feature and topic pages, Epics & stories."""
import re
from site_common import *   # noqa: F401,F403  (shared state and helpers)


# ---------- Pages ----------

FLAG = {"Problem not validated": "Problem unproven", "No measurement plan": "No metric plan"}   # two words on a row; the why is in the tooltip


def flag(slug):
    """The one readiness warning a feature row carries, short (MANTIS-IMP-074 to 076); the reason sits in the title."""
    r = next((x for x in READY.get("features", []) if x["slug"] == slug), None)
    if not r or r["state"] in ("ready", "measuring", "reviewed"):
        return '<span class="t-meta flag"></span>'   # an empty cell keeps the row's columns in line
    label = READY["states"].get(r["state"], r["state"])
    return f'<span class="t-meta flag" title="{esc(label)}: {esc(r["why"])}">{esc(FLAG.get(label, label))}</span>'


def stage(c, feat):
    """Where a card is: a feature's stage; a topic on the roadmap is a topic, off it an idea (a dashed ring)."""
    if feat:
        return f'<span class="st st-{c["status"]}">{STATUS[c["status"]][0]}</span>'
    return '<span class="st">Topic</span>' if on_roadmap(c, False) else '<span class="st st-idea">Idea</span>'


WK = {"business": "Business", "technical": "Technical", "both": "Business and technical"}


def wk(c):
    """The work type as a tag: a word plus its own shape (square, triangle, both), never colour alone."""
    w = c.get("work", "") if isinstance(c, dict) else c
    return f'<span class="wk wk-{w}">{WK[w]}</span>' if w in WK else '<span class="wk wk-none">Type not set</span>'


def nq(c):
    n = len(feature_questions(c["slug"]))
    return f'<span class="t-meta f-q">{n_(n, "question")}</span>' if n else '<span class="t-meta f-q"></span>'


def focus_html(features):
    """Mine: the cards the owner follows, in their own order, grouped into business and technical work. Each row
    says one thing beyond its name: a warning, its stage and its open questions. Drag (or Alt+↑/↓) to rank."""
    by_slug = {c["slug"]: (c, c in features) for c in features + TOPICS}
    mine = [by_slug[s] for s in FOCUS["following"] if s in by_slug]

    def focus_row(c, feat):
        return (f'<li class="f-row" draggable="true" data-slug="{c["slug"]}" data-work="{c.get("work", "")}" tabindex="-1">'
                f'<a class="row-t" href="{"features" if feat else "topics"}/{c["slug"]}.html">{esc(c["title"])}</a>{flag(c["slug"])}{stage(c, feat)}{nq(c)}</li>')

    def section(g, xs):
        """A group's label and rows. A group of ideas only (topics not on the roadmap) starts as one line, "Technical
        · 6 ideas", since its rows would all say just "Idea"; the page remembers whether the owner opened it."""
        rows = f'<ol class="rows focus-list">{"".join(focus_row(c, f) for c, f in xs)}</ol>'
        if all(not f and not on_roadmap(c, False) for c, f in xs):
            return f'<details class="f-fold" data-work="{g}"><summary class="grp-l">{wk(g)} <span class="n">{n_(len(xs), "idea")}</span></summary>{rows}</details>'
        return f'<p class="grp-l">{wk(g)}</p>{rows}'

    groups = [(w, [x for x in mine if x[0].get("work", "") == w]) for w in ("business", "technical", "both")] \
        + [("", [x for x in mine if x[0].get("work", "") not in WK])]
    return ('<div id="focus-list">' + "".join(section(g, xs) for g, xs in groups if xs) + "</div>") if mine \
        else '<p class="empty">You follow nothing yet. Open <b>All</b> and press Follow on the subjects you own.</p>'


def page_features(features, later, built):
    """Features (2026-10-31 redesign, after MANTIS-IMP-094): Mine, Roadmap and All under three tabs, and one Filter
    menu for type, stage, priority and the archive. Mine is the ranked list, Roadmap the board, list and timeline."""
    rd = roadmap_html(features, later)
    cards = [(f, True) for f in features] + [(t, False) for t in TOPICS]
    n_f = sum(1 for s in FOCUS["following"] if not archived(s))
    n_r = sum(1 for c, f in cards if on_roadmap(c, f))
    n_a = sum(1 for c, f in cards if archived(c["slug"]))
    n_epics, n_stories = len({e["id"] for f in features for e in f["epics"]}), sum(len(f["stories"]) for f in features)
    chips = "".join(f'<button data-v="{k}">{v[0]}</button>' for k, v in STATUS.items())
    body = f"""<div class="page-h"><div><h1>Features</h1></div><div class="ph-acts nocopy"><a class="btn-line" href="work.html">Epics and stories <span class="n">{n_epics + n_stories}</span></a></div></div>
<div class="tabs-row"><div class="tabs-u" id="ttab" role="tablist" aria-label="Which features"><button data-v="focus" class="on" role="tab">Mine <span class="n">{n_f}</span></button>
<button data-v="roadmap" role="tab">Roadmap <span class="n">{n_r}</span></button><button data-v="all" role="tab">All <span class="n">{len(cards) - n_a}</span></button><button data-v="ideas" role="tab" hidden>Ideas</button></div>
<details class="pop nocopy" id="f-pop"><summary class="btn-line">Filter</summary><div class="pop-b">
<p class="grp-l">Type</p>{work_chips([c for c, f in cards if not archived(c["slug"])])}
<div class="rd-only"><p class="grp-l">Stage</p><div class="chips" id="f-status"><button data-v="all" class="on">Any</button>{chips}</div>
<p class="grp-l">Priority</p><div class="chips" id="f-prio"><button data-v="all" class="on">Any</button><button data-v="P1">P1</button><button data-v="P2">P2</button><button data-v="P3">P3</button></div></div>
<p class="grp-l">Show</p><div class="chipset"><button type="button" data-ideas>Ideas only</button><button type="button" data-arch>Archived · {n_a}</button></div>
<div id="t-bulk-box" hidden><p class="grp-l">Change everything shown</p><div class="chipset bulk" id="t-bulk"></div></div></div></details></div>
<section data-scope-panel="focus">{focus_html(features)}</section>
<section data-scope-panel="roadmap" hidden>{rd}</section>
<section data-scope-panel="tiles" hidden><div class="toolbar"><input id="tq" type="search" placeholder="Find a feature or idea" aria-label="Find a feature or idea"></div>
<p class="empty" id="t-empty" hidden>Nothing here yet.</p>
<ol class="rows all-list">{"".join(tile(c, f) for c, f in cards)}</ol></section>"""
    return shell("Features", body, active="features", built=built)


def work_chips(cards):
    """The quick filter by work type, shared by Following, Roadmap and the cards. Business and Technical
    each include the cards that are both; Not set finds topics still to classify."""
    n = {w: sum(1 for c in cards if c.get("work", "") == w) for w in ("business", "technical", "both", "")}
    chip = lambda v, label, k: f'<button data-v="{v}"{" class=\"on\"" if v == "all" else ""}>{label} <span class="n">{k}</span></button>'
    return ('<div class="chips" id="t-work" data-k="work" aria-label="Type">'
            + chip("all", "Any", len(cards)) + chip("business", "Business", n["business"] + n["both"])
            + chip("technical", "Technical", n["technical"] + n["both"]) + chip("none", "Not set", n[""]) + "</div>")


def tile(c, feat):
    """A row in All: the name and its one-line summary, stage and questions; Follow, Roadmap and Archive show on hover."""
    url = ("features/" if feat else "topics/") + c["slug"] + ".html"
    fol, road = c["slug"] in FOCUS["following"], on_roadmap(c, feat)
    arc = archived(c["slug"])
    return (f'<li class="f-row all-row" data-slug="{c["slug"]}" data-feat="{int(feat)}" data-following="{int(fol)}" data-roadmap="{int(road)}" data-idea="{int(not feat and not road)}" data-archived="{int(arc)}" data-work="{c.get("work", "")}">'
            f'<span class="f-main"><a class="row-t" href="{url}">{esc(c["title"])}</a><span class="f-sum">{esc(c["summary"])}</span></span>{wk(c)}{stage(c, feat)}{nq(c)}'
            f'<span class="row-acts nocopy"><button type="button" class="act follow{" on" if fol else ""}" data-a="follow" aria-pressed="{str(fol).lower()}">{"Following" if fol else "Follow"}</button>'
            f'<button type="button" class="act road{" on" if road else ""}" data-a="roadmap" aria-pressed="{str(road).lower()}">{"On roadmap" if road else "Roadmap"}</button>'
            f'<button type="button" class="act arc" data-a="archive" title="Hide this card everywhere; restore it from Archived">{"Restore" if arc else "Archive"}</button></span></li>')


def roadmap_html(features, later):
    data = [{k: f[k] for k in ("slug", "title", "type", "status", "status_note", "priority", "jira", "estimate", "updated", "summary", "open")}
            | {"epics": len(f["epics"]), "page": bool(f["page"]), "stories": len(f["stories"]),
               "storiesDone": sum(1 for s in f["stories"] if s["status"] in ("in-jira", "done"))}
            | {"work": f.get("work", ""), "workTag": wk(f)} for f in features if on_roadmap(f, True)]
    for f in data:
        f["url"] = f"features/{f['slug']}.html"
    for t in TOPICS:
        if on_roadmap(t, False):
            fm = read(t["card"])[0]
            data.append({"slug": t["slug"], "url": f"topics/{t['slug']}.html", "title": t["title"], "type": "topic",
                         "status": fm.get("status", "discovery") if fm.get("status") in STATUS else "discovery", "status_note": "",
                         "priority": fm.get("priority", "") if fm.get("priority") in ("P1", "P2", "P3") else "", "jira": "none",
                         "estimate": "", "updated": t["updated"], "summary": t["summary"], "open": t["open"], "epics": 0,
                         "page": False, "stories": 0, "storiesDone": 0, "work": t.get("work", ""), "workTag": wk(t)})
    data += [{"slug": "", "title": l["title"], "type": "feature", "status": "none", "status_note": "", "priority": "", "jira": "",
              "estimate": "", "updated": "", "summary": l["note"], "open": 0, "epics": 0, "page": False, "stories": 0, "storiesDone": 0,
              "work": "", "workTag": ""} for l in later]
    labels = {k: v[0] for k, v in STATUS.items()}
    return f"""<div class="toolbar rd-bar"><div class="seg" id="view" aria-label="Layout"><button data-v="board" class="on">Board</button><button data-v="list">List</button><button data-v="timeline">Timeline</button></div>
<div class="rd-tools" id="rd-tools"><input id="q" type="search" placeholder="Find on the roadmap" aria-label="Find on the roadmap"></div></div>
<div id="board"></div><div id="list" hidden></div><div id="tl-view" hidden>{page_timeline("", embed=True)}</div>
<script id="data" type="application/json">{json.dumps({"items": data, "labels": labels})}</script>"""


MARK = "<!-- GENERATED"
KEYFACTS = {"Outcome wanted": "Outcome", "Cost of doing nothing": "If we wait", "Next decision": "Next decision"}
EVIDENCE = ("Observed", "Opinion", "Unknown", "Assumed", "Inferred")


def _inline(md):
    """A short Markdown value as inline HTML (one paragraph, no wrapper), starting with a capital."""
    md = md.strip()
    return re.sub(r"^<p>|</p>$", "", render(md[:1].upper() + md[1:], sections=False).strip())


def _hint(text, limit=80):
    """A section's first sentence, without list marks or leading labels ("Hypothesis: Proposed: ...")."""
    s = re.sub(r"\s+", " ", plain(text, 400)).strip()
    s = re.sub(r"^(?:[-*•]\s*|\d+\.\s*|\|[^|]*\|\s*)+", "", s)
    s = re.sub(r"^(?:[A-Z][\w'’ -]{0,28}:\s*)+", "", s)
    s = re.split(r"(?<=[.!?;])\s", s)[0].rstrip(";:.")
    s = s[:1].upper() + s[1:]
    return s if len(s) <= limit else s[:limit - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def overview(md, slug, extra=()):
    """A card's Overview (2026-10-31 redesign): its one paragraph large, the few facts a reader needs (outcome,
    the cost of waiting, the next decision, plus `extra`), then every other section closed with a one-line hint.
    The generated part below the marker is not shown here: its sources, questions and people have their own tab
    or the side column. A hidden full copy keeps Copy one-pager pasting the whole card."""
    curated = md.split(MARK)[0]
    lead, facts, folds = "", [], []
    warn = flag(slug)
    for head, text in _sections(curated):
        if head == "Top of the page":
            continue
        if head.lower() == "in one paragraph":
            lead = text
            continue
        hint = _hint(text)
        if head.lower().startswith("problem"):
            keep = []
            for line in text.split("\n"):
                m = re.match(r"^- \*\*(.+?):\*\*\s*(.*)$", line)
                if m and m.group(1) in KEYFACTS:
                    facts.append((KEYFACTS[m.group(1)], m.group(2)))
                else:
                    keep.append(line)
            text = "\n".join(keep)
            tally = {k: len(re.findall(r"\*%s:?\*" % k, text)) for k in EVIDENCE}
            hint = " · ".join(f"{n} {k.lower()}" for k, n in tally.items() if n) or hint
        f = warn if warn and (("Problem" in warn) == head.lower().startswith("problem")) and (head.lower().startswith(("problem", "measurement"))) else ""
        folds.append((head, text, hint, f))
    facts += [(k, v) for k, v in extra if v]
    rows = "".join(f'<details class="fold-row"><summary><span class="pm" aria-hidden="true"></span><span class="fr-t">{esc(h)}</span><span class="fr-s">{esc(s)}</span>{f}</summary>'
                   f'<div class="doc">{render(t, sections=False)}</div></details>' for h, t, s, f in folds if t.strip())
    return (f'<article class="doc" hidden>{render(curated)}</article>'
            + (f'<div class="big">{render(lead, sections=False)}</div>' if lead else "")
            + (f'<dl class="kv">{"".join(f"<dt>{esc(k)}</dt><dd>{_inline(v)}</dd>" for k, v in facts)}</dl>' if facts else "")
            + f'<div class="rows folds">{rows}</div>')


def sources_tab(md):
    """The card's generated Sources table, on its own tab."""
    m = re.search(r"(?ms)^## Sources \(auto\)\s*\n(.*?)(?=^## |\Z)", md.split(MARK, 1)[1] if MARK in md else "")
    return f'<article class="doc">{render(m.group(1), sections=False)}</article>' if m else '<p class="empty">No sources linked yet.</p>'


def card_tasks(slug):
    """The owner's open tasks in this card's group on Today, filled live by app.js; hidden when there are none."""
    return f'<section class="rail-blk" id="card-tasks" data-slug="{esc(slug)}" hidden><h2>Your tasks</h2><div id="card-tasks-b"></div></section>'


_CONF = {}


def confluence_pages(docs, title, n=5):
    """The card's sources that are Confluence pages, each linking to the page itself: pages that already exist
    there (a scoping page, a design decision) were otherwise only a row among the sources. The pages named most
    like the feature come first (its own scoping page before a page that mentions it), then the newest."""
    if not _CONF:
        for p in (M / "02_digests").glob("MANTIS-DOC-*.md"):
            fm = front_matter(p.read_text(encoding="utf-8"))[0]
            if fm.get("confluence_page_id"):
                _CONF[p.stem[:15]] = (fm.get("original_title", "").strip('"'), str(fm["confluence_page_id"]).strip('"'), fm.get("generated_on", ""))
    stems = lambda t: {w.rstrip("s") for w in re.findall(r"[a-z]{4,}", t.lower())}
    want = stems(title)
    pages = sorted((_CONF[d] for d in docs if d in _CONF), key=lambda x: x[2], reverse=True)
    pages.sort(key=lambda x: -len(stems(x[0]) & want))
    site = jira_site()
    if not pages or not site:
        return ""
    rows = "".join(f'<a class="ri" href="{site}/wiki/pages/viewpage.action?pageId={esc(pid)}" target="_blank" rel="noopener"><span class="ri-v">{esc(t)}</span>'
                   f'<span class="ri-s">Open in Confluence ↗</span></a>' for t, pid, _ in pages[:n])
    more = f'<a class="ri" href="#sources"><span class="ri-s">{len(pages) - n} more on the Sources tab</span></a>' if len(pages) > n else ""
    return f'<section class="rail-blk"><h2>In Confluence</h2>{rows}{more}</section>'


def side_people(slug, kind="feature"):
    """The side column: people as initials (each opens their panel), then the systems as one line."""
    ranked = sorted(((x["docs"], e) for e in GRAPH.get("entities", []) for x in e["features"]
                     if x["slug"] == slug and x.get("kind", "feature") == kind and e["type"] not in ("concept", "unknown")), key=lambda t: -t[0])
    ppl = [e["name"] for _, e in ranked if e["type"] == "person"][:6]
    sysl = [e["name"] for _, e in ranked if e["type"] != "person"][:6]
    ini = lambda n: "".join(w[0] for w in n.split()[:2]).upper()
    return ((f'<section class="rail-blk"><h2>People</h2><span class="faces">{"".join(f"<button type=\"button\" class=\"face\" data-person=\"{esc(p)}\" title=\"{esc(p)}\">{esc(ini(p))}</button>" for p in ppl)}</span>'
             f'<p class="ri-s">{esc(", ".join(p.split()[0] for p in ppl))}</p></section>' if ppl else "")
            + (f'<section class="rail-blk"><h2>Systems</h2><p class="ri-v">{esc(" · ".join(sysl))}</p></section>' if sysl else ""))


def page_feature(f, features, epics_by_id, built):
    """A feature card (2026-10-31 redesign): the title and one line of facts, then Overview, Questions, Jira and
    Sources, with Drafts only when one exists. Refresh and the other features sit in the ⋯ menu."""
    label, cls = STATUS[f["status"]]
    switch = "".join(f'<option value="{x["slug"]}.html"{" selected" if x is f else ""}>{esc(x["title"])} · {STATUS[x["status"]][0]}</option>' for x in features if x is f or not archived(x["slug"]))
    nnew, ndocs = len(f.get("new_docs", [])), len(f.get("docs", []))
    meta = [f["priority"], label, "Platform workstream" if f["type"] == "workstream" else "",
            f'<button type="button" class="linkish copy-text" data-text="{esc(f["jira"])}" title="Copy the Jira key">{esc(f["jira"])}</button>' if f["jira"] and f["jira"] != "none" else "",
            f'<a href="#sources"{" class=\"warn-text\" title=\"Linked sources the summary does not cover yet\"" if nnew else ""}>{n_(ndocs, "source")}{f", {nnew} new" if nnew else ""}</a>',
            f'updated {esc(f["updated"])}', "Archived" if archived(f["slug"]) else ""]
    note = f'<p class="muted">{esc(f["status_note"])}</p>' if f["status_note"] else ""
    t = f["title"]
    epics = f["epics"]
    qs = feature_questions(f["slug"])
    tickets = jira_tickets(f["slug"])
    has_drafts = bool(f["page_md"] or epics or f["stories"])
    first_draft = "page" if f["page_md"] else (f'epic-{epics[0]["anchor"]}' if epics else "page")
    tabs = (f'<a href="#overview" data-match="overview">Overview</a>'
            f'<a href="#questions" data-match="questions">Questions{f" <span class=\"n\">{len(qs)}</span>" if qs else ""}</a>'
            f'<a href="#jira" data-match="jira">Jira{f" <span class=\"n\">{len(tickets)}</span>" if tickets else ""}</a>'
            f'<a href="#sources" data-match="sources">Sources <span class="n">{ndocs}</span></a>'
            + (f'<a href="#{first_draft}" data-match="page epic- story-">Drafts</a>' if has_drafts else ""))
    # Drafts: the Confluence page, the epics and the stories, one at a time, with a switcher above each
    drafts = [("page", "Confluence page", f["page_status"])] + [(f"epic-{e['anchor']}", f"Epic: {e['title']}", e["status"]) for e in epics]
    switcher = lambda here: (f'<div class="epic-switch nocopy" aria-label="Drafts">' + "".join(
        f'<a class="chip{" on" if k == here else ""}" href="#{k}">{esc(label)}</a>' for k, label, _ in drafts) + "</div>") if len(drafts) > 1 else ""
    panels = [("overview", "", overview(f["card_md"], f["slug"], [("Estimate 2027", f["estimate"])])),
              ("questions", "", questions_html(qs, "../")),
              ("jira", "", tickets_html(tickets, f.get("jira", ""))),
              ("sources", "", sources_tab(f["card_md"])),
              ("page", (copy_bar("Copy page", f["page"]) if f["page_md"] else ""),
               switcher("page") + (render(f["page_md"]) if f["page_md"] else empty("Confluence page", f"Write the Confluence page for {t}")))]
    for e in epics:
        panels.append((f"epic-{e['anchor']}", copy_bar("Copy epic", e["file"]), switcher(f"epic-{e['anchor']}") + render(e["md"], breaks=True, sections=False)))
    for s in f["stories"]:
        ep = f'<p class="muted small nocopy">Story{" in epic " + esc(s["epic_title"]) if s["epic_title"] else ", not in an epic"} · {WORK.get(s["status"], (s["status"],))[0]}</p>'
        panels.append((f"story-{s['anchor']}", copy_bar("Copy story", s["file"]), ep + render(s["md"], breaks=True, sections=False)))
    # Overview and Sources are built as page parts already; the drafts are Markdown documents in an article
    ph = "".join(f'<div class="tab-panel" id="p-{k}" hidden>{bar}{body if k in ("overview", "sources", "questions", "jira") else f"<article class=\"doc\">{body}</article>"}</div>' for k, bar, body in panels)
    done = sum(1 for s in f["stories"] if s["status"] in ("in-jira", "done"))
    nav = (f'<a class="story" href="#page" data-anchor="page"><span>Confluence page</span>{work_pill(f["page_status"]) if f["page_md"] else "<span class=\"t-meta\">not written</span>"}</a>'
           + "".join(f'<a class="story" href="#epic-{e["anchor"]}" data-anchor="epic-{e["anchor"]}"><span>{esc(e["title"])}</span>{work_pill(e["status"])}</a>' for e in epics)
           + story_list(f["stories"], epics_by_id))
    drafts = (f'<section class="rail-blk"><h2>Drafts <span class="n">{done}/{len(f["stories"])} in Jira</span></h2>{nav}</section>' if has_drafts
              else f'<section class="rail-blk"><h2>Drafts</h2><a class="ri" href="#page"><span class="ri-s">None yet. Write the page or the epic</span></a></section>')
    work = {"business": "Business", "technical": "Technical", "both": "Business and technical"}.get(f.get("work", ""), "")
    body = f"""
<p class="crumbs"><a href="../features.html">Features</a>{f"<span>/</span><span>{work}</span>" if work else ""}</p>
<div class="page-h feat-h"><div><h1>{esc(t)}</h1><p class="meta-line">{" · ".join(m for m in meta if m)}</p>{note}</div>
<div class="ph-acts nocopy"><details class="pop pop-r"><summary class="btn-line" aria-label="More">⋯</summary><div class="pop-b">
{job_btn("refresh-card", "Refresh summary", arg=f["slug"], cls="btn-line")}<select id="switch" class="sel sel-sm" aria-label="Go to another feature">{switch}</select></div></details>
<button type="button" class="btn copy-ov">Copy one-pager</button></div></div>
<div class="feat">
<div class="feat-main"><nav class="tabs" aria-label="This feature">{tabs}</nav>{ph}</div>
<aside class="side rail">{card_tasks(f["slug"])}{confluence_pages(f["docs"], f["title"])}{side_people(f["slug"])}{drafts}</aside>
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
                     + (f'<span class="t-meta">Ask {esc(o["ask"]["name"].split()[0])}</span>' if scope_of(o) == "others" else
                        '<span class="t-meta flag-info">Likely answer</span>' if o["status"] not in ("Open", "Unconfirmed") else "")
                     + "</a>")
    you = [o for o in qs if scope_of(o) == "you"]
    oth = [o for o in qs if scope_of(o) == "others"]
    return ((f'<h3 class="ag-h">For you</h3><div class="rows">' + "".join(row(o) for o in you) + "</div>" if you else "")
            + (f'<h3 class="ag-h">Waiting on others</h3><div class="rows">' + "".join(row(o) for o in oth) + "</div>" if oth else ""))


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
    qs = feature_questions(t["slug"])
    nnew = len(t.get("new_docs", []))
    meta = ["Topic", "Archived" if archived(t["slug"]) else "",
            f'<a href="#sources"{" class=\"warn-text\"" if nnew else ""}>{n_(len(t["docs"]), "source")}{f", {nnew} new" if nnew else ""}</a>', f'updated {esc(t["updated"])}']
    tabs = (f'<a href="#overview" data-match="overview">Overview</a>'
            + (f'<a href="#questions" data-match="questions">Questions <span class="n">{len(qs)}</span></a>' if qs else "")
            + f'<a href="#sources" data-match="sources">Sources <span class="n">{len(t["docs"])}</span></a>')
    body = f"""
<p class="crumbs"><a href="../features.html#all">Features</a></p>
<div class="page-h feat-h"><div><h1>{esc(t["title"])}</h1><p class="meta-line">{" · ".join(m for m in meta if m)}</p></div>
<div class="ph-acts nocopy"><details class="pop pop-r"><summary class="btn-line" aria-label="More">⋯</summary><div class="pop-b">
{job_btn("refresh-card", "Refresh summary", arg=t["slug"], cls="btn-line")}<select id="switch" class="sel sel-sm" aria-label="Go to another topic">{switch}</select></div></details>
<button type="button" class="btn copy-ov">Copy summary</button></div></div>
<div class="feat">
<div class="feat-main"><nav class="tabs" aria-label="This topic">{tabs}</nav>
<div class="tab-panel" id="p-overview">{overview(t["card_md"], t["slug"])}</div>
<div class="tab-panel" id="p-questions" hidden>{questions_html(qs, "../")}</div>
<div class="tab-panel" id="p-sources" hidden>{sources_tab(t["card_md"])}</div></div>
<aside class="side rail">{card_tasks(t["slug"])}{confluence_pages(t["docs"], t["title"])}{side_people(t["slug"], "topic") or '<p class="empty">No people or systems named yet.</p>'}</aside>
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
