"""Daily local copy of the owner's data, with a restore command (IMP-112 item 6).

    python tools/backup.py                       make today's copy if there is none yet (the site server and the session start run this)
    python tools/backup.py now                   make a copy now, replacing today's
    python tools/backup.py list                  the copies kept
    python tools/backup.py restore <file> [--date YYYY-MM-DD]   put one file back from a copy (default: the newest)
    python tools/backup.py check                 exit 1 when there is no copy from the last 36 hours (Health uses this)

What is copied: everything the owner writes or that cannot be fetched again: tasks, follow-ups, schedule, Growth, focus, briefs, the Atlassian and local
settings (not the .env credentials), the knowledge (cards, registers, glossary), the digests and the outputs. Not copied: the sources and the Atlassian
mirror (they can be fetched again), and generated map files. One zip per day in %LOCALAPPDATA%/Mantis/backups, outside OneDrive so a sync mishap cannot
touch it. Kept: the last 14 days, plus one per week for 8 weeks.

Restoring one file first saves the current one next to it as <name>.before-restore, so a restore can itself be undone.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import noconsole; noconsole.install()   # no console windows from background work (tools/noconsole.py)
import os, re, tempfile, zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "mantis"
DIR = (Path(os.environ["LOCALAPPDATA"]) / "Mantis" / "backups") if os.environ.get("LOCALAPPDATA") else Path(tempfile.gettempdir()) / "Mantis" / "backups"
INCLUDE = ["tasks", "growth", "config", "knowledge", "02_digests", "outputs"]   # folders under mantis/
SKIP_NAMES = {".env", ".lock"}
SKIP_SUFFIX = (".tmp", ".lock", ".bak", ".before-restore")
SKIP_PARTS = {"map", "__pycache__"}   # knowledge/map is generated
KEEP_DAYS, KEEP_WEEKS = 14, 8
STALE_HOURS = 36


def files():
    for sub in INCLUDE:
        base = M / sub
        for p in sorted(base.rglob("*")):
            if (p.is_file() and p.name not in SKIP_NAMES and not p.name.endswith(SKIP_SUFFIX)
                    and not (SKIP_PARTS & set(p.relative_to(base).parts))):
                yield p


def name_for(day):
    return DIR / f"mantis-{day}.zip"


def copies():
    """[(date, path)] newest first."""
    out = []
    for p in DIR.glob("mantis-*.zip") if DIR.exists() else []:
        m = re.fullmatch(r"mantis-(\d{4}-\d{2}-\d{2})\.zip", p.name)
        if m:
            out.append((m.group(1), p))
    return sorted(out, reverse=True)


def make(day=None):
    day = day or date.today().isoformat()
    DIR.mkdir(parents=True, exist_ok=True)
    final = name_for(day)
    tmp = final.with_suffix(".zip.tmp")
    n = 0
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for p in files():
            try:
                z.write(p, p.relative_to(ROOT).as_posix())
                n += 1
            except OSError:   # a file held open by OneDrive for a moment: the next copy has it
                continue
    os.replace(tmp, final)
    prune()
    return final, n


def prune(today=None):
    today = today or date.today()
    keep_from = today - timedelta(days=KEEP_DAYS)
    weekly_from = today - timedelta(weeks=KEEP_WEEKS)
    weeks_kept = set()
    for day, p in copies():   # newest first, so the first copy seen in an old week is the one kept
        d = date.fromisoformat(day)
        if d >= keep_from:
            continue
        week = d.isocalendar()[:2]
        if d >= weekly_from and week not in weeks_kept:
            weeks_kept.add(week)
            continue
        p.unlink(missing_ok=True)


def due():
    return not name_for(date.today().isoformat()).exists()


def age_hours():
    c = copies()
    if not c:
        return None
    return (datetime.now() - datetime.fromtimestamp(c[0][1].stat().st_mtime)).total_seconds() / 3600


def problem():
    """A sentence for the Health page, or an empty string when the newest copy is recent enough."""
    h = age_hours()
    if h is None:
        return "There is no backup of your data yet. Run python tools/backup.py (the site server makes one daily while it is up)."
    if h > STALE_HOURS:
        return f"The newest backup of your data is {h / 24:.1f} days old. Run python tools/backup.py, or keep the site server running."
    return ""


def restore(rel, day=None):
    """Put one file back from a copy. rel is a path relative to the repository, or a bare file name that is unique in the copy."""
    c = copies()
    if day:
        c = [x for x in c if x[0] == day]
    if not c:
        raise ValueError("no backup copy" + (f" for {day}" if day else ""))
    when, path = c[0]
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        want = rel.replace("\\", "/")
        hits = [n for n in names if n == want] or [n for n in names if n.endswith("/" + want) or n == want]
        if not hits:
            raise ValueError(f"{rel} is not in the {when} copy")
        if len(hits) > 1:
            raise ValueError(f"{rel} matches {len(hits)} files in the {when} copy; give more of the path: " + ", ".join(hits[:4]))
        target = ROOT / hits[0]
        if target.exists():
            target.with_name(target.name + ".before-restore").write_bytes(target.read_bytes())
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(z.read(hits[0]))
    return hits[0], when


def main(argv):
    cmd = argv[0] if argv else "daily"
    if cmd == "list":
        for day, p in copies():
            print(f"{day}  {p.stat().st_size / 1e6:.1f} MB  {p}")
        return 0
    if cmd == "check":
        msg = problem()
        print(msg or f"Backup: ok (newest {age_hours():.0f} h old)")
        return 1 if msg else 0
    if cmd == "restore":
        if len(argv) < 2:
            print("usage: python tools/backup.py restore <file> [--date YYYY-MM-DD]")
            return 2
        day = argv[argv.index("--date") + 1] if "--date" in argv else None
        try:
            hit, when = restore(argv[1], day)
        except ValueError as e:
            print(e)
            return 1
        print(f"Restored {hit} from the {when} copy. The file it replaced is kept as {Path(hit).name}.before-restore.")
        return 0
    if cmd == "now" or due():
        final, n = make()
        print(f"Backup: {n} files -> {final} ({final.stat().st_size / 1e6:.1f} MB)")
    else:
        print("Backup: today's copy exists.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
