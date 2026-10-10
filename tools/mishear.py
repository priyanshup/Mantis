"""Mishearings: words speech-to-text gets wrong (MANTIS-IMP-051). Stdlib only.

    python tools/mishear.py FILE [...]     list likely mishearings in files (pastes, extracted transcripts, answers)

The list lives in mantis/knowledge/glossary.md, section "## Mishearings" (Heard | Means | Where |
Source); one row can name several spellings ("Easle, Easel"). Matching is on whole words and
ignores case. Nothing is replaced automatically: Claude reads the flagged word as its meaning,
writes the meaning, and says it corrected it. Used by tools/extract.py and tools/answers.py.
"""
import re, sys
from pathlib import Path

sys.dont_write_bytecode = True
GLOSSARY = Path(__file__).resolve().parent.parent / "mantis" / "knowledge" / "glossary.md"


def load():
    """[(spelling, meaning, where)] from the glossary's Mishearings table."""
    text = GLOSSARY.read_text(encoding="utf-8") if GLOSSARY.exists() else ""
    m = re.search(r"(?ms)^## Mishearings\s*$(.*?)(?=^## |\Z)", text)
    out = []
    for line in (m.group(1) if m else "").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or not cells[0] or cells[0] in ("Heard",) or set(cells[0]) <= set("-: "):
            continue
        for spelling in (s.strip() for s in cells[0].split(",")):
            if spelling:
                out.append((spelling, cells[1], cells[2]))
    return out


def scan(text, table=None):
    """[(spelling as found, meaning, where, count)] for every listed mishearing in the text."""
    found = []
    for spelling, means, where in (table if table is not None else load()):
        hits = re.findall(r"(?<![\w-])" + re.escape(spelling) + r"(?![\w-])", text, re.I)
        if hits:
            found.append((hits[0], means, where, len(hits)))
    return found


def report(text, table=None):
    """One line for a CLI or a tool to print, or "" when nothing is found."""
    f = scan(text, table)
    return ("Possible mishearings: " + "; ".join(f'"{h}" x{n} probably means "{m}"' + ("" if w.lower() == "everywhere" else f" ({w})")
                                                for h, m, w, n in f)) if f else ""


if __name__ == "__main__":
    if not sys.argv[1:]:
        sys.exit(__doc__)
    table = load()
    for a in sys.argv[1:]:
        r = report(Path(a).read_text(encoding="utf-8", errors="replace"), table)
        print(f"{a}: {r or 'none found'}")
