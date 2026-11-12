"""Where do things stand on a subject? A few hundred tokens instead of the card and its digests (IMP-109).

    python tools/context.py rollout              a feature or topic card: its lead, outcome and next decision, the open questions,
                                               the people and systems, the newest sources, and where to read more
    python tools/context.py "Sam Lee"          a person or system: where they appear, their cited relations, their sources
    python tools/context.py rollout --max 900    a tighter answer (default 2400 characters, about 600 tokens)
    python tools/context.py rollout --entity     the system or person of that name, when a card has the same name
    python tools/context.py rollout --files     the files that hold the subject and what each costs to read (topic-files.json)

It reads only the generated map (mantis/knowledge/map) and the card's own lead, plus the first line of a few digests. Start here, then use the pointers on its
last line: `peek.py <id>` for a digest's summary, `peek.py <id> --section "<name>"` for one section, the card file for its curated part.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import difflib, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "mantis"
MAP = M / "knowledge" / "map"
MARK = "<!-- GENERATED"
PRIO = {"Critical": 0, "High": 1, "": 2, "Medium": 3, "Low": 4}
ID_PAREN = re.compile(r"\s*\((?:MANTIS-)?(?:DOC|GAP|ASM|CFL|DEC)-\d+(?:[,;]\s*(?:MANTIS-)?(?:DOC|GAP|ASM|CFL|DEC)-\d+)*\)")


def _json(name, default):
    p = MAP / name
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _clean(text):
    return re.sub(r"\s+", " ", ID_PAREN.sub("", re.sub(r"\*\*|\*|`", "", text))).strip()


def _sentences(text):
    return re.split(r"(?<=[.!?])\s+", _clean(text))


def _short(text, n):
    return text if len(text) <= n else text[:n - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def _curated(card):
    p = M / card.get("card", "")
    try:
        return p.read_text(encoding="utf-8").replace("\r\n", "\n").split(MARK)[0]
    except OSError:
        return ""


def lead(curated, limit=260):
    """The first sentence of 'In one paragraph', plus the second when the two together stay short."""
    m = re.search(r"(?ms)^## In one paragraph\s*\n(.*?)(?=^## |\Z)", curated)
    if not m:
        return ""
    s = [x for x in _sentences(m.group(1)) if x]
    out = s[0] if s else ""
    if len(s) > 1 and len(out) + len(s[1]) < 190:
        out += " " + s[1]
    return _short(out, limit)


def fact(curated, label):
    m = re.search(rf"(?m)^- \*\*{re.escape(label)}:\*\*\s*(.+)$", curated)
    return _short(_clean(m.group(1)), 170) if m else ""


def summary_line(doc, n=110):
    try:
        text = (M / "02_digests" / f"{doc}.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    except OSError:
        return ""
    m = re.search(r"(?ms)^## Summary\s*\n(.*?)(?=^## |\Z)", text)
    return _short(_sentences(m.group(1))[0], n) if m and m.group(1).strip() else ""


def resolve(subject, features, topics, entities, entity_only=False):
    """('card', card) or ('entity', entity). Exact slug, title, name or alias first, then a start, then a part; several matches at a step raise instead of guessing.
    A card and a name that match at the same step: the card wins (ask for the name with --entity)."""
    q = subject.strip().lower()
    cands = [] if entity_only else [("card", c, [c["slug"].lower(), c["title"].lower()]) for c in features + topics]
    cands += [("entity", e, [e["name"].lower(), *[a.lower() for a in e.get("aliases", [])]]) for e in entities]
    for test in (lambda k: k == q, lambda k: k.startswith(q), lambda k: q in k):
        hits = [(kind, obj) for kind, obj, keys in cands if any(test(k) for k in keys)]
        one_card = [h for h in hits if h[0] == "card"]
        if len(one_card) == 1:
            return one_card[0]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            names = [(o.get("title") or o["name"]) + (f" ({kind})" if kind == "card" else f" ({o['type']})") for kind, o in hits[:6]]
            raise LookupError(f"'{subject}' matches {len(hits)}: " + "; ".join(names) + ". Use the full name.")
    pool = [k for _, _, keys in cands for k in keys]
    close = difflib.get_close_matches(q, pool, n=4, cutoff=0.6)
    raise LookupError(f"no card or name matches '{subject}'" + (". Closest: " + ", ".join(close) if close else "") + ". python tools/graph.py top lists names.")


def _people(entities, slug):
    got = []
    for e in entities:
        for f in e.get("features", []):
            if f["slug"] == slug:
                got.append((f["docs"], e))
    got.sort(key=lambda t: (-t[0], t[1]["name"]))
    return got


def card_context(c, features_open, entities, max_chars):
    cur = _curated(c)
    head = f"{c['title']} ({c.get('type') or c.get('kind', 'card')}"
    for label, key in (("", "status"), ("", "priority")):
        if c.get(key):
            head += f", {c[key]}"
    head += (f", Jira {c['jira']}" if c.get("jira") and c["jira"] != "none" else "") + (f", updated {c['updated']}" if c.get("updated") else "") + ")"
    lines = [head]
    import cardkeys
    keys = cardkeys.summary(_json("card-keys.json", {}).get(c["slug"]))
    if keys:
        lines.append("Keys: " + keys)
    if lead(cur):
        lines.append("Lead: " + lead(cur))
    for label in ("Outcome wanted", "Next decision"):
        v = fact(cur, label)
        if v:
            lines.append(f"{'Outcome' if label.startswith('Outcome') else label}: {v}")
    opens = sorted((o for o in features_open if c["slug"] in (o.get("features") or []) and o.get("status", "").lower() not in ("closed", "resolved")),
                   key=lambda o: (PRIO.get(o.get("priority", ""), 2), o["id"]))
    open_lines = [f"  {o['id']} {o.get('priority') or '-'}: {_short(o['topic'], 95)}" for o in opens]
    people = [e for _, e in _people(entities, c["slug"])]
    ppl = [f"{e['name']} ({n})" for n, e in _people(entities, c["slug"]) if e["type"] == "person"][:6]
    sysl = [f"{e['name']}" for n, e in _people(entities, c["slug"]) if e["type"] not in ("person", "concept", "unknown")][:6]
    docs = sorted(c.get("docs", []), reverse=True)
    src_lines = [f"  {d}: {summary_line(d)}" for d in docs[:5]]
    more = (f"More: {c.get('card', '')} (curated part first); python tools/peek.py <id> [--section \"<name>\"] for a source; "
            f"python tools/graph.py <name> for a person or system.")

    def assemble(n_open, n_src, with_lead=True):
        out = [lines[0]] + ([l for l in lines[1:] if with_lead or not l.startswith("Lead:")])
        out.append(f"Open ({len(opens)}):" if opens else "Open: none")
        out += open_lines[:n_open]
        if len(opens) > n_open and n_open:
            out.append(f"  (+{len(opens) - n_open} more: python tools/entry.py show <ID>)")
        if ppl:
            out.append("People: " + ", ".join(ppl))
        if sysl:
            out.append("Systems: " + ", ".join(sysl))
        out.append(f"Sources ({len(docs)}), newest first:" if docs else "Sources: none")
        out += src_lines[:n_src]
        out.append(more)
        return "\n".join(out)

    for n_open, n_src, with_lead in ((5, 5, True), (4, 4, True), (3, 3, True), (2, 2, True), (1, 1, True), (0, 0, True), (0, 0, False)):
        text = assemble(n_open, n_src, with_lead)
        if len(text) <= max_chars:
            return text
    return text[:max(0, max_chars - len(more) - 2)].rstrip() + "…\n" + more   # a budget this small keeps only the first lines and the pointer


def entity_context(e, cards, max_chars):
    names = {c["slug"]: c["title"] for c in cards}
    head = f"{e['name']} ({e['type']}" + (f"; also {', '.join(e['aliases'][:4])}" if e.get("aliases") else "") + ")"
    where = ", ".join(f"{f['title']} ({f['docs']})" for f in sorted(e.get("features", []), key=lambda f: -f["docs"])[:6])
    rels = [f"{r['rel']} {r['to']}" if r.get("dir") == "out" else f"{r['to']} {r['rel']} it" for r in e.get("relations", [])[:6]]
    docs = sorted(e.get("docs", []), reverse=True)
    lines = [head, "Appears in: " + (where or "no card yet")]
    if rels:
        lines.append("Relations: " + "; ".join(rels))
    lines.append(f"Sources ({len(docs)}), newest first:")
    lines += [f"  {d}: {summary_line(d)}" for d in docs[:4]]
    more = f"More: python tools/graph.py \"{e['name']}\"; python tools/peek.py <id> [--section \"<name>\"] for a source."
    lines.append(more)
    text = "\n".join(lines)
    return text if len(text) <= max_chars else text[:max(0, max_chars - len(more) - 2)].rstrip() + "…\n" + more


def _kb(n):
    return f"{n / 1000:.1f} KB" if n >= 1000 else f"{n} B"


def files_listing(subject):
    """The files that hold a subject's knowledge and what each costs to read (the file-to-topic map, topicmap.py)."""
    features, topics = _json("features.json", []), _json("topics.json", [])
    kind, obj = resolve(subject, features, topics, [])
    entry = _json("topic-files.json", {}).get(obj["slug"])
    if not entry:
        raise LookupError(f"{obj['title']} is not in the file map yet; run python tools/build_map.py")
    lines = [f"{entry['title']}: files, biggest cost first",
             f"Card: {entry['card']} {_kb(entry['card_bytes'])} (read the curated part first: {_kb(entry['curated_bytes'])})"]
    ds = sorted(entry["digests"], key=lambda d: -d["bytes"])
    lines.append(f"Digests ({len(ds)}, {_kb(entry['digest_bytes'])} in all; a summary is `peek.py <id>`, a section `--section`):")
    lines += [f"  {d['id']} {_kb(d['bytes'])}" for d in ds[:12]] + ([f"  (+{len(ds) - 12} smaller)"] if len(ds) > 12 else [])
    if entry["outputs"]:
        lines.append("Outputs: " + ", ".join(f"{o['file']} {_kb(o['bytes'])}" for o in entry["outputs"]))
    lines.append(f"Open questions: {entry['open']}")
    return "\n".join(lines)


def render(subject, max_chars=2400, entity=False):
    features, topics = _json("features.json", []), _json("topics.json", [])
    entities = _json("entities.json", {}).get("entities", [])
    kind, obj = resolve(subject, features, topics, entities, entity_only=entity)
    if kind == "card":
        text = card_context(obj, _json("open-items.json", []), entities, max_chars)
        also = [e for e in entities if e["name"].lower() == subject.strip().lower() and e["type"] not in ("concept", "unknown")]
        return text + (f"\nAlso a {also[0]['type']}: python tools/context.py \"{also[0]['name']}\" --entity" if also else "")
    return entity_context(obj, features + topics, max_chars)


def main(argv):
    mx, entity, files = 2400, "--entity" in argv, "--files" in argv
    argv = [a for a in argv if a not in ("--entity", "--files")]
    if "--max" in argv:
        i = argv.index("--max")
        mx = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    if not argv:
        print(__doc__)
        return 2
    try:
        print(files_listing(" ".join(argv)) if files else render(" ".join(argv), mx, entity))
    except LookupError as e:
        print(e)
        return 1
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv[1:]))
