"""Rebuild the site when a hand edit changes a source; Claude and the site's buttons rebuild themselves."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import buildlock
import jobs
import subprocess
import sys
import time
from webserver.config import FILES, ROOT, WATCH


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
