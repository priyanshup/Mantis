"""What changed in Jira and Confluence since the last fetch, kept until the owner has it digested (MANTIS-IMP-092). Stdlib only.

Used by tools/atl.py (check-updates, updates, digested) and the session-start hook. No AI: code asks
each product only for what changed since the last fetch, mirrors those items, compares them with
what Mantis holds, and keeps a list of what waits for digesting until the owner says so.

    mantis/mirror/state.json
        confluence / jira:  last_fetch   when updates were last fetched (local time, minutes)
                            last_digest  when the owner last had updates digested
        pending:            confluence {page id: why}, jira {key: what changed}, kept until digested

Confluence: pages under each configured root modified since the last fetch (CQL ancestor + lastmodified),
plus pages a digest names that sit outside those roots (CQL id in (...)). A page a digest names is
diffed against the version the digest holds; a page with no digest is checked for relevance to the
roadmap cards (their own match_topics and titles), so unrelated pages are listed but not queued.
Jira: issues in the configured projects updated since the last fetch, kept when they are already in
the mirror, sit under a mirrored issue, or carry a watched component. Each is compared with its
mirrored copy (status, summary, parent, description, comments, attachments) and mapped to the card
whose Jira Feature or items it falls under.
"""
import json, re, sys
from datetime import datetime, timedelta
from pathlib import Path

import atl_client, atl_compare, atl_confluence, atl_convert, atl_jira, atl_store

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
FEATURES = ROOT / "mantis" / "knowledge" / "features"
MARGIN = timedelta(minutes=10)      # overlap with the previous fetch, so nothing on the boundary is missed
RELEVANT = 3                        # roadmap-keyword hits needed before a new page is queued


def now():
    return datetime.now().strftime("%Y-%m-%dT%H:%M")


def load_state():
    try:
        s = json.loads(atl_store.read("state.json") or "{}")
    except ValueError:
        s = {}
    for k in ("confluence", "jira"):
        s.setdefault(k, {})
    s.setdefault("pending", {}).setdefault("confluence", {})
    s["pending"].setdefault("jira", {})
    return s


def save_state(s):
    atl_store.write("state.json", json.dumps(s, indent=1, ensure_ascii=False))


def query_time(stamp):
    """'2026-10-11T13:00' minus the margin, in the 'yyyy/MM/dd HH:mm' form JQL and CQL accept."""
    return (datetime.strptime(stamp, "%Y-%m-%dT%H:%M") - MARGIN).strftime("%Y/%m/%d %H:%M")


# ------------------------------------------------------------------ roadmap relevance (from the cards)
def roadmap_terms():
    """{card slug: [phrases]} from each roadmap card's match_topics and title."""
    import frontmatter
    out = {}
    for p in FEATURES.glob("*.md"):
        if p.name == "README.md":
            continue
        fm = frontmatter.parse(p.read_text(encoding="utf-8"))
        terms = {t.replace("-", " ").lower() for t in fm.get("match_topics", []) if len(t) > 3}
        if fm.get("title"):
            terms.add(str(fm["title"]).lower())
        out[p.stem] = sorted(terms)
    return out


def relevance(text, title, terms):
    """[(card, hits)] best first; a title hit counts five times."""
    body, title = text.lower(), title.lower()
    rows = [(card, sum(body.count(t) for t in ts) + 5 * sum(title.count(t) for t in ts)) for card, ts in terms.items()]
    return sorted([r for r in rows if r[1]], key=lambda r: -r[1])


# ------------------------------------------------------------------ confluence
def _search(c, cql):
    out, start = [], 0
    while True:
        d = c.get("/rest/api/content/search", {"cql": cql, "limit": 100, "start": start, "expand": "version"})
        out += d.get("results", [])
        start += d.get("size", 0)
        if not d.get("_links", {}).get("next") or not d.get("size"):
            return out


def check_confluence(c, conf, since, log=print):
    index = atl_store.load_index("confluence")
    digests = atl_compare.load_digests()
    by_page = {v["page_id"]: d for d, v in digests.items() if v["page_id"]}
    t = query_time(since)
    hits = {}
    for label, r in conf.get("confluence_roots", {}).items():
        for x in _search(c, f'ancestor = {r["id"]} and type = page and lastmodified > "{t}"'):
            hits[x["id"]] = (label, x)
    outside = [p for p in by_page if p not in hits and index.get(p, {}).get("root") != next(iter(conf.get("confluence_roots", {})), "")]
    for k in range(0, len(outside), 40):
        ids = ",".join(outside[k:k + 40])
        for x in _search(c, f'id in ({ids}) and lastmodified > "{t}"'):
            hits[x["id"]] = (index.get(x["id"], {}).get("root", "linked"), x)
    terms, found = roadmap_terms(), []
    for pid, (label, x) in hits.items():
        new_v = x.get("version", {}).get("number")
        old = index.get(pid, {})
        if old.get("version") == new_v and atl_store.read(f"confluence/pages/{pid}.md"):
            continue                                            # already mirrored at this version
        if any(s.lower() in x["title"].lower() for s in conf.get("skip_titles", ["template"])):
            continue
        body, md, meta = atl_confluence.fetch(c, pid)
        atl_store.write(f"confluence/pages/{pid}.md", atl_confluence.render(pid, md, meta))
        index[pid] = dict(old, title=meta["title"], path=meta["path"], space=meta["space"], version=meta["version"],
                          when=meta["when"], by=meta["by"], root=old.get("root", label),
                          kind=atl_confluence.kind_of(meta["title"], md, old.get("children", 0)), chars=len(md),
                          hash=atl_store.digest(md), comments=len(meta["comments"]), attachments=len(meta["attachments"]),
                          archived=any("archive" in p.lower() for p in meta["path"]))
        row = {"title": meta["title"], "version": meta["version"], "when": meta["when"], "by": meta["by"]}
        doc = by_page.get(pid)
        if doc:
            held = digests[doc]["page_version"]
            old_md = atl_confluence.body_at(c, pid, held) if held else ""
            text, add, rem, secs = atl_compare.section_diff(old_md, md)
            atl_store.write(f"diffs/{pid}.md", f"# {meta['title']} vs {doc}\n\nPage version {held} (held by the digest) to "
                                               f"{meta['version']} ({meta['when']}, {meta['by']}). {add} line(s) added, {rem} removed.\n{text}\n")
            row.update(kind="changed", doc=doc, held=held, added=add, removed=rem, sections=secs[:8],
                       note="formatting only" if not add and not rem else "")
        elif index[pid]["kind"] != "content":
            continue                                            # a container or empty page: nothing to digest
        else:
            rel = relevance(md, meta["title"], terms)
            score = sum(h for _, h in rel)
            row.update(kind="new", cards=[c_ for c_, _ in rel[:3]], score=score, related=score >= RELEVANT)
        found.append((pid, row))
    atl_store.save_index("confluence", index)
    return found


# ------------------------------------------------------------------ jira
def _md_section(md, head):
    m = re.search(r"(?ms)^## %s\s*$(.*?)(?=^## |\Z)" % re.escape(head), md or "")
    return m.group(1).strip() if m else ""


def card_of(key, index, conf):
    """The card whose Jira Feature or items cover this issue, walking up the parent chain."""
    owners = {}
    for slug, v in conf.get("card_jira", {}).items():
        for k in ([v.get("feature")] if v.get("feature") else []) + list(v.get("items", [])):
            owners.setdefault(k, slug)
    seen = set()
    while key and key not in seen:
        if key in owners:
            return owners[key]
        seen.add(key)
        key = index.get(key, {}).get("parent")
    return None


def check_jira(c, conf, since, log=print):
    index = atl_store.load_index("jira")
    names, custom = atl_jira.field_map(c), []
    wanted = {n.lower() for n in conf.get("jira_custom_fields", [])}
    custom = [fid for fid, n in names.items() if fid.startswith("customfield_") and n.lower() in wanted]
    projects = conf.get("scope", {}).get("jira_projects", [])
    comps = {x.lower() for x in conf.get("jira_watch_components", [])}
    jql = f'project in ({",".join(projects)}) AND updated >= "{query_time(since)}" ORDER BY updated DESC'
    issues = atl_jira.search(c, jql, atl_jira.BASE_FIELDS + custom)
    found = []
    for i in issues:
        f, key = i["fields"], i["key"]
        parent = (f.get("parent") or {}).get("key")
        in_scope = key in index or (parent and parent in index) or \
            any(atl_jira._name(x).lower() in comps for x in (f.get("components") or []))
        if not in_scope:
            continue
        old = index.get(key, {})
        if old.get("updated") == f.get("updated"):
            continue
        atl_jira.full_comments(c, i)
        is_feature = atl_jira._name(f.get("issuetype")) in conf.get("jira_epic_types", ["Feature"])
        remote = atl_jira.remote_pages(c, key) if is_feature and not old else old.get("remote", [])
        md = atl_jira.render(i, names, custom, remote)
        old_md = atl_store.read(f"jira/issues/{key}.md")
        changes = []
        if not old:
            changes.append("new issue")
        else:
            st = atl_jira._name(f.get("status"))
            if st != old.get("status"):
                changes.append(f"status {old.get('status')} → {st}")
            if f.get("summary") != old.get("summary"):
                changes.append("summary changed")
            if parent != old.get("parent"):
                changes.append(f"parent {old.get('parent') or '-'} → {parent or '-'}")
            if _md_section(md, "Description") != _md_section(old_md, "Description"):
                text, add, rem, _ = atl_compare.section_diff(_md_section(old_md, "Description"), _md_section(md, "Description"))
                if add or rem:
                    changes.append(f"description +{add}/-{rem} lines")
                    atl_store.write(f"diffs/{key}.md", f"# {key}: description since the last fetch\n{text}\n")
            n_c = len((f.get("comment") or {}).get("comments", []))
            if n_c > old.get("comments", 0):
                changes.append(f"{n_c - old.get('comments', 0)} new comment(s)")
            n_a = len(f.get("attachment") or [])
            if n_a != old.get("attachments", 0):
                changes.append(f"attachments {old.get('attachments', 0)} → {n_a}")
        atl_store.write(f"jira/issues/{key}.md", md)
        links = atl_convert.links_in(atl_jira.raw_text(i) + " ".join(r["url"] for r in remote), projects)
        index[key] = {"summary": f.get("summary"), "type": atl_jira._name(f.get("issuetype")), "status": atl_jira._name(f.get("status")),
                      "parent": parent, "updated": f.get("updated"), "hash": atl_store.digest(md), "remote": remote,
                      "pages": sorted(links["pages"]), "tiny": sorted(links["tiny"]),
                      "comments": len((f.get("comment") or {}).get("comments", [])), "attachments": len(f.get("attachment") or [])}
        if changes:   # an update that changed none of the watched fields (e.g. a rank or watcher change) is not queued
            found.append((key, {"summary": f.get("summary"), "type": index[key]["type"], "status": index[key]["status"],
                                "updated": (f.get("updated") or "")[:16], "card": card_of(key, index, conf), "changes": changes}))
    atl_store.save_index("jira", index)
    return found, len(issues)


# ------------------------------------------------------------------ the check, the list, the clearing
def check(conf, log=print, quiet=False):
    """Fetch what changed since the last fetch; queue it; write the report. Returns (pages, issues) counts queued."""
    s = load_state()
    start = now()
    default = s.get("_initialised") or start
    queued = {"confluence": 0, "jira": 0}
    try:
        cc = atl_client.connect("confluence")
        pages = check_confluence(cc, conf, s["confluence"].get("last_fetch", default), log)
        for pid, row in pages:
            if row["kind"] == "changed" or row.get("related"):
                s["pending"]["confluence"][pid] = row
                queued["confluence"] += 1
        s["confluence"]["last_fetch"] = start
        s["confluence"]["calls"] = cc.calls
    except atl_client.AtlassianError as exc:
        pages = []
        log(f"Confluence check skipped: {exc}")
    try:
        jc = atl_client.connect("jira")
        issues, seen = check_jira(jc, conf, s["jira"].get("last_fetch", default), log)
        for key, row in issues:
            s["pending"]["jira"][key] = row
            queued["jira"] += 1
        s["jira"]["last_fetch"] = start
        s["jira"]["calls"] = jc.calls
    except atl_client.AtlassianError as exc:
        issues = []
        log(f"Jira check skipped: {exc}")
    save_state(s)
    write_report(s, pages, issues)
    return queued


def write_report(s, pages, issues):
    day = now()[:10]
    L = [f"# Updates waiting to digest, {now().replace('T', ' ')}", "",
         f"Confluence: last fetched {s['confluence'].get('last_fetch', '-')}, last digested {s['confluence'].get('last_digest', '-')}. "
         f"Jira: last fetched {s['jira'].get('last_fetch', '-')}, last digested {s['jira'].get('last_digest', '-')}.",
         "Nothing here is digested until the owner says so. Diffs: mantis/mirror/diffs/<page id or key>.md.", ""]
    pc, pj = s["pending"]["confluence"], s["pending"]["jira"]
    L += [f"## Confluence pages ({len(pc)} waiting)", ""]
    if pc:
        L += ["| Page | What | Detail |", "|---|---|---|"]
        for pid, r in sorted(pc.items(), key=lambda x: x[1].get("when", ""), reverse=True):
            if r["kind"] == "changed":
                what = f"changed since {r['doc']} (v{r['held']} → v{r['version']})"
                detail = r.get("note") or f"+{r['added']}/-{r['removed']} lines; {', '.join(r['sections'][:4])}"
            else:
                what = "new, roadmap-related"
                detail = f"cards: {', '.join(r['cards'])}"
            L.append(f"| {r['title']} ({pid}) | {what} | {detail} |")
    skipped = [(p, r) for p, r in pages if r["kind"] == "new" and not r.get("related")]
    if skipped:
        L += ["", f"Also changed, not roadmap-related, not queued ({len(skipped)}): " + "; ".join(r["title"] for _, r in skipped[:20])]
    L += ["", f"## Jira issues ({len(pj)} waiting)", ""]
    by_card = {}
    for key, r in pj.items():
        by_card.setdefault(r.get("card") or "(no card)", []).append((key, r))
    for card, rows in sorted(by_card.items()):
        L += [f"**{card}**", ""] + [f"- {k} {r['summary']} [{r['status']}]: {'; '.join(r['changes'])}" for k, r in sorted(rows)] + [""]
    atl_store.write(f"reports/{day}-updates.md", "\n".join(L) + "\n")


def summary_line(s=None):
    s = s or load_state()
    pc, pj = s["pending"]["confluence"], s["pending"]["jira"]
    if not pc and not pj:
        return ""
    changed = sum(1 for r in pc.values() if r["kind"] == "changed")
    cards = sorted({r.get("card") for r in pj.values() if r.get("card")})
    return (f"Jira and Confluence: {changed} digested page(s) changed and {len(pc) - changed} new roadmap page(s) in Confluence, "
            f"{len(pj)} ticket(s) changed in Jira" + (f" (cards: {', '.join(cards)})" if cards else "") +
            f", since the last digest. List: python tools/atl.py updates.")


def mark_digested(ids, source=None):
    """Clear items from the waiting list; the source's last_digest moves to now."""
    s = load_state()
    done = []
    for src in ("confluence", "jira"):
        if source and source != src:
            continue
        for k in list(s["pending"][src]):
            if ids == ["--all"] or k in ids:
                del s["pending"][src][k]
                done.append(k)
        if ids == ["--all"] or any(k in ids for k in done):
            s[src]["last_digest"] = now()
    save_state(s)
    return done
