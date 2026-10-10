"""Build Mantis's navigation map and reference graph (stdlib only, deterministic).

Reads digest front matter, feature cards, outputs and the gap/assumption/conflict
registers, then writes compact lookup files to mantis/knowledge/map/, lints the
registers, and rebuilds the browser site (tools/build_site.py). Run from anywhere:
    python tools/build_map.py
Outputs are derived data. Never edit them by hand; rerun after any ingest or edit.
"""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import json, re, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# One build at a time: the site server, a background job and a chat session can all start one.
# The next waits for the lock (a stale lock older than 3 minutes is taken over).
import atexit, os, time
_LOCK = (Path(os.environ["LOCALAPPDATA"]) / "Mantis" if os.environ.get("LOCALAPPDATA") else ROOT) / "build.lock"
_LOCK.parent.mkdir(parents=True, exist_ok=True)
for _ in range(600):
    try:
        os.close(os.open(_LOCK, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        break
    except FileExistsError:
        try:
            if time.time() - _LOCK.stat().st_mtime > 180:
                _LOCK.unlink(missing_ok=True)
        except OSError:
            pass
        time.sleep(0.25)
atexit.register(lambda: _LOCK.unlink(missing_ok=True))
M = ROOT / "mantis"
OUT = M / "knowledge" / "map"
ID_RE = re.compile(r"MANTIS-(?:DOC|GAP|ASM|CFL|DEC)-\d+")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import textcache   # unchanged files are not reopened (MANTIS-IMP-016)


def front_matter(text):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    fm = {}
    if not m:
        return fm
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        v = v.strip()
        if v.startswith("[") and v.endswith("]"):
            fm[k] = [x.strip().strip('"') for x in v[1:-1].split(",") if x.strip()]
        elif k and not line.startswith(" "):
            fm[k] = v.split(" #")[0].strip().strip('"')
    return fm


def registers(folder, prefix):
    """Read registers/<folder>/<ID>.md (one entry per file) into {id: {topic, status, docs}}."""
    out = {}
    for p in sorted((M / "knowledge" / "registers" / folder).glob(prefix + "*.md")):
        for blk in re.split(r"(?m)^### ", textcache.read(p))[1:]:
            rid = blk.split("\n", 1)[0].strip().split()[0]
            if not rid.startswith(prefix):
                continue
            def field(label):
                f = re.search(r"\*\*%s:\*\*\s*(.+?)(?=\n- \*\*|\n\n|\Z)" % label, blk, re.S)
                return " ".join(f.group(1).split()) if f else ""
            out[rid] = {
                "topic": field("Topic") or field("Claim") or field("Title"),
                "status": field("Status").split("(")[0].strip(),
                "status_raw": field("Status"),
                "raised": (field("Date raised") or field("Date") or "")[:10],
                "priority": next((p for p in PRIORITIES if field("Priority").lower().startswith(p.lower())), ""),
                "detail": [[k.strip(), " ".join(v.split())[:1500]] for k, v in re.findall(r"(?ms)^- \*\*(.+?):\*\*\s*(.*?)(?=^- \*\*|\Z)", blk)
                           if k.split(" (")[0].strip() not in ("Topic", "Status", "Priority", "Date raised", "Digests affected", "Digests referencing it", "Promoted to") and v.strip()],
                "docs": sorted(set(ID_RE.findall(field("Digests affected") or field("Documents") or blk)) - {rid}),
            }
    return dict(sorted(out.items()))


PRIORITIES = ("Critical", "High", "Medium", "Low")   # MANTIS-IMP-001; blank = not triaged yet
PRIO_RANK = {"Critical": 0, "High": 1, "": 2, "Medium": 3, "Low": 4}   # untriaged sits above Medium and Low


def short(i):
    return i.replace("MANTIS-DOC-", "D")


def is_open(status):
    return not status.lower().startswith(("closed", "promoted", "confirmed", "corrected", "resolved"))


docs, summaries = {}, {}
for p in sorted((M / "02_digests").glob("MANTIS-DOC-*.md")):
    _text = textcache.read(p)
    docs[p.stem] = front_matter(_text)
    _m = re.search(r"(?ms)^## Summary\s*\n(.*?)(?=^## |\Z)", _text)
    summaries[p.stem] = _m.group(1).strip() if _m else ""

gaps = registers("gaps", "MANTIS-GAP-")
asms = registers("assumptions", "MANTIS-ASM-")
cfls = registers("conflicts", "MANTIS-CFL-")

# Index entries (registers/documents/<ID>.md) are generated from the digests; only their Notes are hand-kept.
import index_gen
if __name__ != "index_migrate":
    _n = index_gen.build(docs, gaps, asms, cfls)
    if _n:
        print(f"Index: {_n} entries regenerated")

edges = []  # (from, to, kind)
by_topic, by_entity = defaultdict(list), defaultdict(list)
for did, fm in docs.items():
    for t in fm.get("topics", []): by_topic[t].append(did)
    for e in fm.get("key_entities", []): by_entity[e].append(did)
    for r in fm.get("related_documents", []):
        for x in ID_RE.findall(r): edges.append((did, x, "related"))
    for key, kind in (("gaps_referenced", "gap"), ("assumptions_referenced", "assumption"), ("conflicts_referenced", "conflict")):
        for r in fm.get(key, []):
            for x in ID_RE.findall(r): edges.append((did, x, kind))

OUT.mkdir(parents=True, exist_ok=True)
CONF = {"Very High": "VH", "High": "H", "Medium": "M", "Low": "L", "Very Low": "VL"}

# MAP.md: one short line per document, newest first
lines = ["# Mantis Map", "",
         "Generated by `tools/build_map.py`. For a feature, read `features.md` first. Otherwise find",
         "the document here, then read its summary with `python tools/peek.py <id>`.",
         f"{len(docs)} documents, {len(gaps)} gaps, {len(asms)} assumptions, {len(cfls)} conflicts.", "",
         "id | title | conf | topics | open gaps", "---|---|---|---|---"]
for did, fm in reversed(list(docs.items())):
    open_gaps = [x for r in fm.get("gaps_referenced", []) for x in ID_RE.findall(r) if is_open(gaps.get(x, {}).get("status", "Open"))]
    title = fm.get("original_title", "?")
    lines.append(" | ".join([short(did), title if len(title) <= 70 else title[:68] + "…",
                            CONF.get(fm.get("document_confidence", ""), "?"),
                            ",".join(fm.get("topics", [])[:3]), str(len(open_gaps))]))
lines += ["", "D0001 means MANTIS-DOC-0001. conf: H high, M medium, L low."]
(OUT / "MAP.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


# topics.md and entities.md
def invert(d, title):
    rows = [f"# {title}", "", "Generated. Format: name: documents (D0001 = MANTIS-DOC-0001).", ""]
    for k in sorted(d, key=lambda x: (-len(d[x]), x.lower())):
        rows.append(f"{k}: " + " ".join(short(i) for i in d[k]))
    return "\n".join(rows) + "\n"
(OUT / "topics.md").write_text(invert(by_topic, "Topics"), encoding="utf-8")

# Features and work items: card front matter + outputs (pages, epics, stories)
OUTP = M / "outputs"
# Cards (tools/cards.py): roadmap features in knowledge/features/, other subjects in knowledge/topics/.
import cards as cards_mod
all_cards = cards_mod.link(cards_mod.load(front_matter), docs, summaries)
import steps as steps_mod   # "Next steps" tables on cards -> map/steps.json (MANTIS-IMP-023)
steps_mod.build()
cards = {c["slug"]: (c["path"], c["fm"]) for c in all_cards if c["folder"] == "features"}
card_of = {c["slug"]: c for c in all_cards}


def item(path, kind, folder=None):
    fm = front_matter(path.read_text(encoding="utf-8"))
    feat = fm.get("feature", "").strip() or (folder if folder in cards else "none")
    if feat not in cards:
        feat = "none"
    epic = fm.get("epic", "").strip()
    return {"kind": kind, "id": path.stem if kind == "epic" else f"{path.parent.name}--{path.stem}", "anchor": path.stem,
            "file": path.relative_to(M).as_posix(), "feature": feat, "epic": "" if epic in ("", "none") else epic,
            "title": fm.get("title", "") or path.stem.replace("-", " ").capitalize(),
            "status": fm.get("status", "draft"), "jira": fm.get("jira", "none"), "updated": fm.get("updated", "")}


epics = [item(p, "epic") for p in sorted((OUTP / "epics").glob("*.md"))]
stories = [item(p, "story", p.parent.name) for p in sorted((OUTP / "user-stories").rglob("*.md"))]
epic_ids = {e["id"] for e in epics}
for s in stories:
    if s["epic"] and s["epic"] not in epic_ids:
        print(f"Warning: {s['file']} names epic '{s['epic']}', which has no file in outputs/epics/")

features = []
for slug, (p, fm) in cards.items():
    page = OUTP / "confluence" / f"{slug}.md"
    fdocs = card_of[slug]["linked"]
    fgaps = [g for g in fm.get("gaps", []) if g in gaps and is_open(gaps[g]["status"])]
    prio = fm.get("priority", "")
    features.append({
        "slug": slug, "title": fm.get("title", slug), "type": fm.get("type", "feature"), "status": fm.get("status", "discovery"),
        "status_note": fm.get("status_note", ""), "priority": prio if prio in ("P1", "P2", "P3") else "",
        "jira": fm.get("jira", "none"), "estimate": fm.get("estimate_2027", ""), "updated": fm.get("updated", ""),
        "card": p.relative_to(M).as_posix(), "docs": fdocs, "open_gaps": fgaps, "kind": "feature",
        "new_docs": card_of[slug]["new"], "covered": card_of[slug]["covered"],
        "page": page.relative_to(M).as_posix() if page.exists() else None,
        "epics": [e for e in epics if e["feature"] == slug],
        "stories": [s for s in stories if s["feature"] == slug],
    })
features.sort(key=lambda f: (f["priority"] or "P9", f["title"]))

rows = ["# Features (roadmap)", "",
        "Generated from feature card front matter and `mantis/outputs/`. Read this, then the card.", "",
        "priority | feature | status | jira | 2027 estimate | epics | stories in Jira | open gaps", "---|---|---|---|---|---|---|---"]
for f in features:
    done = sum(1 for s in f["stories"] if s["status"] in ("in-jira", "done"))
    rows.append(" | ".join([f["priority"] or "-", f"{f['title']} ({f['slug']})", f["status"], f["jira"], f["estimate"] or "-",
                            str(len(f["epics"])), f"{done}/{len(f['stories'])}", str(len(f["open_gaps"]))]))
rows += [""]
for f in features:
    rows.append(f"## {f['slug']}")
    rows.append(f"docs: {' '.join(short(d) for d in f['docs'])}")
    for g in f["open_gaps"]:
        rows.append(f"- {g} ({gaps[g]['status']}): {gaps[g]['topic'][:120]}")
    outs = ([f["page"]] if f["page"] else []) + [f"{x['file']} ({x['status']})" for x in f["epics"] + f["stories"]]
    rows.append("outputs: " + (", ".join(outs) if outs else "none"))
    rows.append("")
loose = [x for x in epics + stories if x["feature"] == "none"]
if loose:
    rows.append("## Not linked to a feature")
    rows += [f"- {x['kind']}: {x['file']} ({x['status']})" for x in loose]
(OUT / "features.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
(OUT / "features.json").write_text(json.dumps(features, indent=1), encoding="utf-8")
(OUT / "work.json").write_text(json.dumps({"epics": epics, "stories": stories}, indent=1), encoding="utf-8")

topics = [{"slug": c["slug"], "title": c["title"], "type": "topic", "kind": "topic", "card": c["path"].relative_to(M).as_posix(),
           "docs": c["linked"], "new_docs": c["new"], "covered": c["covered"], "updated": c["fm"].get("updated", ""),
           "match": c["fm"].get("match_topics", [])} for c in all_cards if c["folder"] == "topics"]
topics.sort(key=lambda x: x["title"].lower())
(OUT / "topics.json").write_text(json.dumps(topics, indent=1), encoding="utf-8")
# Entity graph (tools/kgraph.py): writes entities.json, entities.md, entity-graph.md, entity-candidates.md
import kgraph
kg = kgraph.build(docs, features + topics)

# Knowledge assets (tools/assets.py, MANTIS-IMP-008): pull images out of new sources, read the
# asset register, and note which digests and pages use each asset.
import assets as assets_mod
try:
    _n = assets_mod.scan(quiet=True)
    if _n:
        print(f"Assets: {_n} source file(s) scanned for images")
    _tiers = defaultdict(int)
    for _g in assets_mod.groups():
        _tiers[_g["tier"]] += 1
except Exception as e:   # pypdf or Pillow missing: the register still works
    print(f"Assets: scan skipped ({e})")
    _tiers = {}
_texts = {f"02_digests/{p.stem}.md": textcache.read(p) for p in (M / "02_digests").glob("MANTIS-DOC-*.md")}
_texts.update({p.relative_to(M).as_posix(): p.read_text(encoding="utf-8") for p in OUTP.rglob("*.md")})
asset_list = assets_mod.referenced_by(assets_mod.registry(), _texts)
rows = ["# Knowledge assets", "", "Generated from `registers/assets/`. Reuse one before drawing a new diagram",
        "(docs/rules/OUTPUTS_GUIDE.md). Full entry: `python tools/entry.py show <ID>`; candidates: `python tools/assets.py review`.",
        f"{len(asset_list)} registered; {_tiers.get('candidate', 0)} candidate(s) waiting; {_tiers.get('decorative', 0)} decorative and {_tiers.get('ignored', 0)} ignored image(s) left out.", "",
        "id | type | title | sources | used by", "---|---|---|---|---"]
rows += [" | ".join([a["id"], a["type"] or "-", a["title"][:90], ",".join(short(d) for d in a["docs"]), str(len(a["referenced_by"]))]) for a in asset_list]
(OUT / "assets.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
(OUT / "assets.json").write_text(json.dumps({"assets": asset_list, "tiers": dict(_tiers)}, indent=1, ensure_ascii=False), encoding="utf-8")

_c = cards_mod.write(all_cards, docs, summaries, gaps, kg["entities"], is_open, asset_list)
if _c:
    print(f"Cards: {_c} regenerated")

suggest = cards_mod.uncovered_tags(all_cards, docs)
rows = ["# Cards", "", "Generated. Read a subject's card before any digest: `mantis/knowledge/features/<slug>.md` or",
        "`mantis/knowledge/topics/<slug>.md`. new = linked sources the curated summary does not cover yet;",
        "sources = those listed on the card itself (a parent lists only what its narrower cards do not); KB = size of the generated part.", "",
        "card | kind | parent | sources | new | KB | match tags", "---|---|---|---|---|---|---"]
for c in sorted(all_cards, key=lambda c: (c["folder"], c["slug"])):
    rows.append(f"{c['slug']} | {c['folder'][:-1]} | {c['fm'].get('parent', '') or '-'} | {len(c['shown'])} | {len(c['new'])} | "
                f"{c.get('gen_size', 0) / 1024:.1f} | {', '.join(c['fm'].get('match_topics', []))}")
linked_any = {d for c in all_cards for d in c["linked"]}
rows += ["", f"{len(linked_any)} of {len(docs)} documents are linked to at least one card.",
         "", "## Suggested new cards (tags on 3+ documents that no card links)", ""]
rows += [f"- {t}: {n} documents" for t, n in suggest[:20]] or ["None."]
# MANTIS-IMP-017: a card past 60 sources or 20 KB of generated text is split into narrower cards
# (new cards with `parent: <slug>` and more specific match tags).
rows += ["", f"## Cards to split (over {cards_mod.SPLIT_SOURCES} sources or {cards_mod.SPLIT_BYTES // 1000} KB)", ""]
rows += [f"- {x['slug']}: {x['sources']} sources, {x['bytes'] / 1024:.0f} KB. Tags its sources share: "
         + (", ".join(f"{t} ({n})" for t, n in x["tags"]) or "none on 3+ sources") for x in cards_mod.too_large(all_cards, docs)] or ["None."]
(OUT / "cards.md").write_text("\n".join(rows) + "\n", encoding="utf-8")

# open-items.json: every open or potentially resolved entry, for the site's Open items page (IMP-007)
doc_feats = defaultdict(set)
for f in features:
    for d in f["docs"]:
        doc_feats[d].add(f["slug"])
card_gaps = {g: f["slug"] for f in features for g in f["open_gaps"]}
open_items = []
for kind, reg in (("gap", gaps), ("assumption", asms), ("conflict", cfls)):
    for rid, r in reg.items():
        if is_open(r["status"]):
            fs = sorted({card_gaps[rid]} if rid in card_gaps else set().union(*[doc_feats[d] for d in r["docs"]]) if r["docs"] else set())
            st = r.get("status_raw") or r["status"] or "Open"
            open_items.append({"id": rid, "kind": kind, "status": "Potential resolution" if st.lower().startswith("potential") else st.split()[0],
                               "status_full": st, "topic": r["topic"], "raised": r["raised"], "detail": r.get("detail", []), "priority": r["priority"],
                               "features": fs, "docs": [{"id": d, "title": docs.get(d, {}).get("original_title", "")} for d in r["docs"]]})
open_items.sort(key=lambda x: (x["raised"], x["id"]), reverse=True)
open_items.sort(key=lambda x: PRIO_RANK[x.get("priority", "")])   # stable: newest first within each priority
# Name questions for the owner (answered on the Open items page): possible duplicate names, and
# frequently named things the sources never explain. IDs are stable hashes of the names.
import hashlib
_h = lambda s: hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]
_by = {e["name"]: e for e in kg["entities"]}
_dt = lambda e: [{"id": d, "title": docs.get(d, {}).get("original_title", "")} for d in e["docs"][:3]]
for c in kg["candidates"]:
    a, b = _by.get(c["a"]), _by.get(c["b"])
    if a and b:
        open_items.append({"id": "NAME-" + _h(c["a"] + "|" + c["b"]), "kind": "name", "status": "Open", "status_full": "Open",
                           "topic": f'Are "{c["a"]}" and "{c["b"]}" the same thing?', "raised": "", "features": [],
                           "docs": _dt(a) + _dt(b), "names": [c["a"], c["b"]]})
for e in kg["entities"]:
    if e["type"] == "unknown" and len(e["docs"]) >= 5:
        open_items.append({"id": "TERM-" + _h(e["name"]), "kind": "term", "status": "Open", "status_full": "Open",
                           "topic": f'What is "{e["name"]}"? Named in {len(e["docs"])} documents; Mantis has no confirmed meaning or type for it yet.', "raised": "",
                           "features": [], "docs": _dt(e), "names": [e["name"]]})
(OUT / "open-items.json").write_text(json.dumps(open_items, indent=1, ensure_ascii=False), encoding="utf-8")

# registers.md: one line per entry that is still open
rows = ["# Registers (compact)", "",
        "Generated. One line per open or potentially resolved entry. Full text:",
        "`python tools/entry.py show <ID>`. One file per entry in `mantis/knowledge/registers/`.", "",
        "Sorted by priority (Critical, High, not set, Medium, Low), then ID.", "",
        "id | priority | status | topic | docs"]
for reg in (gaps, asms, cfls):
    for rid, r in sorted(reg.items(), key=lambda kv: PRIO_RANK[kv[1]["priority"]]):
        if is_open(r["status"]):
            rows.append(" | ".join([rid, r["priority"] or "-", r["status"], r["topic"][:110], ",".join(short(x) for x in r["docs"])]))
(OUT / "registers.md").write_text("\n".join(rows) + "\n", encoding="utf-8")

# graph.json
nodes = [{"id": d, "type": "document", "title": f.get("original_title", "")} for d, f in docs.items()]
for typ, reg in (("gap", gaps), ("assumption", asms), ("conflict", cfls)):
    nodes += [{"id": i, "type": typ, "status": r["status"], "title": r["topic"][:110]} for i, r in reg.items()]
    for i, r in reg.items():
        for d in r["docs"]: edges.append((d, i, typ))
for f in features:
    nodes.append({"id": f["slug"], "type": "feature", "status": f["status"], "title": f["title"]})
    edges += [(f["slug"], d, "feature-document") for d in f["docs"]] + [(f["slug"], g, "feature-gap") for g in f["open_gaps"]]
for e in kg["entities"]:
    eid = "E:" + e["name"]
    nodes.append({"id": eid, "type": "entity", "kind": e["type"], "title": e["name"]})
    edges += [(d, eid, "mentions") for d in e["docs"]]
    edges += [(eid, "E:" + n, "co-occurs") for n, w in e["neighbours"] if e["name"] < n]
    edges += [(eid, "E:" + r["to"], r["rel"]) for r in e["relations"] if r["dir"] == "out"]
edges = sorted(set(edges))
(OUT / "graph.json").write_text(json.dumps({"nodes": nodes, "edges": [{"from": a, "to": b, "kind": k} for a, b, k in edges]}, indent=1), encoding="utf-8")

print(f"docs={len(docs)} gaps={len(gaps)} asm={len(asms)} cfl={len(cfls)} features={len(features)} entities={len(kg['entities'])} edges={len(edges)}")
for msg in kg["problems"]: print("Graph:", msg)
for f in sorted(OUT.iterdir()): print(f"{f.name}: {f.stat().st_size} bytes")

import entry
problems = entry.check()
textcache.prune()
if problems:
    print(f"\nLint: {len(problems)} problem(s). Run `python tools/entry.py check` for the list.")

try:
    import maintain  # health report only (no cleanup) so the site's Home and Health pages are current
    maintain.report()
except Exception as e:
    print(f"Health report skipped: {e}")

try:
    import build_site
    build_site.build()
except ImportError as e:
    print(f"\nSite not rebuilt: {e}")
