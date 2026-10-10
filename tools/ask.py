"""Ask Mantis a question; get a sourced answer (MANTIS-IMP-081).

    python tools/ask.py answer "question"          one step (the Ask box): best passages by code, one model call, quotes checked (~4,000 tokens)
    python tools/ask.py evidence "question"        the passages a one-step answer would get, with no model call
    python tools/ask.py gather "question"          the evidence, cheapest first: cards, document summaries, open questions, decisions, glossary
    python tools/ask.py section <DOC-ID> "Heading"  one section of a digest, whole (the exact passage a point rests on)
    python tools/ask.py save FILE                   check every quote against its source, then save the answer for the site

Code finds the evidence; Claude writes the answer (docs/rules/workflow/questions.md). Finding: the
question's words, with glossary mishearings and registered aliases folded in, scored against each
card and each digest's title, topics, entities and Summary (BM25: rare words count more). Saving:
every quoted passage must appear in the digest it cites (ignoring case, spacing and quote marks), or
the point is marked "quote not found". That catches an invented or misattributed quote; whether a
paraphrase is fair is the verifier's job (tools/support.py).

Answer JSON (save):
  {"question": "...", "answer": "two or three sentences", "strength": "Strong | Moderate | Weak: why, in words",
   "points": [{"text": "...", "doc": "MANTIS-DOC-XXXX", "quote": "exact words from the digest"},
              {"text": "...", "source": "Owner answer, <date>"}],   # no doc: shown as cited in words, not quote-checked
   "conflicts": ["..."], "unknowns": ["..."]}
Saved as a brief of kind "answer" in mantis/tasks/briefs/, so it opens on the Today page.
"""
import json, math, re, sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import frontmatter

ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "mantis"
K = M / "knowledge"
BRIEFS = M / "tasks" / "briefs"
STOP = set("a an the and or of for to in on with by from is are was were be been it its this that these those what which who whom "
           "when where why how do does did can could should would will we our you your they them their there here about as at "
           "not no yes any all some into than then so if but also only just more most much many very".split())


def words(text):
    return [w for w in re.findall(r"[a-z0-9][a-z0-9&+-]*", text.lower()) if w not in STOP and len(w) > 1]


def expand(q):
    """The question's words plus the real word for a known mishearing and the registered name for an alias.
    Glossary definitions are not added: their words swamped the question in the first trial."""
    toks = words(q)
    extra = []
    gl = K / "glossary.md"
    mish = section(gl.read_text(encoding="utf-8"), "Mishearings") if gl.exists() else ""
    for line in mish.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0] and not cells[0].startswith("-") and words(cells[0]) and set(words(cells[0])) <= set(toks):
            extra += words(cells[1])[:3]   # "MTs" -> "empties"
    try:
        import classify
        for t in list(toks):
            canon = classify.ALIAS.get(classify.NORM(t))
            if canon:
                extra.append(canon)
    except Exception:
        pass
    return toks + extra


def section(text, name):
    m = re.search(r"(?ms)^##\s+%s\s*$(.*?)(?=^##\s|\Z)" % re.escape(name), text)
    return m.group(1).strip() if m else ""


def docs():
    out = {}
    for p in sorted((M / "02_digests").glob("MANTIS-DOC-*.md")):
        t = p.read_text(encoding="utf-8")
        fm, body = frontmatter.split(t)
        summ = section(body, "Summary")
        field = " ".join([fm.get("original_title", "")] * 2 + list(fm.get("topics", []) or []) + list(fm.get("key_entities", []) or []) + [summ])
        out[p.stem] = {"title": fm.get("original_title", ""), "summary": summ, "text": field}
    return out


def cards():
    out = {}
    for f in ("features.json", "topics.json"):
        mp = K / "map" / f
        for c in (json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else []):
            p = M / c["card"]
            if p.exists():
                fm, body = frontmatter.split(p.read_text(encoding="utf-8"))
                cur = body.split("<!-- GENERATED")[0].strip()
                out[c["slug"]] = {"title": c["title"], "curated": cur,
                                  "text": " ".join([c["title"]] * 3 + list(fm.get("match_topics", []) or []) + [cur])}
    return out


def bm25(query, items, k1=1.4, b=0.75):
    """Score each item's text against the query words; rare words weigh more."""
    toks = {i: words(v["text"]) for i, v in items.items()}
    n = len(toks) or 1
    avg = sum(len(t) for t in toks.values()) / n or 1
    df = Counter(w for t in toks.values() for w in set(t))
    q = set(query)
    out = []
    for i, t in toks.items():
        tf = Counter(t)
        s = sum(math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5)) * tf[w] * (k1 + 1) / (tf[w] + k1 * (1 - b + b * len(t) / avg))
                for w in q if w in tf)
        if s > 0:
            out.append((round(s, 2), i))
    return sorted(out, reverse=True)


def collect(question, n_cards=2, n_docs=6):
    """Everything code can find for a question, with no AI: cards, sources, open questions, glossary rows, decisions."""
    q = expand(question)
    cs, ds = cards(), docs()
    top_c, scored = bm25(q, cs)[:n_cards], bm25(q, ds)
    top_d = scored[:n_docs]
    if top_c:   # sources the best card itself cites are curated links: add up to 3 the word scores missed
        rank = {d: s for s, d in scored}
        cited = [d for d in dict.fromkeys(re.findall(r"MANTIS-DOC-\d{4}", cs[top_c[0][1]]["curated"])) if d in ds]
        shown = {d for _, d in top_d}
        top_d += sorted(((rank.get(d, 0), d) for d in cited if d not in shown), reverse=True)[:3]
    items = json.loads((K / "map" / "open-items.json").read_text(encoding="utf-8")) if (K / "map" / "open-items.json").exists() else []
    qs = set(q)
    hits = sorted(((len(qs & set(words(o["topic"]))), o) for o in items), key=lambda x: -x[0])
    opens = [o for s, o in hits if s >= 2][:5]
    gl = K / "glossary.md"
    gloss = []
    for line in (gl.read_text(encoding="utf-8").splitlines() if gl.exists() else []):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and words(cells[0]) and set(words(cells[0])) <= set(words(question)):
            gloss.append(" | ".join(cells)[:300])
    import decisions
    decs = [d for d in decisions.decisions() if len(qs & set(words(d["decision"]))) >= 3]
    return {"q": q, "cards": cs, "docs": ds, "top_c": top_c, "top_d": top_d, "open": opens, "glossary": gloss, "decisions": decs}


def gather(question, n_cards=2, n_docs=6):
    e = collect(question, n_cards, n_docs)
    cs, ds = e["cards"], e["docs"]
    print(f"QUESTION: {question}\nSearch words: {', '.join(dict.fromkeys(e['q']))}\n")
    for s, slug in e["top_c"]:
        print(f"--- CARD {slug} ({cs[slug]['title']}), score {s} ---\n{cs[slug]['curated'][:3500]}\n")
    for s, d in e["top_d"]:
        print(f"--- SOURCE {d} \"{ds[d]['title']}\", score {s} ---\n{ds[d]['summary'][:900]}\n")
    for o in e["open"]:
        print(f"OPEN QUESTION {o['id']} [{o['status']}]: {o['topic'][:200]}")
    for g in e["glossary"]:
        print(f"GLOSSARY: {g}")
    for d in e["decisions"]:
        print(f"DECISION {d['id']} ({d['date']}): {d['decision'][:300]}")
    print("\nNext: open only the sections you need with `python tools/ask.py section <DOC-ID> \"Business Rules\"` "
          "(never answer a business rule, number or date from a summary alone), then write the answer JSON "
          "(format: python tools/ask.py) and save it with `python tools/ask.py save <file>`.")
    return e["top_c"], e["top_d"]


# One-step answers (MANTIS-IMP-085): code picks the passages, the model is called once ----------------
ONE_STEP = """You answer a product owner's question from their own knowledge base. Use ONLY the evidence below;
you know nothing else about this company. Write to the owner as "you".

Return JSON only, no prose:
{"answer": "two or three sentences; if the evidence does not answer it, say so first",
 "strength": "Strong | Moderate | Weak, and why in words (several summaries of one source are one source)",
 "points": [{"text": "a fact the answer rests on", "doc": "MANTIS-DOC-XXXX", "quote": "words copied exactly from that source's passage"}],
 "conflicts": ["open questions or disagreeing sources that touch the answer"],
 "unknowns": ["what the evidence does not say that the owner may need"],
 "enough": true or false: false when the passages below are not enough to answer and a deeper search is needed}

Rules: every quote is copied character for character from a SOURCE passage below (join two pieces with "...").
A fact that only a CARD line states with "owner answer, <date>" becomes a point with "source": "Owner answer, <date>"
and no doc or quote. What no passage says goes in unknowns, never in points. No numbers, dates or names that are not
in the evidence."""


def chunks(text):
    """A digest body as bullets and paragraphs, without its References and Change Log."""
    body = re.split(r"(?m)^##\s+(?:References|Change Log)\s*$", text)[0]
    out, cur = [], []
    for line in body.splitlines():
        if line.startswith("## ") or not line.strip() or (line.startswith("- ") and cur):
            if cur:
                out.append(" ".join(cur))
            cur = [] if (line.startswith("## ") or not line.strip()) else [line.strip()]
        else:
            cur.append(line.strip())
    if cur:
        out.append(" ".join(cur))
    return [c for c in out if len(c) > 40]


def evidence(question, n_passages=6, card_lines=3, n_rel=4):
    """The evidence pack for one call, from the search index (tools/search.py, MANTIS-IMP-086): the best card lines,
    cited relations of the people, systems and features the question names, and the best passages, at most 3 per source."""
    import search
    con = search.connect()
    search.update(con)   # cheap when nothing changed: only files whose content changed are re-indexed
    q = expand(question)
    picked, card_rows, rels, ents = search.search(question, q, n_passages=n_passages, n_card=card_lines, n_rel=n_rel, con=con)
    parts = [f"QUESTION: {question}", "", "=== CARD LINES (curated summaries; they cite their sources) ==="]
    parts += [f"[{slug}] {line[:700]}" for slug, line in card_rows]
    if rels:
        parts += ["", "=== RELATIONS (from the entity register, each with its source; quote from passages, not from these) ==="]
        parts += [f"{line} ({src})" for line, src in rels]
    parts += ["", "=== SOURCE PASSAGES (quote only from these) ==="]
    parts += [f"[{doc} \"{title[:80]}\"] {text[:700]}" for doc, title, text in sorted(picked, key=lambda x: x[0])]
    extra = side_evidence(question, q)
    return "\n".join(parts + extra)


def side_evidence(question, q):
    """Glossary rows, open questions and decisions that touch the question: small, and read without the full collect()."""
    out = []
    gl = K / "glossary.md"
    gloss = []
    for line in (gl.read_text(encoding="utf-8").splitlines() if gl.exists() else []):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and words(cells[0]) and set(words(cells[0])) <= set(words(question)):
            gloss.append(" | ".join(cells)[:300])
    if gloss:
        out += ["", "=== GLOSSARY ==="] + gloss
    items = json.loads((K / "map" / "open-items.json").read_text(encoding="utf-8")) if (K / "map" / "open-items.json").exists() else []
    qs = set(q)
    opens = [o for s, o in sorted(((len(qs & set(words(o["topic"]))), o) for o in items), key=lambda x: -x[0]) if s >= 2][:4]
    if opens:
        out += ["", "=== OPEN QUESTIONS ==="] + [f"{o['id']} [{o['status']}]: {o['topic'][:220]}" for o in opens]
    import decisions
    decs = [d for d in decisions.decisions() if len(qs & set(words(d["decision"]))) >= 3]
    if decs:
        out += ["", "=== DECISIONS ==="] + [f"{d['id']} ({d['date']}): {d['decision'][:300]}" for d in decs]
    return out


def evidence_scan(question, n_passages=14, card_lines=8):
    """The first one-step pack (before the search index): every source scored, best passages of the top ones.
    Kept for comparison on the evaluation set; evidence() replaced it on 2026-10-11."""
    e = collect(question, n_docs=8)
    q = e["q"]
    pool = {}
    for _, d in e["top_d"]:
        p = M / "02_digests" / f"{d}.md"
        for i, c in enumerate(chunks(frontmatter.split(p.read_text(encoding="utf-8"))[1])):
            pool[f"{d}#{i}"] = {"text": c, "doc": d}
    best = [k for _, k in bm25(q, pool)[:n_passages]]
    best.sort(key=lambda k: (k.split("#")[0], int(k.split("#")[1])))   # keep each source's passages in its own order
    cpool = {}
    for _, slug in e["top_c"]:
        for i, line in enumerate(c for c in chunks(e["cards"][slug]["curated"]) if not c.startswith("|---")):
            cpool[f"{slug}#{i}"] = {"text": line}
    cbest = [k for _, k in bm25(q, cpool)[:card_lines]]
    parts = [f"QUESTION: {question}", "", "=== CARD LINES (curated summaries; they cite their sources) ==="]
    parts += [f"[{k.split('#')[0]}] {cpool[k]['text'][:700]}" for k in cbest]
    parts += ["", "=== SOURCE PASSAGES (quote only from these) ==="]
    for k in best:
        d = pool[k]["doc"]
        parts.append(f"[{d} \"{e['docs'][d]['title'][:80]}\"] {pool[k]['text'][:900]}")
    if e["glossary"]:
        parts += ["", "=== GLOSSARY ==="] + e["glossary"]
    if e["open"]:
        parts += ["", "=== OPEN QUESTIONS ==="] + [f"{o['id']} [{o['status']}]: {o['topic'][:220]}" for o in e["open"]]
    if e["decisions"]:
        parts += ["", "=== DECISIONS ==="] + [f"{d['id']} ({d['date']}): {d['decision'][:300]}" for d in e["decisions"]]
    return "\n".join(parts)


def answer(question):
    """One-step answer: evidence by code, one model call, quotes checked by code. Reuses a saved answer when the
    same question meets the same evidence. Returns {"summary", "usage", "reused"}."""
    import hashlib, support
    pack = evidence(question)
    key = hashlib.sha1(pack.encode("utf-8")).hexdigest()[:16]
    same = lambda t: re.sub(r"[^a-z0-9 ]", "", t.lower()).split()
    for p in sorted(BRIEFS.glob("*-answer.json"), reverse=True):
        try:
            b = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if b.get("evidence_key") == key and same(b.get("title", "")) == same(question):
            return {"summary": "Answered before from the same evidence; nothing has changed since, so it was reused (no AI used).\n\n"
                    + b["sections"][0]["bullets"][0]["text"], "usage": None, "reused": True}
    out, usage = support.run_model_text(ONE_STEP + "\n\n" + pack, role="ask", bare=True)
    m = re.search(r"\{.*\}", out, re.S)
    try:
        a = json.loads(m.group(0)) if m else {}
    except ValueError:
        a = {}
    if not a.get("answer"):
        return {"summary": "The answer could not be read from the model's reply. Try again, or use Dig deeper.", "usage": usage, "reused": False}
    a["question"] = question
    tmp = BRIEFS / f".answer-{key}.json"
    BRIEFS.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(a, ensure_ascii=False), encoding="utf-8")
    brief = save(tmp, extra={"evidence_key": key, "mode": "one step", "enough": a.get("enough", True), "usage": usage})
    tmp.unlink(missing_ok=True)
    note = "" if a.get("enough", True) else "\n\nThe passages were not enough for a full answer: use Dig deeper for a wider search."
    return {"summary": a["answer"] + note + (f"\n\n{brief['quotes_not_found']} quote(s) not found in their source." if brief["quotes_not_found"] else ""),
            "usage": usage, "reused": False}


def norm(s):
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("—", "-").replace("–", "-")
    return " ".join(re.sub(r"[*_`]", "", s).lower().split())


def quote_found(doc, quote):
    p = M / "02_digests" / f"{doc}.md"
    if not p.exists() or not quote.strip():
        return False
    body = norm(frontmatter.split(p.read_text(encoding="utf-8"))[1])
    parts = [norm(x) for x in re.split(r"\s*(?:\.\.\.|…)\s*", quote) if len(norm(x)) > 3]   # "..." joins two exact pieces
    return bool(parts) and all(x.strip(" .\"'") in body for x in parts)


def save(path, extra=None):
    a = json.loads(Path(path).read_text(encoding="utf-8"))
    if not a.get("question") or not a.get("answer"):
        sys.exit("An answer needs 'question' and 'answer'.")
    titles = json.loads((K / "map" / "titles.json").read_text(encoding="utf-8")) if (K / "map" / "titles.json").exists() else {}
    pts, bad = [], 0
    for x in a.get("points", [])[:12]:
        if not x.get("doc"):   # the owner's own answer, or another source in words: nothing to quote-check
            pts.append({"text": x.get("text", "")[:400], "detail": "", "source": x.get("source", "") or "owner answer", "doc": "", "quote_ok": None})
            continue
        ok = quote_found(x["doc"], x.get("quote", ""))
        bad += not ok
        pts.append({"text": x.get("text", "")[:400], "detail": (f"“{x.get('quote', '')[:500]}”" if x.get("quote") else "")
                    + ("" if ok else " (quote not found in the source: check before relying on it)"),
                    "source": titles.get(x["doc"], "") or "source not found", "doc": x["doc"], "quote_ok": ok})
    sections = [{"name": "Answer", "bullets": [{"text": a["answer"][:900], "detail": a.get("strength", "")[:300], "source": ""}]},
                {"name": "Evidence", "bullets": pts}]
    if a.get("conflicts"):
        sections.append({"name": "Conflicts and open questions", "bullets": [{"text": str(c)[:400], "detail": "", "source": ""} for c in a["conflicts"][:8]]})
    if a.get("unknowns"):
        sections.append({"name": "Not known", "bullets": [{"text": str(u)[:400], "detail": "", "source": ""} for u in a["unknowns"][:8]]})
    brief = {"for": "Ask Mantis", "kind": "answer", "date": date.today().isoformat(), "title": a["question"][:120], "sections": sections,
             "quotes_checked": len(pts), "quotes_not_found": bad, **(extra or {})}
    BRIEFS.mkdir(parents=True, exist_ok=True)
    same = lambda t: re.sub(r"[^a-z0-9 ]", "", t.lower()).split()
    for old in BRIEFS.glob(f"{brief['date']}-*-answer.json"):   # a re-save (after fixing a quote) replaces that day's earlier answer
        try:
            if same(json.loads(old.read_text(encoding="utf-8")).get("title", "")) == same(brief["title"]):
                old.unlink()
        except (OSError, ValueError):
            pass
    out = BRIEFS / f"{datetime.now().strftime('%Y-%m-%d-%H%M%S')}-answer.json"
    out.write_text(json.dumps(brief, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Saved: {len(pts)} point(s), {bad} quote(s) not found in their source. It opens on the Today page (Ask Mantis).")
    return brief


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if argv[:1] == ["gather"] and len(argv) >= 2:
        gather(" ".join(argv[1:]))
    elif argv[:1] == ["section"] and len(argv) == 3:
        did = argv[1] if argv[1].startswith("MANTIS-") else "MANTIS-" + argv[1]
        p = M / "02_digests" / f"{did}.md"
        if not p.exists():
            sys.exit(f"No digest {did}")
        print(section(frontmatter.split(p.read_text(encoding="utf-8"))[1], argv[2]) or f"No section '{argv[2]}' in {did}.")
    elif argv[:1] == ["save"] and len(argv) == 2:
        save(argv[1])
    elif argv[:1] == ["evidence"] and len(argv) >= 2:
        pack = evidence(" ".join(argv[1:]))
        print(pack + f"\n\n({len(pack)} characters, about {len(pack) // 4} tokens)")
    elif argv[:1] == ["answer"] and len(argv) >= 2:
        r = answer(" ".join(argv[1:]))
        u = r["usage"] or {}
        print(r["summary"] + (f"\n\nTokens: {u.get('input', 0) + u.get('cache_read', 0) + u.get('cache_write', 0)} in, {u.get('output', 0)} out; {u.get('wall', '?')} s." if u else ""))
    else:
        sys.exit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
