"""What a pull fetches: list, add, change, remove and test a filter (also used by the site)."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import atl_client
import atl_updates
import sys
from pullkit.state import say


# ------------------------------------------------------------------ filters (also used by the site)
def list_filters():
    return atl_updates.filters(atl_client.load_config())


def set_filter(action, fid="", label=None, value=None, active=None, typ=None):
    """Add, change or remove one filter. Returns the filter list. Raises ValueError on bad input."""
    conf = atl_client.load_config()
    fl = atl_updates.filters(conf)
    if action == "add":
        if typ not in ("jira", "confluence") or not (label or "").strip() or not (value or "").strip():
            raise ValueError("a filter needs a type (jira or confluence), a label and a value")
        base = atl_updates.slug(label)
        fid = base if base not in {f["id"] for f in fl} else f"{base}-{len(fl) + 1}"
        fl.append({"id": fid, "label": label.strip(), "type": typ, "value": value.strip(), "active": active is not False,
                   "last_run": "", "last_counts": {}})
    else:
        f = next((f for f in fl if f["id"] == fid), None)
        if not f:
            raise ValueError(f"no filter '{fid}'")
        if action == "remove":
            fl.remove(f)
        elif action == "set":
            if label is not None and label.strip():
                f["label"] = label.strip()
            if value is not None and value.strip() and value.strip() != f["value"]:
                f["value"], f["last_run"], f["last_counts"] = value.strip(), "", {}   # a new value starts fresh
            if active is not None:
                f["active"] = bool(active)
        else:
            raise ValueError("unknown action")
    atl_client.save_config(conf)
    return fl


def test_filter(fid="", typ=None, value=None):
    """How many items a filter selects now: {"count", "sample"}. One call; nothing saved."""
    if fid:
        f = next((f for f in list_filters() if f["id"] == fid), None)
        if not f:
            raise ValueError(f"no filter '{fid}'")
        typ, value = f["type"], f["value"]
    c = atl_client.connect(typ)
    if typ == "jira":   # the search API gives no total any more: count up to 500 (5 calls at most)
        import atl_jira
        got = atl_jira.search(c, atl_updates.without_order(atl_jira.jql_for(c, value)), ["summary"], limit=501)
        return {"count": len(got) if len(got) <= 500 else "500+",
                "sample": [f"{i['key']} {i['fields'].get('summary', '')}" for i in got[:5]]}
    d = c.get("/rest/api/search", {"cql": atl_updates.page_cql(value), "limit": 5})   # this endpoint reports the total
    return {"count": d.get("totalSize", 0), "sample": [x.get("title") or x.get("content", {}).get("title", "") for x in d.get("results", [])]}


def cmd_filters():
    for f in list_filters():
        n = f.get("last_counts", {})
        say(f"[{'on ' if f.get('active') else 'off'}] {f['id']}: {f['label']} ({f['type']})\n      {f['value']}\n"
            f"      last run {f.get('last_run') or 'never'}" + (f": {n.get('new', 0)} new, {n.get('changed', 0)} changed" if n else ""))


def opt(args, name):
    return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else None


def cmd_filter(args):
    a = args[0] if args else ""
    if a == "add" and len(args) >= 4:
        set_filter("add", label=args[2], value=args[3], typ=args[1], active="--off" not in args)
    elif a == "set" and len(args) >= 2:
        set_filter("set", args[1], label=opt(args, "--label"), value=opt(args, "--value"),
                   active=True if "--on" in args else False if "--off" in args else None)
    elif a == "remove" and len(args) == 2:
        set_filter("remove", args[1])
    elif a == "test" and len(args) == 2:
        r = test_filter(args[1])
        say(f"{r['count']} item(s) now. For example: " + "; ".join(r["sample"]))
        return
    else:
        sys.exit(__doc__)
    cmd_filters()
