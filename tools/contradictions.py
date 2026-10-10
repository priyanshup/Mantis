"""Contradiction check (MANTIS-IMP-047): what to compare when a source arrives or a summary is refreshed.

    python tools/contradictions.py context <document ID> [--with-source]   a source you just digested against its cards and closest sources
    python tools/contradictions.py context --card <slug>     a card's new sources against its curated summary

Code cannot tell whether two sentences disagree; Claude can. This tool only gathers the material,
cheaply: the source's Summary, Business Rules and Next Steps; the curated summary of every card
that links it; and the same parts of the three most similar sources. Dated statements (go-live,
launch, pilot, deadline...) are listed first, because a moved date is the most common clash.

What Claude does with it (docs/rules/WORKFLOW.md, ingest step 7 and "Refresh summary"): for each
statement that disagrees with the card or another source on a date, number, scope, owner or
meaning, record an unconfirmed conflict with both statements and their sources, status
"Unconfirmed (possible conflict found <date> by the contradiction check)". The owner settles it on
Open items: "Yes, they conflict", "The plan changed" or "Not a conflict". Nothing is overwritten
in the meantime: the card keeps its claim until the owner answers.
"""
import json, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "mantis"
sys.path.insert(0, str(Path(__file__).parent))
MARK = "<!-- GENERATED"
# The three closest sources are shown if they score at least this. It was 0.4, which left the check with no
# close source for 131 of 158 documents and missed the other side of every known conflict; 0.05 finds 4 of 6
# for about 900 more tokens per check (MANTIS-IMP-082, owner approved 2026-10-11). Watch the possible conflicts it raises.
FLOOR = 0.05
MON = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"
DATE = re.compile(r"\b(?:(?:early|mid|late|end of)\s+)?(?:(?:" + MON + r")[a-z]*\.?\s+20\d\d|q[1-4]\s*'?(?:20)?\d\d|h[12]\s+20\d\d|20\d\d-\d\d(?:-\d\d)?|(?:" + MON + r")[a-z]*\b)", re.I)
MILESTONE = re.compile(r"\b(go[- ]live|launch\w*|pilot|roll-?out|release[sd]?|deadline|mvp|deploy\w*|live|kick-?off|sunset|migrat\w+|cut-?over|due|by end)\b", re.I)


def section(text, name, limit):
    m = re.search(r"(?ms)^## %s\s*\n(.*?)(?=^## |\Z)" % re.escape(name), text)
    s = " ".join(m.group(1).split()) if m else ""
    return s if len(s) <= limit else s[:limit].rsplit(" ", 1)[0] + " …"


def digest(did):
    p = M / "02_digests" / f"{did}.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def title(text):
    m = re.search(r'(?m)^original_title:\s*"?(.*?)"?\s*$', text)
    return m.group(1) if m else "?"


def dated(text):
    body = re.sub(r"(?ms)^## (Change Log|References).*?(?=^## |\Z)", "", text.split("\n---", 2)[-1])
    return [s.strip() for s in re.split(r"(?<=[.;])\s+", " ".join(body.split()))
            if MILESTONE.search(s) and DATE.search(s) and len(s) < 360]


def card_of(slug):
    for folder in ("features", "topics"):
        p = M / "knowledge" / folder / f"{slug}.md"
        if p.exists():
            return p
    sys.exit(f"No card called {slug}.")


def curated(p):
    t = p.read_text(encoding="utf-8").split(MARK)[0]
    t = re.sub(r"\A---\n.*?\n---\n", "", t, flags=re.S)
    t = re.sub(r"(?s)<!--.*?-->", "", t)
    t = " ".join(t.split())
    return t if len(t) <= 3500 else t[:3500].rsplit(" ", 1)[0] + " …"


def show_source(did, full=True):
    t = digest(did)
    print(f"\n=== {did}: {title(t)}")
    print("Summary: " + section(t, "Summary", 1200 if full else 500))
    br = section(t, "Business Rules", 2500 if full else 900)
    if br:
        print("Business rules: " + br)
    ns = section(t, "Next Steps recorded in the source", 800 if full else 300)
    if ns:
        print("Next steps: " + ns)


def context_doc(did, with_source=False):
    import classify
    maps = json.loads((M / "knowledge" / "map" / "topics.json").read_text(encoding="utf-8")) + \
        json.loads((M / "knowledge" / "map" / "features.json").read_text(encoding="utf-8"))
    cards = [c for c in maps if did in c.get("docs", [])]
    print(f"CONTRADICTION CHECK for {did}. Compare the NEW SOURCE with each CARD and each CLOSE SOURCE below.")
    d = dated(digest(did))
    if d:
        print("\nDated statements in the new source (check these first):")
        for s in d[:12]:
            print("  - " + s)
    if with_source:   # at ingest Claude has just written this digest, so it is not printed again by default (MANTIS-IMP-057)
        print("\n--- NEW SOURCE ---")
        show_source(did)
    else:
        print(f"\n--- NEW SOURCE: {title(digest(did))} (the digest you just wrote; add --with-source to print its summary and rules) ---")
    for c in cards:
        p = M / c["card"]
        print(f"\n--- CARD {c['slug']} ({c['title']}): what Mantis currently says ---\n" + curated(p))
    w = json.loads(classify.CONFIG.read_text(encoding="utf-8"))["weights"]
    close = [(s, a if b == did else b) for s, a, b in classify.pair_scores(classify.corpus(), w, floor=FLOOR) if did in (a, b)][:3]
    for s, other in close:
        print(f"\n--- CLOSE SOURCE (similarity {s:.2f}) ---")
        show_source(other, full=False)
        od = dated(digest(other))
        if od:
            print("Dated statements: " + " | ".join(od[:6]))
    footer()


def context_card(slug):
    p = card_of(slug)
    cards = json.loads((M / "knowledge" / "map" / "topics.json").read_text(encoding="utf-8")) + \
        json.loads((M / "knowledge" / "map" / "features.json").read_text(encoding="utf-8"))
    c = next((x for x in cards if x["slug"] == slug), None)
    new = c.get("new_docs", []) if c else []
    print(f"CONTRADICTION CHECK for card {slug}: {len(new)} new source(s) against the curated summary.")
    print("\n--- CARD: what Mantis currently says ---\n" + curated(p))
    for did in new:
        print("\n--- NEW SOURCE ---")
        show_source(did, full=False)
        d = dated(digest(did))
        if d:
            print("Dated statements: " + " | ".join(d[:6]))
    if not new:
        print("\nNo new sources: nothing to compare.")
    footer()


def footer():
    print("\nFor each statement that disagrees (a date, number, scope, owner or meaning), record an UNCONFIRMED conflict:\n"
          "  python tools/entry.py next cfl   then write the entry from mantis/TEMPLATES/conflict-entry.md with\n"
          "  Statement A (what Mantis says, with its source), Statement B (the new source), and\n"
          "  - **Status:** Unconfirmed (possible conflict found <date> by the contradiction check)\n"
          "  python tools/entry.py add cfl <file>\n"
          "Do not change the card's claim: it stays until the owner answers on Open items. A newer plan that\n"
          "replaces an older one is still recorded this way; the owner answers 'The plan changed'.")


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) in (2, 3) and a[0] == "context" and a[1].startswith("MANTIS-DOC-"):
        context_doc(a[1], with_source="--with-source" in a)
    elif len(a) == 3 and a[0] == "context" and a[1] == "--card":
        context_card(a[2])
    else:
        sys.exit(__doc__)
