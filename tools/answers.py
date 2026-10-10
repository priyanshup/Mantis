"""Check the owner's answers before recording them (MANTIS-IMP-050). Stdlib only.

    python tools/answers.py check FILE      FILE = mantis/00_inbox/answers-*.md
    python tools/answers.py check --all     every answers file waiting in the inbox, each answer with its entry's full text

With --all this is the one read a processing session needs: no separate file reads or `entry.py show`.

For each answer it prints what needs care, so nothing slips through:
  EARLIER   the owner's earlier answers on the same entry and on entries linked to it (an entry
            that names it, or that it names). A new answer that differs replaces the old one,
            and the note must say so.
  MISHEARD  words the glossary's Mishearings table knows (tools/mishear.py).
  PROMISE   sentences that read as a promise: by the owner ("I will send") -> a task; by
            someone else ("Sam will confirm") -> a follow-up wait.
  DECISION  sentences that read as a settled choice ("we will use", "it was decided") -> a
            decision entry, if the choice is new.
  UNDECIDED "Answers it" whose text says it is not decided -> record it as "Not decided yet".
It only reads; docs/rules/WORKFLOW.md ("Owner answers from the site") says what to record.
"""
import re, sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
REG = ROOT / "mantis" / "knowledge" / "registers"
sys.path.insert(0, str(Path(__file__).parent))
ID = re.compile(r"MANTIS-(?:GAP|ASM|CFL)-\d{3}")
SENT = re.compile(r"(?<=[.!?])\s+|\n+")
PROMISE = re.compile(r"\b(I|I'll|I will|I am going to|I'm going to)\b[^.]*?\b(send|share|post|give|provide|check|ask|confirm|follow up|get back|upload|forward)\b", re.I)
OTHER_PROMISE = re.compile(r"\b([A-Z][a-z]+(?: [A-Z][a-z]+)?) (will|is going to|to) (send|share|confirm|check|ask|provide|get back|follow up)\b")
DECISION = re.compile(r"\b(we (will|'ll|are going to|have decided to|decided to) (use|reuse|build|go with|keep|drop|park|not|piggyback|skip)|it (was|has been) decided|we have discarded|we discarded|we parked)\b", re.I)
UNDECIDED = re.compile(r"\b(do not know|don't know|not decided|will be decided|to be decided|open question|not sure yet|we will see|tbd|has not been decided|might get parked)\b", re.I)


def blocks(text):
    for m in re.finditer(r"(?ms)^## (\S+?):? (.*?)\n(.*?)(?=^## |\Z)", text):
        rid, topic, body = m.group(1).rstrip(":"), m.group(2).strip(), m.group(3)
        verdict = (re.search(r"(?m)^- Verdict:\s*(.+)$", body) or [None, ""])[1].strip()
        ans = body.split("- Answer:", 1)[1] if "- Answer:" in body else ""
        yield rid, topic, verdict, "\n".join(l.strip() for l in ans.splitlines()).strip()


def entry_path(rid):
    folder = {"GAP": "gaps", "ASM": "assumptions", "CFL": "conflicts"}[rid.split("-")[1]]
    return REG / folder / f"{rid}.md"


def earlier(rid):
    """[(entry, label, text)] owner answers already recorded on this entry or linked ones."""
    if not ID.fullmatch(rid) or not entry_path(rid).exists():
        return []
    own = entry_path(rid).read_text(encoding="utf-8")
    linked = set(ID.findall(own)) - {rid}
    for folder in ("gaps", "assumptions", "conflicts"):
        for p in (REG / folder).glob("MANTIS-*.md"):
            if p.stem != rid and rid in p.read_text(encoding="utf-8"):
                linked.add(p.stem)
    out = []
    for e in [rid] + sorted(linked):
        p = entry_path(e)
        if not p.exists():
            continue
        for label, text in re.findall(r"(?ms)^- \*\*([^*]+?):\*\*\s*(.*?)(?=^- \*\*|\Z)", p.read_text(encoding="utf-8")):
            t = " ".join(text.split())
            if "owner answer" in (label + " " + t[:120]).lower() or "owner, 20" in t.lower():
                out.append((e, label.strip(), t[:280] + ("…" if len(t) > 280 else "")))
    return out


def check(paths, with_entry=False):
    import mishear
    table = mishear.load()
    n = 0
    for path in paths:
        if len(paths) > 1:
            print(f"\n##### {Path(path).name}")
        n += check_one(Path(path).read_text(encoding="utf-8"), table, with_entry)
    print(f"\n{n} answer(s) checked in {len(paths)} file(s).")


def check_one(text, table, with_entry):
    import mishear
    n = 0
    for rid, topic, verdict, ans in blocks(text):
        n += 1
        print(f"\n=== {rid}: {topic[:100]}\nVerdict: {verdict or '-'}")
        if with_entry and ID.fullmatch(rid) and entry_path(rid).exists():
            body = re.sub(r"(?s)<!--.*?-->", "", entry_path(rid).read_text(encoding="utf-8")).strip()
            print("ENTRY:\n" + "\n".join("  " + l for l in body.splitlines()[1:] if l.strip()))
        if with_entry:
            print("ANSWER:\n" + "\n".join("  " + l for l in ans.splitlines()))
        for e, label, t in earlier(rid):
            if with_entry and e == rid:
                continue   # already in ENTRY above
            print(f"  EARLIER ({e}, {label}): {t}")
        m = mishear.report(ans, table)
        if m:
            print("  MISHEARD: " + m.replace("Possible mishearings: ", ""))
        for s in (x.strip() for x in SENT.split(ans) if x.strip()):
            if PROMISE.search(s):
                print(f"  PROMISE (owner -> task): {s[:220]}")
            elif OTHER_PROMISE.search(s) and not s.lower().startswith(("we ", "the team")):
                print(f"  PROMISE (someone else -> follow-up): {s[:220]}")
            if DECISION.search(s):
                print(f"  DECISION?: {s[:220]}")
        if verdict.lower().startswith("answers it") and UNDECIDED.search(ans):
            print(f"  UNDECIDED: the answer says it is not decided ({UNDECIDED.search(ans).group(0)!r}); record it as 'Not decided yet' (Deferred).")
    return n


if __name__ == "__main__":
    if sys.argv[1:] == ["check", "--all"]:
        files = sorted((ROOT / "mantis" / "00_inbox").glob("answers-*.md"))
        if not files:
            sys.exit("No answers waiting in the inbox.")
        check([str(f) for f in files], with_entry=True)
    elif len(sys.argv) == 3 and sys.argv[1] == "check":
        check([sys.argv[2]])
    else:
        sys.exit(__doc__)
