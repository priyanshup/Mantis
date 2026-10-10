"""Search index for questions: SQLite full-text search plus the entity graph (MANTIS-IMP-086).

    python tools/search.py "question"     the passages, card lines and relations a question would get
    python tools/search.py update         bring the index up to date (only changed files; build_map.py runs this)
    python tools/search.py rebuild        start the index again from nothing
    python tools/search.py status         what the index holds

The index lives outside OneDrive (%LOCALAPPDATA%/Mantis/search.db), like the site: it is generated,
never edited, and safe to delete. It holds every digest paragraph, every line of every card's
curated part, and every cited relation in the entity graph ("Sam Lee approves price changes for the
pricing tool", with its source). Each file is fingerprinted; an update re-indexes only what changed, so
a new digest or an edited card is searchable after the next rebuild, which Mantis runs after every
change. No AI is involved: building and searching cost no tokens.

Searching: the question's words (mishearings and aliases folded in, words stemmed so "promotion"
matches "promotions") are ranked with BM25. People, systems and features the question names are
looked up in the entity graph: their cited relations are added as evidence, and their documents
and the sources the best card cites rank higher. At most a few passages come from any one source,
so one long document cannot crowd out the rest.
"""
import hashlib, json, os, re, sqlite3, sys, tempfile
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import frontmatter

ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "mantis"
K = M / "knowledge"
DB = (Path(os.environ["LOCALAPPDATA"]) / "Mantis" if os.environ.get("LOCALAPPDATA") else Path(tempfile.gettempdir()) / "Mantis") / "search.db"
VERSION = "2"   # raise when what is indexed or how it is cut changes: the next update rebuilds everything


def connect(path=None):
    p = Path(path or DB)
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(p))
    con.execute("CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, hash TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
    con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(text, title, kind UNINDEXED, ref UNINDEXED, doc UNINDEXED, "
                "path UNINDEXED, tokenize='porter unicode61 remove_diacritics 2')")
    return con


def chunks_of(text):
    """Bullets and paragraphs of a Markdown body, without References and Change Log."""
    body = re.split(r"(?m)^##\s+(?:References|Change Log)\s*$", text)[0]
    out, cur = [], []
    for line in body.splitlines():
        if line.startswith("## ") or not line.strip() or (line.lstrip().startswith("- ") and cur) or line.startswith("|---"):
            if cur:
                out.append(" ".join(cur))
            cur = [] if (line.startswith("## ") or not line.strip() or line.startswith("|---")) else [line.strip()]
        else:
            cur.append(line.strip())
    if cur:
        out.append(" ".join(cur))
    return [c for c in out if len(c) > 40]


def files():
    """Every file the index covers, as (path, kind)."""
    out = [(p, "source") for p in sorted((M / "02_digests").glob("MANTIS-DOC-*.md"))]
    for folder in ("features", "topics"):
        out += [(p, "card") for p in sorted((K / folder).glob("*.md")) if p.name != "README.md"]
    return out


def read(p, kind):
    """(ref, title, indexed text) of one file: a digest's body, or a card's curated part."""
    fm, body = frontmatter.split(p.read_text(encoding="utf-8"))
    if kind == "source":
        return p.stem, fm.get("original_title", ""), body
    return fm.get("feature") or p.stem, fm.get("title", p.stem), body.split("<!-- GENERATED")[0]


def relation_rows():
    """Cited relations from the entity graph, one row each: tiny, precise evidence."""
    mp = K / "map" / "entities.json"
    if not mp.exists():
        return []
    rows, seen = [], set()
    for e in json.loads(mp.read_text(encoding="utf-8")).get("entities", []):
        for r in e.get("relations", []):
            if r.get("dir") != "out":
                continue
            line = f"{e['name']} {r['rel']} {r['to']}"
            if line not in seen:
                seen.add(line)
                rows.append((line, r.get("source", "")))
    return rows


def update(con=None, quiet=True, full=False):
    """Re-index only what changed since the last update. Returns (files re-indexed, files removed)."""
    con = con or connect()
    if full or (con.execute("SELECT v FROM meta WHERE k='version'").fetchone() or [None])[0] != VERSION:
        con.execute("DELETE FROM chunks"); con.execute("DELETE FROM files")
        con.execute("INSERT OR REPLACE INTO meta VALUES ('version', ?)", (VERSION,))
    known = dict(con.execute("SELECT path, hash FROM files").fetchall())
    seen, changed = set(), 0
    for p, kind in files():
        key = p.relative_to(M).as_posix()
        seen.add(key)
        st = p.stat()
        stamp = f"{st.st_size}:{st.st_mtime_ns}"
        if known.get(key, "").startswith(stamp + "|"):
            continue   # same size and time as when indexed: not read again
        ref, title, body = read(p, kind)
        h = stamp + "|" + hashlib.sha1(body.encode("utf-8")).hexdigest()[:16]
        if known.get(key, "").split("|")[-1] == h.split("|")[-1]:
            con.execute("INSERT OR REPLACE INTO files VALUES (?, ?)", (key, h))   # touched, not changed: just note the new time
            continue
        con.execute("DELETE FROM chunks WHERE path = ?", (key,))
        con.executemany("INSERT INTO chunks (text, title, kind, ref, doc, path) VALUES (?, ?, ?, ?, ?, ?)",
                        [(c, title, kind, ref, ref if kind == "source" else "", key) for c in chunks_of(body)])
        con.execute("INSERT OR REPLACE INTO files VALUES (?, ?)", (key, h))
        changed += 1
    mp = K / "map" / "entities.json"
    rh = hashlib.sha1(mp.read_bytes()).hexdigest()[:16] if mp.exists() else ""
    if known.get("map/entities.json", "") != rh:
        con.execute("DELETE FROM chunks WHERE path = 'map/entities.json'")
        con.executemany("INSERT INTO chunks (text, title, kind, ref, doc, path) VALUES (?, '', 'relation', '', ?, 'map/entities.json')", relation_rows())
        con.execute("INSERT OR REPLACE INTO files VALUES ('map/entities.json', ?)", (rh,))
        changed += 1
    seen.add("map/entities.json")
    gone = [k for k in known if k not in seen]
    for k in gone:
        con.execute("DELETE FROM chunks WHERE path = ?", (k,)); con.execute("DELETE FROM files WHERE path = ?", (k,))
    con.commit()
    if not quiet:
        print(f"Search index: {changed} file(s) re-indexed, {len(gone)} removed.")
    return changed, len(gone)


def entities_in(question):
    """People, systems and features the question names (by name or alias), skipping ones on most documents."""
    mp = K / "map" / "entities.json"
    if not mp.exists():
        return []
    ents = json.loads(mp.read_text(encoding="utf-8")).get("entities", [])
    n_docs = len(list((M / "02_digests").glob("MANTIS-DOC-*.md"))) or 1
    q = " " + re.sub(r"[^a-z0-9 ]", " ", question.lower()) + " "
    found = []
    for e in ents:
        names = [e["name"]] + e.get("aliases", [])
        if any(len(n) >= 3 and f" {re.sub(r'[^a-z0-9 ]', ' ', n.lower()).strip()} " in q for n in names) and len(e.get("docs", [])) <= n_docs * 0.25:
            found.append(e)
    return found


def card_docs(slug):
    """The documents linked to a card (map/features.json and topics.json)."""
    for f in ("features.json", "topics.json"):
        mp = K / "map" / f
        for c in (json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else []):
            if c["slug"] == slug:
                return set(c.get("docs", []))
    return set()


def fts_query(words):
    """An FTS5 OR query from plain words: each one quoted, so punctuation and keywords cannot break it."""
    terms = [w.replace('"', "") for w in dict.fromkeys(words) if len(w) > 1]
    return " OR ".join(f'"{t}"' for t in terms) or '""'


def search(question, words, n_passages=8, per_doc=3, n_card=4, n_rel=4, con=None):
    """Ranked evidence for a question: (passages, card lines, relations). words: the expanded question words."""
    con = con or connect()
    ents = entities_in(question)
    boost = {d for e in ents for d in e.get("docs", [])}
    q = fts_query(words + [w for e in ents for w in re.findall(r"[a-z0-9]+", e["name"].lower())])
    rows = con.execute("SELECT text, title, kind, ref, doc, bm25(chunks, 1.0, 0.4) AS s FROM chunks WHERE chunks MATCH ? ORDER BY s LIMIT 400",
                       (q,)).fetchall()
    cards = [r for r in rows if r[2] == "card"][:n_card]
    cited = set(re.findall(r"MANTIS-DOC-\d{4}", " ".join(c[0] for c in cards)))
    subject = card_docs(cards[0][3]) if cards else set()   # the sources of the card the question is most about
    keys = [w[:5] for w in dict.fromkeys(words) if len(w) >= 4]   # distinct content words, by stem-ish prefix
    scored = []
    for text, title, kind, ref, doc, s in rows:
        if kind != "source":
            continue
        low = text.lower()
        coverage = sum(1 for k in keys if k in low) / len(keys) if keys else 1.0   # more of the question's words beats one word many times
        score = (-s * (1.3 if doc in boost else 1.0) * (1.2 if doc in cited else 1.0)   # bm25() is lower-is-better
                 * (1.6 if doc in subject else 1.0) * (0.5 + coverage))
        scored.append((score, text, title, doc))
    scored.sort(key=lambda x: -x[0])
    picked, per = [], {}
    for score, text, title, doc in scored:
        if per.get(doc, 0) < per_doc:
            picked.append((doc, title, text))
            per[doc] = per.get(doc, 0) + 1
        if len(picked) == n_passages:
            break
    qset = set(words)
    rels = []
    for e in ents:   # relations of the named entities, those sharing most words with the question first
        for line, src in relation_rows():
            if line.lower().startswith(e["name"].lower() + " ") or f" {e['name'].lower()}" in line.lower():
                overlap = len(qset & set(re.findall(r"[a-z0-9]+", line.lower())))
                rels.append((overlap, line, src))
    rels = [(l, s) for o, l, s in sorted(set(rels), key=lambda x: -x[0])][:n_rel]
    return picked, [(r[3], r[0]) for r in cards], rels, [e["name"] for e in ents]


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if argv[:1] in (["update"], ["rebuild"]):
        update(quiet=False, full=argv[0] == "rebuild")
    elif argv[:1] == ["status"]:
        con = connect()
        n = dict(con.execute("SELECT kind, count(*) FROM chunks GROUP BY kind").fetchall())
        print(f"{DB}: {n.get('source', 0)} source passages, {n.get('card', 0)} card lines, {n.get('relation', 0)} relations, "
              f"{con.execute('SELECT count(*) FROM files').fetchone()[0]} files; {DB.stat().st_size // 1024} KB")
    elif argv:
        import ask
        con = connect()
        update(con)
        q = " ".join(argv)
        picked, cards, rels, ents = search(q, ask.expand(q), con=con)
        print(f"Entities named: {', '.join(ents) or 'none'}")
        for slug, line in cards:
            print(f"[card {slug}] {line[:200]}")
        for line, src in rels:
            print(f"[relation, {src}] {line}")
        for doc, title, text in picked:
            print(f"[{doc} {title[:50]}] {text[:200]}")
    else:
        sys.exit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
