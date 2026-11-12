"""Which checks does a change need? (IMP-112 item 8)

    python tools/affected.py               the changed files (git) and the checks they need
    python tools/guard.py affected         run exactly those checks (the quick cycle: seconds to about a minute, not three minutes)

The full run (guard.py full) stays: it runs daily and before a push. This is for the quick cycle between edits. Every changed file is matched by the first rule
that fits; a file no rule knows runs the quick set and is listed as unmapped, so a new kind of file can never silently skip a check.
The quick set (self-test, snapshots, rule tests) always runs; the rules only add to it.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import noconsole; noconsole.install()   # no console windows from background work (tools/noconsole.py)
import re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# check names: build, flows, pagefn, detail, smoke, browser-app, browser-pages, browser-all   (quick always runs)
RULES = [
    (r"^docs/", set()),
    (r"^(README|CLAUDE|AGENTS)\.md$|^\.gitignore$|^\.gitattributes$|^requirements\.txt$", set()),
    (r"^tools/tests/", set()),
    (r"^tools/uitest/snapshots/", {"build"}),
    (r"^tools/uitest/browser-baseline\.json$", {"browser-all"}),
    (r"^tools/uitest/", {"flows", "pagefn", "detail", "smoke"}),
    (r"^tools/site_config/theme\.json$|^tools/(theme|csskit|stylelint|unusedcss)\.py$|^tools/site_assets/(chrome|header)\.css$", {"build", "pagefn", "smoke", "browser-all"}),
    (r"^tools/site_assets/app/|^tools/site_config/layout\.json$|^tools/(site_app|layout|wiring)\.py$", {"build", "flows", "smoke", "browser-app"}),
    (r"^tools/site_assets/pages/|^tools/site_config/pages\.json$|^tools/(site_pages|site_shell|site_chrome)\.py$", {"build", "pagefn", "detail", "browser-pages"}),
    (r"^tools/pagebuild/|^tools/(build_site|sitecache|snapshots)\.py$", {"build", "pagefn", "detail", "browser-pages"}),
    (r"^tools/(webserver/|serve\.py|jobs\.py|extra\.py|tasks_store\.py|followups\.py|schedule\.py|growth\.py|datafile\.py)", {"flows"}),
    (r"^tools/(guard|guard_browser|affected|backup|skillscan|selftest|maintain|session_start|codemap|toollist|leakcheck|build_map|local_config)\.py$", set()),
    (r"^tools/[\w/]+\.py$", set()),   # the other command-line tools: the quick set (self-test, rule tests) covers their imports and rules
    (r"^mantis/", set()),
]


# An app script that belongs to one screen only affects that screen's flows (names in tools/uitest/flows-check.js). Anything shared affects all of them.
FLOWS_OF = [
    (r"^tools/site_assets/app/(feature-meetings|widgets-meetings-questions)\.js$", ["meetings", "meetingFilter", "preview", "questions"]),
    (r"^tools/site_assets/app/(feature-filters|feature-inbox|widgets-sources)\.js$", ["sources"]),
    (r"^tools/site_assets/app/(feature-growth|widgets-growth)\.js$", ["growth"]),
    (r"^tools/site_assets/app/(widgets-features|feature-reader)\.js$", ["features"]),
    (r"^tools/site_assets/app/(widgets-today|groups-refill|group-ranking|week-view|agenda-calendar|snooze-history)\.js$", ["today"]),
]


SHARED_FLOW_INPUTS = r"^tools/(site_assets/app/|site_config/layout\.json|uitest/|webserver/|(jobs|extra|tasks_store|followups|schedule|growth|datafile)\.py$)"


def flows_scope(files):
    """The flow names to run for these changes, or None for all of them: a shared script, the server or a store, or a file no screen claims."""
    names = []
    for f in files:
        hit = next((flows for pattern, flows in FLOWS_OF if re.search(pattern, f)), None)
        if hit:
            names += hit
        elif re.search(SHARED_FLOW_INPUTS, f):
            return None
    return sorted(set(names)) or None


def changed_files(root=ROOT):
    """Paths (repo-relative, forward slashes) of files that differ from the last commit, including new ones."""
    out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=str(root), capture_output=True, text=True).stdout
    files = []
    for line in out.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip().strip('"').split(" -> ")[-1]
        files.append(path)
    return sorted(set(files))


def plan(files):
    """(checks, unmapped): the extra checks the files need on top of the quick set, and the files no rule knows."""
    checks, unmapped = set(), []
    for f in files:
        for pattern, extra in RULES:
            if re.search(pattern, f):
                checks |= extra
                break
        else:
            unmapped.append(f)
    if "browser-app" in checks and "browser-pages" in checks:
        checks -= {"browser-app", "browser-pages"}
        checks.add("browser-all")
    if "browser-all" in checks:
        checks -= {"browser-app", "browser-pages"}
    return checks, unmapped


def describe(files):
    checks, unmapped = plan(files)
    return {"files": files, "extra": sorted(checks), "unmapped": unmapped}


if __name__ == "__main__":
    d = describe(changed_files())
    print(f"{len(d['files'])} changed file(s). Quick set always; also: {', '.join(d['extra']) or 'nothing'}")
    if d["unmapped"]:
        print("No rule for (quick set only): " + ", ".join(d["unmapped"]))
