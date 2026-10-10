"""Entity knowledge graph for Mantis (MANTIS-IMP-004). Stdlib only, deterministic.

Called by build_map.py. Reads the `key_entities` of every digest, the entity register
(mantis/knowledge/entity_register.md: canonical names, types, aliases, cited relations) and
the feature list, then writes:
    map/entities.json        the graph, read by tools/graph.py and the site
    map/entities.md          canonical entity -> documents (replaces the raw-name index)
    map/entity-graph.md      one line per entity: type, aliases, features, relations, neighbours
    map/entity-candidates.md possible duplicates for the owner to confirm (never merged here)
Merging: names equal after folding case, punctuation and a plural "s" merge automatically;
any other merge needs an alias row in the register.
"""
import json, re
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
K = ROOT / "mantis" / "knowledge"
OUT = K / "map"
TYPES = ("person", "system", "organisation", "distributor", "market", "team", "concept", "unknown")


def norm(name):
    k = re.sub(r"[^0-9a-z]", "", name.lower())
    return k[:-1] if len(k) > 4 and k.endswith("s") and not k.endswith("ss") else k


def table(text, heading):
    m = re.search(r"(?ms)^## %s[ \t]*$(.*?)(?=^## |\Z)" % heading, text)
    if not m:
        return []
    lines = [l for l in m.group(1).split("\n") if l.lstrip().startswith("|")]
    rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in lines]
    return [r for r in rows[2:] if r and r[0]]  # skip the header and the |---| row


def register():
    p = K / "entity_register.md"
    text = p.read_text(encoding="utf-8") if p.exists() else ""
    ents = {}
    for r in table(text, "Entities"):
        name, typ = r[0], (r[1] if len(r) > 1 and r[1] in TYPES else "unknown")
        aliases = [a.strip() for a in (r[2] if len(r) > 2 else "").split(",") if a.strip()]
        ents[name] = {"type": typ, "aliases": aliases}
    rels = [{"from": r[0], "rel": r[1], "to": r[2], "source": r[3] if len(r) > 3 else ""} for r in table(text, "Relations") if len(r) >= 3]
    return ents, rels


def build(docs, features):
    """docs: {doc_id: front matter}; features: list from build_map. Returns the graph dict."""
    reg, rels = register()
    alias = {}
    for name, e in reg.items():
        for n in [name] + e["aliases"]:
            alias[norm(n)] = name

    spellings = defaultdict(Counter)  # canonical key -> raw spellings
    mentions = defaultdict(set)       # canonical key -> docs
    doc_ents = defaultdict(set)
    for did, fm in docs.items():
        for raw in fm.get("key_entities", []):
            raw = raw.strip()
            if not raw:
                continue
            key = alias.get(norm(raw), norm(raw))
            spellings[key][raw] += 1
            mentions[key].add(did)
            doc_ents[did].add(key)
    for name in reg:  # register entries exist even before a digest names them
        spellings[name][name] += 0

    def display(key):
        return key if key in reg else spellings[key].most_common(1)[0][0]

    co = Counter()
    for did, keys in doc_ents.items():
        for a, b in combinations(sorted(keys), 2):
            co[(a, b)] += 1
    neigh = defaultdict(list)
    for (a, b), w in co.items():
        if w >= 2:
            neigh[a].append((b, w))
            neigh[b].append((a, w))

    feat_of = defaultdict(list)
    for f in features:
        fd = set(f["docs"])
        counts = Counter(k for d in fd for k in doc_ents.get(d, ()))
        for k, n in counts.items():
            feat_of[k].append((f["slug"], f["title"], n, f.get("kind", "feature")))

    ents = {}
    for key in spellings:
        name = display(key)
        regent = reg.get(key, {"type": "unknown", "aliases": []})
        ents[key] = {
            "id": name, "name": name, "type": regent["type"],
            "aliases": sorted({s for s in spellings[key] if s != name} | set(regent["aliases"])),
            "docs": sorted(mentions[key], reverse=True),
            "features": [{"slug": s, "title": t, "docs": n, "kind": k} for s, t, n, k in sorted(feat_of[key], key=lambda x: -x[2])],
            "neighbours": [[display(b), w] for b, w in sorted(neigh[key], key=lambda x: (-x[1], display(x[0])))[:12]],
            "relations": [],
        }
    by_name = {e["name"]: e for e in ents.values()}
    resolve = lambda n: by_name.get(n) or ents.get(alias.get(norm(n), norm(n)))
    problems = []
    for r in rels:
        a, b = resolve(r["from"]), resolve(r["to"])
        if not a or not b:
            problems.append(f"Relation names an unknown entity: {r['from']} -> {r['to']}")
            continue
        a["relations"].append({"rel": r["rel"], "to": b["name"], "source": r["source"], "dir": "out"})
        b["relations"].append({"rel": r["rel"], "to": a["name"], "source": r["source"], "dir": "in"})

    # Possible duplicates: one name contained in another, or equal once a brand prefix is dropped
    # (brand prefixes are local settings, mantis/config/settings.json).
    import local_config
    brands = [b.lower() for b in local_config.load().get("brand_prefixes", [])]
    # Pairs the owner said are different (register table "Not the same") are never asked again.
    _text = (K / "entity_register.md").read_text(encoding="utf-8") if (K / "entity_register.md").exists() else ""
    distinct = {frozenset((r[0].lower(), r[1].lower())) for r in table(_text, "Not the same") if len(r) >= 2}
    keys = [k for k in ents if len(ents[k]["docs"]) >= 2 and len(norm(ents[k]["name"])) >= 3]
    cands = []
    for a, b in combinations(sorted(keys), 2):
        short, long_ = sorted((norm(ents[a]["name"]), norm(ents[b]["name"])), key=len)
        if any(short == long_.replace(b, "") for b in brands) or long_.startswith(short) or (short in long_ and len(short) >= 5):
            if frozenset((ents[a]["name"].lower(), ents[b]["name"].lower())) not in distinct:
                cands.append((ents[a]["name"], ents[b]["name"], len(ents[a]["docs"]) + len(ents[b]["docs"])))
    cands.sort(key=lambda c: -c[2])

    graph = {"entities": sorted(ents.values(), key=lambda e: (-len(e["docs"]), e["name"].lower())),
             "candidates": [{"a": a, "b": b} for a, b, _ in cands], "problems": problems}
    write(graph, docs)
    return graph


def short(d):
    return d.replace("MANTIS-DOC-", "D")


def write(graph, docs):
    es = graph["entities"]
    (OUT / "entities.json").write_text(json.dumps(graph, indent=1, ensure_ascii=False), encoding="utf-8")
    rows = ["# Key entities", "", "Generated by `tools/kgraph.py`. Canonical name (aliases): documents. "
            "D0001 = MANTIS-DOC-0001. For one entity's links run `python tools/graph.py <name>`.", ""]
    for e in es:
        al = f" ({', '.join(e['aliases'])})" if e["aliases"] else ""
        rows.append(f"{e['name']}{al}: " + " ".join(short(d) for d in e["docs"]))
    (OUT / "entities.md").write_text("\n".join(rows) + "\n", encoding="utf-8")

    rows = ["# Entity graph", "", "Generated. Entities in two or more documents. Format: name [type] | docs | "
            "features | relations | most linked entities (shared documents).", ""]
    for e in es:
        if len(e["docs"]) < 2 and not e["relations"]:
            continue
        parts = [f"{e['name']} [{e['type']}]", f"{len(e['docs'])} docs"]
        if e["features"]:
            parts.append("features: " + ", ".join(f["slug"] for f in e["features"][:5]))
        if e["relations"]:
            parts.append("rel: " + "; ".join(f"{r['rel']} {r['to']}" if r["dir"] == "out" else f"{r['to']} {r['rel']} it" for r in e["relations"]))
        if e["neighbours"]:
            parts.append("linked: " + ", ".join(f"{n}({w})" for n, w in e["neighbours"][:6]))
        rows.append(" | ".join(parts))
    (OUT / "entity-graph.md").write_text("\n".join(rows) + "\n", encoding="utf-8")

    rows = ["# Possible duplicate entities", "", "Generated. Each pair might be one thing under two names. Nothing "
            "is merged until the owner confirms; then add an alias row to `mantis/knowledge/entity_register.md`.", ""]
    rows += [f"- {c['a']} / {c['b']}" for c in graph["candidates"]] or ["None."]
    (OUT / "entity-candidates.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
