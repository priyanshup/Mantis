"""Write tools/README.md, the one list of tools, from each tool's own first help line (MANTIS-IMP-062).

    python tools/toollist.py           rewrite tools/README.md if it is out of date
    python tools/toollist.py --check   exit 1 if it is out of date (selftest.py runs this)

The first line of a tool's docstring is its description everywhere, so the list cannot drift from
the code. Groups come from GROUPS below; a new tool lands under "Other" until it is placed.
Packages a tool needs are found in its imports.
"""
import ast, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
T = Path(__file__).resolve().parent
OUT = T / "README.md"
GROUPS = [
    ("Everyday", ["pull", "build_map", "serve", "tasks", "followups", "brief", "away", "schedule", "deadlines", "people", "steps", "jobs"]),
    ("Ingest and answers", ["extract", "mishear", "classify", "entry", "entities", "answers", "contradictions", "support", "estimates", "assets", "apply_edits"]),
    ("Look up", ["ask", "search", "peek", "graph", "readiness", "decisions"]),
    ("Housekeeping and setup", ["maintain", "session_start", "init", "leakcheck", "selftest", "toollist", "citations", "repeats", "evaluate", "answered", "prune_sources", "refresh_report"]),
    ("Jira and Confluence (read-only)", ["atl", "atl_client", "atl_confluence", "atl_jira", "atl_compare", "atl_convert", "atl_media", "atl_store", "atl_updates"]),
    ("Modules (used by the commands)", ["build_site", "site_common", "site_day", "site_plan", "site_people", "site_reference", "cards", "changes", "index_gen", "kgraph", "tasks_store", "edit_common", "frontmatter",
                                        "buildlock", "textcache", "extra", "local_config"]),
]
PACKAGES = {"pypdf": "pypdf", "PIL": "pillow", "markdown": "markdown", "openpyxl": "openpyxl", "markdownify": "markdownify", "docx": "python-docx"}
HEAD = """# tools

Run every command from the project folder: `python tools/<name>.py`; each file's first lines
explain its options. This list is written by `python tools/toollist.py` from each tool's own first
help line, so it always matches the code; edit a tool's docstring, not this file.
"""


def describe(p):
    try:
        tree = ast.parse(p.read_text(encoding="utf-8"))
    except SyntaxError:
        return "(does not parse)", []
    doc = (ast.get_docstring(tree) or "").strip().splitlines()
    first = re.sub(r"\s*\(MANTIS-IMP-\d+(?:[^)]*)\)", "", doc[0]).strip() if doc else "(no description)"
    first = re.sub(r"\s*\(?\b[Ss]tdlib only[^.)]*[.)]?|\s*\((?:stdlib only, )?deterministic\)\.?", "", first).strip()
    pk = sorted({PACKAGES[n.split(".")[0]] for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
                 for n in ([a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""])
                 if n.split(".")[0] in PACKAGES})
    return first, pk


def render():
    tools = {p.stem: p for p in sorted(T.glob("*.py"))}
    placed = set()
    rows = [HEAD]
    for title, names in GROUPS + [("Other", sorted(set(tools) - {n for _, ns in GROUPS for n in ns}))]:
        names = [n for n in names if n in tools]
        if not names:
            continue
        rows += [f"\n## {title}\n", "| Tool | What it does | Needs |", "|---|---|---|"]
        for n in names:
            d, pk = describe(tools[n])
            rows.append(f"| `{n}.py` | {d.replace('|', '/')} | {', '.join(pk) or 'standard library'} |")
            placed.add(n)
    rows += ["\n## Files that are not commands\n", "| File | Role |", "|---|---|",
             "| `site_assets/` | The site's CSS, JavaScript, logo and vendored libraries |",
             "| `githooks/pre-commit` | Runs `leakcheck.py` and `selftest.py --quick` before every commit (`git config core.hooksPath tools/githooks`) |",
             "| `classify_config.json` | Cut-offs for `classify.py` |"]
    return "\n".join(rows) + "\n"


def current():
    return OUT.exists() and OUT.read_text(encoding="utf-8") == render()


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(0 if current() else 1)
    if current():
        print("tools/README.md is up to date.")
    else:
        OUT.write_text(render(), encoding="utf-8")
        print("tools/README.md rewritten.")
