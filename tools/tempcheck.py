"""Leftover browser profiles and headless browsers in %TEMP% (IMP-112 item 7). Reports on Health; cleans only when asked.

    python tools/tempcheck.py            what is there: profile folders (size) and headless browsers still running on them
    python tools/tempcheck.py clean      stop the orphaned headless browsers and delete the profile folders nothing is using

Why: headless Edge/Chrome runs that hang leave a process holding a profile of 0.5 to 2 GB, and the folder is never removed (6 GB found on 2026-11-12).
Only browsers whose command line is headless AND points at a "browser-profile" folder under the Claude temp folder count as orphans, and only after
they have run for 30 minutes; the owner's own browser and Playwright's throwaway profiles are never touched. Cleaning is never automatic.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import noconsole; noconsole.install()   # no console windows from background work (tools/noconsole.py)
import json, os, re, shutil, subprocess, tempfile
from datetime import datetime, timedelta
from pathlib import Path

TEMP = Path(os.environ.get("TEMP") or tempfile.gettempdir())
WARN_MB = 500
ORPHAN_AFTER = timedelta(minutes=30)
PROFILE = re.compile(r"browser-profile", re.I)


def profile_dirs(temp=TEMP):
    """[(path, MB)] of every browser-profile folder under the Claude temp folder, biggest first."""
    out = []
    base = Path(temp) / "claude"
    if base.exists():
        for p in base.rglob("browser-profile"):
            if p.is_dir():
                size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
                out.append((p, round(size / 1e6)))
    return sorted(out, key=lambda x: -x[1])


def is_orphan(cmdline, started, now=None):
    """A headless browser on a scratchpad profile that has been running longer than ORPHAN_AFTER."""
    now = now or datetime.now()
    c = cmdline or ""
    return bool("headless" in c.lower() and PROFILE.search(c) and "claude" in c.lower() and started and now - started > ORPHAN_AFTER)


def browsers():
    """[(pid, cmdline, started)] for Edge and Chrome processes (Windows; an empty list elsewhere or when the listing fails)."""
    if os.name != "nt":
        return []
    ps = ("Get-CimInstance Win32_Process | Where-Object { $_.Name -in 'msedge.exe','chrome.exe' } | "
          "ForEach-Object { [pscustomobject]@{ pid = $_.ProcessId; cmd = $_.CommandLine; started = $_.CreationDate.ToString('s') } } | ConvertTo-Json -Compress")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=30)
        rows = json.loads(r.stdout) if r.stdout.strip() else []
    except (OSError, ValueError, subprocess.TimeoutExpired):   # no PowerShell or an odd answer: no browsers are reported, nothing is stopped
        return []
    rows = rows if isinstance(rows, list) else [rows]
    return [(int(x["pid"]), x.get("cmd") or "", datetime.fromisoformat(x["started"])) for x in rows if x.get("started")]


def scan(temp=TEMP):
    profiles = profile_dirs(temp)
    orphans = [(pid, started) for pid, cmd, started in browsers() if is_orphan(cmd, started)]
    return {"profiles": profiles, "profile_mb": sum(mb for _, mb in profiles), "orphans": orphans}


def problem(info=None):
    """A sentence for the Health page, or an empty string."""
    info = info or scan()
    parts = []
    if info["profile_mb"] >= WARN_MB:
        parts.append(f"{info['profile_mb'] / 1000:.1f} GB of old browser profiles in {TEMP}")
    if info["orphans"]:
        parts.append(f"{len(info['orphans'])} headless browser process(es) left running")
    return ("; ".join(parts) + ". python tools/tempcheck.py clean removes them.") if parts else ""


def clean():
    info = scan()
    for pid, _ in info["orphans"]:
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
    freed = 0
    for path, mb in info["profiles"]:
        shutil.rmtree(path, ignore_errors=True)
        if not path.exists():
            freed += mb
    return len(info["orphans"]), freed


def main(argv):
    if argv[:1] == ["clean"]:
        n, mb = clean()
        print(f"Stopped {n} headless browser process(es); freed {mb / 1000:.2f} GB.")
        return 0
    info = scan()
    for p, mb in info["profiles"]:
        print(f"{mb:>6} MB  {p}")
    for pid, started in info["orphans"]:
        print(f"orphaned headless browser {pid} running since {started:%d %b %H:%M}")
    print(problem(info) or "Temp: ok (no old browser profiles or orphaned headless browsers).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
