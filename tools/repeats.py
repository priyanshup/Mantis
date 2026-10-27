"""Repetition check: what an output says twice (MANTIS-IMP-094). Stdlib, no AI.

    python tools/repeats.py FILE [FILE ...]   a page, epic or story (Markdown) or a brief or handover (JSON)
    python tools/repeats.py --outputs         every page, epic and story in mantis/outputs/

Flags a sentence that says nearly the same as another one (in the same section or another), and two
sections that largely say the same thing. The one summary at the top (At a glance, In one minute,
Summary) is meant to restate the body and is left out. Tables, headings, front matter, code and short
lines (under six content words: labels repeat by design) are skipped. Exit code 1 when something repeats.
"""
import json, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from answered import words   # the same content words the "asked before?" check uses

SUMMARY = re.compile(r"^(at a glance|in one minute|summary|in one paragraph)\b", re.I)
SAME, MIN_WORDS = 0.7, 6               # sentences: word overlap and the shortest one compared
SECTION_SAME, SECTION_MIN = 0.6, 25    # sections: share of the smaller one's words, and its least size


def units_md(text):
    """[(section, sentence)] from a Markdown output."""
    text = re.sub(r"(?s)\A---\n.*?\n---\n", "", text)
    text = re.sub(r"(?s)<!--.*?-->|```.*?```", "", text)
    out, sec = [], "Top"
    for line in text.splitlines():
        s = line.strip()
        label = re.fullmatch(r"\*\*([^*]+)\*\*:?", s)
        if s.startswith("#") or label:   # Jira text has bold labels (**Acceptance criteria**) where pages have headings
            sec = label.group(1) if label else s.lstrip("#").strip()
            continue
        # the team's epic format names each job again above its criteria ("MVP JTBD 1: ..."): a label, not a repeat
        if not s or s.startswith("|") or s.startswith("*Source") or re.match(r"(Post )?MVP JTBD \d+:", s):
            continue
        s = re.sub(r"^([-*+]|\d+\.)\s+", "", s)
        out += [(sec, x) for x in re.split(r"(?<=[.!?])\s+", s) if x.strip()]
    return out


def units_json(d):
    out = []
    for s in d.get("sections", []):
        for b in s.get("bullets", []):
            out += [(s["name"], x) for x in re.split(r"(?<=[.!?])\s+", " ".join([b.get("text", ""), b.get("detail", "")])) if x.strip()]
    return out


def check(units):
    """[(kind, where, a, b)] for what repeats."""
    rows = [(sec, t, words(t)) for sec, t in units if not SUMMARY.match(sec)]
    rows = [r for r in rows if len(r[2]) >= MIN_WORDS]
    found = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a, b = rows[i][2], rows[j][2]
            if len(a & b) / len(a | b) >= SAME:
                where = rows[i][0] if rows[i][0] == rows[j][0] else f"{rows[i][0]} / {rows[j][0]}"
                found.append(("sentence", where, rows[i][1], rows[j][1]))
    secs = {}
    for sec, _, w in rows:
        secs.setdefault(sec, set()).update(w)
    names = list(secs)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = secs[names[i]], secs[names[j]]
            small = min(len(a), len(b))
            if small >= SECTION_MIN and len(a & b) / small >= SECTION_SAME:
                found.append(("section", f"{names[i]} / {names[j]}", f"{round(100 * len(a & b) / small)}% of the words are shared", ""))
    return found


def check_file(p):
    p = Path(p)
    text = p.read_text(encoding="utf-8")
    return check(units_json(json.loads(text)) if p.suffix == ".json" else units_md(text))


def main(args):
    files = [p for p in (ROOT / "mantis" / "outputs").rglob("*.md") if p.name != "README.md"] if args == ["--outputs"] else [Path(a) for a in args]
    if not files:
        print(__doc__)
        return 2
    bad = 0
    for f in files:
        found = check_file(f)
        if not found:
            continue
        bad += 1
        print(f"{f.relative_to(ROOT) if f.is_absolute() and ROOT in f.parents else f}: {len(found)} repeat(s)")
        for kind, where, a, b in found:
            print(f"  {kind} in {where}:\n    {a[:160]}" + (f"\n    {b[:160]}" if b else ""))
    print(f"{len(files) - bad} of {len(files)} file(s) say each thing once." if bad else f"All {len(files)} file(s) say each thing once.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(errors="replace")
    sys.exit(main(sys.argv[1:]))
