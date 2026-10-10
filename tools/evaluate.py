"""Evaluation set: does Mantis still get known cases right? (MANTIS-IMP-077)

    python tools/evaluate.py run [--label NAME] [--verify]   run every case; --verify also runs the AI verifier (costs tokens)
    python tools/evaluate.py compare [A] [B]                 compare two recorded runs per case (default: first and latest)
    python tools/evaluate.py list                            the cases, with their expected outcome and its basis
    python tools/evaluate.py add-verdict <CFL-ID> [--right A|B]  an owner-answered conflict becomes a counter case (MANTIS-IMP-083)
    python tools/evaluate.py stability <ids> [--times 3]   run the verifier on a few cases several times; count agreement (MANTIS-IMP-084)

Cases live in mantis/eval/cases.json (local knowledge, never committed): each one has the expected
outcome, why it is expected, and whether that is established (an owner verdict, an ingest
decision, or true by construction) or provisional (Claude's reading of the source, waiting for the
owner). Groups:
  identity   classify.py on a document whose identity is known (new version, recurring meeting, near-duplicate)
  retrieval  the contradiction check shows the other source of a known conflict (closest sources, or a shared card)
  discovery  where the other side of a known disagreement ranks among all documents (benchmark for MANTIS-IMP-082)
  qa         ask.py finds the right card and source for a question with a known answer (MANTIS-IMP-081)
  pack       the one-step evidence pack holds an expected source; its size in tokens is reported
  answer     a saved answer from the Ask job has the expected facts and source, every quote found, unknowns honest
  citation   citations.py on a fixture card: errors and warnings expected (MANTIS-IMP-078)
  support    the verifier's verdict on a claim and its cited source (MANTIS-IMP-079)
  counter    the verifier flags counterevidence for a claim that a known conflict contradicts, and not for one that reconciles
A check that does not exist yet scores as a miss, so the first run is an honest baseline. Every run
is appended to mantis/eval/runs.jsonl with its date, label and per-case results. A small set shows
regressions on known cases; it does not prove general reliability.
"""
import importlib, json, sys, time
from datetime import datetime
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "mantis"
E = M / "eval"
CASES, RUNS, VERDICTS = E / "cases.json", E / "runs.jsonl", E / "verdicts.json"


def load_cases():
    return json.loads(CASES.read_text(encoding="utf-8"))["cases"]


def optional(name):
    try:
        return importlib.import_module(name)
    except ImportError:
        return None


# identity -----------------------------------------------------------------------------------
def run_identity(c, ctx):
    import classify
    docs = dict(ctx["corpus"])
    if c.get("source"):
        fm = classify.front((M / c["source"]).read_text(encoding="utf-8"))
        fp = classify.fingerprint(fm)
    else:
        fm = docs[c["doc"]]
        fp = classify.fingerprint(fm)
        if not c.get("keep_self"):        # a near-duplicate: the document itself is not in the corpus it is judged against
            docs.pop(c["doc"], None)
        if c.get("title"):                # a next instance of a recurring meeting: same fingerprint, new title
            fp = dict(fp, title=c["title"])
    verdict, top = classify.classify(fp, docs, ctx["cfg"])
    exp = c["expect"]
    if exp.startswith("version:"):
        ok = verdict == "NEW VERSION of " + exp.split(":", 1)[1]
    elif exp == "not-version":
        ok = not verdict.startswith("NEW VERSION")
    else:   # "new"
        ok = verdict.startswith("NEW DOCUMENT") or (c.get("ask_ok") and verdict.startswith("AMBIGUOUS"))
    return ok, f"{verdict.split(' (')[0]} (top {top[0][1][-4:]} {top[0][0]})" if top else verdict


# retrieval ----------------------------------------------------------------------------------
def run_retrieval(c, ctx):
    import classify
    close = [(s, a if b == c["doc"] else b) for s, a, b in ctx["pairs"] if c["doc"] in (a, b)][:3]
    shown = {d for _, d in close}
    cards = {x["slug"] for x in ctx["cards"] if c["doc"] in x.get("docs", []) and c["other"] in x.get("docs", [])}
    if c["other"] in shown:
        return True, "shown as a close source"
    if cards:
        return True, f"not a close source; shares card {', '.join(sorted(cards))} (only its curated summary is shown)"
    return False, "not shown: not among the 3 closest sources and no shared card"


# discovery (MANTIS-IMP-082 benchmark) --------------------------------------------------------
def run_discovery(c, ctx):
    """Where the other side of a known disagreement ranks among ALL documents, by today's similarity.
    The contradiction check prints the top 3, so a rank above 3 means it is never shown as a source."""
    import classify
    w = ctx["cfg"]["weights"]
    pre = ctx.setdefault("prep", {d: classify.prep(fm) for d, fm in ctx["corpus"].items()})
    ranked = sorted(((classify.score_prep(pre[c["doc"]], pre[d], w), d) for d in pre if d != c["doc"]), reverse=True)
    rank = next(i + 1 for i, (_, d) in enumerate(ranked) if d == c["other"])
    score = next(s for s, d in ranked if d == c["other"])
    import contradictions
    k, floor = c.get("k", 3), c.get("floor", contradictions.FLOOR)   # what contradictions.py shows: the top 3 at or above its floor
    shown = rank <= k and score >= floor
    why = "shown" if shown else (f"below the {floor} similarity floor" if rank <= k else f"not in the top {k}")
    return shown, f"rank {rank} of {len(ranked)}, similarity {score}: {why}"


# questions (MANTIS-IMP-081) ------------------------------------------------------------------
def run_qa(c, ctx):
    """ask.py gather: the expected card among the top 2, and an expected source among the top 6 (or a glossary row)."""
    import io, ask
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        top_c, top_d = ask.gather(c["question"])
    cards, docs = [s for _, s in top_c], [d for _, d in top_d]
    ok_card = not c.get("card") or c["card"] in cards
    ok_doc = not c.get("docs") or any(d in docs for d in c["docs"]) or (c.get("glossary") and "GLOSSARY:" in buf.getvalue())
    return ok_card and ok_doc, f"cards {', '.join(cards)}; sources {', '.join(d[-4:] for d in docs)}" + ("" if ok_card else "; expected card missing") + ("" if ok_doc else "; expected source missing")


def run_pack(c, ctx):
    """The one-step evidence pack (ask.evidence): does an expected source reach it, and how big is it?"""
    import re as _re, ask
    pack = ask.evidence(c["question"])
    docs = set(_re.findall(r"\[(MANTIS-DOC-\d{4})", pack.split("=== SOURCE PASSAGES")[-1])) | set(_re.findall(r"MANTIS-DOC-\d{4}", pack.split("=== RELATIONS")[-1] if "=== RELATIONS" in pack else ""))
    ok_doc = any(d in docs for d in c["docs"])
    ok_text = not c.get("must") or bool(_re.search(c["must"], pack, _re.I))   # the answer-bearing words, not just the document
    return ok_doc and ok_text, f"{len(pack) // 4} tokens; " + ("answer passage in the pack" if ok_doc and ok_text else
        ("expected source missing" if not ok_doc else "source there, but not the passage that answers"))


def run_answer(c, ctx):
    """A saved answer (the Ask job): expected facts present, expected source cited, every quote found, unknowns honest."""
    import re as _re
    bs = sorted((M / "tasks" / "briefs").glob("*-answer.json"), reverse=True)
    same = lambda t: _re.sub(r"[^a-z0-9 ]", "", t.lower()).split()   # punctuation may differ: compare the words
    b = next((json.loads(p.read_text(encoding="utf-8")) for p in bs if same(json.loads(p.read_text(encoding="utf-8")).get("title", "")) == same(c["question"])), None)
    if not b:
        return False, "no saved answer (run: python tools/jobs.py run ask \"<question>\")"
    text = " ".join(x["text"] + " " + x.get("detail", "") for s in b["sections"] for x in s["bullets"])
    cited = {x.get("doc") for s in b["sections"] for x in s["bullets"] if x.get("doc")}
    miss = [f for f in c.get("facts", []) if not _re.search(f, text, _re.I)]
    bad = [f for f in c.get("must_not", []) if _re.search(f, text, _re.I)]
    no_src = c.get("docs") and not (cited & set(c["docs"]))
    problems = (["missing: " + ", ".join(miss)] if miss else []) + (["should not say: " + ", ".join(bad)] if bad else []) \
        + (["expected source not cited"] if no_src else []) + ([f"{b['quotes_not_found']} quote(s) not found"] if b.get("quotes_not_found") else [])
    return not problems, "; ".join(problems) or f"facts present, {b.get('quotes_checked', 0)} quote(s) all found"


# citation -----------------------------------------------------------------------------------
def run_citation(c, ctx):
    cit = optional("citations")
    if not cit:
        return False, "no citation check exists"
    found = cit.check_card(c["text"], set(c["card_docs"]), ctx_override=c.get("ctx"))
    errs = sorted({f["code"] for f in found if f["level"] == "error"})
    warns = sorted({f["code"] for f in found if f["level"] == "warning"})
    ok = errs == sorted(c["expect"].get("errors", [])) and warns == sorted(c["expect"].get("warnings", []))
    return ok, f"errors {errs or 'none'}, warnings {warns or 'none'}"


# support and counter ------------------------------------------------------------------------
def run_support(c, ctx):
    v = ctx["verdicts"].get(c["id"])
    if not v:
        return False, "no verifier verdict"
    ok = v["verdict"] in c["expect"]
    return ok, f"{v['verdict']}: {v.get('reason', '')[:140]}"


def run_counter(c, ctx):
    v = ctx["verdicts"].get(c["id"])
    if not v:
        return False, "no verifier verdict"
    flagged = bool(v.get("counterevidence"))
    exp = c["expect_counter"]
    ok = True if exp == "either" else flagged == exp
    return ok, ("counterevidence: " + "; ".join(x.get("why", "")[:90] for x in v["counterevidence"])[:200]) if flagged else "no counterevidence flagged"


RUNNERS = {"identity": run_identity, "retrieval": run_retrieval, "discovery": run_discovery, "qa": run_qa, "pack": run_pack, "answer": run_answer, "citation": run_citation,
           "support": run_support, "counter": run_counter}


def run(label, verify):
    import classify
    cases = load_cases()
    cfg = json.loads(classify.CONFIG.read_text(encoding="utf-8"))
    corpus = classify.corpus()
    ctx = {"corpus": corpus, "cfg": cfg, "pairs": classify.pair_scores(corpus, cfg["weights"], floor=0.4),
           "cards": json.loads((M / "knowledge/map/features.json").read_text(encoding="utf-8"))
           + json.loads((M / "knowledge/map/topics.json").read_text(encoding="utf-8")), "verdicts": {}, "usage": None}
    if verify:
        sup = optional("support")
        if not sup:
            sys.exit("No verifier yet (tools/support.py).")
        t0 = time.time()
        out = sup.verify_cases([c for c in cases if c["group"] in ("support", "counter")])
        ctx["usage"] = dict(out["usage"], wall_seconds=round(time.time() - t0))
        VERDICTS.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    if VERDICTS.exists():
        saved = json.loads(VERDICTS.read_text(encoding="utf-8"))
        ctx["verdicts"] = {v["id"]: v for v in saved["verdicts"]}
        ctx["usage"] = ctx["usage"] or saved.get("usage")
    results = []
    for c in cases:
        try:
            ok, got = RUNNERS[c["group"]](c, ctx)
        except Exception as e:   # a crash is a failure of that case, not of the run
            ok, got = False, f"crashed: {type(e).__name__}: {e}"
        results.append({"id": c["id"], "group": c["group"], "ok": ok, "got": got, "established": c.get("established", True)})
    rec = {"when": datetime.now().isoformat(timespec="seconds"), "label": label, "results": results, "usage": ctx["usage"]}
    with RUNS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    report(rec, cases)


def report(rec, cases):
    print(f"Run '{rec['label']}' at {rec['when']}")
    by = {}
    for r in rec["results"]:
        by.setdefault(r["group"], []).append(r)
    for g, rs in by.items():
        est = [r for r in rs if r["established"]]
        prov = [r for r in rs if not r["established"]]
        line = f"  {g:<10} {sum(r['ok'] for r in rs)}/{len(rs)} pass"
        if g == "retrieval":   # strict: the other source itself is printed; loose: only a shared card's summary is
            line += f" (strict {sum(r['got'].startswith('shown') for r in rs)}/{len(rs)}: the other source itself is shown)"
        if prov:
            line += f"  (established {sum(r['ok'] for r in est)}/{len(est)}, provisional {sum(r['ok'] for r in prov)}/{len(prov)})"
        print(line)
    for r in rec["results"]:
        print(f"    {'PASS' if r['ok'] else 'FAIL'} {r['id']:<4} {'' if r['established'] else '(provisional) '}{r['got']}")
    if rec.get("usage"):
        u = rec["usage"]
        print(f"  verifier: {u.get('input', 0)} input + {u.get('cache_read', 0)} cached + {u.get('output', 0)} output tokens, "
              f"{u.get('seconds', '?')} s model time, {u.get('wall_seconds', '?')} s wall, ${u.get('cost_usd', 0)} list price")


def add_verdict(cid, right=""):
    """Turn an owner-answered conflict into a counter case (MANTIS-IMP-083): Statement A as the claim, its
    document as the citation, and the owner's verdict as the expectation. "Not a conflict" cases matter most:
    they are how false alarms get measured. Skipped when a side is not a document: the verifier sees only documents."""
    import re as _re
    p = next(iter(M.glob(f"knowledge/registers/conflicts/{cid}.md")), None)
    if not p:
        sys.exit(f"No conflict {cid}")
    t = p.read_text(encoding="utf-8")
    grab = lambda k: (_re.search(r"\*\*%s:\*\*\s*(.+?)(?=\n- \*\*|\Z)" % k, t, _re.S) or [None, ""])[1]
    a, b, status = grab("Statement A"), grab("Statement B"), grab("Status").strip()
    claim_a, src_a = (a.split("**Source:**") + [""])[:2]
    docs_a = sorted(set(_re.findall(r"MANTIS-DOC-\d{4}", src_a)))
    docs_b = sorted(set(_re.findall(r"MANTIS-DOC-\d{4}", (b.split("**Source:**") + [""])[1])))
    if not docs_a or not docs_b:
        print(f"{cid}: skipped, one side is not a document (the owner's answer or user knowledge), so the verifier cannot see it.")
        return
    resolution = " ".join(_re.findall(r"\*\*Resolution[^*]*:\*\*\s*(.+)", t))
    if status.startswith("Closed (not a conflict)") or _re.search(r"reconcil|not a conflict|no conflict", status + " " + resolution, _re.I):
        expect = False   # the owner found the two statements compatible: flagging it would be a false alarm
    elif status.startswith(("Resolved", "Open")):
        # Statement A is the claim. If the owner ruled A right, raising the losing source against it is
        # allowed but not required ("either"); if A lost (or the plan moved on from it), it must be flagged.
        if status.startswith("Resolved") and right not in ("A", "B"):
            print(f"{cid}: say which statement the owner ruled right: add-verdict {cid} --right A|B")
            return
        expect = "either" if right == "A" else True
    else:
        print(f"{cid}: skipped, not settled yet ({status[:60]}).")
        return
    d = json.loads(CASES.read_text(encoding="utf-8"))
    if any(c.get("from") == cid for c in d["cases"]):
        print(f"{cid}: already a case.")
        return
    cards = json.loads((M / "knowledge/map/features.json").read_text(encoding="utf-8")) + json.loads((M / "knowledge/map/topics.json").read_text(encoding="utf-8"))
    card = next((c["slug"] for c in cards if set(docs_a) & set(c.get("docs", [])) and set(docs_b) & set(c.get("docs", []))), "")
    claim = " ".join(_re.sub(r"[*\u2014\-]+\s*$", "", claim_a.strip()).strip('" ').split())
    d["cases"].append({"id": f"V{cid[-3:]}", "from": cid, "group": "counter", "claim": claim, "cites": docs_a[:2], "card": card,
                       "expect_counter": expect, "basis": f"Owner verdict on {cid}: {status[:160]}. Added by evaluate.py add-verdict."})
    CASES.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{cid}: added as V{cid[-3:]} (counterevidence {'expected' if expect else 'NOT expected: a false-alarm check'}; card {card or 'none shared'}).")


def stability(ids, times, label):
    """Run the verifier on a few cases several times, alone (a different context from the full run), and
    count how often each verdict comes back (MANTIS-IMP-084). A case is stable when every run agrees."""
    import support
    cases = [c for c in load_cases() if c["id"] in ids]
    seen = {c["id"]: [] for c in cases}
    usage = []
    for _ in range(times):
        out = support.verify_cases(cases)
        usage.append(out["usage"])
        for v in out["verdicts"]:
            if v.get("id") in seen:
                seen[v["id"]].append(v["verdict"] + (" +counter" if v.get("counterevidence") else ""))
    stable = sum(1 for v in seen.values() if len(set(v)) == 1)
    print(f"Stability '{label}': {stable}/{len(seen)} case(s) gave the same verdict in all {times} runs")
    for c in cases:
        exp = c.get("expect", c.get("expect_counter"))
        print(f"  {c['id']:<4} expected {exp}: {', '.join(seen[c['id']])}")
    print(f"  tokens per run: {sum(u['input'] + u['cache_read'] + u['cache_write'] for u in usage) // times} in, "
          f"{sum(u['output'] for u in usage) // times} out; list-price equivalent ${sum(u['cost_usd'] for u in usage):.2f} in all")
    with (E / "stability.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"when": datetime.now().isoformat(timespec="seconds"), "label": label, "runs": times, "verdicts": seen}) + "\n")


def runs():
    return [json.loads(l) for l in RUNS.read_text(encoding="utf-8").splitlines() if l.strip()] if RUNS.exists() else []


def compare(a=None, b=None):
    rs = runs()
    if len(rs) < 2:
        sys.exit("Need two recorded runs.")
    pick = lambda k, d: next((r for r in rs if r["label"] == k), None) if k else d
    A, B = pick(a, rs[0]), pick(b, rs[-1])
    ra, rb = {r["id"]: r for r in A["results"]}, {r["id"]: r for r in B["results"]}
    print(f"'{A['label']}' ({A['when']}) -> '{B['label']}' ({B['when']})")
    print(f"  pass: {sum(r['ok'] for r in A['results'])}/{len(ra)} -> {sum(r['ok'] for r in B['results'])}/{len(rb)}")
    for i in rb:
        before = ra.get(i, {}).get("ok")
        if before is not None and before != rb[i]["ok"]:
            print(f"  {'FIXED  ' if rb[i]['ok'] else 'REGRESSED'} {i}: {rb[i]['got']}")
    lost = [i for i in rb if ra.get(i, {}).get("ok") and not rb[i]["ok"]]
    print(f"  regressions: {len(lost)}" + (f" ({', '.join(lost)})" if lost else ""))


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if not CASES.exists():
        sys.exit(f"No cases yet: {CASES.relative_to(ROOT)}")
    if argv[:1] == ["run"]:
        label = argv[argv.index("--label") + 1] if "--label" in argv else datetime.now().strftime("%Y-%m-%d %H:%M")
        run(label, "--verify" in argv)
    elif argv[:1] == ["add-verdict"] and len(argv) >= 2:
        right = argv[argv.index("--right") + 1] if "--right" in argv else ""
        for cid in [x for x in argv[1:] if x not in ("--right", right)]:
            add_verdict(cid if cid.startswith("MANTIS-") else "MANTIS-" + cid, right)
    elif argv[:1] == ["stability"] and len(argv) >= 2:
        times = int(argv[argv.index("--times") + 1]) if "--times" in argv else 3
        label = argv[argv.index("--label") + 1] if "--label" in argv else "stability"
        stability(set(argv[1].split(",")), times, label)
    elif argv[:1] == ["compare"]:
        compare(*(argv[1:3]))
    elif argv[:1] == ["list"]:
        for c in load_cases():
            print(f"{c['id']:<4} {c['group']:<9} {'established' if c.get('established', True) else 'PROVISIONAL'}: {c.get('basis', '')}")
    else:
        sys.exit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
