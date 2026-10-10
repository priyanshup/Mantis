"""Decision readiness of roadmap features: problem evidence, measurement plan, launch review (MANTIS-IMP-074 to 076).

    python tools/readiness.py          one line per feature: its state and why
    python tools/readiness.py due      launch reviews due or overdue, and features deciding without evidence

Reads the curated "Problem and outcome", "Measurement" and "Launch review" sections and the
`review_on` front matter of every feature card (format: mantis/TEMPLATES/feature-card.md) into
mantis/knowledge/map/readiness.json for the site and the daily brief. It judges by the evidence,
never by how many fields are filled: a problem backed only by opinions is "not validated" however
complete it looks, and a review with no data is "reviewed, no data", never a success. Cards
without the sections still work: they read as "not framed yet". Approved and mandatory work is not
asked for problem validation (pm-feature-framing, "How deep to go").
"""
import json, re, sys
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import frontmatter

ROOT = Path(__file__).resolve().parent.parent
K = ROOT / "mantis" / "knowledge"
OUT = K / "map" / "readiness.json"
MARK = "<!-- GENERATED"
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# state -> (label, order on Home); lower comes first
STATES = {
    "review-overdue": ("Launch review overdue", 0),
    "live-no-review": ("Live, no review date", 1),
    "no-plan": ("No measurement plan", 2),
    "unvalidated": ("Problem not validated", 3),
    "incomplete": ("Framing incomplete", 4),
    "ready": ("Ready for the next decision", 5),
    "measuring": ("Live, measuring", 6),
    "reviewed-no-data": ("Reviewed, no data", 7),
    "reviewed": ("Reviewed", 8),
    "not-framed": ("Not framed yet", 9),
}


def section(text, name):
    m = re.search(r"(?ms)^##\s+%s\s*$(.*?)(?=^##\s|\Z)" % re.escape(name), text)
    return re.sub(r"(?s)<!--.*?-->", "", m.group(1)) if m else None


def field(sec, name):
    """The value after **Name:**, or "" when missing, a template placeholder, or marked *Unknown*."""
    m = re.search(r"\*\*%s:\*\*[ \t]*(.*)" % re.escape(name), sec or "")
    v = m.group(1).strip() if m else ""
    return "" if not v or v.startswith("<") or v.lower().startswith("*unknown") else v


def plain(s, n=140):
    s = re.sub(r"\*+", "", re.sub(r"\((?:MANTIS-)?[A-Z]{3}-\d+[^)]*\)", "", s)).strip(" .;")
    return s if len(s) <= n else s[:n - 1].rsplit(" ", 1)[0] + "…"


def read_card(path, today):
    text = path.read_text(encoding="utf-8")
    fm, body = frontmatter.split(text)
    cur = body.split(MARK)[0]
    slug, status = fm.get("feature") or path.stem, (fm.get("status") or "discovery").strip()
    r = {"slug": slug, "title": fm.get("title") or slug, "status": status, "framed": False,
         "work_type": "discretionary", "observed": 0, "opinion": 0, "unknown": 0, "request": "", "outcome": "",
         "next_decision": "", "plan": "none", "primary": "", "data_source": "", "decision_rule": False,
         "baselines_to_get": [], "proposed_targets": 0, "review_on": "", "result": "none", "decision": ""}

    po = section(cur, "Problem and outcome")
    if po is not None:
        r["framed"] = True
        for lab in ("Observed", "Opinion", "Unknown"):
            r[lab.lower()] = len(re.findall(r"\*%s:?\*[ \t]*(?!<)\S" % lab, po))   # a template placeholder is not evidence
        wt = field(po, "Work type").lower()
        r["work_type"] = "mandatory" if wt.startswith("mandatory") else "approved" if wt.startswith("approved") else "discretionary"
        r["request"], r["outcome"], r["next_decision"] = field(po, "Request"), field(po, "Outcome wanted"), field(po, "Next decision")

    ms = section(cur, "Measurement")
    if ms is not None:
        prim = re.search(r"\*\*Primary:\s*([^*<][^*]*)\*\*", ms)
        r["primary"] = prim.group(1).strip() if prim else ""
        ds = [d.strip().strip("*").strip() for d in re.findall(r"Data source:\s*([^·\n]+)", ms)]
        r["data_source"] = next((d for d in ds if d and not d.startswith("<") and not d.lower().startswith("unknown")), "")
        r["decision_rule"] = bool(field(ms, "Decision rule"))
        for line in ms.splitlines():
            if "Baseline:" in line and "*Unknown*" in line:
                where = re.search(r"get it from\s+(.+)", line)
                r["baselines_to_get"].append(plain(where.group(1), 90) if where else "source not named")
        r["proposed_targets"] = len(re.findall(r"Target:.*\*Proposed", ms))
        if field(ms, "Obligation") and field(ms, "Acceptance"):
            r["plan"] = "obligation"
        elif r["primary"]:
            r["plan"] = "full" if r["data_source"] and r["decision_rule"] else "partial"
    elif section(cur, "Metrics") and re.search(r"(?m)^\|(?!\s*-)(?!\s*Metric\s*\|).+\|", section(cur, "Metrics")):
        r["plan"] = "legacy"    # the old table: metrics named, no data source or decision rule

    ro = (fm.get("review_on") or "").strip()
    r["review_on"] = ro if DATE.match(ro) else ""
    lr = section(cur, "Launch review")
    res = field(lr, "Result")
    r["result"] = "gap" if "Measurement gap" in res else "value" if res else "none"
    r["decision"] = field(lr, "Decision")
    r["state"], r["why"] = judge(r, today)
    return r


def balance(r):
    return ", ".join(f"{r[k]} {k}" for k in ("observed", "opinion", "unknown") if r[k]) or "no evidence labelled"


def judge(r, today):
    if r["status"] == "live":
        if r["result"] == "value":
            return "reviewed", plain(r["decision"]) or "result recorded"
        if r["result"] == "gap":
            return "reviewed-no-data", "reviewed, but there was no data to judge the outcome"
        if not r["review_on"]:
            return "live-no-review", "live with no date to check whether it worked"
        if r["review_on"] <= today:
            return "review-overdue", f"launch review was due on {r['review_on']}"
        return "measuring", f"review on {r['review_on']}"
    if not r["framed"]:
        return "not-framed", "no Problem and outcome section yet"
    needs_plan = r["status"] in ("refinement", "build")
    if r["work_type"] == "mandatory":
        if needs_plan and r["plan"] != "obligation":
            return "no-plan", "mandatory work without its obligation and acceptance criteria"
    elif r["work_type"] == "discretionary" and (not r["observed"] or r["unknown"] > r["observed"]):
        # validated means observed evidence outweighs what is still unknown; opinions never count as evidence
        return "unvalidated", ("no observed evidence of the problem" if not r["observed"] else "more unknown than observed") + f" ({balance(r)})"
    if needs_plan and r["plan"] not in ("full", "obligation"):
        return "no-plan", {"none": "no success metric yet", "legacy": "metrics named, but no data source or decision rule",
                           "partial": "metric named, but no data source or decision rule"}[r["plan"]] + f", and it is in {r['status']}"
    if not r["next_decision"]:
        return "incomplete", "next decision not stated"
    left = [balance(r)] if r["work_type"] == "discretionary" else []
    if r["baselines_to_get"]:
        left.append(f"{len(r['baselines_to_get'])} baseline(s) to get")
    if r["proposed_targets"]:
        left.append(f"{r['proposed_targets']} proposed target(s) to confirm")
    return "ready", plain(r["next_decision"]) + (f" ({', '.join(left)})" if left else "")


def scan(today=None):
    today = today or date.today().isoformat()
    focus = json.loads((K / "focus.json").read_text(encoding="utf-8")) if (K / "focus.json").exists() else {}
    hidden = set(focus.get("archived", [])) | set(focus.get("off_roadmap", []))
    rows = [read_card(p, today) for p in sorted((K / "features").glob("*.md")) if p.name != "README.md"]
    rows = [r for r in rows if r["slug"] not in hidden]
    follow = focus.get("following", [])
    rows.sort(key=lambda r: (STATES[r["state"]][1], follow.index(r["slug"]) if r["slug"] in follow else 99))
    return rows


def attention(rows):
    """(slug, message, action) for Home's Needs attention: only what needs the owner now."""
    out = []
    for r in rows:
        s, t = r["state"], r["title"]
        if s == "review-overdue":
            out.append((r["slug"], f"{t}: launch review was due on {r['review_on']}. Record the result, or the measurement gap", "Review"))
        elif s == "live-no-review":
            out.append((r["slug"], f"{t} is live with no review date: set when its effect should show in the data", "Set date"))
        elif s == "not-framed" and r["status"] in ("refinement", "build"):
            out.append((r["slug"], f"{t} is in {r['status']} with no problem or measurement written down", "Frame"))
        elif s == "no-plan":
            out.append((r["slug"], f"{t}: {r['why']}", "Plan"))
        elif s == "unvalidated" and r["status"] in ("refinement", "build"):
            out.append((r["slug"], f"{t} is in {r['status']} but its problem is not validated: {r['why']}", "Check"))
        if r["proposed_targets"] and r["status"] != "live":
            out.append((r["slug"], f"{t}: {r['proposed_targets']} proposed target(s) await your confirmation", "Confirm"))
    return out


def build():
    rows = scan()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"states": {k: v[0] for k, v in STATES.items()}, "features": rows,
                               "attention": attention(rows)}, indent=1), encoding="utf-8")
    return rows


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    rows = scan()
    if argv[:1] == ["due"]:
        for slug, msg, _ in attention(rows):
            print(f"Decision readiness ({slug}): {msg}.")
        for r in rows:
            if r["state"] == "measuring":
                print(f"Measuring ({r['slug']}): {r['title']}, review on {r['review_on']}.")
        return 0
    for r in rows:
        print(f"{r['slug']:<24} {r['status']:<11} {STATES[r['state']][0]}: {r['why']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
