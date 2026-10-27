"""Cached file reads for the rebuild (MANTIS-IMP-016). Stdlib only.

A rebuild reads every digest and register entry several times (build_map, index_gen, classify,
entry.check). On OneDrive an open costs about 35 times a stat, so this module keeps the text of
each file it has read, keyed by its size and modification time, in one cache file outside
OneDrive. A file that has not changed since the last rebuild is never opened again.

    import textcache
    text = textcache.read(path)        # same as path.read_text(encoding="utf-8")
    textcache.write(path, text)        # same as path.write_text(...), but skipped when nothing changed

A rebuild that changes nothing must write nothing: every write wakes OneDrive and the site
server's watcher (a write on every build kept the server rebuilding nonstop until 2026-10-27).

The cache is saved when the process exits. Deleting it is always safe; the next rebuild refills it.
"""
import atexit, json, os, tempfile
from pathlib import Path

DIR = (Path(os.environ["LOCALAPPDATA"]) / "Mantis") if os.environ.get("LOCALAPPDATA") else Path(tempfile.gettempdir()) / "Mantis"
FILE = DIR / "textcache.json"
_cache, _dirty, _loaded = {}, False, False


def _load():
    global _cache, _loaded
    _loaded = True
    try:
        _cache = json.loads(FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        _cache = {}


def _save():
    if not _dirty:
        return
    try:
        DIR.mkdir(parents=True, exist_ok=True)
        tmp = FILE.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(_cache, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, FILE)
    except OSError:
        pass  # a cache that cannot be saved only costs the next rebuild some time


atexit.register(_save)


def read(path):
    """Return the file's text, from the cache when its size and modification time are unchanged."""
    global _dirty
    if not _loaded:
        _load()
    p = Path(path)
    st = p.stat()
    key = os.path.normcase(os.path.abspath(p))   # no syscall, unlike Path.resolve()
    stamp = [st.st_size, st.st_mtime_ns]
    hit = _cache.get(key)
    if hit and hit[0] == stamp:
        return hit[1]
    text = p.read_text(encoding="utf-8")
    _cache[key] = [stamp, text]
    _dirty = True
    return text


def write(path, text):
    """Write the file only if its text differs from what is there. Returns True when it wrote."""
    global _dirty
    p = Path(path)
    try:
        if read(p) == text:
            return False
    except (OSError, UnicodeDecodeError):
        pass
    p.write_text(text, encoding="utf-8")
    st = p.stat()
    _cache[os.path.normcase(os.path.abspath(p))] = [[st.st_size, st.st_mtime_ns], text]
    _dirty = True
    return True


def prune():
    """Drop cached files that no longer exist (called by build_map)."""
    global _dirty
    if not _loaded:
        _load()
    gone = [k for k in _cache if not os.path.exists(k)]
    for k in gone:
        del _cache[k]
    _dirty = _dirty or bool(gone)
