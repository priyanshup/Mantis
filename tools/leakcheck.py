"""Check that files bound for the public engine repo carry no knowledge (MANTIS-IMP-036).

    python tools/leakcheck.py              check every file git would commit (staged + tracked)
    python tools/leakcheck.py FILE ...     check the named files
    python tools/leakcheck.py --staged     check staged files only (the pre-commit hook)

The engine repo holds tools, site code, rules and templates, never knowledge. This check is the
safety net behind the whitelist in .gitignore. It fails on:
  - any file under the data folders (sources, digests, archive, knowledge, outputs, tasks, jobs)
  - knowledge IDs (DOC, GAP, ASM, CFL, DEC numbers), email addresses, company URLs
  - names from the local knowledge: people, organisations, distributors, markets and teams in
    mantis/knowledge/entity_register.md and mantis/knowledge/people.md, plus every line of
    mantis/config/denylist.txt (local, never committed)
Standard library only. Exit code 1 when anything is found.
"""
import re, subprocess, sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "mantis"
DATA_DIRS = ("mantis/00_inbox/", "mantis/01_sources/", "mantis/02_digests/", "mantis/03_archive/",
             "mantis/knowledge/", "mantis/outputs/", "mantis/tasks/", "mantis/jobs/", "mantis/config/")
ALLOWED_IN_DATA = re.compile(r"^mantis/(TEMPLATES/.*|README\.md|.*/README\.md)$")
PATTERNS = [
    (re.compile(r"\bMANTIS-(DOC|GAP|ASM|CFL|DEC)-\d+", re.I), "knowledge ID"),
    (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I), "email address"),
    (re.compile(r"https?://[a-z0-9.-]*atlassian\.net", re.I), "company Jira/Confluence URL"),
]
TYPES = {"person", "organisation", "distributor", "market", "team"}
SKIP_SUFFIX = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".zip"}
SELF = {"tools/leakcheck.py"}
THIRD_PARTY = ("tools/site_assets/vendor/",)   # vendored libraries keep their authors' credits


def denylist():
    terms = set()
    reg = DATA / "knowledge" / "entity_register.md"
    if reg.exists():
        for line in reg.read_text(encoding="utf-8").splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 4 and cells[1].lower() in TYPES:
                terms.add(cells[0])
                terms.update(a.strip() for a in cells[2].split(",") if a.strip())
    ppl = DATA / "knowledge" / "people.md"
    if ppl.exists():
        for m in re.finditer(r"(?m)^##\s+(.+)$", re.sub(r"(?s)<!--.*?-->", "", ppl.read_text(encoding="utf-8"))):
            terms.add(m.group(1).strip())
    extra = DATA / "config" / "denylist.txt"
    if extra.exists():
        terms.update(l.strip() for l in extra.read_text(encoding="utf-8").splitlines()
                     if l.strip() and not l.startswith("#"))
    terms = {t for t in terms if len(t) >= 4 and not re.match(r"^\d{4}-\d{2}-\d{2}$", t)
             and not t.lower().startswith(("owner answer", "source", "mantis-"))}
    return [(t, re.compile(r"(?<![\w])" + re.escape(t) + r"(?![\w])", re.I)) for t in sorted(terms)]


def git_files(staged_only):
    args = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"] if staged_only else ["git", "ls-files", "--cached"]
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    return [l for l in r.stdout.splitlines() if l]


def check(rel, terms):
    hits = []
    norm = rel.replace("\\", "/")
    if norm.startswith(DATA_DIRS) and not ALLOWED_IN_DATA.match(norm):
        return [f"{norm}: knowledge folder, never committed"]
    if norm in SELF or norm.startswith(THIRD_PARTY):
        return []
    p = ROOT / rel
    if not p.is_file() or p.suffix.lower() in SKIP_SUFFIX:
        return []
    try:
        text = p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    for n, line in enumerate(text.splitlines(), 1):
        for rx, why in PATTERNS:
            m = rx.search(line)
            if m and why == "knowledge ID" and re.search(r"-0*1$", m.group(0)):
                m = None   # MANTIS-DOC-0001, MANTIS-GAP-001: format examples, not real entries
            if m and why == "email address" and re.search(r"example|@b\.co$", m.group(0), re.I):
                m = None   # reserved example domains used in test data
            if m:
                hits.append(f"{norm}:{n}: {why} '{m.group(0)}'")
        for term, rx in terms:
            if rx.search(line):
                hits.append(f"{norm}:{n}: name from local knowledge '{term}'")
    return hits


def main(argv):
    staged = "--staged" in argv
    files = [a for a in argv if not a.startswith("--")] or git_files(staged)
    terms = denylist()
    hits = [h for f in files for h in check(f, terms)]
    for h in hits:
        print(h)
    print(f"leakcheck: {len(files)} file(s), {len(terms)} local names, {len(hits)} problem(s)")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
