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
import functools, http.server, os, socket, subprocess, sys, threading, webbrowser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import jobs
from webserver.config import PIDFILE, PORT, ROOT, SITE, URL
from webserver.handler import Quiet
from webserver.lifecycle import stop
from webserver.watching import rebuild, watch


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
