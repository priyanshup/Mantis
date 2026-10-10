"""Does the cited source support the claim? An AI verifier, fed by code (MANTIS-IMP-079).

    python tools/support.py packet --card <slug>      claims on a card not checked yet, with their evidence (for a session to judge)
    python tools/support.py check --card <slug>       the same, judged by Claude headless; results recorded (costs tokens)
    python tools/support.py record <file>             record verdicts a session wrote (JSON list, format below)
    python tools/support.py report                    every recorded claim that is not plainly supported

Code gathers the evidence; the model judges it. For each claim: the claim, the cited digests'
Summary, Business Rules and Known Gaps, and the closest other sources on the same card (the
evaluation baseline showed the contradiction check's three closest sources miss the other side of
every known conflict, so the card's own sources are always candidates). Each source is sent once
per run, however many claims cite it.

Two checks, kept apart: claim verification (does the cited source support the claim?) and counterevidence
discovery (does another source qualify or dispute it?). The second searches only the card's sources and the
closest ones, not the whole knowledge base (MANTIS-IMP-082), so finding nothing proves nothing.

Verdicts: supported, partially supported, unsupported (the source does not say it), contradicted
(the source says otherwise), indeterminate (the passage is too thin to tell). Counterevidence: other
sources that disagree, each with why. Word overlap is not support. An attributed statement ("Willem
says X") supports "Willem says X", not X as fact. Results go to knowledge/support.json, keyed by the
claim and the hash of its sources, so a claim is checked again only when it or its source changes.
Nothing is rewritten: findings surface on Health and Home for the owner and the next card refresh.

Record format: [{"card": slug, "claim": text, "cites": [ids], "verdict": ..., "reason": one line,
"counterevidence": [{"doc": id, "why": one line}]}]
"""
import hashlib, json, re, subprocess, sys, time
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import frontmatter

ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "mantis"
STORE = M / "knowledge" / "support.json"
MARK = "<!-- GENERATED"
VERDICTS = ("supported", "partially supported", "unsupported", "contradicted", "indeterminate")
VERSION = 5   # raise when what the verifier sees or is told changes: older verdicts then count as unchecked
DOC = re.compile(r"\bMANTIS-DOC-\d{4}\b")

INSTRUCTIONS = """You verify claims against their cited sources for a product knowledge base. Judge only from the
passages below; you have no other knowledge of this company. For each claim:

1. verdict, comparing the claim with its CITED sources only:
   - "supported": the cited passage states it (a faithful paraphrase is fine).
   - "partially supported": part of the claim is stated and part is not, or the source attributes it
     to one person ("X says ...") while the claim states it as fact.
   - "unsupported": the cited passage does not address what the claim says.
   - "contradicted": the cited passage says something incompatible (a different number, date, owner,
     scope, or the opposite).
   - "indeterminate": the passage touches the subject but is too thin to tell.
   Shared words are not support: check the meaning, numbers, negations and who said it.
   Part of a claim may be cited to something outside these sources (an owner answer, a decision
   entry, a gap): judge only the parts cited to the documents here, and do not mark the claim down
   for the rest.
2. counterevidence: OTHER SOURCES (not the cited ones) that state something incompatible with the
   claim. List only real disagreements on a fact, number, date, scope, owner or meaning, each with the
   source ID and one line on why. Different detail or emphasis is not a disagreement. Empty list if none.
   A digest's own note that a conflict was "logged" or "raised" is history, not evidence: the
   REGISTER STATUS section gives where each logged item stands now (an owner may have found the two
   statements reconcile). Judge the statements themselves, using that status.

3. Three yes/no checks, comparing the claim's wording with the cited passage (answer each one even
   when the facts match):
   - "attributed": the passage gives it as one named person's or speaker's view, account or
     description ("Willem says", "Speaker 1 agrees", "the presenter prefers"), and the claim states it
     as plain fact without saying whose it is. Not attributed: a decision, plan or fact the meeting
     stated and nobody disputed, merely cited to the transcript or the speaker who said it.
   - "hedge_dropped": the passage qualifies it ("confirmed", "probably", "proposed", "tentative",
     "likely", "to be discussed") and the claim drops or strengthens that qualifier.
   - "status_changed": the passage describes something planned, prepared, pending or proposed, and
     the claim states it as done, issued, decided or in place (or the reverse).

Answer with JSON only, no prose: a list of {"id": ..., "verdict": ..., "reason": "<one line>",
"attributed": true|false, "hedge_dropped": true|false, "status_changed": true|false,
"counterevidence": [{"doc": "...", "why": "<one line>"}]} in the order given."""
CHECKS = {"attributed": "a view stated as fact", "hedge_dropped": "a qualifier dropped", "status_changed": "planned stated as done"}


def settle(v):
    """The supported/partly-supported line is drawn by code from the three checks, not left to the verdict's
    wording: the free verdict flipped on such claims from run to run (MANTIS-IMP-084)."""
    hits = [why for k, why in CHECKS.items() if v.get(k) is True]
    if v["verdict"] == "supported" and hits:
        v["verdict"] = "partially supported"
        v["reason"] = (v.get("reason", "") + f" (checks: {', '.join(hits)})").strip()
    return v


def section(text, name, limit):
    m = re.search(r"(?ms)^##\s+%s\s*$(.*?)(?=^##\s|\Z)" % re.escape(name), text)
    return m.group(1).strip()[:limit] if m else ""


def passage(did, limit, whole=False):
    """A source as the verifier sees it. A cited source goes in whole (but its References and Change Log):
    a 3,500-character cut once hid the very sentence a claim rested on, in 4 of 7 flags on real cards."""
    p = M / "02_digests" / f"{did}.md"
    if not p.exists():
        return ""
    text = p.read_text(encoding="utf-8")
    title = frontmatter.parse(text).get("original_title", "")
    if whole:
        body = frontmatter.split(text)[1]
        body = re.split(r"(?m)^##\s+(?:References|Change Log)\s*$", body)[0]
        return f'{did} "{title}" (whole digest)\n{body.strip()[:limit]}'
    parts = [("Summary", section(text, "Summary", limit)), ("Business Rules", section(text, "Business Rules", limit)),
             ("Known Gaps", section(text, "Known Gaps", limit // 3))]
    return f'{did} "{title}"\n' + "\n".join(f"[{n}]\n{t}" for n, t in parts if t)


def others(cited, card, k=3):
    """The other sources most like the cited ones: on the same card, or among the corpus's closest."""
    import classify
    cfg = json.loads(classify.CONFIG.read_text(encoding="utf-8"))
    corpus = classify.corpus()
    pool = set()
    if card:
        for f in ("features.json", "topics.json"):
            for c in json.loads((M / "knowledge" / "map" / f).read_text(encoding="utf-8")):
                if c["slug"] == card:
                    pool |= set(c.get("docs", []))
    for s, a, b in classify.pair_scores(corpus, cfg["weights"], floor=0.3):
        if a in cited or b in cited:
            pool.add(b if a in cited else a)
    pool -= set(cited)
    pre = {d: classify.prep(corpus[d]) for d in pool | set(cited) if d in corpus}
    rank = sorted(((max(classify.score_prep(pre[d], pre[c], cfg["weights"]) for c in cited if c in pre), d) for d in pool if d in pre), reverse=True)
    return [d for _, d in rank[:k]]


def packet(claims):
    """The prompt: instructions, each source once, then the claims."""
    cited_all, other_all, rows = [], [], []
    for c in claims:
        o = others(c["cites"], c.get("card", ""))
        c["_others"] = o
        cited_all += [d for d in c["cites"] if d not in cited_all]
        other_all += [d for d in o if d not in other_all and d not in cited_all]
        rows.append(f'- id {c["id"]}: "{c["claim"]}"\n  cited: {", ".join(c["cites"])}; other sources to check: {", ".join(o) or "none"}')
    srcs = "\n\n".join(passage(d, 20000, whole=True) for d in cited_all) + "\n\n" + "\n\n".join(passage(d, 1500) for d in other_all if d not in cited_all)
    return f"{INSTRUCTIONS}\n\n=== SOURCES ===\n{srcs}\n\n=== REGISTER STATUS ===\n{register_status(srcs)}\n\n=== CLAIMS ===\n" + "\n".join(rows)


def register_status(text):
    """Where each conflict, gap or assumption the passages mention stands now: digests keep notes that go stale."""
    import entry
    lines = []
    for rid in sorted(set(re.findall(r"MANTIS-(?:CFL|GAP|ASM)-\d{3}", text))):
        try:
            body = entry.show(rid) if hasattr(entry, "show") else ""
        except SystemExit:
            body = ""
        if not body:
            p = next(iter(M.glob(f"knowledge/registers/*/{rid}.md")), None)
            body = p.read_text(encoding="utf-8") if p else ""
        st = re.search(r"\*\*Status:\*\*\s*(.+)", body)
        res = re.findall(r"\*\*Resolution[^*]*:\*\*\s*(.+)", body)
        res = next((r for r in reversed(res) if r.strip() and not r.startswith("(none")), "")
        if st:
            lines.append(f"{rid}: {st.group(1).strip()[:160]}" + (f" | {res.strip()[:220]}" if res else ""))
    return "\n".join(lines) or "none mentioned"


def run_model(prompt):
    text, usage = run_model_text(prompt, "verify")
    m = re.search(r"\[.*\]", text, re.S)
    verdicts = json.loads(m.group(0)) if m else []
    for v in verdicts:
        v["verdict"] = str(v.get("verdict", "")).strip().lower()
        v.setdefault("counterevidence", [])
        settle(v)
    return verdicts, usage


def run_model_text(prompt, role="verify", bare=False):
    """One model call with no tools: the prompt in, the reply text and token use out. Used by the verifier and by
    one-step answers (tools/ask.py). A model per role can be set in local settings: {"job_models": {"ask": "..."}}.
    bare=True: a one-line system prompt, run from an empty folder so no project instructions load. For a prompt that
    carries everything it needs, that cut a call from about 11,000 to 4,000 tokens (measured 2026-10-11)."""
    import jobs, tempfile
    cmd = jobs.agent_command()
    if not cmd:
        sys.exit("No headless agent found (claude).")
    # the prompt goes in on stdin: a Windows command line stops at about 32,000 characters
    cmd = cmd + ["-p", "--output-format", "json", "--tools", "", "--strict-mcp-config", "--disable-slash-commands"]
    run_in = ROOT
    if bare:
        cmd += ["--system-prompt", "You answer questions from the evidence you are given and reply with JSON only."]
        run_in = Path(tempfile.mkdtemp(prefix="mantis-call-"))
    try:
        import local_config
        model = local_config.load().get("job_models", {}).get(role)
        if model:
            cmd += ["--model", model]
    except Exception:
        pass
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=run_in, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900,
                           env=jobs._clean_env(), input=prompt, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    finally:
        if bare:
            import shutil
            shutil.rmtree(run_in, ignore_errors=True)
    try:
        out = json.loads(r.stdout)
    except ValueError:
        raise SystemExit(f"The model did not answer: {(r.stderr or r.stdout).strip()[:300]}")
    u = out.get("usage") or {}
    usage = {"input": u.get("input_tokens", 0), "output": u.get("output_tokens", 0), "cache_read": u.get("cache_read_input_tokens", 0),
             "cache_write": u.get("cache_creation_input_tokens", 0), "cost_usd": round(out.get("total_cost_usd", 0) or 0, 4),
             "seconds": round((out.get("duration_ms", 0) or 0) / 1000), "wall": round(time.time() - t0),
             "model": ",".join((out.get("modelUsage") or {}).keys()), "prompt_chars": len(prompt)}
    return out.get("result", "") or "", usage


def verify_cases(cases):
    """For the evaluation set (tools/evaluate.py): one model call for every support and counter case."""
    claims = [{"id": c["id"], "claim": c["claim"], "cites": c["cites"], "card": c.get("card", "")} for c in cases]
    verdicts, usage = run_model(packet(claims))
    return {"verdicts": verdicts, "usage": usage}


# Routine use on cards ------------------------------------------------------------------------
def card_claims(slug):
    """Business rules and observed problem evidence on a card, with the documents each cites."""
    p = next((q for q in (M / "knowledge" / "features" / f"{slug}.md", M / "knowledge" / "topics" / f"{slug}.md") if q.exists()), None)
    if not p:
        sys.exit(f"No card {slug}")
    cur = frontmatter.split(p.read_text(encoding="utf-8"))[1].split(MARK)[0]
    out = []
    for name, pat in (("Business rules agreed so far", r"^- (.+)$"), ("Problem and outcome", r"^\s*- \*Observed:\*\s*(.+)$")):
        sec = re.search(r"(?ms)^## %s\s*$(.*?)(?=^## |\Z)" % re.escape(name), cur)
        for line in re.findall(pat, sec.group(1) if sec else "", re.M):
            cites = sorted(set(DOC.findall(line)))
            if cites:
                claim = re.sub(r"\s*\((?:[^()]*MANTIS-DOC-\d{4}[^()]*)\)", "", line).strip()
                out.append({"card": slug, "claim": claim, "cites": cites})
    return out


def key(c):
    src = "".join(hashlib.sha1((M / "02_digests" / f"{d}.md").read_bytes()).hexdigest()[:8]
                  for d in c["cites"] if (M / "02_digests" / f"{d}.md").exists())
    return hashlib.sha1((c["claim"] + "|" + src).encode("utf-8")).hexdigest()[:16]


def load():
    return json.loads(STORE.read_text(encoding="utf-8")) if STORE.exists() else {}


def unchecked(slug):
    done = load().get(slug, {})
    cs = card_claims(slug)
    for i, c in enumerate(cs):
        c["id"] = f"{slug}-{i + 1}"
    return [c for c in cs if done.get(key(c), {}).get("version") != VERSION]


def record(items):
    st = load()
    for v in items:
        if v.get("verdict") not in VERDICTS:
            raise SystemExit(f"Unknown verdict {v.get('verdict')!r} for: {v.get('claim', '')[:60]}")
        c = {"claim": v["claim"], "cites": v["cites"]}
        st.setdefault(v["card"], {})[key(c)] = {"claim": v["claim"], "cites": v["cites"], "verdict": v["verdict"],
                                                 "reason": v.get("reason", ""), "counterevidence": v.get("counterevidence", []),
                                                 "checked": date.today().isoformat(), "version": VERSION}
    STORE.write_text(json.dumps(st, indent=1, ensure_ascii=False), encoding="utf-8")
    return st


def findings():
    """Recorded claims that are not plainly supported, or that other sources dispute; stale ones (card text changed) dropped."""
    out = []
    for slug, items in load().items():
        try:
            live = {key(c) for c in card_claims(slug)}
        except SystemExit:
            continue
        for k, v in items.items():
            if k in live and v.get("version") == VERSION and (v["verdict"] != "supported" or v["counterevidence"]):
                out.append(dict(v, card=slug))
    order = {"contradicted": 0, "unsupported": 1, "partially supported": 2, "indeterminate": 3, "supported": 4}
    return sorted(out, key=lambda v: (order.get(v["verdict"], 5), v["card"]))


USAGE = M / "knowledge" / "support-runs.jsonl"


def log_run(card, asked, answered, u):
    """One line per verifier run, so cost per claim, cache hits and run time can be watched as use grows."""
    total_in = u["input"] + u["cache_read"] + u["cache_write"]
    row = {"date": date.today().isoformat(), "card": card, "claims_asked": asked, "claims_answered": answered,
           "tokens_in": total_in, "cache_read": u["cache_read"], "cache_write": u["cache_write"], "output": u["output"],
           "cache_hit": round(u["cache_read"] / total_in, 3) if total_in else 0, "seconds": u["wall"],
           "list_price_usd": u["cost_usd"], "model": u["model"], "version": VERSION}
    with USAGE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def usage_report():
    rows = [json.loads(l) for l in USAGE.read_text(encoding="utf-8").splitlines() if l.strip()] if USAGE.exists() else []
    if not rows:
        print("No verifier runs logged yet.")
        return
    n = sum(r["claims_answered"] for r in rows)
    print(f"{len(rows)} run(s), {n} claim(s). Per claim: {sum(r['tokens_in'] for r in rows) // max(n, 1)} tokens in, "
          f"{sum(r['output'] for r in rows) // max(n, 1)} out, {sum(r['seconds'] for r in rows) / max(n, 1):.1f} s. "
          f"Cache hit {sum(r['cache_read'] for r in rows) / max(sum(r['tokens_in'] for r in rows), 1):.0%}. "
          f"List-price equivalent ${sum(r['list_price_usd'] for r in rows):.2f} in all; a subscription is not billed per token.")
    for r in rows[-10:]:
        print(f"  {r['date']} {r['card']:<22} {r['claims_answered']:>3} claims  {r['tokens_in']:>6} in  {r['cache_hit']:.0%} cached  {r['seconds']:>3} s  ${r['list_price_usd']}")


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if argv[:1] in (["packet"], ["check"]) and "--card" in argv:
        slug = argv[argv.index("--card") + 1]
        cs = unchecked(slug)
        if not cs:
            print(f"Every claim on {slug} has been checked against its current sources.")
            return 0
        if argv[0] == "packet":
            print(packet(cs) + "\n\nThen save the list (with card, claim and cites copied from each claim) and run: python tools/support.py record <file>")
            return 0
        verdicts, usage = run_model(packet(cs))
        by = {v.get("id"): v for v in verdicts}
        rec = [dict(c, **{k: by[c["id"]][k] for k in ("verdict", "reason", "counterevidence") if k in by.get(c["id"], {})})
               for c in cs if c["id"] in by]
        record(rec)
        log_run(slug, len(cs), len(rec), usage)
        print(f"Checked {len(rec)} of {len(cs)} claim(s) on {slug}: " + ", ".join(f"{sum(r['verdict'] == v for r in rec)} {v}" for v in VERDICTS if any(r['verdict'] == v for r in rec)))
        print(f"Tokens: {usage['input']} input, {usage['cache_write']} written to cache, {usage['cache_read']} read from cache, "
              f"{usage['output']} output; {usage['wall']} s. List-price equivalent ${usage['cost_usd']} (not what a subscription is billed).")
        return 0
    if argv[:1] == ["usage"]:
        usage_report()
        return 0
    if argv[:1] == ["record"] and len(argv) == 2:
        record(json.loads(Path(argv[1]).read_text(encoding="utf-8")))
        print("Recorded.")
        return 0
    if argv[:1] == ["report"]:
        for v in findings():
            ce = "; ".join(f"{x['doc']}: {x['why']}" for x in v["counterevidence"])
            print(f"[{v['verdict']}] {v['card']}: {v['claim'][:120]}\n    {v['reason']}" + (f"\n    other sources disagree: {ce}" if ce else ""))
        return 0
    sys.exit(__doc__)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
