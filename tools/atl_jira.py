"""Jira reads: JQL search, saved filters, a Feature with all its children, issues as Markdown, a mirror sync (MANTIS-IMP-087). Stdlib only.

Used by tools/atl.py. Every call is a GET through atl_client. Search uses /rest/api/2/search/jql,
which returns descriptions and comments as wiki text (far smaller than v3's document JSON). Only the
fields Mantis uses are requested; custom fields are named in mantis/config/atlassian.json.
Children are found level by level with `parent in (...)`, 50 keys a query, so a Feature holding
Features holding stories is walked to the bottom in a handful of calls.
"""
import json, sys

import atl_convert, atl_store

sys.dont_write_bytecode = True
BASE_FIELDS = ["summary", "status", "issuetype", "priority", "assignee", "reporter", "parent", "labels", "components",
               "fixVersions", "created", "updated", "duedate", "resolution", "description", "comment", "issuelinks",
               "subtasks", "attachment"]
MAX_ISSUES = 3000


def field_map(c):
    """Custom field id -> name, fetched once and kept in the mirror."""
    cached = atl_store.read("jira/fields.json")
    if cached:
        return json.loads(cached)
    names = {f["id"]: f["name"] for f in c.get("/rest/api/2/field")}
    atl_store.write("jira/fields.json", json.dumps(names, indent=1, ensure_ascii=False))
    return names


def search(c, jql, fields, limit=MAX_ISSUES):
    out, token = [], None
    while len(out) < limit:
        params = {"jql": jql, "fields": ",".join(fields), "maxResults": 100}
        if token:
            params["nextPageToken"] = token
        data = c.get("/rest/api/2/search/jql", params)
        out += data.get("issues", [])
        token = data.get("nextPageToken")
        if not token or data.get("isLast"):
            break
    return out[:limit]


def resolve(cfg, name_or_jql):
    """A saved query name (config 'jira_queries'), a filter ID, or JQL as given."""
    q = cfg.get("jira_queries", {}).get(name_or_jql, name_or_jql)
    return q


def jql_for(c, q):
    if isinstance(q, dict) and q.get("filter_id"):
        return c.get(f"/rest/api/2/filter/{q['filter_id']}")["jql"]
    if str(q).isdigit():
        return c.get(f"/rest/api/2/filter/{q}")["jql"]
    return q if isinstance(q, str) else q.get("jql", "")


def favourite_filters(c):
    return [{"id": f["id"], "name": f["name"], "jql": f.get("jql", "")} for f in c.get("/rest/api/2/filter/favourite")]


def _name(v):
    if isinstance(v, dict):
        return v.get("displayName") or v.get("name") or v.get("value") or v.get("key") or ""
    if isinstance(v, list):
        return ", ".join(filter(None, (_name(x) for x in v)))
    return "" if v is None else str(v)


def with_children(c, roots, fields):
    """The root issues plus every descendant, walked level by level."""
    seen = {i["key"]: i for i in roots}
    level = list(seen)
    while level and len(seen) < MAX_ISSUES:
        nxt = []
        for k in range(0, len(level), 50):
            batch = ",".join(level[k:k + 50])
            for i in search(c, f"parent in ({batch})", fields):
                if i["key"] not in seen:
                    seen[i["key"]] = i
                    nxt.append(i["key"])
        level = nxt
    return list(seen.values())


def remote_pages(c, key):
    """Confluence pages linked to an issue (the 'mentioned in' and 'linked pages' panel)."""
    out = []
    for r in c.get(f"/rest/api/2/issue/{key}/remotelink"):
        url, title = r.get("object", {}).get("url", ""), r.get("object", {}).get("title", "")
        if "confluence" in (r.get("application", {}).get("type") or "") or "/wiki/" in url:
            out.append({"title": title, "url": url})
    return out


def render(issue, names, custom, remote=()):
    f = issue["fields"]
    parent = f.get("parent") or {}
    head = [f"# {issue['key']}: {f.get('summary', '')}", ""]
    rows = [("Type", _name(f.get("issuetype"))), ("Status", _name(f.get("status"))), ("Priority", _name(f.get("priority"))),
            ("Assignee", _name(f.get("assignee")) or "Unassigned"), ("Reporter", _name(f.get("reporter"))),
            ("Parent", f"{parent.get('key')} {parent.get('fields', {}).get('summary', '')}" if parent else ""),
            ("Labels", _name(f.get("labels"))), ("Components", _name(f.get("components"))), ("Fix versions", _name(f.get("fixVersions"))),
            ("Created", (f.get("created") or "")[:10]), ("Updated", (f.get("updated") or "")[:10]), ("Due", f.get("duedate") or ""),
            ("Resolution", _name(f.get("resolution")))]
    rows += [(names.get(fid, fid), _name(f.get(fid))) for fid in custom]
    head += [f"- {k}: {v}" for k, v in rows if v]
    body = ["", "## Description", "", atl_convert.jira_to_md(f.get("description")) or "(none)"]
    links = f.get("issuelinks") or []
    if links:
        body += ["", "## Linked issues"]
        for l in links:
            other = l.get("outwardIssue") or l.get("inwardIssue") or {}
            rel = l["type"]["outward"] if "outwardIssue" in l else l["type"]["inward"]
            body.append(f"- {rel} {other.get('key')}: {other.get('fields', {}).get('summary', '')} [{_name(other.get('fields', {}).get('status'))}]")
    if remote:
        body += ["", "## Confluence pages"] + [f"- {r['title']}: {r['url']}" for r in remote]
    att = f.get("attachment") or []
    if att:
        body += ["", "## Attachments"] + [f"- {a['filename']} ({a.get('mimeType', '')}, {a.get('size', 0) // 1024} KB)" for a in att]
    comments = (f.get("comment") or {}).get("comments", [])
    if comments:
        body += ["", f"## Comments ({len(comments)})"]
        body += [f"\n**{_name(k.get('author'))}, {k.get('created', '')[:10]}:** {atl_convert.jira_to_md(k.get('body'))}" for k in comments]
    return "\n".join(head + body) + "\n"


def raw_text(issue):
    f = issue["fields"]
    return (f.get("description") or "") + "\n" + "\n".join(k.get("body", "") for k in (f.get("comment") or {}).get("comments", []))


def full_comments(c, issue):
    """Search returns a capped comment list; fetch the rest when there are more."""
    cm = issue["fields"].get("comment") or {}
    if cm.get("total", 0) > len(cm.get("comments", [])):
        data = c.get(f"/rest/api/2/issue/{issue['key']}/comment", {"maxResults": 100})
        issue["fields"]["comment"] = {"comments": data.get("comments", []), "total": data.get("total", 0)}
