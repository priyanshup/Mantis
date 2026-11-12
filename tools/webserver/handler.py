"""The request handler: every /api route the site calls, and the static files."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import extra
import growth
import http.server
import jobs
import json
import pull
import re
import tasks_store
import threading
import time
from webserver.config import OUTPUTS, PORT, ROOT
from webserver.focus import set_focus
from webserver.inbox import pending_answers, pending_edits, reopen, save_answers, save_edit, save_inbox
from webserver.watching import rebuild


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def reply(self, code, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.split("?")[0] == "/api/answers/pending":
            return self.reply(200, {"pending": pending_answers()})
        if self.path.split("?")[0] == "/api/tasks":
            try:
                st = tasks_store.load()
                return self.reply(200, {"today": tasks_store.today(), "rev": st["rev"], "tasks": st["tasks"], "groups": st.get("groups", []),
                                        "dismissed": st.get("dismissed", []), "suggestions": tasks_store.suggestions(st["tasks"])})
            except OSError as e:
                return self.reply(503, {"error": str(e)})
        if self.path.split("?")[0] == "/api/edits/pending":
            return self.reply(200, {"pending": pending_edits()})
        if self.path.split("?")[0] == "/api/jobs":
            return self.reply(200, jobs.status())
        if self.path.split("?")[0] == "/api/extra":
            try:
                return self.reply(200, extra.payload())
            except Exception as e:
                return self.reply(500, {"error": str(e)})
        if self.path.split("?")[0] == "/api/filters":   # what Mantis pulls (MANTIS-IMP-094); edited on the Sources page
            try:
                return self.reply(200, {"filters": pull.list_filters()})
            except (OSError, ValueError) as e:
                return self.reply(500, {"error": str(e)})
        if self.path.split("?")[0] == "/api/unmapped":   # tickets no card owns, for the owner to map or skip
            try:
                return self.reply(200, {"items": pull.unmapped(), "cards": [{"slug": k, "title": v["title"]} for k, v in pull.cards().items()]})
            except (OSError, ValueError) as e:
                return self.reply(500, {"error": str(e)})
        if self.path.split("?")[0] == "/api/growth":   # the Growth tab (tools/growth.py)
            try:
                return self.reply(200, growth.payload())
            except (OSError, ValueError) as e:
                return self.reply(500, {"error": str(e)})
        if self.path.split("?")[0] == "/api/pull-brief":
            return self.reply(200, {**pull.load_brief(), "pending": pull.pending_counts()})
        if self.path.startswith("/api/brief?id="):
            try:
                return self.reply(200, extra.brief(self.path.split("=", 1)[1]))
            except (ValueError, OSError) as e:
                return self.reply(404, {"error": str(e)})
        return super().do_GET()

    def do_POST(self):
        # Only the site itself may post (blocks other web pages from writing to the inbox).
        origin = self.headers.get("Origin", "")
        if self.path not in ("/api/answers", "/api/edits", "/api/focus", "/api/tasks", "/api/jobs", "/api/followups", "/api/deadlines", "/api/schedule", "/api/published", "/api/filters", "/api/inbox", "/api/reopen", "/api/mapping", "/api/growth") \
                or origin not in (f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}"):
            return self.reply(403, {"error": "not allowed"})
        if self.path == "/api/growth":   # {"action", "id", ...}: one change on the Growth tab
            try:
                body = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length", "0")), 50_000)).decode("utf-8"))
                return self.reply(200, {"result": growth.act(body), **growth.payload()})
            except (ValueError, OSError, TypeError, KeyError) as e:
                return self.reply(400, {"error": str(e)[:300]})
        if self.path == "/api/mapping":   # {"root": "<Jira key>", "card": "<slug>" or "skip"}
            try:
                b = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length", "0")), 5_000)).decode("utf-8"))
                return self.reply(200, {"items": pull.map_ticket(str(b.get("root", "")), str(b.get("card", "")))})
            except (ValueError, OSError, TypeError) as e:
                return self.reply(400, {"error": str(e)[:300]})
        if self.path in ("/api/inbox", "/api/reopen"):
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if size > 21_000_000:
                    return self.reply(413, {"error": "too large: 15 MB at most"})
                b = json.loads(self.rfile.read(size).decode("utf-8"))
                if self.path == "/api/reopen":
                    reopen(str(b.get("id", "")))
                    print(time.strftime("%H:%M:%S"), f"Reopened {b.get('id')} (the owner undid an automatic close)", flush=True)
                    return self.reply(200, {"ok": True})
                name = save_inbox(b)
                print(time.strftime("%H:%M:%S"), f"Saved mantis/00_inbox/{name}", flush=True)
                return self.reply(200, {"file": name, **jobs.status()})
            except (ValueError, OSError, TypeError, UnicodeDecodeError) as e:
                return self.reply(400, {"error": str(e)[:300]})
        if self.path == "/api/filters":   # {"action": add|set|remove|test, "id", "label", "type", "value", "active"}
            try:
                b = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length", "0")), 20_000)).decode("utf-8"))
                act = str(b.get("action", ""))
                if act == "test":
                    return self.reply(200, pull.test_filter(str(b.get("id", "")), b.get("type"), b.get("value")))
                active = b.get("active") if isinstance(b.get("active"), bool) else None
                text = lambda k: str(b[k])[:2000] if b.get(k) is not None else None
                return self.reply(200, {"filters": pull.set_filter(act, str(b.get("id", "")), text("label"), text("value"), active, b.get("type"))})
            except (ValueError, OSError, TypeError) as e:
                return self.reply(400, {"error": str(e)})
            except Exception as e:   # a Jira or Confluence error while testing
                return self.reply(502, {"error": str(e)[:300]})
        if self.path == "/api/published":   # Confluence sync (MANTIS-IMP-019): remember the version now in Confluence
            try:
                body = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length", "0")), 10_000)).decode("utf-8"))
                rel = str(body.get("path", ""))
                target = (ROOT / rel).resolve()
                if not rel.startswith(("mantis/outputs/confluence/", "mantis/outputs/epics/", "mantis/outputs/user-stories/"))                         or not rel.endswith(".md") or OUTPUTS not in target.parents or not target.exists():
                    raise ValueError("only pages, epics and stories under mantis/outputs/ can be marked as copied")
                import edit_common
                text = target.read_text(encoding="utf-8")
                front, _, md = edit_common.split(text)
                rec = {"date": time.strftime("%Y-%m-%d"), "body": md}
                if not rel.startswith("mantis/outputs/confluence/"):   # Jira (MANTIS-IMP-045): remember each field
                    t = re.search(r'(?m)^title:\s*"?(.*?)"?\s*$', front)
                    rec["fields"] = edit_common.jira_fields(md, t.group(1) if t else target.stem)
                snap = OUTPUTS / ".published" / (str(target.relative_to(OUTPUTS)) + ".json")
                snap.parent.mkdir(parents=True, exist_ok=True)
                snap.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
                threading.Thread(target=rebuild, daemon=True).start()
                return self.reply(200, {"ok": True, "date": time.strftime("%Y-%m-%d")})
            except (ValueError, OSError) as e:
                return self.reply(400, {"error": str(e)})
        if self.path in ("/api/followups", "/api/deadlines", "/api/schedule"):
            try:
                body = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length", "0")), 50_000)).decode("utf-8"))
                fn = {"/api/followups": extra.act_followup, "/api/deadlines": extra.act_deadline, "/api/schedule": extra.act_schedule}[self.path]
                result = fn(body)
                return self.reply(200, {"result": result, **extra.payload()})
            except (ValueError, OSError, TypeError, KeyError) as e:
                return self.reply(400, {"error": str(e)})
        if self.path == "/api/jobs":
            try:
                body = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length", "0")), 10_000)).decode("utf-8"))
                job = jobs.submit(str(body.get("type", "")), str(body.get("arg", "")))
                print(time.strftime("%H:%M:%S"), f"Job queued: {job['label']}", flush=True)
                return self.reply(200, {"job": job, **jobs.status()})
            except ValueError as e:
                return self.reply(400, {"error": str(e)})
        if self.path == "/api/tasks":
            try:
                body = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length", "0")), 3_000_000)).decode("utf-8"))
                st = tasks_store.save(body.get("tasks", []), body.get("rev", -1), body.get("dismissed"), body.get("groups"))
                return self.reply(200, {"rev": st["rev"], "tasks": st["tasks"], "groups": st.get("groups", []), "dismissed": st.get("dismissed", [])})
            except RuntimeError:
                st = tasks_store.load()
                return self.reply(409, {"error": "changed elsewhere", "rev": st["rev"], "tasks": st["tasks"], "groups": st.get("groups", []), "dismissed": st.get("dismissed", [])})
            except (ValueError, OSError, TypeError) as e:
                return self.reply(400, {"error": str(e)})
        if self.path == "/api/focus":
            try:
                body = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length", "0")), 10_000)).decode("utf-8"))
                order = body.get("order") if isinstance(body.get("order"), list) else None
                return self.reply(200, set_focus(str(body.get("slug", "")), str(body.get("action", "")), [str(s)[:80] for s in (order or [])][:200]))
            except (ValueError, OSError) as e:
                return self.reply(400, {"error": str(e)})
        if self.path == "/api/edits":
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if size > 2_000_000:
                    return self.reply(413, {"error": "too large"})
                name = save_edit(json.loads(self.rfile.read(size).decode("utf-8")))
            except (ValueError, OSError) as e:
                return self.reply(400, {"error": str(e)})
            print(time.strftime("%H:%M:%S"), f"Saved an edit to mantis/00_inbox/{name}", flush=True)
            return self.reply(200, {"file": f"mantis/00_inbox/{name}", "pending": pending_edits()})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size > 2_000_000:
                return self.reply(413, {"error": "too large"})
            payload = json.loads(self.rfile.read(size).decode("utf-8"))
            n, name = save_answers(payload.get("answers", []))
        except (ValueError, OSError) as e:
            return self.reply(400, {"error": str(e)})
        if not n:
            return self.reply(400, {"error": "Nothing to save: add a short answer (or who to ask) to each question before submitting."})
        print(time.strftime("%H:%M:%S"), f"Saved {n} answer(s) to mantis/00_inbox/{name}", flush=True)
        return self.reply(200, {"saved": n, "file": f"mantis/00_inbox/{name}", "pending": pending_answers()})
