"""Import the team's estimation sheet onto the roadmap cards (MANTIS-IMP-053).

    python tools/estimates.py preview FILE                     show each row and the card it would go to
    python tools/estimates.py apply FILE --doc <document ID>   write the estimates onto the matched cards
        [--map "row text=card-slug" ...]                       fix a match the preview got wrong, or add one
        [--skip "row text" ...]                                leave a row out

FILE is the sheet itself (.xlsx, .csv) or its Markdown table. The header row is found by its
column names: an item column (initiative, feature, item, epic, title, name, topic), and any of
complexity, effort (size, t-shirt, estimate, points) and notes (comment, remarks, assumptions).
Each row is matched to a card by the words it shares with the card's title, slug and match tags;
weak matches are listed, never applied. `apply` writes `estimate_2027` (for example "High
complexity, Extra large effort") and `estimate_source` (the sheet's document ID) into each
matched card's front matter, so the Roadmap and the cards show it. Ingest the sheet as a document
first (docs/rules/WORKFLOW.md), so the estimate is cited. Needs openpyxl for .xlsx.
"""
import csv, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
K = ROOT / "mantis" / "knowledge"
ITEM = re.compile(r"initiative|feature|item|epic|title|name|topic|capabilit|requirement", re.I)
COLS = {"complexity": re.compile(r"complex", re.I), "effort": re.compile(r"effort|size|t-?shirt|estimat|points?|sp\b", re.I),
        "notes": re.compile(r"note|comment|remark|assumption|scope", re.I)}
STOP = {"the", "a", "an", "and", "or", "of", "for", "to", "in", "on", "with", "by", "from", "feature", "management", "mvp",
        "new", "support"}
try:   # words too common in this instance to tell cards apart (product names): mantis/config/settings.json "estimate_stopwords"
    sys.path.insert(0, str(Path(__file__).parent))
    import local_config
    STOP |= {w.lower() for w in local_config.load().get("estimate_stopwords", [])}
except Exception:
    pass
SIZES = {"xs": "Extra small", "s": "Small", "m": "Medium", "l": "Large", "xl": "Extra large", "xxl": "Extra extra large",
         "low": "Low", "medium": "Medium", "med": "Medium", "high": "High", "very high": "Very high"}
MIN_SCORE = 0.34


def rows_of(path):
    p = Path(path)
    if p.suffix.lower() in (".xlsx", ".xlsm"):
        import openpyxl
        wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
        grid = [[("" if v is None else str(v)).strip() for v in r] for ws in wb.worksheets for r in ws.iter_rows(values_only=True)]
    elif p.suffix.lower() == ".csv":
        grid = [[c.strip() for c in r] for r in csv.reader(p.read_text(encoding="utf-8-sig").splitlines())]
    else:   # a Markdown table
        grid = [[c.strip() for c in l.strip().strip("|").split("|")] for l in p.read_text(encoding="utf-8").splitlines()
                if l.strip().startswith("|") and not re.match(r"^\|[\s:|-]+\|$", l.strip())]
    for i, r in enumerate(grid):   # header: the first row with an item column and one more known column
        cols = {k: next((j for j, c in enumerate(r) if rx.search(c or "")), None) for k, rx in COLS.items()}
        item = next((j for j, c in enumerate(r) if ITEM.search(c or "")), None)
        if item is not None and (cols["complexity"] is not None or cols["effort"] is not None):
            out = []
            for row in grid[i + 1:]:
                get = lambda j: row[j].strip() if j is not None and j < len(row) and row[j] else ""
                if get(item):
                    out.append({"item": get(item), "complexity": get(cols["complexity"]), "effort": get(cols["effort"]), "notes": get(cols["notes"])})
            return out
    sys.exit("No header row found: the sheet needs an item column (initiative, feature, item...) and a complexity or effort column.")


def words(s):
    return {w[:-1] if len(w) > 4 and w.endswith("s") else w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP and len(w) > 2}


def cards():
    sys.path.insert(0, str(Path(__file__).parent))
    from build_site import front_matter
    out = []
    for folder in ("features", "topics"):
        for p in sorted((K / folder).glob("*.md")):
            if p.name == "README.md":
                continue
            fm = front_matter(p.read_text(encoding="utf-8"))[0]
            tags = re.findall(r"[\w-]+", fm.get("match_topics", ""))
            out.append({"slug": p.stem, "title": fm.get("title", p.stem), "path": p,
                        "words": words(fm.get("title", "") + " " + p.stem.replace("-", " ") + " " + " ".join(t.replace("-", " ") for t in tags))})
    return out


def match(row, cs):
    w = words(row["item"])
    scored = sorted(((len(w & c["words"]) / max(1, len(w)), c) for c in cs), key=lambda x: -x[0])
    return scored[0] if scored and scored[0][0] > 0 else (0, None)


def label(v, what):
    v = v.strip()
    if not v:
        return ""
    return f"{SIZES.get(v.lower(), v)} {what}"


def plan(path, maps=(), skips=()):
    cs = cards()
    by_slug = {c["slug"]: c for c in cs}
    forced = {}
    for m in maps:
        text, _, slug = m.rpartition("=")
        if slug not in by_slug:
            sys.exit(f"--map: no card '{slug}'.")
        forced[text.strip().lower()] = by_slug[slug]
    out = []
    for r in rows_of(path):
        if r["item"].lower() in {s.lower() for s in skips}:
            continue
        if r["item"].lower() in forced:
            score, c = 1.0, forced[r["item"].lower()]
        else:
            score, c = match(r, cs)
        value = ", ".join(x for x in (label(r["complexity"], "complexity"), label(r["effort"], "effort")) if x)
        out.append({**r, "card": c, "score": score, "value": value})
    return out


def preview(path, maps=(), skips=()):
    p = plan(path, maps, skips)
    for r in p:
        ok = r["card"] and r["score"] >= MIN_SCORE
        target = f"{r['card']['slug']} ({r['score']:.2f})" if r["card"] else "-"
        print(f"{'OK  ' if ok else 'WEAK' if r['card'] else 'NONE'} {r['item'][:60]:60} -> {target:32} {r['value'] or '(no size)'}")
    weak = [r for r in p if not (r["card"] and r["score"] >= MIN_SCORE)]
    if weak:
        print(f"\n{len(weak)} row(s) not matched with confidence. Fix with --map \"row text=card-slug\" or leave them with --skip.")
    return p


def apply(path, doc, maps=(), skips=()):
    if not re.fullmatch(r"MANTIS-DOC-\d{4}", doc or ""):
        sys.exit("apply needs --doc <the sheet's document ID>: ingest the sheet first so the estimate is cited.")
    done = 0
    for r in plan(path, maps, skips):
        if not (r["card"] and r["score"] >= MIN_SCORE and r["value"]):
            continue
        p = r["card"]["path"]
        t = p.read_text(encoding="utf-8")
        head, body = t.split("\n---", 1) if t.startswith("---") else ("", t)
        val = r["value"].replace('"', "'")
        head = re.sub(r'(?m)^estimate_2027:.*$', f'estimate_2027: "{val}"', head) if re.search(r"(?m)^estimate_2027:", head) else head + f'\nestimate_2027: "{val}"'
        head = re.sub(r'(?m)^estimate_source:.*$', f"estimate_source: {doc}", head) if re.search(r"(?m)^estimate_source:", head) else head + f"\nestimate_source: {doc}"
        p.write_text(head + "\n---" + body, encoding="utf-8")
        print(f"{r['card']['slug']}: {val}")
        done += 1
    print(f"{done} card(s) updated. Run python tools/build_map.py.")


if __name__ == "__main__":
    a = sys.argv[1:]
    take = lambda flag: [a[i + 1] for i, x in enumerate(a) if x == flag and i + 1 < len(a)]
    if len(a) >= 2 and a[0] == "preview":
        preview(a[1], take("--map"), take("--skip"))
    elif len(a) >= 2 and a[0] == "apply":
        apply(a[1], (take("--doc") or [""])[0], take("--map"), take("--skip"))
    else:
        sys.exit(__doc__)
