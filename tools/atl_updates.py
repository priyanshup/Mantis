"""What changed in Jira and Confluence since the last pull, per filter (MANTIS-IMP-092, MANTIS-IMP-094). Stdlib only.

Used by tools/pull.py. No AI: code asks each product only for what changed since each filter last
ran, mirrors those items, compares them with what Mantis holds, and keeps a list of what waits for
digesting until a card pass clears it.

Filters (mantis/config/atlassian.json, "filters"): what Mantis pulls. Each has an id, a label, a type
(jira or confluence), a value, an active flag, the time it last ran and what that run found.
  jira        value is JQL (or a saved filter ID). It picks the root issues, usually Features; their
              children are followed through the mirror's parent chain, at any depth.
  confluence  value is a page ID or URL (every page under it) or CQL.
Pages Mantis has digested are always checked, wherever they sit and whatever the filters say.

    mantis/mirror/state.json
        confluence / jira:  last_fetch   when updates were last fetched (local time, minutes)
                            last_digest  when a card pass last cleared something
        pending:            confluence {page id: row}, jira {key: row}, kept until a card pass clears them
        base:               {page id: version} the version Mantis has digested up to (diffs start here)
        roots:              {filter id: {"value", "keys"}} the root issues each Jira filter selects
"""
import json, re, sys
from datetime import datetime, timedelta
from pathlib import Path

import atl_client, atl_compare, atl_confluence, atl_convert, atl_jira, atl_store

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
FEATURES = ROOT / "mantis" / "knowledge" / "features"
MARGIN = timedelta(minutes=10)      # overlap with the previous fetch, so nothing on the boundary is missed
FIRST_RUN = timedelta(days=14)      # how far back a filter that never ran looks
RELEVANT = 3                        # roadmap-keyword hits needed before a new page is queued
NOISE = {"status", "parent", "attachments"}   # Jira changes code can report without AI


def now():
    return datetime.now().strftime("%Y-%m-%dT%H:%M")


def load_state():
    try:
        s = json.loads(atl_store.read("state.json") or "{}")
    except ValueError:
        s = {}
    for k in ("confluence", "jira", "base", "roots"):
        s.setdefault(k, {})
    s.setdefault("pending", {}).setdefault("confluence", {})
    s["pending"].setdefault("jira", {})
    return s


def save_state(s):
    atl_store.write("state.json", json.dumps(s, indent=1, ensure_ascii=False))


def query_time(stamp):
    """'2026-10-11T13:00' minus the margin, in the 'yyyy/MM/dd HH:mm' form JQL and CQL accept."""
    return (datetime.strptime(stamp, "%Y-%m-%dT%H:%M") - MARGIN).strftime("%Y/%m/%d %H:%M")


def first_run():
    return (datetime.now() - FIRST_RUN).strftime("%Y-%m-%dT%H:%M")


# ------------------------------------------------------------------ filters
def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:40] or "filter"


def filters(conf):
    """The filter list, migrated on first use from the older confluence_roots and default_jira_query."""
    if "filters" not in conf:
        s, out = load_state(), []
        for name, r in conf.pop("confluence_roots", {}).items():
            out.append({"id": name, "label": r.get("note") or name, "type": "confluence", "value": str(r["id"]),
                        "active": True, "last_run": s["confluence"].get("last_fetch", ""), "last_counts": {}})
        q = conf.get("default_jira_query", "")
        jql = conf.get("jira_queries", {}).get(q, "")
        if jql:
            out.append({"id": slug(q), "label": q.replace("-", " ").capitalize(), "type": "jira",
                        "value": jql if isinstance(jql, str) else jql.get("jql", ""),
                        "active": True, "last_run": s["jira"].get("last_fetch", ""), "last_counts": {}})
            conf["jira_queries"].pop(q, None)
        conf.pop("default_jira_query", None)
        conf["filters"] = out
        atl_client.save_config(conf)
    return conf["filters"]


def tree_root(value):
    """The page ID of a Confluence filter that names a page tree, or '' when its value is CQL."""
    v = str(value).strip()
    return v if v.isdigit() else (atl_confluence.page_id(v) if "/pages/" in v or "pageId=" in v else "")


def without_order(jql):
    return re.split(r"(?i)\s+order\s+by\s+", str(jql).strip())[0].strip()


def projects_of(jql, conf):
    m = re.search(r"(?i)\bproject\s*(?:=\s*\"?([A-Z][A-Z0-9_]+)\"?|in\s*\(([^)]*)\))", jql)
    if m:
        return [m.group(1)] if m.group(1) else [p.strip(' "') for p in m.group(2).split(",") if p.strip()]
    return conf.get("scope", {}).get("jira_projects", [])


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


def page_cql(value):
    root = tree_root(value)
    return f"ancestor = {root} and type = page" if root else f"({value}) and type = page"


def check_confluence(c, conf, flts, s, log=print):
    """[(page id, row)] for pages changed under the active Confluence filters, plus digested pages anywhere."""
    index = atl_store.load_index("confluence")
    digests = atl_compare.load_digests()
    by_page = {}
    for d, v in digests.items():   # the latest digest of each page
        if v["page_id"] and (v["page_version"] or 0) >= (digests.get(by_page.get(v["page_id"]), {}).get("page_version") or 0):
            by_page[v["page_id"]] = d
    hits = {}
    for f in flts:
        for x in _search(c, f'{page_cql(f["value"])} and lastmodified > "{query_time(f.get("last_run") or first_run())}"'):
            hits[x["id"]] = (f["id"], x)
    roots = {f["id"] for f in flts if tree_root(f["value"])}
    outside = [p for p in by_page if p not in hits and index.get(p, {}).get("root") not in roots]
    since = s["confluence"].get("last_fetch") or first_run()
    for k in range(0, len(outside), 40):
        for x in _search(c, f'id in ({",".join(outside[k:k + 40])}) and lastmodified > "{query_time(since)}"'):
            hits[x["id"]] = ("digested", x)
    terms, found = roadmap_terms(), []
    for pid, (fid, x) in hits.items():
        new_v = x.get("version", {}).get("number")
        old = index.get(pid, {})
        if old.get("version") == new_v and atl_store.read(f"confluence/pages/{pid}.md") and pid not in by_page:
            continue                                            # already mirrored at this version
        if any(t.lower() in x["title"].lower() for t in conf.get("skip_titles", ["template"])):
            continue
        doc = by_page.get(pid)
        held = max(digests[doc]["page_version"] or 0, s["base"].get(pid, 0)) if doc else s["base"].get(pid, 0)
        if held and held == new_v:
            continue                                            # digested at this version already
        body, md, meta = atl_confluence.fetch(c, pid)
        atl_store.write(f"confluence/pages/{pid}.md", atl_confluence.render(pid, md, meta))
        index[pid] = dict(old, title=meta["title"], path=meta["path"], space=meta["space"], version=meta["version"],
                          when=meta["when"], by=meta["by"], root=old.get("root", fid),
                          kind=atl_confluence.kind_of(meta["title"], md, old.get("children", 0)), chars=len(md),
                          hash=atl_store.digest(md), comments=len(meta["comments"]), attachments=len(meta["attachments"]),
                          archived=any("archive" in p.lower() for p in meta["path"]))
        row = {"title": meta["title"], "version": meta["version"], "when": meta["when"], "by": meta["by"], "filter": fid}
        if doc or held:
            old_md = atl_confluence.body_at(c, pid, held) if held else ""
            text, add, rem, secs = atl_compare.section_diff(old_md, md)
            atl_store.write(f"diffs/{pid}.md", f"# {meta['title']}: version {held} to {meta['version']}\n\n"
                                               f"{meta['when']}, {meta['by']}. {add} line(s) added, {rem} removed.\n{text}\n")
            row.update(kind="changed", doc=doc or "", held=held, added=add, removed=rem, sections=secs[:8],
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
    for slug_, v in conf.get("card_jira", {}).items():
        for k in ([v.get("feature")] if v.get("feature") else []) + list(v.get("items", [])):
            owners.setdefault(k, slug_)
    seen = set()
    while key and key not in seen:
        if key in owners:
            return owners[key]
        seen.add(key)
        key = index.get(key, {}).get("parent")
    return None


def filter_of(key, parents, roots):
    """The filter whose root issues include this issue or one of its ancestors."""
    seen = set()
    while key and key not in seen:
        for fid, keys in roots.items():
            if key in keys:
                return fid
        seen.add(key)
        key = parents.get(key)
    return None


def check_jira(c, conf, flts, s, log=print):
    index = atl_store.load_index("jira")
    names = atl_jira.field_map(c)
    wanted = {n.lower() for n in conf.get("jira_custom_fields", [])}
    custom = [fid for fid, n in names.items() if fid.startswith("customfield_") and n.lower() in wanted]
    fields = atl_jira.BASE_FIELDS + custom
    comps = {x.lower() for x in conf.get("jira_watch_components", [])}
    issues, roots, projects, oldest = {}, {}, set(), None
    for f in flts:
        jql = without_order(atl_jira.jql_for(c, f["value"]))
        r = s["roots"].get(f["id"], {})
        if r.get("value") != jql:   # a new or edited filter: learn which issues it selects
            r = {"value": jql, "keys": [i["key"] for i in atl_jira.search(c, jql, ["summary"])]}
        since = f.get("last_run") or first_run()
        for i in atl_jira.search(c, f'({jql}) AND updated >= "{query_time(since)}"', fields):
            issues[i["key"]] = i
            r["keys"] = sorted(set(r["keys"]) | {i["key"]})
        s["roots"][f["id"]] = r
        roots[f["id"]] = set(r["keys"])
        projects |= set(projects_of(jql, conf))
        oldest = min(oldest or since, since)
    if projects:   # children of the roots, at any depth, found through the mirror's parent chain
        for i in atl_jira.search(c, f'project in ({",".join(sorted(projects))}) AND updated >= "{query_time(oldest)}" '
                                    f'ORDER BY updated DESC', fields):
            issues.setdefault(i["key"], i)
    parents = {k: v.get("parent") for k, v in index.items()}
    parents.update({k: (i["fields"].get("parent") or {}).get("key") for k, i in issues.items()})
    skipped = {"skip": set(conf.get("jira_skip", []))}   # items the owner skipped on Sources, with everything under them
    found = []
    for key, i in issues.items():
        f = i["fields"]
        if filter_of(key, parents, skipped):
            continue
        fid = filter_of(key, parents, roots) or \
            ("component" if any(atl_jira._name(x).lower() in comps for x in (f.get("components") or [])) else None)
        if not fid:
            continue
        old = index.get(key, {})
        if old.get("updated") == f.get("updated"):
            continue
        atl_jira.full_comments(c, i)
        is_feature = atl_jira._name(f.get("issuetype")) in conf.get("jira_epic_types", ["Feature"])
        remote = atl_jira.remote_pages(c, key) if is_feature and not old else old.get("remote", [])
        md = atl_jira.render(i, names, custom, remote)
        old_md = atl_store.read(f"jira/issues/{key}.md")
        changes, kinds = [], []
        if not old:
            changes.append("new issue")
            kinds.append("new")
        else:
            st = atl_jira._name(f.get("status"))
            parent = parents.get(key)
            if st != old.get("status"):
                changes.append(f"status {old.get('status')} → {st}")
                kinds.append("status")
            if f.get("summary") != old.get("summary"):
                changes.append("summary changed")
                kinds.append("summary")
            if parent != old.get("parent"):
                changes.append(f"parent {old.get('parent') or '-'} → {parent or '-'}")
                kinds.append("parent")
            if _md_section(md, "Description") != _md_section(old_md, "Description"):
                text, add, rem, _ = atl_compare.section_diff(_md_section(old_md, "Description"), _md_section(md, "Description"))
                if add or rem:
                    changes.append(f"description +{add}/-{rem} lines")
                    kinds.append("description")
                    atl_store.write(f"diffs/{key}.md", f"# {key}: description since the last pull\n{text}\n")
            n_c = len((f.get("comment") or {}).get("comments", []))
            if n_c > old.get("comments", 0):
                changes.append(f"{n_c - old.get('comments', 0)} new comment(s)")
                kinds.append("comments")
            n_a = len(f.get("attachment") or [])
            if n_a != old.get("attachments", 0):
                changes.append(f"attachments {old.get('attachments', 0)} → {n_a}")
                kinds.append("attachments")
        atl_store.write(f"jira/issues/{key}.md", md)
        links = atl_convert.links_in(atl_jira.raw_text(i) + " ".join(r["url"] for r in remote),
                                     conf.get("scope", {}).get("jira_projects", []) or sorted(projects))
        index[key] = {"summary": f.get("summary"), "type": atl_jira._name(f.get("issuetype")), "status": atl_jira._name(f.get("status")),
                      "parent": parents.get(key), "updated": f.get("updated"), "hash": atl_store.digest(md), "remote": remote,
                      "pages": sorted(links["pages"]), "tiny": sorted(links["tiny"]),
                      "comments": len((f.get("comment") or {}).get("comments", [])), "attachments": len(f.get("attachment") or [])}
        if changes:   # an update that changed none of the watched fields (e.g. a rank or watcher change) is not queued
            found.append((key, {"summary": f.get("summary"), "type": index[key]["type"], "status": index[key]["status"],
                                "updated": (f.get("updated") or "")[:16], "card": card_of(key, index, conf), "filter": fid,
                                "changes": changes, "kinds": kinds,
                                "new_comments": max(0, index[key]["comments"] - old.get("comments", 0)) if old else 0}))
    atl_store.save_index("jira", index)
    return found


# ------------------------------------------------------------------ the check
def check(conf, log=print):
    """Fetch what changed under the active filters; queue it. Returns {"confluence": [...], "jira": [...]} rows found."""
    s = load_state()
    start = now()
    fl = filters(conf)
    active = {t: [f for f in fl if f.get("active") and f["type"] == t] for t in ("confluence", "jira")}
    got = {"confluence": [], "jira": []}
    for typ, fn in (("confluence", check_confluence), ("jira", check_jira)):
        try:
            c = atl_client.connect(typ)
            got[typ] = fn(c, conf, active[typ], s, log)
            s[typ]["last_fetch"], s[typ]["calls"] = start, c.calls
        except atl_client.AtlassianError as exc:
            log(f"{typ.title()} skipped: {exc}")
            continue
        for k, row in got[typ]:
            if typ == "jira" or row["kind"] == "changed" or row.get("related"):
                s["pending"][typ][k] = row
        for f in active[typ]:
            mine = [r for _, r in got[typ] if r.get("filter") == f["id"]]
            f["last_run"] = start
            f["last_counts"] = {"new": sum(1 for r in mine if r.get("kind") == "new" or "new" in r.get("kinds", [])),
                                "changed": sum(1 for r in mine if r.get("kind") == "changed" or (r.get("kinds") and "new" not in r["kinds"]))}
    save_state(s)
    atl_client.save_config(conf)
    return got


def mark_digested(ids, source=None):
    """Clear items from the waiting list; a page's digested version becomes the base its next diff starts from."""
    s = load_state()
    done = []
    for src in ("confluence", "jira"):
        if source and source != src:
            continue
        for k in list(s["pending"][src]):
            if ids == ["--all"] or k in ids:
                row = s["pending"][src].pop(k)
                if src == "confluence" and row.get("version"):
                    s["base"][k] = row["version"]
                done.append(k)
        if done:
            s[src]["last_digest"] = now()
    save_state(s)
    return done
