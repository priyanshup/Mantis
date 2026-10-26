"""What a card refresh changed and what it cost: curated part before and after, plus exact token use (MANTIS-IMP-090). Stdlib only.

    python tools/refresh_report.py SNAPSHOT_DIR [--since YYYY-MM-DDTHH:MM]

SNAPSHOT_DIR holds copies of the cards taken before the refresh (features/ and topics/, e.g.
mantis/03_archive/cards-before-refresh-<date>/). For each card that changed it prints the front-matter
fields that changed, the sections whose text changed (lines added and removed), and the tokens of the
"refresh-card" job that did it, read from the job record Claude Code itself reported (input, output,
cache reads and writes, cost, turns, seconds). Writes the same as REPORT.md in SNAPSHOT_DIR.
"""
import json, re, sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
K = ROOT / "mantis" / "knowledge"
JOBS = ROOT / "mantis" / "jobs"


def curated(text):
    return text.split("<!-- GENERATED", 1)[0]


def front(text):
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    return dict(re.findall(r"(?m)^(\w+):\s*(.*)$", m.group(1))) if m else {}


def sections(text):
    """{heading: body} of the curated part, front matter excluded."""
    body = re.sub(r"(?s)^---\n.*?\n---\n", "", curated(text))
    out, head = {}, "(top)"
    for line in body.splitlines():
        if line.startswith("#"):
            head = line.lstrip("# ").strip()
            continue
        if line.strip() and not line.startswith("<!--"):
            out.setdefault(head, []).append(line.strip())
    return out


def jobs_for(slug, since):
    rows = []
    for p in JOBS.glob("*.json"):
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if j.get("type") == "refresh-card" and j.get("arg") == slug and j.get("created", "") >= since:
            rows.append(j)
    return sorted(rows, key=lambda j: j["created"])


def main(argv):
    sys.stdout.reconfigure(errors="replace")
    if not argv:
        print(__doc__)
        return 1
    snap = Path(argv[0])
    since = argv[argv.index("--since") + 1] if "--since" in argv else ""
    L = [f"# Card refresh report", "", f"Before: `{snap.as_posix()}`. Tokens are those Claude Code reported for each job.", ""]
    total = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "cost_usd": 0.0}
    table = ["| Card | Sections changed | Lines +/- | Input | Output | Cache read | Cache write | Cost (USD) | Minutes | Result |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    detail = []
    for before in sorted(list(snap.glob("features/*.md")) + list(snap.glob("topics/*.md"))):
        if before.name == "README.md":
            continue
        now_p = K / before.parent.name / before.name
        if not now_p.exists():
            continue
        b, n = before.read_text(encoding="utf-8"), now_p.read_text(encoding="utf-8")
        slug = before.stem
        js = jobs_for(slug, since)
        if curated(b) == curated(n) and not js:
            continue
        fb, fn = front(b), front(n)
        fields = [k for k in sorted(set(fb) | set(fn)) if fb.get(k) != fn.get(k)]
        sb, sn = sections(b), sections(n)
        changed, plus, minus = [], 0, 0
        for h in list(sn) + [h for h in sb if h not in sn]:
            old, new = set(sb.get(h, [])), set(sn.get(h, []))
            if old != new:
                changed.append(h)
                plus, minus = plus + len(new - old), minus + len(old - new)
        u = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0, "cost_usd": 0.0, "seconds": 0}
        state = js[-1].get("state", "") if js else "no job (front matter only)"
        for j in js:
            for k in u:
                u[k] += (j.get("usage") or {}).get(k, 0) or 0
        for k in total:
            total[k] += u[k]
        table.append(f"| {slug} | {len(changed)} | +{plus} / -{minus} | {u['input']:,} | {u['output']:,} | {u['cache_read']:,} | "
                     f"{u['cache_write']:,} | {u['cost_usd']:.2f} | {u['seconds'] / 60:.0f} | {state} |")
        detail += [f"## {slug}", "", f"- Front matter changed: {', '.join(fields) or 'nothing'}",
                   f"- Sections changed: {'; '.join(changed) or 'none'}"]
        for j in js:
            if j.get("summary"):
                detail.append(f"- Job summary: {j['summary'].strip()[:900]}")
            for nv in j.get("needs_you", []):
                detail.append(f"- Needs you: {nv}")
        detail.append("")
    table.append(f"| **Total** | | | {total['input']:,} | {total['output']:,} | {total['cache_read']:,} | {total['cache_write']:,} | "
                 f"{total['cost_usd']:.2f} | | |")
    L += table + ["", "Input = new tokens sent; cache read = tokens re-read from the prompt cache (cheaper); "
                  "cost is what Claude Code reports (on a subscription it is notional).", ""] + detail
    (snap / "REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
