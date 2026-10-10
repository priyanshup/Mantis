"""Citation checks that code can do (MANTIS-IMP-078): do the cited sources exist and belong where they are cited?

    python tools/citations.py            every finding on cards and digests, errors first
    python tools/citations.py --errors   errors only

Checks the curated part of every card and the body of every digest:
  error    malformed-id      an ID with the wrong number of digits (a document number with three digits)
  error    missing-doc       a cited document has no digest
  error    missing-register  a cited gap, assumption, conflict, decision or asset is in no register
  warning  not-linked        a card cites a real document that is not linked to it: not among its sources,
                             not a related document of one of them, and not a source of a card it names.
                             It may be legitimate, so it is never an error.
  warning  uncited-rule      a card's business rule with no source: no ID and no source in words
                             ("owner answer, <date>", "user knowledge", "Confluence page", ...)
Shared sources are normal: a document linked to many cards is valid on each of them. Code only
checks that a citation resolves and belongs; whether the source says what the sentence claims is
the verifier's job (tools/support.py, MANTIS-IMP-079). Nothing is ever rewritten.
"""
import json, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import frontmatter

ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "mantis"
MARK = "<!-- GENERATED"
DIGITS = {"DOC": 4, "GAP": 3, "ASM": 3, "CFL": 3, "DEC": 3, "AST": 3}
ID = re.compile(r"\b(MANTIS-)?(DOC|GAP|ASM|CFL|DEC|AST)-(\d+)\b")
IN_WORDS = re.compile(r"\((?=[^)]*\b(owner|answer|user knowledge|source|confluence|sme|research|transcript|deck|slide|page|session|meeting)\b)[^)]*\)", re.I)
_CTX = {}


def context():
    """Known IDs, related documents and card sources, read once."""
    if _CTX:
        return _CTX
    import entry
    known = {k.upper(): set(entry.ids_in(k)) for k in ("doc", "gap", "asm", "cfl", "dec", "ast")}
    related = {}
    for p in (M / "02_digests").glob("MANTIS-DOC-*.md"):
        for r in frontmatter.parse(p.read_text(encoding="utf-8")).get("related_documents", []) or []:
            related.setdefault(p.stem, set()).add(r)
            related.setdefault(r, set()).add(p.stem)
    cards = {}
    for f in ("features.json", "topics.json"):
        mp = M / "knowledge" / "map" / f
        for c in (json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else []):
            cards[c["slug"]] = {"docs": set(c.get("docs", [])), "path": M / c["card"]}
    _CTX.update(known=known, related=related, cards=cards)
    return _CTX


def full(prefix, kind, num):
    return f"MANTIS-{kind}-{num}"


def check_ids(text, where):
    """Errors for IDs that are malformed or resolve to nothing."""
    ctx, out = context(), []
    for m in ID.finditer(text):
        kind, num = m.group(2), m.group(3)
        rid = full(m.group(1), kind, num)
        line = text[:m.start()].count("\n") + 1
        if len(num) != DIGITS[kind]:
            out.append({"level": "error", "code": "malformed-id", "where": where, "line": line,
                        "msg": f"{m.group(0)} has {len(num)} digits; {kind} IDs have {DIGITS[kind]}"})
        elif rid not in ctx["known"][kind]:
            out.append({"level": "error", "code": "missing-doc" if kind == "DOC" else "missing-register", "where": where, "line": line,
                        "msg": f"{rid} is cited but " + ("has no digest" if kind == "DOC" else "is in no register")})
    return out


def check_card(text, card_docs, where="card", ctx_override=None):
    """Findings for one card's curated text. card_docs: the documents linked to the card."""
    ctx = context()
    cur = text.split(MARK)[0]
    out = check_ids(cur, where)
    allowed = set(card_docs)
    for d in card_docs:
        allowed |= ctx["related"].get(d, set())
    for slug in set(re.findall(r"([a-z0-9][a-z0-9-]+)\.md\b", cur)):   # sources of a card this card names ("see customer-groups.md")
        allowed |= ctx["cards"].get(slug, {}).get("docs", set())
    for m in ID.finditer(cur):
        rid = full(m.group(1), m.group(2), m.group(3))
        if m.group(2) == "DOC" and rid in ctx["known"]["DOC"] and rid not in allowed:
            out.append({"level": "warning", "code": "not-linked", "where": where, "line": cur[:m.start()].count("\n") + 1,
                        "msg": f"{rid} is cited but not linked to this card, nor related to one of its sources"})
    rules = re.search(r"(?ms)^## Business rules agreed so far\s*$(.*?)(?=^## |\Z)", cur)
    if rules:
        start = cur[:rules.start(1)].count("\n")
        for i, line in enumerate(rules.group(1).splitlines()):
            if re.match(r"^- \S", line) and not ID.search(line) and not IN_WORDS.search(line):
                out.append({"level": "warning", "code": "uncited-rule", "where": where, "line": start + i + 1,
                            "msg": "business rule with no source: " + line[2:90]})
    # a not-linked warning for an ID already reported as an error would only repeat it
    return [f for f in out if not (f["code"] == "not-linked" and any(e["level"] == "error" and e["line"] == f["line"] for e in out))]


def shift(found, text, body):
    """Line numbers count from the top of the file, not from the end of the front matter."""
    off = text[:len(text) - len(body)].count("\n")
    return [dict(f, line=f["line"] + off) for f in found]


def scan():
    ctx, out = context(), []
    for slug, c in sorted(ctx["cards"].items()):
        if c["path"].exists():
            text = c["path"].read_text(encoding="utf-8")
            fm, body = frontmatter.split(text)
            docs = c["docs"] | set(fm.get("source_documents", []) or [])
            out += shift(check_card(body, docs, where=c["path"].relative_to(M).as_posix()), text, body)
    for p in sorted((M / "02_digests").glob("MANTIS-DOC-*.md")):
        text = p.read_text(encoding="utf-8")
        body = frontmatter.split(text)[1]
        out += shift(check_ids(body, p.relative_to(M).as_posix()), text, body)
    return sorted(out, key=lambda f: (f["level"] != "error", f["where"], f["line"]))


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    found = scan()
    if "--errors" in argv:
        found = [f for f in found if f["level"] == "error"]
    for f in found:
        print(f"{f['level'].upper():<7} {f['code']:<16} {f['where']}:{f['line']}  {f['msg']}")
    e = sum(f["level"] == "error" for f in found)
    print(f"{e} error(s), {len(found) - e} warning(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
