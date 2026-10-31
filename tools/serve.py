"""Serve the Mantis site at http://localhost:8000 and rebuild it when Markdown changes.

    python tools/serve.py           (run from the Mantis folder; Ctrl+C stops it)
    python tools/serve.py --open    (also opens the browser)
    python tools/serve.py --background   (starts it hidden and returns; Claude Code runs this at session start)
    python tools/serve.py --stop         (stops a running site, wherever it was started)
    python tools/serve.py --restart      (stops it, then starts it hidden again: use after changing serve.py)

It also accepts answers posted from the Open items page (POST /api/answers) and saves them
as mantis/00_inbox/answers-<time>.md; GET /api/answers/pending lists the IDs waiting there.
Edited pages, epics and stories (POST /api/edits) are saved as mantis/00_inbox/edit-<time>-<name>.md;
tools/apply_edits.py applies them. GET /api/edits/pending lists the documents waiting.

Notes, transcripts and files dropped on the Meetings or Sources page (POST /api/inbox {"name", "text" or
base64 "data", "meeting"}) go to mantis/00_inbox/ for the next pull. Undo of an automatic close
(POST /api/reopen {"id"}) runs tools/entry.py reopen.

Buttons on the site start background jobs (tools/jobs.py): POST /api/jobs {"type", "arg"} queues
one of the fixed job types; GET /api/jobs returns recent jobs, the running one and inbox counts.

Open pages reload by themselves after a rebuild (they check every 3 seconds, only while visible). The
watcher rebuilds for hand edits only, checking every 5 seconds. If the site is already being served,
this exits quietly. Stop with Ctrl+C.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import functools, http.server, json, os, re, socket, subprocess, sys, threading, time, webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import tasks_store
import jobs
import extra
import buildlock
import pull
PORT = 8000
URL = f"http://localhost:{PORT}/"
PIDFILE = (Path(os.environ["LOCALAPPDATA"]) / "Mantis" if os.environ.get("LOCALAPPDATA") else ROOT) / "serve.pid"
SITE = Path(os.environ["LOCALAPPDATA"]) / "Mantis" / "site" if os.environ.get("LOCALAPPDATA") else ROOT / "site"
WATCH = [ROOT / "mantis" / "knowledge", ROOT / "mantis" / "outputs", ROOT / "mantis" / "02_digests", ROOT / "tools"]
FILES = [ROOT / "docs" / "project" / "IMPROVEMENT_BACKLOG.md", ROOT / "docs" / "project" / "IMPROVEMENT_DONE.md"]


def stamp():
    newest = 0.0
    for d in WATCH:
        for p in d.rglob("*"):
            if p.suffix in (".md", ".py", ".css", ".js", ".json") and "map" not in p.parts and "__pycache__" not in p.parts:
                newest = max(newest, p.stat().st_mtime)
    return max([newest] + [f.stat().st_mtime for f in FILES if f.exists()])


def rebuild():
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "build_map.py")], capture_output=True, text=True, **jobs.quiet())
    last = (r.stdout.strip().splitlines() or [""])[-1]
    print(time.strftime("%H:%M:%S"), last if r.returncode == 0 else "Build failed:\n" + r.stderr[-1500:], flush=True)


def watch():
    """Rebuild for hand edits only. Claude and the site's buttons rebuild themselves when they finish, so an
    edit older than the last rebuild's end is already in, and a build's own writes never trigger another."""
    seen = 0.0
    while True:
        time.sleep(5)
        try:
            now = stamp()
        except OSError:
            continue
        if now != seen and now > buildlock.last_done() and not buildlock.held():
            time.sleep(1)  # let the editor finish writing
            rebuild()
        seen = now


INBOX = ROOT / "mantis" / "00_inbox"
ANSWER_ID = re.compile(r"^(?:MANTIS-(?:GAP|ASM|CFL)-\d{3}|NAME-[0-9a-f]{8}|TERM-[0-9a-f]{8})$")
VERDICTS = {"answers": "Answers it", "partly": "Partly answers it", "someone": "Someone else must answer",
            "later": "Not decided yet",                                                          # MANTIS-IMP-049
            "real": "Yes, they conflict", "changed": "The plan changed", "notconflict": "Not a conflict",   # MANTIS-IMP-047
            "same": "Same thing", "different": "Different things"}
COMPLETE = ("same", "different", "real", "changed", "notconflict", "later")   # need no text or name


def pending_answers():
    """IDs that have an answer waiting in the inbox."""
    ids = set()
    for p in INBOX.glob("answers-*.md"):
        ids |= set(re.findall(r"(?m)^## (MANTIS-(?:GAP|ASM|CFL)-\d{3}|NAME-[0-9a-f]{8}|TERM-[0-9a-f]{8})\b", p.read_text(encoding="utf-8")))
    return sorted(ids)


def save_answers(items):
    """Validate the posted answers and write one inbox file. Returns (count, file name)."""
    rows = []
    for it in items[:200]:
        rid, verdict = str(it.get("id", "")), str(it.get("verdict", ""))
        text, who = str(it.get("answer", "")).strip()[:5000], str(it.get("who", "")).strip()[:200]
        # Choices such as "Same thing" or "Not decided yet" are complete on their own; others need text or a name.
        if not ANSWER_ID.match(rid) or verdict not in VERDICTS or not (text or who or verdict in COMPLETE):
            continue
        topic = " ".join(str(it.get("topic", "")).split())[:300]
        body = "\n".join("  " + line for line in text.splitlines()) or "  (no text)"
        rows.append(f"## {rid}: {topic}\n\n- Verdict: {VERDICTS[verdict]}\n" + (f"- Who to ask: {who}\n" if who else "") + f"- Answer:\n{body}\n")
    if not rows:
        return 0, ""
    INBOX.mkdir(parents=True, exist_ok=True)
    stamp_ = time.strftime("%Y-%m-%d-%H%M%S")
    name = f"answers-{stamp_}.md"
    (INBOX / name).write_text(
        "# Owner answers from the Open items page\n\n"
        f"Submitted {time.strftime('%Y-%m-%d %H:%M')} through http://localhost:8000/review.html. Mantis processes this\n"
        "file per docs/rules/workflow/answers.md, then moves it to 03_archive/answers/.\n\n"
        + "\n".join(rows), encoding="utf-8")
    return len(rows), name


OUTPUTS = (ROOT / "mantis" / "outputs").resolve()
FOCUS = ROOT / "mantis" / "knowledge" / "focus.json"
FOCUS_ACTIONS = {"follow": ("following", True), "unfollow": ("following", False),
                 "roadmap": ("on_roadmap", True), "unroadmap": ("on_roadmap", False),
                 "archive": ("archived", True), "unarchive": ("archived", False)}


def card_slugs():
    k = ROOT / "mantis" / "knowledge"
    feats = {p.stem for p in (k / "features").glob("*.md") if p.name != "README.md"}
    topics = {p.stem for p in (k / "topics").glob("*.md") if p.name != "README.md"}
    return feats, topics


def set_focus(slug, action, order=None, rebuild_after=True):
    """Update the owner's focus choices (a preference file, not knowledge; written directly, no inbox)."""
    feats, topics = card_slugs()
    if action.startswith("bulk-"):   # several cards at once: bulk-follow, bulk-unfollow, bulk-roadmap, bulk-unroadmap
        f = None
        for s in [s for s in (order or []) if s in feats | topics]:
            f = set_focus(s, action[5:], rebuild_after=False)
        threading.Thread(target=rebuild, daemon=True).start()
        return f or json.loads(FOCUS.read_text(encoding="utf-8"))
    if action in ("archive-work", "unarchive-work"):   # one epic or story, keyed by its file under mantis/ (outputs/...)
        target = (ROOT / "mantis" / slug).resolve()
        if not slug.startswith("outputs/") or not slug.endswith(".md") or OUTPUTS not in target.parents or not target.exists():
            raise ValueError("unknown epic or story")
        f = json.loads(FOCUS.read_text(encoding="utf-8")) if FOCUS.exists() else {"following": []}
        rest = [s for s in f.get("archived_work", []) if s != slug]
        f["archived_work"] = sorted(rest + ([slug] if action == "archive-work" else []))
        FOCUS.write_text(json.dumps(f, indent=1) + "\n", encoding="utf-8")
        if rebuild_after:
            threading.Thread(target=rebuild, daemon=True).start()
        return f
    if action == "order":   # the owner's ranking of followed cards, top first
        f = json.loads(FOCUS.read_text(encoding="utf-8")) if FOCUS.exists() else {"following": []}
        known = [s for s in (order or []) if s in f.get("following", [])]
        f["following"] = known + [s for s in f.get("following", []) if s not in known]
        FOCUS.write_text(json.dumps(f, indent=1) + "\n", encoding="utf-8")
        threading.Thread(target=rebuild, daemon=True).start()
        return f
    if slug not in feats | topics or action not in FOCUS_ACTIONS:
        raise ValueError("unknown card or action")
    f = json.loads(FOCUS.read_text(encoding="utf-8")) if FOCUS.exists() else {"following": [], "on_roadmap": [], "off_roadmap": []}
    for k in ("following", "on_roadmap", "off_roadmap", "archived"):
        f.setdefault(k, [])
    if action == "archive":   # an archived card leaves focus and the roadmap; restoring it does not put it back
        f["following"] = [s for s in f["following"] if s != slug]
        f["on_roadmap"] = [s for s in f["on_roadmap"] if s != slug]
        if slug in feats and slug not in f["off_roadmap"]:
            f["off_roadmap"] = sorted(f["off_roadmap"] + [slug])
    key, on = FOCUS_ACTIONS[action]
    if key == "on_roadmap" and slug in feats:   # roadmap features are on the roadmap unless taken off
        key, on = "off_roadmap", not on
    if key == "following":   # keep the owner's ranking: a new follow goes to the bottom
        f[key] = [s for s in f[key] if s != slug] + ([slug] if on else [])
    else:
        lst = set(f[key])
        (lst.add if on else lst.discard)(slug)
        f[key] = sorted(lst)
    FOCUS.write_text(json.dumps(f, indent=1) + "\n", encoding="utf-8")
    if rebuild_after:
        threading.Thread(target=rebuild, daemon=True).start()   # the page reloads itself when the rebuild lands
    return f


INBOX_TYPES = {".md", ".txt", ".vtt", ".srt", ".docx", ".pdf", ".html", ".htm", ".xlsx", ".pptx"}


def save_inbox(b):
    """Meeting notes, a transcript or a file dropped on the site, saved to the inbox for the next pull. Returns its name."""
    import base64
    name = re.sub(r"[^\w .-]+", "", str(b.get("name", "")).strip())[:80].strip(" .") or "notes.md"
    stem, ext = os.path.splitext(name)
    ext = ext.lower() or ".md"
    if ext not in INBOX_TYPES:
        raise ValueError("Mantis reads notes, transcripts, Word, PDF, web pages and spreadsheets: " + ", ".join(sorted(INBOX_TYPES)))
    meeting = re.sub(r"[^\w -]+", "", str(b.get("meeting", "")))[:60].strip()
    if b.get("text") is not None:
        text = str(b["text"]).replace("\r\n", "\n").strip()
        if not text:
            raise ValueError("nothing to save")
        head = f"# {meeting} notes, {time.strftime('%Y-%m-%d')}\n\nMeeting: {meeting}\n\n" if meeting else ""
        data, ext = (head + text + "\n").encode("utf-8"), ".md" if ext not in (".txt", ".vtt", ".srt") else ext
    else:
        data = base64.b64decode(str(b.get("data", "")), validate=True)
    if not data or len(data) > 15_000_000:
        raise ValueError("the file is empty or larger than 15 MB")
    prefix = time.strftime("%Y-%m-%d") + (f"-{meeting.lower().replace(' ', '-')}" if meeting else "")
    INBOX.mkdir(parents=True, exist_ok=True)
    target = INBOX / f"{prefix}-{stem.replace(' ', '-')}{ext}"
    n = 2
    while target.exists():   # never overwrite something waiting
        target = INBOX / f"{prefix}-{stem.replace(' ', '-')}-{n}{ext}"
        n += 1
    target.write_bytes(data)
    return target.name


def reopen(rid):
    """The owner's Undo for an automatic close (MANTIS-IMP-094): entry.py reopen, which refuses any other close."""
    if not re.fullmatch(r"MANTIS-GAP-\d{3}", rid):
        raise ValueError("only an open question that closed automatically can be reopened")
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "entry.py"), "reopen", rid], capture_output=True, text=True, cwd=ROOT, **jobs.quiet())
    if r.returncode:
        raise ValueError((r.stderr or r.stdout).strip().splitlines()[-1] if (r.stderr or r.stdout).strip() else "could not reopen")
    threading.Thread(target=rebuild, daemon=True).start()


def pending_edits():
    """Target paths (mantis/outputs/...) that have an edit waiting in the inbox."""
    out = set()
    for p in INBOX.glob("edit-*.md"):
        m = re.search(r"(?m)^target: (.+)$", p.read_text(encoding="utf-8"))
        if m:
            out.add(m.group(1).strip())
    return sorted(out)


def save_edit(payload):
    """Validate an edited document and write it to the inbox. Returns the file name."""
    rel, base, md = str(payload.get("path", "")), str(payload.get("base", "")), str(payload.get("markdown", ""))
    target = (ROOT / rel).resolve()
    if not rel.startswith("mantis/outputs/") or not rel.endswith(".md") or OUTPUTS not in target.parents or not target.exists():
        raise ValueError("only existing pages, epics and stories under mantis/outputs/ can be edited")
    if not re.fullmatch(r"[0-9a-f]{16}", base) or not md.strip() or len(md) > 500_000:
        raise ValueError("invalid edit")
    name = f"edit-{time.strftime('%Y-%m-%d-%H%M%S')}-{target.stem}.md"
    INBOX.mkdir(parents=True, exist_ok=True)
    (INBOX / name).write_text(
        f"---\ntype: page-edit\ntarget: {rel}\nbase_hash: {base}\nsubmitted: {time.strftime('%Y-%m-%d %H:%M')}\n---\n\n"
        + md.replace("\r\n", "\n").strip() + "\n", encoding="utf-8")
    return name


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
                                        "dismissed": st.get("dismissed", []), "suggestions": tasks_store.suggestions()})
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
        if self.path not in ("/api/answers", "/api/edits", "/api/focus", "/api/tasks", "/api/jobs", "/api/followups", "/api/deadlines", "/api/schedule", "/api/published", "/api/filters", "/api/inbox", "/api/reopen", "/api/mapping") \
                or origin not in (f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}"):
            return self.reply(403, {"error": "not allowed"})
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


def stop():
    """Stop the running site by the process ID it recorded at start. Returns True if one was stopped."""
    try:
        pid = int(PIDFILE.read_text().strip())
    except (OSError, ValueError):
        return False
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
        else:
            os.kill(pid, 15)
    except OSError:
        pass
    PIDFILE.unlink(missing_ok=True)
    for _ in range(20):   # wait until the port is free
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", PORT)) != 0:
                return True
        time.sleep(0.25)
    return True


if __name__ == "__main__":
    if "--stop" in sys.argv or "--restart" in sys.argv:
        print("Mantis site stopped." if stop() else "No running Mantis site was recorded.")
        if "--stop" in sys.argv:
            sys.exit(0)
        sys.argv.append("--background")
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", PORT)) == 0:
            print(f"Mantis is already running at {URL}")
            if "--open" in sys.argv:
                webbrowser.open(URL)
            sys.exit(0)
    if "--background" in sys.argv:  # start a hidden copy and return at once (used by the SessionStart hook)
        exe = Path(sys.executable).with_name("pythonw.exe")
        subprocess.Popen([str(exe if exe.exists() else sys.executable), __file__], cwd=str(ROOT),
                         creationflags=getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True,
                         startupinfo=jobs.quiet().get("startupinfo"))
        print(f"Mantis is starting at {URL}")
        sys.exit(0)
    PIDFILE.parent.mkdir(parents=True, exist_ok=True)
    PIDFILE.write_text(str(os.getpid()))
    jobs.recover()   # a job left running by a stopped server is marked interrupted
    rebuild()
    threading.Thread(target=watch, daemon=True).start()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), functools.partial(Quiet, directory=str(SITE)))
    print(f"Mantis is running at {URL}  (Ctrl+C to stop)", flush=True)
    if "--open" in sys.argv:
        webbrowser.open(URL)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
