"""The feature card page, and the helpers a card shares with the topic page."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import re
from pagebuild.day import qkey, scope_of, topic_text, yours
from pagebuild.frame import _sections, copy_bar, empty, job_btn, shell
from pagebuild.labels import STATUS, WORK, work_pill
from pagebuild.loaders import jira_site, story_list
from pagebuild.markup import plain, render
from pagebuild.paths import M
from pagebuild.registry import FOCUS, GRAPH, OPEN, READY, archived, on_roadmap
from pagebuild.text import esc, front_matter, n_


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
    return shell(t, body, base="../", active="features", built=built, kind="feature")


def feature_questions(slug):
    mine = [o for o in yours() if slug in o.get("features", [])]
    return mine + [o for o in OPEN if slug in o.get("features", []) and scope_of(o) == "others"]


def questions_html(qs, base):
    """A feature's open questions, each linking to where it is answered (the Questions page)."""
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
