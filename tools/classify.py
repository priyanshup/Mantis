"""Classify a new document against the corpus before ingest (MANTIS-IMP-005). Stdlib only.

    python tools/classify.py --title "Title" --topics a,b,c --entities "X, Y, Z"
    python tools/classify.py --digest path/to/draft-digest.md     (reads title, topics, entities)
    python tools/classify.py --calibrate                          (prints the corpus score spread)

Scores each existing digest by title, topic and entity overlap (0 to 1) and gives a verdict
using the cut-offs in tools/classify_config.json:
    score >= version  -> likely a NEW VERSION of the top match: proceed as a version, report it
    score <  new      -> NEW DOCUMENT: proceed without asking
    otherwise         -> AMBIGUOUS: stop and ask the owner (WORKFLOW_RULES, Ingestion step 3)
Entities are compared on canonical names, so a product and its registered alias count as one.
"""
import argparse, json, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "mantis"
CONFIG = Path(__file__).with_name("classify_config.json")
RECURRING = re.compile(r"(weekly|daily|monthly|sync|stand-?up|retro|meeting with)", re.I)
STOP = {"the", "a", "an", "and", "or", "of", "for", "to", "in", "on", "with", "by", "from", "page", "pasted",
        "transcript", "summary", "untitled", "notes", "meeting", "session", "doc", "document", "v1", "v2"}


def front(text):
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    fm = {}
    for line in (m.group(1) if m else "").splitlines():
        k, _, v = line.partition(":")
        v = v.strip()
        if v.startswith("[") and v.endswith("]"):
            fm[k] = [x.strip().strip('"') for x in v[1:-1].split(",") if x.strip()]
        elif k and not line.startswith(" "):
            fm[k] = v.strip('"')
    return fm


def aliases():
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        import kgraph
        reg, _ = kgraph.register()
        out = {}
        for name, e in reg.items():
            for n in [name] + e["aliases"]:
                out[kgraph.norm(n)] = kgraph.norm(name)
        return out, kgraph.norm
    except Exception:
        n = lambda s: re.sub(r"[^0-9a-z]", "", s.lower())
        return {}, n


ALIAS, NORM = aliases()


def words(title):
    return {w for w in re.findall(r"[a-z0-9]+", title.lower()) if w not in STOP and len(w) > 1}


def ents(values):
    return {ALIAS.get(NORM(v), NORM(v)) for v in values if NORM(v)}


def jac(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0


def score(fp, fm, w):
    t = 1.0 if fp["title"].strip().lower() == fm.get("original_title", "").strip().lower() else jac(words(fp["title"]), words(fm.get("original_title", "")))
    return round(w["title"] * t + w["topics"] * jac(set(fp["topics"]), set(fm.get("topics", []))) +
                 w["entities"] * jac(ents(fp["entities"]), ents(fm.get("key_entities", []))), 3)


def corpus():
    return {p.stem: front(p.read_text(encoding="utf-8")) for p in sorted((M / "02_digests").glob("MANTIS-DOC-*.md"))}


def fingerprint(fm):
    return {"title": fm.get("original_title", ""), "topics": fm.get("topics", []), "entities": fm.get("key_entities", [])}


def classify(fp, docs, cfg):
    ranked = sorted(((score(fp, fm, cfg["weights"]), d, fm.get("original_title", "")) for d, fm in docs.items()), reverse=True)
    top = ranked[0][0] if ranked else 0
    verdict = ("NEW VERSION of " + ranked[0][1]) if top >= cfg["version"] else "NEW DOCUMENT" if top < cfg["new"] else "AMBIGUOUS: ask the owner"
    if verdict.startswith("NEW VERSION") and RECURRING.search(fp["title"] + " " + ranked[0][2]):
        verdict = "AMBIGUOUS: ask the owner (recurring meeting: a new instance is a new document, not a version)"
    return verdict, ranked[:5]


def calibrate(docs, cfg):
    best = []
    for d, fm in docs.items():
        others = {k: v for k, v in docs.items() if k != d}
        s, k, _ = max((score(fingerprint(fm), v, cfg["weights"]), k, 0) for k, v in others.items())
        best.append((s, d, k))
    best.sort()
    q = lambda f: best[min(len(best) - 1, int(f * len(best)))][0]
    print(f"Closest-other-document score across {len(best)} digests: min {best[0][0]}, p25 {q(.25)}, median {q(.5)}, p75 {q(.75)}, p90 {q(.9)}, max {best[-1][0]}")
    print("Highest pairs:", ", ".join(f"{d[-4:]}~{k[-4:]} {s}" for s, d, k in best[-6:]))
    import local_config   # known version pairs live in mantis/config/settings.json (local)
    for pair in local_config.load().get("classify_known_version_pairs", []):
        arch = M / pair["archived"]
        if arch.exists() and pair["current"] in docs:
            old = front(arch.read_text(encoding="utf-8"))
            print(f"Known version pair {pair['current']} (archived vs current): {score(fingerprint(old), docs[pair['current']], cfg['weights'])}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="")
    ap.add_argument("--topics", default="")
    ap.add_argument("--entities", default="")
    ap.add_argument("--digest")
    ap.add_argument("--calibrate", action="store_true")
    a = ap.parse_args()
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    docs = corpus()
    if a.calibrate:
        calibrate(docs, cfg)
        sys.exit()
    if a.digest:
        fm = front(Path(a.digest).read_text(encoding="utf-8"))
        docs.pop(fm.get("document_id", ""), None)
        fp = fingerprint(fm)
    else:
        fp = {"title": a.title, "topics": [x.strip() for x in a.topics.split(",") if x.strip()],
              "entities": [x.strip() for x in a.entities.split(",") if x.strip()]}
    verdict, top = classify(fp, docs, cfg)
    print(f"Verdict: {verdict}  (cut-offs: new < {cfg['new']}, version >= {cfg['version']})")
    for s, d, t in top:
        print(f"  {s:.3f}  {d}  {t[:80]}")
    # Which cards the document joins through its topic tags, and which open items it may bear on,
    # so the cross-check reads a handful of entries instead of the whole register.
    MAPD = M / "knowledge" / "map"
    try:
        cards_ = json.loads((MAPD / "features.json").read_text(encoding="utf-8")) + json.loads((MAPD / "topics.json").read_text(encoding="utf-8"))
        tags = set(fp["topics"])
        hits = []
        for c in cards_:
            card_fm = front((M / c["card"]).read_text(encoding="utf-8"))
            if tags & set(card_fm.get("match_topics", [])):
                hits.append(c["slug"])
        print("Joins cards: " + (", ".join(hits) if hits else "none by tag. Add a matching tag, or a card's tag to the digest, if it belongs to one."))
        items = json.loads((MAPD / "open-items.json").read_text(encoding="utf-8"))
        mine = ents(fp["entities"]) | {NORM(t) for t in fp["topics"]}
        fw = words(fp["title"]) | {w for t in fp["topics"] for w in words(t.replace("-", " "))}
        scored = []
        for o in items:
            oe = set()
            for d in o["docs"]:
                oe |= ents(docs.get(d["id"], {}).get("key_entities", []))
            s = 0.6 * jac(mine, oe) + 0.4 * jac(fw, words(o["topic"]))
            if s > 0:
                scored.append((round(s, 3), o["id"], o["topic"][:90]))
        scored.sort(reverse=True)
        print("Open items to check (python tools/entry.py show <ID>):")
        for s, i, t in scored[:6]:
            print(f"  {s:.3f}  {i}  {t}")
    except FileNotFoundError:
        pass
