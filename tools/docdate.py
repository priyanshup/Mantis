"""When was the document written, not when did Mantis add it? (IMP-055)

    python tools/docdate.py propose            digests with no `document_date` whose title names exactly one date: what would be written
    python tools/docdate.py apply              write those dates into the digests' front matter (only the one line is added)
    python tools/docdate.py show               how many digests have a document_date

`generated_on` is when Mantis added a source. `document_date` is when the document was written or the meeting held; the Timeline places a source by it when it is there.
Only a date the title states is used (for example "Pri-CK 1-1, 12 November 2026" or "2026-11-12 notes"); a title with no date, or with two, is left blank rather than guessed.
Pull digests (several dated sections) and mirrored Jira and Confluence digests are skipped: their dates are in their sections.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIGESTS = ROOT / "mantis" / "02_digests"
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}
ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
LONG = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)? (" + "|".join(MONTHS) + r")(?: (\d{4}))?\b", re.I)
FRONT = re.compile(r"\A(---\r?\n)(.*?)(\r?\n---\r?\n)", re.S)


def title_date(title, year_hint=None):
    """The one date a title names as 'YYYY-MM-DD' or '12 November 2026' ('12 November' takes year_hint), or None for no date or several."""
    if re.search(r"\bmirrored\b|^(Jira|Confluence)\b", title):
        return None   # a mirrored Jira or Confluence digest: the date in its title is the day Mantis copied it
    found = set()
    for y, m, d in ISO.findall(title):
        found.add((int(y), int(m), int(d)))
    for d, mon, y in LONG.findall(title):
        year = int(y) if y else year_hint
        if year:
            found.add((year, MONTHS[mon.lower()], int(d)))
    if len(found) != 1:
        return None
    try:
        return date(*next(iter(found))).isoformat()
    except ValueError:
        return None


def field(head, key):
    m = re.search(rf'(?m)^{key}:\s*"?(.*?)"?\s*$', head)
    return m.group(1) if m else ""


def candidates(folder=DIGESTS):
    """[(doc id, date)] for digests with no document_date, not a pull or mirror digest, whose title gives one date."""
    out = []
    for p in sorted(Path(folder).glob("MANTIS-DOC-*.md")):
        m = FRONT.match(p.read_text(encoding="utf-8"))
        if not m or field(m.group(2), "document_date") or field(m.group(2), "pull_card") or field(m.group(2), "confluence_page_id"):
            continue
        year = field(m.group(2), "generated_on")[:4]
        d = title_date(field(m.group(2), "original_title"), int(year) if year.isdigit() else None)
        if d:
            out.append((p.stem, d))
    return out


def write(folder, doc, day):
    """Add `document_date: day` to a digest's front matter, before generated_on when it has one. Nothing else changes."""
    p = Path(folder) / f"{doc}.md"
    text = p.read_bytes().decode("utf-8")
    m = FRONT.match(text)
    if not m or re.search(r"(?m)^document_date:", m.group(2)):
        return False
    nl = "\r\n" if "\r\n" in m.group(1) else "\n"
    head = m.group(2)
    line = f"document_date: {day}"
    g = re.search(r"(?m)^generated_on:", head)
    head = head[:g.start()] + line + nl + head[g.start():] if g else head + nl + line
    p.write_bytes((m.group(1) + head + m.group(3) + text[m.end():]).encode("utf-8"))
    return True


def main(argv):
    cmd = argv[0] if argv else ""
    if cmd == "show":
        n = sum(1 for p in DIGESTS.glob("MANTIS-DOC-*.md") if re.search(r"(?m)^document_date:", p.read_text(encoding="utf-8")[:3000]))
        print(f"{n} of {len(list(DIGESTS.glob('MANTIS-DOC-*.md')))} digests have a document_date")
        return 0
    if cmd not in ("propose", "apply"):
        print(__doc__)
        return 2
    got = candidates()
    for doc, day in got:
        print(f"{doc}: {day}")
        if cmd == "apply":
            write(DIGESTS, doc, day)
    print(f"{len(got)} digest(s) " + ("updated. Run python tools/build_map.py." if cmd == "apply" else "would be updated; run apply."))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
