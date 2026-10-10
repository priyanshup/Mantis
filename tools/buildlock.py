"""One build at a time (MANTIS-IMP-063): the site server, a background job and a chat session can all start one.

    import buildlock; buildlock.acquire()     waits for the lock (a lock older than 3 minutes is taken over)

build_map.py takes it for the whole rebuild; build_site.py takes it when run on its own, so a site
build can never interleave with a full rebuild (on 2026-10-10 that left a half-written health file).
The lock is released when the process exits. Taking it twice in one process is a no-op.
"""
import atexit, os, time
from pathlib import Path

LOCK = (Path(os.environ["LOCALAPPDATA"]) / "Mantis" if os.environ.get("LOCALAPPDATA") else Path(__file__).resolve().parent.parent) / "build.lock"
_held = False


def acquire(wait_seconds=150):
    global _held
    if _held:
        return
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(int(wait_seconds / 0.25)):
        try:
            os.close(os.open(LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            _held = True
            atexit.register(lambda: LOCK.unlink(missing_ok=True))
            return
        except FileExistsError:
            try:
                if time.time() - LOCK.stat().st_mtime > 180:   # left by a crashed build
                    LOCK.unlink(missing_ok=True)
            except OSError:
                pass
            time.sleep(0.25)
