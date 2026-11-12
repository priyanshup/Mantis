"""The self-running safety net (IMP-112 item 1): runs the checks without anyone asking, records the result for the Health page.

    python tools/guard.py quick      the self-test (quick), page structure snapshots, the rule tests          (about 20 s)
    python tools/guard.py full       quick, plus the full self-test, the jsdom flow and page checks, and the real-browser checks
                                     (every page, desktop and phone, light and dark: errors, contrast, sideways scroll, touch targets)
    python tools/guard.py affected   quick, plus only the checks the changed files can affect (tools/affected.py): the quick cycle between edits
    python tools/guard.py status     what the last runs found

The site server runs `quick` after every hand edit it rebuilds for, and `full` once a day while it is up (webserver/watching.py).
Results go to %LOCALAPPDATA%/Mantis/guard.json; the Health page and the session-start notice report a failing or stale run.
The browser checks need the Playwright tool (see tools/uitest/README.md) and the site running; without them that check is reported as skipped,
never as passed.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import json, os, subprocess, tempfile, threading, time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
STATE_DIR = (Path(os.environ["LOCALAPPDATA"]) / "Mantis") if os.environ.get("LOCALAPPDATA") else Path(tempfile.gettempdir()) / "Mantis"
STATE = STATE_DIR / "guard.json"
PLAYWRIGHT_PY = Path(os.environ.get("APPDATA", str(Path.home()))) / "uv" / "tools" / "playwright" / "Scripts" / "python.exe"
STALE_HOURS = 36
_lock = threading.Lock()


def _quiet():
    if os.name == "nt":
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return {"startupinfo": si, "creationflags": 0x08000000}
    return {}


def _run(cmd, timeout, cwd=None):
    t = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, cwd=str(cwd or ROOT), **_quiet())
        return r.returncode, (r.stdout + r.stderr).strip(), round(time.time() - t, 1)
    except subprocess.TimeoutExpired:
        return 1, f"timed out after {timeout} s", round(time.time() - t, 1)
    except OSError as e:
        return 1, str(e), round(time.time() - t, 1)


def _tail(text, n=3):
    lines = [l for l in text.splitlines() if l.strip()]
    return " | ".join(lines[-n:])[:400]


def _site_up():
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:8000/index.html", timeout=3).read(1)
        return True
    except (OSError, ValueError):   # not running, or not answering
        return False


def jsdom_checks(scripts):
    """[(name, callable)] for the jsdom scripts in tools/uitest; skipped (not passed) when their packages are not installed."""
    if not scripts:
        return []
    ui = TOOLS / "uitest"
    if not (ui / "node_modules").exists():
        return [("jsdom checks", lambda: (None, "skipped: run npm install in tools/uitest", 0))]

    def one(script, args):
        rc, o, secs = _run(["node", f"{script}.js", *args], 240, ui)
        return rc == 0 and ("errors: []" in o or '"errors": []' in o), _tail(o), secs
    jobs = [(s, []) if isinstance(s, str) else s for s in scripts]
    return [(f"jsdom {s}" + (" (" + a[0][7:] + ")" if a else ""), lambda s=s, a=a: one(s, a)) for s, a in jobs]


def browser_check(scope, sub):
    """The real-browser pass over every page (scope all), the app tabs (app) or the content pages (pages)."""
    name = "browser (pages, themes, phone width)" + ("" if scope == "all" else f", {scope} only")
    if PLAYWRIGHT_PY.exists() and _site_up():
        return sub(name, [str(PLAYWRIGHT_PY), str(TOOLS / "guard_browser.py"), "--only", scope], 420)
    return (name, lambda: (None, "skipped: the Playwright tool or the running site is missing", 0))


def checks(level):
    """[(name, callable -> (ok or None for skipped, detail, seconds))]"""
    py = sys.executable
    pyw = Path(py).with_name("python.exe")   # the server runs under pythonw; the checks want a console interpreter
    py = str(pyw if pyw.exists() else py)

    def sub(name, cmd, timeout, cwd=None):
        return (name, lambda: (lambda rc, out, s: (rc == 0, _tail(out), s))(*_run(cmd, timeout, cwd)))

    out = [sub("self-test (quick)", [py, str(TOOLS / "selftest.py"), "--quick"], 120),
           sub("page structure snapshots", [py, str(TOOLS / "snapshots.py"), "check"], 60)]
    tests = TOOLS / "tests"
    if tests.exists():
        out.append(sub("rule tests", [py, "-m", "unittest", "discover", "-s", str(tests), "-t", str(TOOLS), "-q"], 180))
    if level == "full":
        out.append(sub("self-test (full)", [py, str(TOOLS / "selftest.py")], 400))
        out += jsdom_checks(["flows-check", "pagefn-check", "detail-check", "smoke"])
        out.append(browser_check("all", sub))
    elif level == "affected":   # only what the changed files can affect (tools/affected.py); the quick set above always runs
        import affected
        extra, unmapped = affected.plan(affected.changed_files())
        if unmapped:
            out.append(("files no rule knows", lambda: (True, "only the quick set ran for: " + ", ".join(unmapped[:5]), 0)))
        if "build" in extra:
            out.append(sub("rebuild the site", [py, str(TOOLS / "build_site.py")], 180))
        names = {"flows": "flows-check", "pagefn": "pagefn-check", "detail": "detail-check", "smoke": "smoke"}
        scope_flows = affected.flows_scope(affected.changed_files())   # None = all flows
        jobs = [(names[k], ["--only=" + ",".join(scope_flows)] if k == "flows" and scope_flows else []) for k in ("flows", "pagefn", "detail", "smoke") if k in extra]
        out += jsdom_checks(jobs)
        scope = "all" if "browser-all" in extra else ("app" if "browser-app" in extra else ("pages" if "browser-pages" in extra else None))
        if scope:
            out.append(browser_check(scope, sub))
    return out


def run(level="quick"):
    """Run the checks one after another, write the result, return it. One run at a time."""
    if not _lock.acquire(blocking=False):
        return {"level": level, "skipped": "another run is in progress"}
    try:
        t0, rows = time.time(), []
        for name, fn in checks(level):
            ok, detail, secs = fn()
            rows.append({"name": name, "ok": ok, "detail": "" if ok else detail, "seconds": secs})
        res = {"level": level, "ran_at": datetime.now().isoformat(timespec="seconds"), "seconds": round(time.time() - t0, 1), "checks": rows,
               "failed": [r["name"] for r in rows if r["ok"] is False], "skipped": [r["name"] for r in rows if r["ok"] is None]}
        state = load()
        state[level] = res
        if level == "full":   # a full run also counts as a quick one
            state["quick"] = res
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        tmp = STATE.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=1, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, STATE)
        return res
    finally:
        _lock.release()


def run_async(level="quick"):
    threading.Thread(target=run, args=(level,), daemon=True).start()


def load():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def running():
    return _lock.locked()


def last_epoch():
    """When the newest run (quick or full) started, as a timestamp; 0 when there has been none."""
    t = [datetime.fromisoformat(r["ran_at"]).timestamp() for r in load().values() if isinstance(r, dict) and r.get("ran_at")]
    return max(t, default=0.0)


def due_full(hours=24):
    last = load().get("full", {}).get("ran_at")
    return not last or (datetime.now() - datetime.fromisoformat(last)).total_seconds() > hours * 3600


def problems():
    """For Health and session start: [(level, message)]. A failing run is a warning; no recent full run is a note."""
    state, out = load(), []
    for level in ("quick", "full"):
        r = state.get(level)
        if r and r.get("failed"):
            out.append(("warn", f"{level} checks failed on {r['ran_at'][:16]}: " + "; ".join(f"{c['name']} ({c['detail'][:90]})" for c in r["checks"] if c["ok"] is False)[:420]
                        + ". Run python tools/guard.py " + level + " to see it."))
    last = state.get("full", {}).get("ran_at")
    if not last:
        out.append(("info", "The full safety-net run has never happened. The site server runs it daily while it is up; python tools/guard.py full runs it now."))
    elif (datetime.now() - datetime.fromisoformat(last)).total_seconds() > STALE_HOURS * 3600:
        out.append(("warn", f"The last full safety-net run was {last[:16]}, more than {STALE_HOURS} hours ago. Start the site (python tools/serve.py --background) or run python tools/guard.py full."))
    skipped = state.get("full", {}).get("skipped")
    if skipped:
        out.append(("info", "Skipped in the last full run (so not checked): " + "; ".join(skipped)))
    return out


def main(argv):
    cmd = argv[0] if argv else "quick"
    if cmd == "status":
        for lvl, msg in problems():
            print(f"[{lvl}] {msg}")
        st = load()
        for level in ("quick", "full"):
            if level in st:
                print(f"{level}: {st[level]['ran_at']}, {st[level]['seconds']} s, failed {st[level]['failed'] or 'none'}, skipped {st[level]['skipped'] or 'none'}")
        return 0
    if cmd == "affected":
        import affected
        d = affected.describe(affected.changed_files())
        print(f"{len(d['files'])} changed file(s). Quick set, plus: {', '.join(d['extra']) or 'nothing'}")
    res = run(cmd)
    for c in res.get("checks", []):
        print(f"{'ok  ' if c['ok'] else ('skip' if c['ok'] is None else 'FAIL')}  {c['name']}  ({c['seconds']} s)" + (f"  {c['detail']}" if c["ok"] is not True else ""))
    print(f"{cmd}: {'all passed' if not res.get('failed') else 'FAILED: ' + ', '.join(res['failed'])} in {res.get('seconds')} s")
    return 1 if res.get("failed") else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
