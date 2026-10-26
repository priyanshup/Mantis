"""Confluence attachments: download a page's images and diagram previews once, by content hash (MANTIS-IMP-087). Stdlib only.

    mantis/mirror/attachments/<hash>.<ext>     each file once, however many pages carry it
    mantis/mirror/attachments/index.json       hash -> names, pages, type, size; "_seen" -> attachment id@version -> hash

Rules, all code: only images (image/*), so draw.io diagrams come as their ".drawio.png" preview; no
temporary "~" files; nothing over MAX_BYTES; an attachment version already downloaded is never
fetched again. Downloading costs API calls, never AI tokens: an image is looked at only when a
digest or a decision needs it. Needs the token scope readonly:content.attachment:confluence.
"""
import hashlib, json, sys

import atl_store

sys.dont_write_bytecode = True
MAX_BYTES = 5 * 1024 * 1024
EXT = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif", "image/svg+xml": "svg", "image/webp": "webp"}


def load():
    try:
        return json.loads(atl_store.read("attachments/index.json") or "{}")
    except ValueError:
        return {}


def save(idx):
    atl_store.write("attachments/index.json", json.dumps(idx, indent=1, ensure_ascii=False, sort_keys=True))


def listing(c, pid):
    out, start = [], 0
    while True:
        d = c.get(f"/rest/api/content/{pid}/child/attachment", {"limit": 100, "start": start, "expand": "version"})
        out += d.get("results", [])
        start += d.get("size", 0)
        if not d.get("_links", {}).get("next") or not d.get("size"):
            return out


def fetch_page(c, pid, idx):
    """Download a page's wanted attachments. Returns (downloaded, already had, skipped)."""
    seen = idx.setdefault("_seen", {})
    got = had = skipped = 0
    for a in listing(c, pid):
        name, ext = a["title"], a.get("extensions", {})
        mtype, size = ext.get("mediaType", ""), ext.get("fileSize", 0) or 0
        if name.startswith("~") or mtype not in EXT or size > MAX_BYTES:
            skipped += 1
            continue
        key = f"{a['id']}@{a.get('version', {}).get('number', 1)}"
        h = seen.get(key)
        if not h:
            data = c.get_bytes(a["_links"]["download"])
            h = hashlib.sha1(data).hexdigest()[:16]
            p = atl_store.path("attachments", f"{h}.{EXT[mtype]}")
            if not p.exists():
                p.write_bytes(data)
            seen[key] = h
            got += 1
        else:
            had += 1
        e = idx.setdefault(h, {"names": [], "pages": [], "type": mtype, "size": size, "file": f"{h}.{EXT[mtype]}"})
        if name not in e["names"]:
            e["names"].append(name)
        if pid not in e["pages"]:
            e["pages"].append(pid)
    return got, had, skipped


def for_page(pid, idx=None):
    """[(name, file path)] of a page's downloaded attachments."""
    idx = idx or load()
    return [(n, atl_store.MIRROR / "attachments" / e["file"]) for h, e in idx.items()
            if not h.startswith("_") and pid in e["pages"] for n in e["names"]]
