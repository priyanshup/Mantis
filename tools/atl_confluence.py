"""Confluence reads: a folder or page tree, one page as Markdown, its old versions, and a mirror sync (MANTIS-IMP-087). Stdlib only.

Used by tools/atl.py. Every call is a GET through atl_client. The whole tree under a root comes from
/descendant (200 items a call, each with its ancestors), so listing 500 pages takes a few calls.
A page body is fetched only when its version differs from the mirror's.
"""
import re, sys

import atl_convert, atl_store

sys.dont_write_bytecode = True
CONTAINER_CHARS = 120     # a page with less text than this and child pages is a container


def page_id(value):
    """A page or folder ID from a URL (/pages/<id>, /folder/<id>, pageId=<id>) or a bare ID."""
    m = re.search(r"/(?:pages|folder|folders)/(\d+)", value) or re.search(r"pageId=(\d+)", value)
    return m.group(1) if m else value.strip()


def _all(c, path, params):
    out, start = [], 0
    while True:
        data = c.get(path, dict(params, start=start))
        out += data.get("results", [])
        start += data.get("size", 0)
        if not data.get("_links", {}).get("next") or not data.get("size"):
            return out


def tree(c, root):
    """Every page and folder under root: {id: {title, type, parent, path, version, when}}."""
    head = c.get(f"/rest/api/content/{root}", {"expand": "version,ancestors"})
    nodes = {root: {"title": head["title"], "type": head["type"], "parent": None, "path": [],
                    "version": head.get("version", {}).get("number"), "when": head.get("version", {}).get("when", "")[:10]}}
    for kind in ("page", "folder"):
        for r in _all(c, f"/rest/api/content/{root}/descendant/{kind}", {"expand": "version,ancestors", "limit": 200}):
            anc = [a for a in r.get("ancestors", [])]
            ids = [a["id"] for a in anc]
            below = anc[ids.index(root) + 1:] if root in ids else anc
            nodes[r["id"]] = {"title": r["title"], "type": r["type"], "parent": anc[-1]["id"] if anc else None,
                              "path": [a["title"] for a in below], "version": r.get("version", {}).get("number"),
                              "when": r.get("version", {}).get("when", "")[:10]}
    for nid, n in nodes.items():
        n["children"] = sum(1 for m in nodes.values() if m["parent"] == nid)
    return nodes


def fetch(c, pid):
    """One page with its comments and attachment list: (raw storage body, rendered Markdown, meta)."""
    p = c.get(f"/rest/api/content/{pid}", {"expand": "body.storage,version,space,ancestors,metadata.labels,"
                                                     "children.comment.body.storage,children.comment.version,children.attachment"})
    comments = p.get("children", {}).get("comment", {})
    items = comments.get("results", [])
    if comments.get("size", 0) >= comments.get("limit", 25):
        items = _all(c, f"/rest/api/content/{pid}/child/comment", {"expand": "body.storage,version", "depth": "all", "limit": 50})
    attach = p.get("children", {}).get("attachment", {}).get("results", [])
    body = p.get("body", {}).get("storage", {}).get("value", "")
    meta = {"title": p["title"], "space": p.get("space", {}).get("key", ""), "version": p.get("version", {}).get("number"),
            "when": p.get("version", {}).get("when", "")[:10], "by": p.get("version", {}).get("by", {}).get("displayName", ""),
            "path": [a["title"] for a in p.get("ancestors", [])], "labels": [l["name"] for l in p.get("metadata", {}).get("labels", {}).get("results", [])],
            "comments": [{"by": k.get("version", {}).get("by", {}).get("displayName", ""), "when": k.get("version", {}).get("when", "")[:10],
                          "text": atl_convert.storage_to_md(k.get("body", {}).get("storage", {}).get("value", ""))} for k in items],
            "attachments": [{"name": a["title"], "type": a.get("extensions", {}).get("mediaType", ""), "size": a.get("extensions", {}).get("fileSize", 0)} for a in attach],
            "links": atl_convert.links_in(body + "".join(k.get("body", {}).get("storage", {}).get("value", "") for k in items))}
    return body, atl_convert.storage_to_md(body), meta


def render(pid, md, meta):
    lines = [f"# {meta['title']}", "",
             f"Page {pid} · space {meta['space']} · version {meta['version']} · updated {meta['when']} by {meta['by']}",
             f"Path: {' / '.join(meta['path']) or '-'}"]
    if meta["labels"]:
        lines.append("Labels: " + ", ".join(meta["labels"]))
    if meta["attachments"]:
        lines.append("Attachments: " + "; ".join(f"{a['name']} ({a['type']}, {a['size'] // 1024} KB)" for a in meta["attachments"]))
    lines += ["", "---", "", md or "(empty page)"]
    if meta["comments"]:
        lines += ["", "---", "", f"## Comments ({len(meta['comments'])})"]
        lines += [f"\n**{k['by']}, {k['when']}:** {k['text']}" for k in meta["comments"]]
    return "\n".join(lines) + "\n"


def versions(c, pid):
    """[(number, date)] newest first."""
    return [(v["number"], v.get("when", "")[:10]) for v in _all(c, f"/rest/api/content/{pid}/version", {"limit": 200})]


def body_at(c, pid, number):
    p = c.get(f"/rest/api/content/{pid}", {"status": "historical", "version": number, "expand": "body.storage"})
    return atl_convert.storage_to_md(p.get("body", {}).get("storage", {}).get("value", ""))


def kind_of(title, md, children):
    if re.search(r"template", title, re.I):
        return "template"
    if len(re.sub(r"\s+", "", md)) < CONTAINER_CHARS:
        return "container" if children else "empty"
    return "content"


def sync(c, root, label, skip_titles=(), log=print, refresh=False):
    """Mirror every page under root whose version changed (every page with refresh). Returns counts."""
    nodes = tree(c, root)
    index = atl_store.load_index("confluence")
    counts = {"pages": 0, "folders": 0, "fetched": 0, "unchanged": 0, "skipped": 0}
    pages = [(i, n) for i, n in nodes.items() if n["type"] == "page"]
    counts["folders"] = sum(1 for n in nodes.values() if n["type"] == "folder")
    for i, (pid, n) in enumerate(pages, 1):
        counts["pages"] += 1
        old = index.get(pid, {})
        entry = dict(old, title=n["title"], path=n["path"], parent=n["parent"], children=n["children"], root=label,
                     archived=any("archive" in t.lower() for t in n["path"]))
        if any(s.lower() in n["title"].lower() for s in skip_titles):
            entry.update(kind="template", version=n["version"], when=n["when"])
            counts["skipped"] += 1
        elif not refresh and old.get("version") == n["version"] and atl_store.read(f"confluence/pages/{pid}.md"):
            counts["unchanged"] += 1
        else:
            body, md, meta = fetch(c, pid)
            atl_store.write(f"confluence/pages/{pid}.md", render(pid, md, meta))
            entry.update(version=meta["version"], when=meta["when"], by=meta["by"], space=meta["space"],
                         kind=kind_of(n["title"], md, n["children"]), chars=len(md), hash=atl_store.digest(md),
                         comments=len(meta["comments"]), attachments=len(meta["attachments"]),
                         images=sum(1 for a in meta["attachments"] if a["type"].startswith("image/")),
                         links={k: sorted(map(str, v)) for k, v in meta["links"].items() if v})
            counts["fetched"] += 1
            if i % 25 == 0:
                log(f"  {i}/{len(pages)} pages ({c.calls} calls)")
                atl_store.save_index("confluence", index)
        index[pid] = entry
    for fid, n in nodes.items():
        if n["type"] == "folder":
            index.setdefault("_folders", {})[fid] = {"title": n["title"], "path": n["path"], "children": n["children"], "root": label}
    atl_store.save_index("confluence", index)
    return counts


def fetch_one(c, pid, scope_spaces):
    """Mirror a single page (one linked from Jira). Out-of-scope spaces keep only the title."""
    body, md, meta = fetch(c, pid)
    index = atl_store.load_index("confluence")
    entry = {"title": meta["title"], "path": meta["path"], "space": meta["space"], "version": meta["version"],
             "when": meta["when"], "root": "linked from Jira"}
    if scope_spaces and meta["space"] not in scope_spaces:
        entry["kind"] = "out of scope"
    else:
        atl_store.write(f"confluence/pages/{pid}.md", render(pid, md, meta))
        entry.update(kind=kind_of(meta["title"], md, 0), chars=len(md), hash=atl_store.digest(md), by=meta["by"],
                     archived=any("archive" in t.lower() for t in meta["path"]), comments=len(meta["comments"]),
                     attachments=len(meta["attachments"]))
    index[pid] = entry
    atl_store.save_index("confluence", index)
    return entry
