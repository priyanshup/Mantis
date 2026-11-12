"""The site's POST routes as plain functions: body in, (status, answer) out. IMP-112 item 10.

The handler only checks the origin, reads the body up to a limit, calls `post`, and replies. Each route here can be called in a test without a
server. A route may raise: the exceptions listed for it become the status and message the site has always answered with.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import edit_common
import extra
import growth
import jobs
import json
import pull
import re
import tasks_store
import threading
import time
from webserver.config import OUTPUTS, ROOT
from webserver.focus import set_focus
from webserver.inbox import pending_answers, pending_edits, reopen, save_answers, save_edit, save_inbox
from webserver.watching import rebuild


def _log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def _short(e):
    return {"error": str(e)[:300]}


def _plain(e):
    return {"error": str(e)}


def growth_act(b):   # {"action", "id", ...}: one change on the Growth tab
    return 200, {"result": growth.act(b), **growth.payload()}


def mapping(b):   # {"root": "<Jira key>", "card": "<slug>" or "skip"}
    return 200, {"items": pull.map_ticket(str(b.get("root", "")), str(b.get("card", "")))}


def inbox(b):   # a note, transcript or file dropped on the site: {"name", "text" or base64 "data", "meeting"}
    name = save_inbox(b)
    _log(f"Saved mantis/00_inbox/{name}")
    return 200, {"file": name, **jobs.status()}


def reopen_route(b):   # Undo of an automatic close: {"id"}
    reopen(str(b.get("id", "")))
    _log(f"Reopened {b.get('id')} (the owner undid an automatic close)")
    return 200, {"ok": True}


def filters(b):   # {"action": add|set|remove|test, "id", "label", "type", "value", "active"}
    act = str(b.get("action", ""))
    if act == "test":
        return 200, pull.test_filter(str(b.get("id", "")), b.get("type"), b.get("value"))
    active = b.get("active") if isinstance(b.get("active"), bool) else None
    text = lambda k: str(b[k])[:2000] if b.get(k) is not None else None
    return 200, {"filters": pull.set_filter(act, str(b.get("id", "")), text("label"), text("value"), active, b.get("type"))}


PUBLISHABLE = ("mantis/outputs/confluence/", "mantis/outputs/epics/", "mantis/outputs/user-stories/")


def published(b):   # Confluence sync (MANTIS-IMP-019): remember the version now in Confluence
    rel = str(b.get("path", ""))
    target = (ROOT / rel).resolve()
    if not rel.startswith(PUBLISHABLE) or not rel.endswith(".md") or OUTPUTS not in target.parents or not target.exists():
        raise ValueError("only pages, epics and stories under mantis/outputs/ can be marked as copied")
    front, _, md = edit_common.split(target.read_text(encoding="utf-8"))
    rec = {"date": time.strftime("%Y-%m-%d"), "body": md}
    if not rel.startswith("mantis/outputs/confluence/"):   # Jira (MANTIS-IMP-045): remember each field
        t = re.search(r'(?m)^title:\s*"?(.*?)"?\s*$', front)
        rec["fields"] = edit_common.jira_fields(md, t.group(1) if t else target.stem)
    snap = OUTPUTS / ".published" / (str(target.relative_to(OUTPUTS)) + ".json")
    snap.parent.mkdir(parents=True, exist_ok=True)
    snap.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    threading.Thread(target=rebuild, daemon=True).start()
    return 200, {"ok": True, "date": time.strftime("%Y-%m-%d")}


def _extra(fn):
    return lambda b: (200, {"result": fn(b), **extra.payload()})


def jobs_submit(b):
    job = jobs.submit(str(b.get("type", "")), str(b.get("arg", "")))
    _log(f"Job queued: {job['label']}")
    return 200, {"job": job, **jobs.status()}


def tasks(b):
    try:
        st = tasks_store.save(b.get("tasks", []), b.get("rev", -1), b.get("dismissed"), b.get("groups"))
        return 200, {"rev": st["rev"], "tasks": st["tasks"], "groups": st.get("groups", []), "dismissed": st.get("dismissed", [])}
    except RuntimeError:   # the list changed elsewhere: send the current one back
        st = tasks_store.load()
        return 409, {"error": "changed elsewhere", "rev": st["rev"], "tasks": st["tasks"], "groups": st.get("groups", []), "dismissed": st.get("dismissed", [])}


def focus(b):
    order = b.get("order") if isinstance(b.get("order"), list) else None
    return 200, set_focus(str(b.get("slug", "")), str(b.get("action", "")), [str(s)[:80] for s in (order or [])][:200])


def edits(b):
    name = save_edit(b)
    _log(f"Saved an edit to mantis/00_inbox/{name}")
    return 200, {"file": f"mantis/00_inbox/{name}", "pending": pending_edits()}


def answers(b):
    n, name = save_answers(b.get("answers", []))
    if not n:
        return 400, {"error": "Nothing to save: add a short answer (or who to ask) to each question before submitting."}
    _log(f"Saved {n} answer(s) to mantis/00_inbox/{name}")
    return 200, {"saved": n, "file": f"mantis/00_inbox/{name}", "pending": pending_answers()}


class Route:
    """fn: body -> (status, answer). limit: bytes read (a longer body is cut). too_large: (bytes, status, message) refuses a longer body instead.
    errors: [(exceptions, status, message function)] in order; the first that matches turns an exception into the answer."""
    def __init__(self, fn, limit=50_000, too_large=None, errors=()):
        self.fn, self.limit, self.too_large, self.errors = fn, limit, too_large, errors


_VK = (ValueError, OSError, TypeError, KeyError)
ROUTES = {
    "/api/growth": Route(growth_act, 50_000, errors=[(_VK, 400, _short)]),
    "/api/mapping": Route(mapping, 5_000, errors=[((ValueError, OSError, TypeError), 400, _short)]),
    "/api/inbox": Route(inbox, 21_000_000, too_large=(21_000_000, 413, "too large: 15 MB at most"), errors=[((ValueError, OSError, TypeError), 400, _short)]),
    "/api/reopen": Route(reopen_route, 21_000_000, too_large=(21_000_000, 413, "too large: 15 MB at most"), errors=[((ValueError, OSError, TypeError), 400, _short)]),
    "/api/filters": Route(filters, 20_000, errors=[((ValueError, OSError, TypeError), 400, _plain), ((Exception,), 502, _short)]),   # a Jira error while testing is a 502
    "/api/published": Route(published, 10_000, errors=[((ValueError, OSError), 400, _plain)]),
    "/api/followups": Route(_extra(extra.act_followup), 50_000, errors=[(_VK, 400, _plain)]),
    "/api/deadlines": Route(_extra(extra.act_deadline), 50_000, errors=[(_VK, 400, _plain)]),
    "/api/schedule": Route(_extra(extra.act_schedule), 50_000, errors=[(_VK, 400, _plain)]),
    "/api/jobs": Route(jobs_submit, 10_000, errors=[((ValueError,), 400, _plain)]),
    "/api/tasks": Route(tasks, 3_000_000, errors=[((ValueError, OSError, TypeError), 400, _plain)]),
    "/api/focus": Route(focus, 10_000, errors=[((ValueError, OSError), 400, _plain)]),
    "/api/edits": Route(edits, 2_000_000, too_large=(2_000_000, 413, "too large"), errors=[((ValueError, OSError), 400, _plain)]),
    "/api/answers": Route(answers, 2_000_000, too_large=(2_000_000, 413, "too large"), errors=[((ValueError, OSError), 400, _plain)]),
}


def post(path, raw):
    """(status, answer) for a POST to `path` with the (already length-limited) body bytes. An unknown path is the caller's 403."""
    route = ROUTES[path]
    try:
        return route.fn(json.loads(raw.decode("utf-8")))
    except Exception as e:   # turned into the answer the route lists for it; anything unlisted is raised again
        for excs, status, message in route.errors:
            if isinstance(e, excs):
                return status, message(e)
        raise
