"""Incremental site build (Phase 3, task 1). Stdlib only.

The site's pages are a pure function of the knowledge files, the Python that draws them and the site configuration.
When none of those changed since the last build, the pages are not drawn again: the files already in the site folder are kept.
The assets (scripts, styles, tokens) are cheap and are always rebuilt, so a change to a script or a stylesheet never waits for the pages.

How a change is noticed: a fingerprint of (path, size, modification time) for every input file. Reading nothing, only listing.
Anything unsure rebuilds: a missing page, a missing state file, `--full` on the command line or MANTIS_FULL=1 in the environment.

    import sitecache
    sig = sitecache.fingerprint()          # compare with the one saved after the last build
    sitecache.load() / sitecache.save(sig, page_files, counts)

State lives next to the site, outside OneDrive (buildstate.json). Deleting it is always safe: the next build draws everything.
"""
import hashlib, json, os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
DIR = (Path(os.environ["LOCALAPPDATA"]) / "Mantis") if os.environ.get("LOCALAPPDATA") else ROOT / ".cache"
FILE = DIR / "buildstate.json"

# Folders under mantis/ the site never reads (sources, archive, background jobs, the inbox, templates, test data).
SKIP_UNDER_MANTIS = {"00_inbox", "01_sources", "03_archive", "jobs", "eval", "TEMPLATES"}
# Files that change on every build, so counting them would make every build look different.
SKIP_FILES = {"timings.json", "health.json", "health.md", "CODEMAP.md"}


def full():
    return "--full" in sys.argv or bool(os.environ.get("MANTIS_FULL"))


def _walk(folder, skip_dirs=()):
    try:
        entries = list(os.scandir(folder))
    except OSError:
        return
    for e in entries:
        if e.is_dir(follow_symlinks=False):
            if e.name in skip_dirs or e.name in ("__pycache__", "node_modules", ".git"):
                continue
            yield from _walk(e.path)
        elif e.name not in SKIP_FILES:
            try:
                st = e.stat()
            except OSError:
                continue
            yield e.path, st.st_size, st.st_mtime_ns


def inputs():
    """Every file a page can depend on, as (path, size, mtime)."""
    for sub in sorted(os.scandir(ROOT / "mantis"), key=lambda x: x.name):
        if sub.is_dir(follow_symlinks=False) and sub.name not in SKIP_UNDER_MANTIS:
            yield from _walk(sub.path)
        elif sub.is_file():
            yield sub.path, sub.stat().st_size, sub.stat().st_mtime_ns
    yield from _walk(ROOT / "docs")
    for p in sorted([*TOOLS.glob("*.py"), *(TOOLS / "pagebuild").glob("*.py")]):   # the Python that draws the pages
        st = p.stat()
        yield str(p), st.st_size, st.st_mtime_ns
    yield from _walk(TOOLS / "site_config")
    env = ROOT / ".env"
    if env.exists():
        st = env.stat()
        yield str(env), st.st_size, st.st_mtime_ns


def fingerprint():
    h = hashlib.sha1()
    n = 0
    for path, size, mtime in sorted(inputs()):
        h.update(f"{os.path.relpath(path, ROOT)}|{size}|{mtime}\n".encode("utf-8"))
        n += 1
    return f"{h.hexdigest()}:{n}"


def load():
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(sig, files, counts):
    try:
        DIR.mkdir(parents=True, exist_ok=True)
        tmp = FILE.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps({"sig": sig, "files": sorted(files), "counts": counts}), encoding="utf-8")
        os.replace(tmp, FILE)
    except OSError:
        pass   # only costs the next build some time


def reusable(state, sig, site):
    """True when the pages from the last build are still right: same inputs, every page file still there."""
    return (not full() and state.get("sig") == sig and bool(state.get("files"))
            and all((site / rel).exists() for rel in state["files"]))


# ---- stages of build_map.py that only read files: skipped when nothing they read has changed ----

STAGES = DIR / "stagestate.json"


def stage_signature(roots, extra=""):
    """A fingerprint of everything under the given folders (and the extra text, e.g. today's date). Lists, never reads."""
    h = hashlib.sha1(extra.encode("utf-8"))
    for root in roots:
        for path, size, mtime in sorted(_walk(root)):
            h.update(f"{os.path.relpath(path, ROOT)}|{size}|{mtime}\n".encode("utf-8"))
    return h.hexdigest()


def stage_unchanged(name, sig, output=None):
    """True when this stage ran with the same inputs last time and its output file still exists."""
    if full() or (output is not None and not Path(output).exists()):
        return False
    try:
        return json.loads(STAGES.read_text(encoding="utf-8")).get(name) == sig
    except (OSError, ValueError):
        return False


def stage_done(name, sig):
    try:
        try:
            state = json.loads(STAGES.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            state = {}
        state[name] = sig
        DIR.mkdir(parents=True, exist_ok=True)
        tmp = STAGES.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(state), encoding="utf-8")
        os.replace(tmp, STAGES)
    except OSError:
        pass
