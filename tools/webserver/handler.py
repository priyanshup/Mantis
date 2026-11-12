"""The request handler: the static files, the GET routes, and POST through webserver/routes.py (one plain function per route)."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import extra
import growth
import http.server
import jobs
import json
import pull
import tasks_store
from webserver import routes
from webserver.config import PORT
from webserver.inbox import pending_answers, pending_edits


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

    def drain(self, cap=65536):
        """Read and drop a small request body before refusing, so the client that is still sending it gets the answer instead of a reset connection."""
        try:
            self.rfile.read(min(int(self.headers.get("Content-Length", "0")), cap))
        except (ValueError, OSError):
            pass

    def do_POST(self):
        # Only the site itself may post (blocks other web pages from writing to the inbox).
        origin = self.headers.get("Origin", "")
        if self.path not in routes.ROUTES or origin not in (f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}"):
            self.drain()
            return self.reply(403, {"error": "not allowed"})
        route = routes.ROUTES[self.path]
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self.reply(400, {"error": "bad Content-Length"})
        if route.too_large and size > route.too_large[0]:
            return self.reply(route.too_large[1], {"error": route.too_large[2]})
        raw = self.rfile.read(size if route.too_large else min(size, route.limit))
        try:
            status, answer = routes.post(self.path, raw)
        except Exception as e:   # a route's listed errors are answered by routes.post; anything else is a bug, and the site is told so instead of the connection dropping
            return self.reply(500, {"error": str(e)[:300]})
        return self.reply(status, answer)
