"""What the owner has already settled, so Mantis never asks it again (MANTIS-IMP-088). Stdlib only, no AI.

    python tools/answered.py check FILE        would these new register entries repeat a settled question?
    python tools/answered.py stale             old wording still used after the owner corrected it

Read by kgraph.py (name and term questions), build_map.py (answered question IDs), entry.py (new
gaps, conflicts and assumptions) and maintain.py (health report). Sources of "already settled":
  - every question answered on the Open items page (mantis/03_archive/answers/*.md)
  - people.md aliases (a first name listed under a full name) and the glossary's terms
  - closed, resolved and confirmed register entries, with their resolution text
  - the glossary's Mishearings table (the stale check)
"""
import re, sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "mantis"
K = M / "knowledge"
ANSWERS = M / "03_archive" / "answers"
OPEN = re.compile(r"^(Open|Unconfirmed|Potential Resolution)", re.I)
STOP = set("""a an the and or of to in on for with by is are was were be been it its this that these those as at from
not no but if then than so which what who whom how when where why can may might will would should could do does did
has have had there their them they we our you your he she his her about into over under per via eg ie also only more
most other such same each any all both one two whether mantis doc gap cfl asm source sources says said
topic evidence strength status date raised missing what's open closed resolved moderate strong weak note owner
answer answered statement digests affected resolution priority unconfirmed""".split())


def answered_ids():
    """NAME-, TERM- and register IDs the owner answered on the Open items page."""
    ids = set()
    for p in ANSWERS.glob("answers-*.md") if ANSWERS.exists() else []:
        ids |= set(re.findall(r"(?m)^## ((?:NAME|TERM)-[0-9a-f]{8}|MANTIS-(?:GAP|ASM|CFL)-\d{3})\b", p.read_text(encoding="utf-8")))
    return ids


def people_aliases():
    """{alias: full name} from people.md ("## Full Name" ... "- **Aliases:** a, b")."""
    p = K / "people.md"
    out = {}
    if p.exists():
        text = re.sub(r"(?s)<!--.*?-->", "", p.read_text(encoding="utf-8"))   # skip the format example
        for m in re.finditer(r"(?ms)^## (.+?)\s*$(.*?)(?=^## |\Z)", text):
            al = re.search(r"(?m)^- \*\*Aliases:\*\*\s*(.+)$", m.group(2))
            out[m.group(1).strip()] = m.group(1).strip()
            for a in (al.group(1).split(",") if al else []):
                if a.strip():
                    out[a.strip()] = m.group(1).strip()
    return out


def glossary_terms():
    """Terms the glossary explains (first column of its main table, before any '## ' section)."""
    p = K / "glossary.md"
    text = p.read_text(encoding="utf-8") if p.exists() else ""
    head = re.split(r"(?m)^## ", text, maxsplit=1)[0]
    terms = set()
    for line in head.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.lstrip().startswith("|") and cells and cells[0] and cells[0] != "Term" and not set(cells[0]) <= set("-: "):
            terms |= {t.strip() for t in re.split(r"\s*/\s*", cells[0]) if t.strip()}
    return terms


def words(text):
    text = re.sub(r"MANTIS-[A-Z]{3}-\d+|\d{4}-\d{2}-\d{2}", " ", text or "")      # IDs and dates say nothing about the topic
    found = (w.strip(".'-") for w in re.findall(r"[a-z0-9][a-z0-9.'-]*", text.lower()))
    return {w for w in found if w not in STOP and len(w) > 2}


def settled():
    """[(id, status, words, short text)] for every settled register entry and every archived answer."""
    out = []
    for folder in ("gaps", "conflicts", "assumptions"):
        for p in (K / "registers" / folder).glob("MANTIS-*.md"):
            t = p.read_text(encoding="utf-8")
            st = re.search(r"(?m)^- \*\*Status:\*\*\s*(.+)$", t)
            status = st.group(1).strip() if st else ""
            if status and not OPEN.match(status):
                topic = re.search(r"(?m)^- \*\*Topic:\*\*\s*(.+)$", t)
                out.append((p.stem, status[:60], words(t), (topic.group(1) if topic else "")[:110]))
    for p in ANSWERS.glob("answers-*.md") if ANSWERS.exists() else []:
        for m in re.finditer(r"(?ms)^## (\S+): (.+?)$(.*?)(?=^## |\Z)", p.read_text(encoding="utf-8")):
            out.append((m.group(1), f"answered in {p.name}", words(m.group(2) + " " + m.group(3)), m.group(2)[:110]))
    return out


FLOOR = 0.20   # calibrated 2026-10-11: repeats score 0.25-0.40 (GAP-044 vs CFL-007, GAP-040 vs CFL-004), unrelated entries 0.17 or less


def similar(text, top=3, floor=FLOOR, exclude=()):
    """Settled entries close to the new entry: [(score, id, status, topic)].

    Cosine similarity of word sets weighted by rarity (idf), so shared rare words ("MTs", "POPIA")
    count and words every entry uses do not; long entries cannot match everything."""
    import math
    rows = [r for r in settled() if r[0] not in exclude and r[2]]
    w = words(text)
    if len(w) < 4 or not rows:
        return []
    df = {}
    for r in rows:
        for x in r[2]:
            df[x] = df.get(x, 0) + 1
    idf = lambda x: math.log((len(rows) + 1) / (df.get(x, 0) + 1)) + 1
    norm_w = math.sqrt(sum(idf(x) ** 2 for x in w))
    hits = []
    for rid, status, sw, topic in rows:
        score = sum(idf(x) ** 2 for x in w & sw) / (norm_w * math.sqrt(sum(idf(x) ** 2 for x in sw)))
        if score >= floor:
            hits.append((round(score, 2), rid, status, topic))
    return sorted(hits, reverse=True)[:top]


def check_entries(text):
    """Print a warning per new '### ID' block that looks settled already. Returns how many warned."""
    n = 0
    for m in re.finditer(r"(?ms)^### (\S+)\s*$(.*?)(?=^### |\Z)", text):
        hits = similar(m.group(2))
        if hits:
            n += 1
            print(f"Looks settled already, check before keeping {m.group(1)}:")
            for score, rid, status, topic in hits:
                print(f"  {rid} ({status}; similarity {score:.2f}): {topic}")
    return n


def mishearings():
    try:
        sys.path.insert(0, str(ROOT / "tools"))
        import mishear
        return mishear.load()
    except Exception:
        return []


CURATED = [K / "features", K / "topics", M / "outputs", K / "focus.json"]


def stale():
    """[(file, line, heard, means)] where a corrected mishearing is still written as fact."""
    out = []
    pairs = mishearings()
    if not pairs:
        return out
    files = []
    for c in CURATED:
        files += [c] if c.is_file() else list(c.rglob("*.md")) if c.exists() else []
    for f in files:
        text = f.read_text(encoding="utf-8")
        text = text.split("<!-- GENERATED", 1)[0]          # cards: only the curated part
        for i, line in enumerate(text.splitlines(), 1):
            plain = re.sub(r'"[^"]*"|“[^”]*”|\(transcript:[^)]*\)', "", line)   # quotes and marked transcript words are fine
            for heard, means, _ in pairs:
                if re.search(r"(?i)\b%s\b" % re.escape(heard), plain):
                    out.append((str(f.relative_to(ROOT)), i, heard, means))
    return out


def main(argv):
    sys.stdout.reconfigure(errors="replace")
    if argv[:1] == ["check"] and len(argv) == 2:
        n = check_entries(Path(argv[1]).read_text(encoding="utf-8"))
        print(f"{n} entr{'y' if n == 1 else 'ies'} may repeat a settled question." if n else "Nothing looks settled already.")
        return 0
    if argv[:1] == ["stale"]:
        rows = stale()
        for f, i, heard, means in rows:
            print(f"{f}:{i}  \"{heard}\" is written; the owner said it means \"{means}\"")
        print(f"{len(rows)} place(s)." if rows else "No corrected wording is still in use.")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
