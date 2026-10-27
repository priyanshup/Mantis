"""Jira and Confluence, read-only: fetch, mirror and compare with what Mantis already holds (MANTIS-IMP-087). Stdlib only.

    python tools/atl.py login                         check both keys (prints who you are, never the token)
    python tools/atl.py filters                       your starred Jira filters, saved by name in the config
    python tools/atl.py jira <query name | JQL>       list matching issues, one line each (nothing saved)
    python tools/atl.py issue <KEY> [...]             issues as Markdown, saved to the mirror
    python tools/atl.py page <url | id> [...]         pages as Markdown, saved to the mirror
    python tools/atl.py tree <filter | url | id>      outline of a folder or page tree, titles only
    python tools/atl.py sync-confluence [filter] [--refresh]   mirror every page under a Confluence filter's tree
                                                      whose version changed (--refresh: every page, after a converter fix)
    python tools/atl.py compare                       mirrored pages against digests: same, changed, related, new
    python tools/atl.py sync-jira [filter | query]    a query's issues with all their children, plus linked pages
                                                      (default: the first active Jira filter)
    python tools/atl.py attachments <url | id> ... | --digested   download page images and diagram previews
    python tools/atl.py summary                       the counts from the last compare and sync-jira

Keys: mantis/config/.env. Filters, saved queries and fields: mantis/config/atlassian.json. Output:
mantis/mirror/ (see atl_store.py); reports in mantis/mirror/reports/. Nothing here writes to Jira or
Confluence. These are the bulk and one-off reads; the everyday "what changed" is tools/pull.py.
"""
import datetime, json, sys

import atl_client, atl_compare, atl_confluence, atl_jira, atl_media, atl_store, atl_updates

sys.dont_write_bytecode = True
TODAY = datetime.date.today().isoformat()


def cfg():
    return atl_client.load_config()


def say(msg):
    print(msg, flush=True)


def jira_fields(c, conf):
    names = atl_jira.field_map(c)
    wanted = {n.lower() for n in conf.get("jira_custom_fields", [])}
    custom = [fid for fid, n in names.items() if fid.startswith("customfield_") and n.lower() in wanted]
    return names, custom


def root_id(conf, value):
    """A Confluence filter (by id or label) that names a page tree, or a page URL or ID as given."""
    roots = [f for f in atl_updates.filters(conf) if f["type"] == "confluence" and atl_updates.tree_root(f["value"])]
    r = next((f for f in roots if value in (f["id"], f["label"])), None) if value else (roots[0] if roots else None)
    return (r["id"], atl_updates.tree_root(r["value"])) if r else (value, atl_confluence.page_id(value))


def jira_query(conf, value):
    """A Jira filter (by id or label), a saved query name, a filter ID, or JQL; empty: the first active Jira filter."""
    fl = [f for f in atl_updates.filters(conf) if f["type"] == "jira"]
    r = next((f for f in fl if value in (f["id"], f["label"])), None) if value else \
        next((f for f in fl if f.get("active")), None)
    return r["value"] if r else atl_jira.resolve(conf, value)


# ------------------------------------------------------------------ simple commands
def cmd_login(_):
    for p in ("jira", "confluence"):
        try:
            c = atl_client.connect(p)
            say(f"{p.title()}: logged in as {c.user} ({'API gateway' if 'api.atlassian.com' in c.base else 'site URL'})")
        except atl_client.AtlassianError as exc:
            say(f"{p.title()}: {exc}")


def cmd_filters(_):
    c, conf = atl_client.connect("jira"), cfg()
    q = conf.setdefault("jira_queries", {})
    for f in atl_jira.favourite_filters(c):
        q[f["name"]] = {"filter_id": f["id"], "jql": f["jql"]}
        say(f"{f['name']}  (filter {f['id']}): {f['jql']}")
    atl_client.save_config(conf)
    say(f"Saved. Run one with: python tools/atl.py jira \"<name>\"")


def cmd_jira(args):
    c, conf = atl_client.connect("jira"), cfg()
    jql = atl_jira.jql_for(c, jira_query(conf, " ".join(args)))
    issues = atl_jira.search(c, jql, ["summary", "status", "issuetype", "assignee", "updated", "parent"])
    say(f"JQL: {jql}\n{len(issues)} issue(s)\n")
    for i in issues:
        f = i["fields"]
        say(f"{i['key']:<10} {atl_jira._name(f.get('issuetype')):<12} {atl_jira._name(f.get('status')):<14} "
            f"{(f.get('updated') or '')[:10]}  {(f.get('summary') or '')[:80]}")


def cmd_issue(args):
    c, conf = atl_client.connect("jira"), cfg()
    names, custom = jira_fields(c, conf)
    for i in atl_jira.search(c, f"key in ({','.join(args)})", atl_jira.BASE_FIELDS + custom):
        atl_jira.full_comments(c, i)
        p = atl_store.write(f"jira/issues/{i['key']}.md", atl_jira.render(i, names, custom, atl_jira.remote_pages(c, i["key"])))
        say(f"{i['key']}: {p.relative_to(atl_store.ROOT)}")


def cmd_page(args):
    c, conf = atl_client.connect("confluence"), cfg()
    for a in args:
        pid = atl_confluence.page_id(a)
        e = atl_confluence.fetch_one(c, pid, conf.get("scope", {}).get("confluence_spaces"))
        say(f"{e['title']} ({e['kind']}): mantis/mirror/confluence/pages/{pid}.md")


def cmd_tree(args):
    c, conf = atl_client.connect("confluence"), cfg()
    _, rid = root_id(conf, " ".join(args))
    nodes = atl_confluence.tree(c, rid)

    def walk(nid, depth):
        n = nodes[nid]
        say(f"{'  ' * depth}{'[folder] ' if n['type'] == 'folder' else ''}{n['title']}  (v{n['version']}, {n['when']})")
        for k, m in sorted(nodes.items(), key=lambda x: x[1]["title"]):
            if m["parent"] == nid:
                walk(k, depth + 1)
    walk(rid, 0)
    say(f"\n{sum(1 for n in nodes.values() if n['type'] == 'page')} pages, "
        f"{sum(1 for n in nodes.values() if n['type'] == 'folder')} folders, {c.calls} calls")


# ------------------------------------------------------------------ confluence sync and compare
def cmd_sync_confluence(args):
    c, conf = atl_client.connect("confluence"), cfg()
    refresh = "--refresh" in args
    label, rid = root_id(conf, " ".join(a for a in args if a != "--refresh"))
    say(f"Mirroring the tree under {label} ({rid}){', fetching every page again' if refresh else ''}")
    counts = atl_confluence.sync(c, rid, label, conf.get("skip_titles", ["template"]), log=say, refresh=refresh)
    say(f"{counts['pages']} pages in {counts['folders']} folders: {counts['fetched']} fetched, "
        f"{counts['unchanged']} unchanged, {counts['skipped']} skipped (templates). {c.calls} calls.")


def cmd_compare(_):
    index, digests = atl_store.load_index("confluence"), atl_compare.load_digests()
    matches = atl_compare.match_all(index, digests, log=say)
    # A matched page is checked against its own history only when it was edited after our snapshot:
    # a page last edited before it cannot have changed, whatever the text comparison says.
    edited = []
    for pid, m in matches.items():
        if m["verdict"] not in ("same", "changed"):
            continue
        if m.get("linked"):
            if m["verdict"] == "same":
                m["how"] = f"page version {m['version_then']} is the one the digest holds"
            else:
                edited.append(pid)
            continue
        snap = digests[m["doc"]]["snapshot"]
        if index[pid].get("when", "") <= snap:
            m.update(verdict="same", how=f"page not edited since our copy of {snap}")
        else:
            edited.append(pid)
    for old in (atl_store.MIRROR / "diffs").glob("*.md"):
        old.unlink()
    c = atl_client.connect("confluence") if edited else None
    say(f"Diffing {len(edited)} page(s) edited after Mantis took its copy")
    for pid in edited:
        m, e, d = matches[pid], index[pid], digests[matches[pid]["doc"]]
        if m.get("linked"):
            at = m["version_then"]
        else:
            try:
                vers = atl_confluence.versions(c, pid)
            except atl_client.AtlassianError:
                vers = []
            at = next((n for n, when in vers if when <= d["snapshot"]), None)
        m["version_then"], m["version_now"] = at, e.get("version")
        m["verdict"] = "changed"
        if at and at == e.get("version"):
            m.update(verdict="same", how=f"page not edited since our copy of {d['snapshot']}")
            continue
        if at:
            old = atl_confluence.body_at(c, pid, at)
            text, add, rem, secs = atl_compare.section_diff(old, atl_compare.page_body(pid))
            m["how"] = f"page edited since our copy (v{at} on {d['snapshot']} to v{e.get('version')} on {e.get('when')})"
        else:
            m["how"] = f"the page has no version as old as our copy of {d['snapshot']}; compared with our copy's text"
            text, add, rem, secs = atl_compare.section_diff(atl_compare.source_text(m["doc"], d["source_file"]),
                                                            atl_compare.page_body(pid))
        m.update(added=add, removed=rem, sections=secs[:12])
        if not add and not rem:
            m.update(verdict="same", how=m["how"] + ", formatting only")
            continue
        atl_store.write(f"diffs/{pid}.md", f"# {e['title']} vs {m['doc']}\n\n{m['how']}. "
                                           f"{add} line(s) added, {rem} removed.\n{text}\n")
    atl_store.write("confluence/matches.json", json.dumps(matches, indent=1, ensure_ascii=False))
    write_confluence_report(index, matches, digests)
    summary_confluence(index, matches)
    if c:
        say(f"{c.calls} calls.")


def write_confluence_report(index, matches, digests):
    pages = {p: e for p, e in index.items() if not p.startswith("_")}
    L = [f"# Confluence pages compared with Mantis, {TODAY}", "",
         "Made by code (tools/atl.py compare). Nothing has been digested. Diffs: mantis/mirror/diffs/<page id>.md.", ""]
    for verdict, head in (("changed", "Changed since Mantis took its copy"), ("new", "New: no digest matches"),
                          ("check", "Check: same title as a digest, different content"),
                          ("related", "Related: overlaps a source, no clear match"), ("same", "Same as the Mantis copy")):
        rows = sorted((p for p, m in matches.items() if m["verdict"] == verdict),
                      key=lambda p: (pages[p].get("archived", False), " / ".join(pages[p]["path"]), pages[p]["title"]))
        L += [f"## {head} ({len(rows)})", ""]
        if not rows:
            continue
        L += ["| Page | Where | Updated | Mantis doc | Match | Detail |", "|---|---|---|---|---|---|"]
        for p in rows:
            e, m = pages[p], matches[p]
            where = ("archive: " if e.get("archived") else "") + " / ".join(e["path"][-2:])
            detail = ""
            if verdict == "changed":
                detail = f"+{m.get('added', 0)} / -{m.get('removed', 0)} lines; {', '.join(m.get('sections', [])[:4])}"
            elif verdict in ("new", "check", "related"):
                detail = f"{e.get('chars', 0)} chars, {e.get('comments', 0)} comments, {e.get('images', 0)} images"
            elif m.get("how"):
                detail = m["how"]
            L.append(f"| {e['title']} ({p}) | {where} | {e.get('when', '')} | {m.get('doc') or '-'} "
                     f"| cover {m['cover']}, back {m['back']}, title {m['title_score']} | {detail} |")
        L.append("")
    kinds = {}
    for e in pages.values():
        kinds[e.get("kind", "?")] = kinds.get(e.get("kind", "?"), 0) + 1
    L += ["## Not compared", "", ", ".join(f"{v} {k}" for k, v in sorted(kinds.items()) if k != "content") +
          " (containers have no text of their own; templates and out-of-scope pages are skipped)."]
    atl_store.write(f"reports/{TODAY}-confluence.md", "\n".join(L) + "\n")


def summary_confluence(index, matches):
    by = {}
    for p, m in matches.items():
        key = (m["verdict"], bool(index[p].get("archived")))
        by[key] = by.get(key, 0) + 1
    say("\nConfluence (content pages):")
    for v in ("same", "changed", "check", "related", "new"):
        say(f"  {v:<8} {by.get((v, False), 0):>4} current, {by.get((v, True), 0):>4} in the archive")
    say(f"Report: mantis/mirror/reports/{TODAY}-confluence.md")


# ------------------------------------------------------------------ jira sync
def mantis_keys(project_keys):
    import re
    keys = set()
    pat = re.compile(r"\b((?:%s)-\d+)\b" % "|".join(project_keys))
    for folder in ("02_digests", "knowledge", "outputs"):
        for p in (atl_store.ROOT / "mantis" / folder).rglob("*.md"):
            if "map" in p.parts:
                continue
            keys |= set(pat.findall(p.read_text(encoding="utf-8", errors="replace")))
    return keys


def cmd_sync_jira(args):
    c, conf = atl_client.connect("jira"), cfg()
    jql = atl_jira.jql_for(c, jira_query(conf, " ".join(args)))
    names, custom = jira_fields(c, conf)
    fields = atl_jira.BASE_FIELDS + custom
    say(f"JQL: {jql}")
    roots = atl_jira.search(c, jql, fields)
    issues = atl_jira.with_children(c, roots, fields)
    say(f"{len(roots)} root issue(s), {len(issues)} with all children ({c.calls} calls)")
    index = atl_store.load_index("jira")
    projects = conf.get("scope", {}).get("jira_projects", ["CUD"])
    stats = {"new": 0, "updated": 0, "unchanged": 0}
    page_refs, tiny = {}, set()
    for n, i in enumerate(issues, 1):
        f, key = i["fields"], i["key"]
        old = index.get(key, {})
        is_feature = atl_jira._name(f.get("issuetype")) in conf.get("jira_epic_types", ["Feature"])
        if old.get("updated") == f.get("updated") and atl_store.read(f"jira/issues/{key}.md"):
            stats["unchanged"] += 1
            remote = old.get("remote", [])
        else:
            atl_jira.full_comments(c, i)
            remote = atl_jira.remote_pages(c, key) if is_feature else []
            md = atl_jira.render(i, names, custom, remote)
            atl_store.write(f"jira/issues/{key}.md", md)
            stats["updated" if old else "new"] += 1
            links = atl_jira.atl_convert.links_in(atl_jira.raw_text(i) + " ".join(r["url"] for r in remote), projects)
            old = {"summary": f.get("summary"), "type": atl_jira._name(f.get("issuetype")), "status": atl_jira._name(f.get("status")),
                   "parent": (f.get("parent") or {}).get("key"), "updated": f.get("updated"), "hash": atl_store.digest(md),
                   "remote": remote, "pages": sorted(links["pages"]), "tiny": sorted(links["tiny"]),
                   "comments": len((f.get("comment") or {}).get("comments", [])), "attachments": len(f.get("attachment") or [])}
        index[key] = old
        for pid in old.get("pages", []):
            page_refs.setdefault(pid, set()).add(key)
        tiny |= set(old.get("tiny", []))
        if n % 100 == 0:
            say(f"  {n}/{len(issues)} issues ({c.calls} calls)")
            atl_store.save_index("jira", index)
    atl_store.save_index("jira", index)

    # Confluence pages the tickets link to: digested ones are left alone, new ones are fetched.
    cidx = atl_store.load_index("confluence")
    try:
        matches = json.loads(atl_store.read("confluence/matches.json") or "{}")
    except ValueError:
        matches = {}
    cap = conf.get("max_linked_pages", 60)
    to_fetch = [p for p in page_refs if p not in cidx][:cap]
    cc = atl_client.connect("confluence") if to_fetch else None
    for pid in to_fetch:
        try:
            atl_confluence.fetch_one(cc, pid, conf.get("scope", {}).get("confluence_spaces"))
        except atl_client.AtlassianError as exc:
            cidx_e = atl_store.load_index("confluence")
            cidx_e[pid] = {"title": "(no access)" if " 403 " in f" {exc}" else "(could not read)", "kind": "no access" if " 403 " in f" {exc}" else "unreadable", "error": str(exc)[:120], "path": [], "root": "linked from Jira"}
            atl_store.save_index("confluence", cidx_e)
    if to_fetch:
        cidx = atl_store.load_index("confluence")
        fresh = {p: cidx[p] for p in to_fetch if p in cidx}
        matches.update(atl_compare.match_all(fresh, atl_compare.load_digests(), log=say))
        atl_store.write("confluence/matches.json", json.dumps(matches, indent=1, ensure_ascii=False))
    write_jira_report(jql, roots, issues, index, page_refs, tiny, cidx, matches, projects, stats, len(page_refs) - len(to_fetch) if len(page_refs) > cap else 0)
    say(f"Issues: {stats['new']} new to the mirror, {stats['updated']} updated, {stats['unchanged']} unchanged. "
        f"{c.calls + (cc.calls if cc else 0)} calls.")
    say(f"Report: mantis/mirror/reports/{TODAY}-jira.md")


def page_status(pid, cidx, matches):
    e, m = cidx.get(pid), matches.get(pid, {})
    if not e:
        return "not fetched (over the cap)"
    if e.get("kind") == "out of scope":
        return f"out of scope (space {e.get('space')})"
    if e.get("kind") in ("container", "empty", "template", "unreadable", "no access"):
        return e["kind"]
    return {"same": "already digested", "changed": "digested, page changed since", "related": "partly covered",
            "check": "a digest has the same title, different content", "new": "new, not in Mantis"}.get(m.get("verdict"), "fetched, not compared")


def write_jira_report(jql, roots, issues, index, page_refs, tiny, cidx, matches, projects, stats, over_cap):
    known = mantis_keys(projects)
    keys = [i["key"] for i in issues]
    types, statuses = {}, {}
    for k in keys:
        types[index[k]["type"]] = types.get(index[k]["type"], 0) + 1
    root_keys = [r["key"] for r in roots]
    L = [f"# Jira compared with Mantis, {TODAY}", "", f"Query: `{jql}`", "",
         "Made by code (tools/atl.py sync-jira). Nothing has been digested. Issues: mantis/mirror/jira/issues/<KEY>.md.", "",
         f"{len(root_keys)} Features, {len(keys)} issues with all their children: " +
         ", ".join(f"{v} {k}" for k, v in sorted(types.items(), key=lambda x: -x[1])) + ".",
         f"Mirror: {stats['new']} new, {stats['updated']} updated, {stats['unchanged']} unchanged since the last sync.", ""]

    def kids(k):
        return [x for x in keys if index[x].get("parent") == k]

    def count_desc(k):
        n = 0
        for x in kids(k):
            n += 1 + count_desc(x)
        return n

    L += ["## Features", "", "| Feature | Status | Children | In Mantis | Confluence pages linked |", "|---|---|---|---|---|"]
    for k in sorted(root_keys, key=lambda x: (x not in known, x)):
        e = index[k]
        pages = [f"{cidx.get(p, {}).get('title', p)}: {page_status(p, cidx, matches)}" for p in e.get("pages", [])]
        L.append(f"| {k} {e['summary']} | {e['status']} | {count_desc(k)} | {'yes' if k in known else 'no'} | {'; '.join(pages) or '-'} |")
    child_known = sum(1 for k in keys if k not in root_keys and k in known)
    L += ["", f"Children Mantis already mentions: {child_known} of {len(keys) - len(root_keys)}.", ""]
    by = {}
    for p in page_refs:
        by.setdefault(page_status(p, cidx, matches), []).append(p)
    L += ["## Confluence pages linked from these issues", ""]
    for st, ps in sorted(by.items(), key=lambda x: -len(x[1])):
        L.append(f"- **{st}** ({len(ps)}): " + "; ".join(f"{cidx.get(p, {}).get('title', p)} ({', '.join(sorted(page_refs[p])[:3])})" for p in ps[:25]))
    if tiny:
        L.append(f"- **short links not followed** ({len(tiny)}): /wiki/x/ links cannot be resolved without a search permission")
    if over_cap:
        L.append(f"- **not fetched, over the per-run cap** ({over_cap}); run sync-jira again to take the next batch")
    atl_store.write(f"reports/{TODAY}-jira.md", "\n".join(L) + "\n")
    in_m = sum(1 for k in root_keys if k in known)
    say(f"\nJira: {len(root_keys)} Features ({in_m} mentioned in Mantis, {len(root_keys) - in_m} not), {len(keys)} issues in all.")
    for st, ps in sorted(by.items(), key=lambda x: -len(x[1])):
        say(f"  linked pages, {st}: {len(ps)}")


def cmd_attachments(args):
    """Images and diagram previews of the named pages, or of every page a digest names (--digested)."""
    c = atl_client.connect("confluence")
    if "--digested" in args:
        pids = [d["page_id"] for d in atl_compare.load_digests().values() if d["page_id"]]
    else:
        pids = [atl_confluence.page_id(a) for a in args]
    idx = atl_media.load()
    totals = [0, 0, 0]
    for pid in pids:
        try:
            got = atl_media.fetch_page(c, pid, idx)
        except atl_client.AtlassianError as exc:
            say(f"{pid}: {exc}")
            continue
        totals = [t + g for t, g in zip(totals, got)]
    atl_media.save(idx)
    say(f"{len(pids)} page(s): {totals[0]} downloaded, {totals[1]} already had, {totals[2]} skipped "
        f"(not an image, temporary or too large). {c.calls} calls. Files: mantis/mirror/attachments/")


def cmd_summary(_):
    index = atl_store.load_index("confluence")
    matches = json.loads(atl_store.read("confluence/matches.json") or "{}")
    if matches:
        summary_confluence(index, {p: m for p, m in matches.items() if p in index})
    j = atl_store.load_index("jira")
    if j:
        say(f"\nJira mirror: {len(j)} issues, {sum(1 for e in j.values() if e.get('type') == 'Feature')} Features.")


COMMANDS = {"login": cmd_login, "filters": cmd_filters, "jira": cmd_jira, "issue": cmd_issue, "page": cmd_page,
            "tree": cmd_tree, "sync-confluence": cmd_sync_confluence, "compare": cmd_compare,
            "sync-jira": cmd_sync_jira, "attachments": cmd_attachments, "summary": cmd_summary}


def main(argv):
    sys.stdout.reconfigure(errors="replace")
    if not argv or argv[0] not in COMMANDS:
        print(__doc__)
        return 1
    try:
        COMMANDS[argv[0]](argv[1:])
    except atl_client.AtlassianError as exc:
        print(f"Error: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
