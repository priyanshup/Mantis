"""Mantis housekeeping: safe automatic cleanup plus a health report (MANTIS-IMP-015).

    python tools/maintain.py             clean up and write the health report now
    python tools/maintain.py --if-due    do it only if the last run was 7+ days ago (the session-start hook uses this)
    python tools/maintain.py --report    health report only, no cleanup (build_map.py uses this on every rebuild)

Cleanup touches only things that are regenerated or temporary: __pycache__ folders, editor and
OS temp files, old site build folders in %TEMP%, extracted inbox copies whose original has
gone, and project backups beyond the newest five (%LOCALAPPDATA%/Mantis/backups). It never deletes knowledge, sources, outputs or archives; those are reported for the owner.
Writes mantis/knowledge/map/health.md and health.json.
"""
import json, os, re, shutil, sys, tempfile, time
from datetime import date, datetime
from itertools import combinations
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "mantis"
MAP = M / "knowledge" / "map"
STAMP = MAP / ".maintained"
TODAY = date.today()


def days_since(s):
    try:
        return (TODAY - datetime.strptime(s[:10], "%Y-%m-%d").date()).days
    except (ValueError, TypeError):
        return None


def cleanup():
    removed = [f"diagram candidate image ({n})" for n in range(prune_asset_files())]
    for p in list(ROOT.rglob("__pycache__")):
        shutil.rmtree(p, ignore_errors=True)
        removed.append(p.relative_to(ROOT).as_posix())
    for pat in ("*.tmp", "~$*", "*.bak", ".~lock*", "Thumbs.db", ".DS_Store"):
        for p in ROOT.rglob(pat):
            if p.is_file() and "01_sources" not in p.parts:
                p.unlink(missing_ok=True)
                removed.append(p.relative_to(ROOT).as_posix())
    for p in Path(tempfile.gettempdir()).glob("mantis-site-*"):
        if time.time() - p.stat().st_mtime > 86400:
            shutil.rmtree(p, ignore_errors=True)
            removed.append(f"%TEMP%/{p.name}")
    try:   # task list: archive yesterday's done items, drop archive entries older than 7 days
        sys.path.insert(0, str(Path(__file__).parent))
        import tasks_store
        tasks_store.load()
    except Exception:
        pass
    backups = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "Mantis" / "backups"
    if backups.exists():   # whole-project zips taken before big changes: keep the newest five
        for p in sorted(backups.glob("*.zip"), key=lambda x: x.stat().st_mtime, reverse=True)[5:]:
            p.unlink(missing_ok=True)
            removed.append(f"backups/{p.name}")
    ext = M / "00_inbox" / ".extracted"
    if ext.exists():
        originals = {p.stem for p in (M / "00_inbox").iterdir() if p.is_file()}
        for p in ext.glob("*.md"):
            if p.stem not in originals:
                p.unlink()
                removed.append(p.relative_to(ROOT).as_posix())
    return removed


def load(name):
    p = MAP / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def prune_asset_files():
    """Weekly: image files of unregistered candidates go; they are extracted again when needed (MANTIS-IMP-067)."""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        import assets
        return assets.prune_files()
    except Exception:
        return 0


def report():
    sys.path.insert(0, str(Path(__file__).parent))
    import entry
    items = []  # (level, area, message)
    add = lambda lvl, area, msg: items.append({"level": lvl, "area": area, "msg": msg})

    lint = entry.check()
    if lint:
        missing = sorted({m.group(0) for l in lint for m in [re.search(r"MANTIS-(?:GAP|ASM|CFL)-\d+", l)] if m})
        add("warn", "Registers", f"{len(lint)} register problem(s)" + (f"; digests cite entries that do not exist: {', '.join(missing)}" if missing else "") + ". Run `python tools/entry.py check`.")

    # Citations that resolve to nothing, and card claims the verifier found unsupported (MANTIS-IMP-078, 079)
    import citations, support
    cf = citations.scan()
    errs, warns = [f for f in cf if f["level"] == "error"], [f for f in cf if f["level"] == "warning"]
    if errs:
        add("warn", "Citations", f"{len(errs)} citation(s) resolve to nothing: " + "; ".join(f"{f['where']} line {f['line']}: {f['msg']}" for f in errs[:3])
            + ". Run `python tools/citations.py`; fix the citation, never the source.")
    if warns:
        add("info", "Citations", f"{len(warns)} citation warning(s): a source not linked to its card, or a business rule with no source. Run `python tools/citations.py`.")
    sf = support.findings()
    # Two different checks, reported apart: does the cited source support the claim (claim verification), and does
    # another source dispute it (counterevidence: searched only among the card's sources and the closest, MANTIS-IMP-082)
    bad = [v for v in sf if v["verdict"] in ("contradicted", "unsupported")]
    soft = [v for v in sf if v["verdict"] in ("partially supported", "indeterminate")]
    disputed = [v for v in sf if v["counterevidence"]]
    if bad:
        add("warn", "Claims", f"{len(bad)} card claim(s) not supported by their own cited source: "
            + "; ".join(f"{v['card']}: \"{v['claim'][:70]}\" ({v['verdict']})" for v in bad[:3])
            + ". Run `python tools/support.py report`. The card keeps its claim until you decide.")
    if disputed:
        add("warn", "Counterevidence", f"{len(disputed)} card claim(s) another source qualifies or disputes: "
            + "; ".join(f"{v['card']}: \"{v['claim'][:70]}\"" for v in disputed[:3])
            + ". Searched only among the card's sources and the closest ones, so a clean result is not proof. Run `python tools/support.py report`.")
    if soft:
        add("info", "Claims", f"{len(soft)} card claim(s) only partly supported (often a view stated as fact, or a dropped hedge) or too thin to judge. "
            "These verdicts vary between runs; treat them as prompts to reread. Run `python tools/support.py report`.")

    # Owner actions (summaries to refresh, suggested cards, drafts, questions and names waiting) are on Home's
    # "Needs attention" list; this report keeps what is about Mantis itself (MANTIS-IMP-069).
    cards_md = (MAP / "cards.md").read_text(encoding="utf-8") if (MAP / "cards.md").exists() else ""
    split = re.search(r"(?ms)^## Cards to split.*?\n\n(.*?)(?=^## |\Z)", cards_md)
    for line in (split.group(1).strip().splitlines() if split else []):
        if line.startswith("- "):
            add("todo", "Cards", f"Too large to read cheaply, split into narrower cards (`parent:` in their front matter): {line[2:]}")
    m = re.search(r"(\d+) of (\d+) documents are linked", cards_md)
    if m and m.group(1) != m.group(2):
        add("info", "Cards", f"{int(m.group(2)) - int(m.group(1))} document(s) are linked to no card (see map/cards.md).")

    inbox = [p for p in (M / "00_inbox").iterdir() if p.is_file()] if (M / "00_inbox").exists() else []
    for p in inbox:
        age = (time.time() - p.stat().st_mtime) / 86400
        kind = "answers" if p.name.startswith("answers-") else "edit" if p.name.startswith("edit-") else "file to ingest"
        add("warn" if age > 7 else "todo", "Inbox", f"{p.name} ({kind}) waiting {age:.0f} day(s).")

    assets = load("assets.json")
    tiers = assets.get("tiers", {}) if isinstance(assets, dict) else {}
    if tiers.get("candidate"):
        add("info", "Diagrams", f"{tiers['candidate']} image(s) from the sources wait for a look ({tiers.get('registered', 0)} registered so far). "
                                "`python tools/assets.py review` lists them, largest first.")

    big = sorted(((p.stat().st_size, p.stem) for p in (M / "02_digests").glob("MANTIS-DOC-*.md") if p.stat().st_size > 16000), reverse=True)
    if big:
        add("info", "Digests", f"{len(big)} digest(s) over 16 KB (largest {big[0][1]}, {big[0][0] // 1024} KB); read their summary with peek.py first.")

    try:
        import classify
        docs = classify.corpus()
        w = json.loads(classify.CONFIG.read_text(encoding="utf-8"))
        pairs = classify.pair_scores(docs, w["weights"], floor=min(0.5, w["version"] - 0.05))
        near = [p for p in pairs if p[0] >= 0.5]
        if near:
            add("info", "Duplicates", "Near-duplicate digests (same card covers them): " + ", ".join(f"{x[-4:]}~{y[-4:]} ({s:.2f})" for s, x, y in near[:6]) + ".")
        if pairs and pairs[0][0] >= w["version"] - 0.05:
            add("warn", "Classifier", f"Two distinct digests score {pairs[0][0]:.2f}, close to the version cut-off {w['version']}; re-run `python tools/classify.py --calibrate`.")
    except Exception as e:
        add("info", "Classifier", f"Duplicate check skipped ({e}).")

    arch = M / "03_archive"
    size = sum(p.stat().st_size for p in arch.rglob("*") if p.is_file()) if arch.exists() else 0
    oldest = [p.name for p in arch.iterdir() if p.name != "README.md" and (time.time() - p.stat().st_mtime) / 86400 > 90] if arch.exists() else []
    add("info", "Archive", f"03_archive holds {size / 1e6:.1f} MB" + (f"; older than 90 days: {', '.join(oldest[:6])}. The owner decides what to delete." if oldest else "."))

    order = {"warn": 0, "todo": 1, "info": 2}
    items.sort(key=lambda i: order[i["level"]])
    MAP.mkdir(parents=True, exist_ok=True)
    (MAP / "health.json").write_text(json.dumps({"date": TODAY.isoformat(), "items": items}, indent=1), encoding="utf-8")
    label = {"warn": "Fix", "todo": "To do", "info": "Note"}
    rows = ["# Mantis health", "", f"Generated {TODAY.isoformat()} by `tools/maintain.py`.", ""]
    rows += [f"- **{label[i['level']]}** ({i['area']}): {i['msg']}" for i in items] or ["All clear."]
    (MAP / "health.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return items


def main(args):
    if "--if-due" in args and STAMP.exists() and (time.time() - STAMP.stat().st_mtime) < 7 * 86400:
        return
    removed = [] if "--report" in args else cleanup()
    items = report()
    if "--report" not in args:
        STAMP.write_text(TODAY.isoformat() + "\n", encoding="utf-8")
        n = {k: sum(1 for i in items if i["level"] == k) for k in ("warn", "todo")}
        print(f"Maintenance: removed {len(removed)} temporary item(s); health: {n['warn']} to fix, {n['todo']} to do. See mantis/knowledge/map/health.md.")


if __name__ == "__main__":
    main(sys.argv[1:])
