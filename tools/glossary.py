"""Look up glossary terms instead of reading the whole glossary (IMP-100).

    python tools/glossary.py lookup <term> [...]     the row for each term (exact, then start, then part of a term), with its meaning and source
    python tools/glossary.py check <file> [...]      the glossary terms and mishearings found in a draft, and any product name this instance forbids (`wrong_names` in mantis/config/settings.json)

The glossary (mantis/knowledge/glossary.md) is about 2,500 words. A writing task needs only the rows for the terms in its draft, so use this instead of opening the file.
Reads the table "Term | Meaning | Source" and leaves the Mishearings table to tools/mishear.py.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GLOSSARY = ROOT / "mantis" / "knowledge" / "glossary.md"


def terms(text=None):
    """[(term, meaning, source)] from the main table, before the Mishearings section."""
    text = GLOSSARY.read_text(encoding="utf-8") if text is None else text
    main = re.split(r"(?m)^## Mishearings\s*$", text)[0]
    out = []
    for line in main.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not line.startswith("|") or len(cells) < 2 or cells[0] in ("Term",) or set(cells[0]) <= set("-: "):
            continue
        out.append((cells[0], cells[1], cells[2] if len(cells) > 2 else ""))
    return out


def lookup(query, table):
    """Rows for a term: an exact match (a row may list alternatives as 'A / B'), else rows starting with it, else rows containing it."""
    q = query.strip().lower()
    names = lambda t: [p.strip().lower() for p in re.split(r"\s*/\s*", t)] + [t.lower()]
    for test in (lambda t: q in names(t), lambda t: any(n.startswith(q) for n in names(t)), lambda t: any(q in n for n in names(t))):
        hits = [r for r in table if test(r[0])]
        if hits:
            return hits
    return []


def check(text, table, wrong_names=None):
    """({term: row} for each glossary term found as a whole word in the text, [(wrong name, count, right name)] for the names in wrong_names, a {wrong: right} dict from local settings)."""
    found = {}
    for row in table:
        for name in {p.strip() for p in re.split(r"\s*/\s*", row[0]) if len(p.strip()) > 2}:
            if re.search(r"(?<![\w-])" + re.escape(name) + r"(?![\w-])", text, re.I):
                found[row[0]] = row
    wrong = []
    for bad, good in (wrong_names or {}).items():
        n = len(re.findall(r"(?<![\w-])" + bad + r"(?![\w-])", text))
        if n:
            wrong.append((bad, n, good))
    return found, wrong


def main(argv):
    if len(argv) < 2 or argv[0] not in ("lookup", "check"):
        print(__doc__)
        return 2
    table = terms()
    if argv[0] == "lookup":
        for q in argv[1:]:
            rows = lookup(q, table)
            print(f"{q}: " + ("no row" if not rows else ""))
            for t, m, s in rows[:5]:
                print(f"  {t}: {m} ({s})")
        return 0
    for f in argv[1:]:
        import local_config
        found, wrong = check(Path(f).read_text(encoding="utf-8", errors="replace"), table, local_config.load().get("wrong_names", {}))
        print(f"{f}: {len(found)} glossary term(s)")
        for t, m, s in found.values():
            print(f"  {t}: {m} ({s})")
        for bad, n, good in wrong:
            print(f"  WRONG NAME: '{bad}' x{n}, write {good}")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
