"""Self-test for the Mantis engine (MANTIS-IMP-061). Run before every commit (the pre-commit hook does).

    python tools/selftest.py           every check (about 20 seconds)
    python tools/selftest.py --quick   code and document checks only, no tool runs (the pre-commit hook)

Checks, each one a failure that has happened before:
  code      every tool parses; every tool imports without running (a broken string once stopped the server)
  js        the site script parses (node --check), when Node is installed
  css       the stylesheet's braces balance
  docs      every "rules: <Section>" in the workflow files names a real section of WORKFLOW_RULES.md;
            every docs/ and tools/ path mentioned in the rules exists; the tool list in tools/README.md
            matches the tools on disk (python tools/toollist.py writes it)
  tools     read-only commands answer: entry.py check, answers.py, mishear.py, assets.py status,
            changes.py, graph.py, contradictions.py, estimates.py
  readiness fixed cards get the expected decision-readiness state (evidence, not filled fields)
  data      every generated map file is valid JSON
Exit code 1 lists every failure; nothing is changed.
"""
import ast, importlib, json, re, shutil, subprocess, sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
T = ROOT / "tools"
sys.path.insert(0, str(T))
NO_IMPORT = {"build_map", "selftest", "peek", "session_start"}   # scripts that act on import; this file is the test
fails = []


def check(name, ok, detail=""):
    if not ok:
        fails.append(f"{name}: {detail}")


def code():
    for p in [*sorted(T.glob("*.py")), *sorted((T / "site_assets" / "js").glob("*.js")), T / "site_assets" / "style.css"]:
        bad = re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", p.read_text(encoding="utf-8"))
        if bad:   # a control character in code: the mark of a shell-quoting accident ("\b" becoming a backspace)
            line = p.read_text(encoding="utf-8")[:bad.start()].count("\n") + 1
            check("code", False, f"{p.name} line {line} contains control character {bad.group(0)!r}")
    for p in sorted(T.glob("*.py")):
        try:
            ast.parse(p.read_text(encoding="utf-8"), filename=p.name)
        except SyntaxError as e:
            check("code", False, f"{p.name} line {e.lineno}: {e.msg}")
            continue
        if p.stem not in NO_IMPORT:
            try:
                importlib.import_module(p.stem)
            except SystemExit:
                pass
            except Exception as e:
                check("code", False, f"{p.name} does not import: {type(e).__name__}: {e}")


def js_css():
    if shutil.which("node"):   # the site script is joined from site_assets/js/ at build time; check the joined whole
        import tempfile, build_site
        with tempfile.NamedTemporaryFile("wb", suffix=".js", delete=False) as f:
            f.write(build_site.app_js())
        r = subprocess.run(["node", "--check", f.name], capture_output=True, text=True)
        Path(f.name).unlink(missing_ok=True)
        check("js", r.returncode == 0, r.stderr.strip()[:300])
    css = re.sub(r"/\*.*?\*/", "", (T / "site_assets" / "style.css").read_text(encoding="utf-8"), flags=re.S)
    check("css", css.count("{") == css.count("}"), f"{css.count('{')} opening and {css.count('}')} closing braces")


def docs():
    rules = (ROOT / "docs" / "rules" / "WORKFLOW_RULES.md").read_text(encoding="utf-8")
    heads = {h.strip().lower() for h in re.findall(r"(?m)^#{2,4} (.+)$", rules)}
    wf = [ROOT / "docs" / "rules" / "WORKFLOW.md", *sorted((ROOT / "docs" / "rules" / "workflow").glob("*.md"))]
    for f in wf:
        for ref in re.findall(r"rules: ([^)\n;]+)", f.read_text(encoding="utf-8")):
            for name in re.split(r",| and ", ref):
                name = name.strip().strip("`.").strip()
                if name and not any(h.startswith(name.lower()) or name.lower() in h for h in heads):
                    check("docs", False, f"{f.name} points to 'rules: {name}', not a section of WORKFLOW_RULES.md")
    for f in [ROOT / "CLAUDE.md", ROOT / "AGENTS.md", *(ROOT / "docs").rglob("*.md")]:
        if "project" in f.parts:
            continue
        for path in set(re.findall(r"`((?:tools|docs)/[\w/.-]+\.(?:py|md|json))`", f.read_text(encoding="utf-8"))):
            check("docs", (ROOT / path).exists(), f"{f.relative_to(ROOT).as_posix()} mentions {path}, which does not exist")
    import toollist
    check("docs", toollist.current(), "tools/README.md does not list the tools on disk; run python tools/toollist.py")


def readiness_rules():
    """Decision readiness judges evidence, not filled fields (MANTIS-IMP-074 to 076): fixed cards, expected states."""
    import tempfile, readiness
    po = "## Problem and outcome\n- **Work type:** {wt}\n- **Problem:**\n{ev}\n- **Next decision:** {nd}\n\n"
    full = ("## Measurement\n- **Primary: Orders with promotion**: share of orders\n  - Data source: analytics (instrumented: yes)\n"
            "  - Baseline: *Unknown*: get it from the order report\n  - Target: *Proposed:* 10%, because pilot\n"
            "- **Decision rule:** scale if above 10%; roll back if below 2%\n")
    obs, opi = "  - *Observed:* agents re-key orders daily (DOC-1)", "  - *Opinion:* Sam says it is slow (DOC-2)"
    cases = [  # (front matter, curated body, expected state)
        ("status: build", "## In one paragraph\nText.\n", "not-framed"),
        ("status: discovery", po.format(wt="discretionary", ev=opi, nd="Fund discovery"), "unvalidated"),
        ("status: discovery", (ROOT / "mantis" / "TEMPLATES" / "feature-card.md").read_text(encoding="utf-8").split("---", 2)[2], "unvalidated"),
        ("status: discovery", po.format(wt="discretionary", ev=obs, nd="Fund discovery"), "ready"),
        ("status: discovery", po.format(wt="discretionary", ev=obs + "\n  - *Unknown:* volume\n  - *Unknown:* cost", nd="Interviews"), "unvalidated"),
        ("status: refinement", po.format(wt="discretionary", ev=obs, nd="Approve MVP") + "## Metrics\n| Metric | Baseline | Target | Source |\n|---|---|---|---|\n| Orders | unknown | 10 | DOC-1 |\n", "no-plan"),
        ("status: build", po.format(wt="discretionary", ev=obs, nd="Go-live date") + full, "ready"),
        ("status: build", po.format(wt="mandatory: tax rule (DOC-3)", ev="", nd="Sign-off") + "## Measurement\n- **Obligation:** e-invoice by July (DOC-3)\n- **Acceptance:** audit passes\n", "ready"),
        ("status: refinement", po.format(wt="approved commitment: steering (DOC-4)", ev="", nd="Sprint plan") + full, "ready"),
        ("status: live", po.format(wt="discretionary", ev=obs, nd="-") + full, "live-no-review"),
        ("status: live\nreview_on: 2000-01-01", po.format(wt="discretionary", ev=obs, nd="-") + full, "review-overdue"),
        ("status: live\nreview_on: 2999-01-01", po.format(wt="discretionary", ev=obs, nd="-") + full, "measuring"),
        ("status: live\nreview_on: 2000-01-01", full + "## Launch review\n- **Result:** *Measurement gap:* no tracking\n- **Interpretation:** looks fine\n", "reviewed-no-data"),
    ]
    with tempfile.TemporaryDirectory() as d:
        for i, (fm, body, want) in enumerate(cases):
            p = Path(d) / f"case{i}.md"
            p.write_text(f"---\nfeature: case{i}\n{fm}\n---\n{body}\n<!-- GENERATED -->\n## Sources (auto)\n", encoding="utf-8")
            got = readiness.read_card(p, "2026-10-10")
            check("readiness", got["state"] == want, f"case {i}: expected {want}, got {got['state']} ({got['why']})")


def decision_watch():
    """A decision is flagged when something it rests on changes, and only then (MANTIS-IMP-080)."""
    import decisions
    ds = decisions.decisions()
    if not ds or not ds[0]["rests_on"]:
        return
    d, dep = ds[0]["id"], ds[0]["rests_on"][0]
    now = {x: "Open" for x in ds[0]["rests_on"]}
    sync = decisions.record({d}, sync={}, state_of=lambda x: now.get(x, "Open"), today="2026-01-01")
    flagged = lambda: [c for dd, c in decisions.scan(sync, state_of=lambda x: now.get(x, "Open")) if dd["id"] == d][0]
    check("decisions", flagged() == [], "an unchanged basis was flagged")
    now[dep] = "Corrected"
    check("decisions", [c[0] for c in flagged()] == [dep], f"a changed basis was not flagged: {flagged()}")
    sync = decisions.record({d}, sync=sync, state_of=lambda x: now.get(x, "Open"))
    check("decisions", flagged() == [], "marking it reviewed did not clear the flag")


def search_index():
    """The search index picks up a new, a changed and a deleted source, and finds words by their stem (MANTIS-IMP-086)."""
    import tempfile, search
    old = (search.M, search.K)
    with tempfile.TemporaryDirectory() as d:
        m = Path(d) / "mantis"
        (m / "02_digests").mkdir(parents=True)
        (m / "knowledge" / "features").mkdir(parents=True)
        doc = m / "02_digests" / "MANTIS-DOC-0001.md"
        doc.write_text("---\noriginal_title: \"Fixture\"\n---\n## Summary\n\nDistributors create their own promotions every month in the pilot markets.\n", encoding="utf-8")
        search.M, search.K = m, m / "knowledge"
        try:
            con = search.connect(Path(d) / "s.db")
            check("search", search.update(con) == (1, 0), "a new source was not indexed")
            hits = lambda w: con.execute("SELECT count(*) FROM chunks WHERE chunks MATCH ?", (f'"{w}"',)).fetchone()[0]
            check("search", hits("promotion") == 1, "stemming: 'promotion' did not find 'promotions'")
            check("search", search.update(con) == (0, 0), "an unchanged source was indexed again")
            doc.write_text(doc.read_text(encoding="utf-8").replace("promotions", "price lists"), encoding="utf-8")
            check("search", search.update(con)[0] == 1 and hits("promotion") == 0 and hits("price") == 1, "a changed source was not re-indexed")
            doc.unlink()
            check("search", search.update(con)[1] == 1 and hits("price") == 0, "a deleted source stayed in the index")
            con.close()
        finally:
            search.M, search.K = old


def tools():
    runs = [["entry.py", "check"], ["mishear.py", str(ROOT / "README.md")], ["assets.py", "status"], ["changes.py", "1"],
            ["answers.py"], ["contradictions.py"], ["estimates.py"], ["graph.py", "--help"],
            ["citations.py"], ["support.py", "report"], ["readiness.py"], ["decisions.py"]]
    for r in runs:
        p = subprocess.run([sys.executable, str(T / r[0]), *r[1:]], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", cwd=ROOT, timeout=120)
        crashed = "Traceback (most recent call last)" in (p.stderr + p.stdout)
        check("tools", not crashed, f"{' '.join(r)} crashed: {(p.stderr or p.stdout).strip().splitlines()[-1:]}")


def data():
    for f in (ROOT / "mantis" / "knowledge" / "map").glob("*.json"):
        try:
            json.loads(f.read_text(encoding="utf-8"))
        except ValueError as e:
            check("data", False, f"{f.name} is not valid JSON: {e}")


if __name__ == "__main__":
    quick = "--quick" in sys.argv
    code(); js_css(); docs(); readiness_rules(); decision_watch(); search_index()
    if not quick:
        tools(); data()
    if fails:
        print(f"Self-test failed ({len(fails)}):\n" + "\n".join("  - " + f for f in fails))
        sys.exit(1)
    print("Self-test passed" + (" (quick)" if quick else "") + ".")
