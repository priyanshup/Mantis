"""Create an empty Mantis knowledge base on a new machine (MANTIS-IMP-036).

    python tools/init.py            create whatever is missing; never overwrites an existing file
    python tools/init.py --check    list what is missing, change nothing

The engine (tools, site, rules, templates, skills) comes from the repo. The knowledge base under
mantis/ never does: this command creates its empty folders and starter files so every tool and
page works from the first run. Then drop documents into mantis/00_inbox/ and ingest them
(docs/rules/WORKFLOW.md). Standard library only.
"""
import json, sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
M = ROOT / "mantis"

FOLDERS = [
    "00_inbox", "01_sources", "02_digests", "03_archive/answers", "03_archive/edits",
    "knowledge/features", "knowledge/topics", "knowledge/map",
    "knowledge/registers/documents", "knowledge/registers/gaps", "knowledge/registers/assumptions",
    "knowledge/registers/conflicts", "knowledge/registers/decisions",
    "outputs/confluence", "outputs/epics", "outputs/user-stories", "outputs/knowledge-docs",
    "tasks", "jobs", "config",
]

FILES = {
    "knowledge/entity_register.md": """# Entity register

Shared register for the knowledge graph. It names the canonical form of an entity, its type and
the other names sources use for it. `tools/build_map.py` reads it; the graph itself is generated
(`map/graph.json`, `map/entity-graph.md`).

Rules:
- Names that differ only in case, punctuation or a plural "s" merge automatically.
- Any other merge needs a row here with a source. Never merge on a guess: possible duplicates
  are listed in `map/entity-candidates.md` for the owner to confirm.
- Type is one of: person, system, organisation, distributor, market, team, concept, unknown.
- Add a relation only when a digest states it, with that digest as the source.

## Entities

| Entity | Type | Aliases | Source |
|---|---|---|---|

## Relations

| From | Relation | To | Source |
|---|---|---|---|

## Not the same

| Name | Other name | Source |
|---|---|---|
""",
    "knowledge/glossary.md": """# Glossary

Shared register. Outputs link here and copy only the terms a page needs. One plain sentence per
term, with its source. "General term" marks standard industry meaning. Unknown meanings stay
[define], never guessed.

| Term | Meaning | Source |
|---|---|---|
""",
    "knowledge/personas.md": """# Personas

Shared register. Outputs link here and don't rewrite persona text. Every line cites a source.
Evidence level: **assumed** (team belief) or **interviewed** (backed by user interviews).
Skill: `pm-personas`.
""",
    "knowledge/user_knowledge.md": """# User Knowledge Register

Facts the owner stated directly that are not yet in any ingested document. Every entry carries
the tag `Source: User knowledge, [date], not yet present in any ingested document.` When a
document covering the same point is ingested, cross-check it against the entry here and do not
assume a match silently. This file is not generated; edit by hand with approval.
""",
    "knowledge/people.md": """# People

One section per person the owner works with: role, team, how to reach them, what they need in a
briefing or handover, and personal notes the owner wants remembered. Local knowledge, never
committed. Read by the People page, meeting briefs and the away planner.

<!-- Format:
## Full Name
- **Role:** ... (source)
- **Team:** ...
- **Aliases:** ...
- **Channel:** Teams / email
- **Briefing style:** what they need from a brief or handover
- **Notes:** personal or professional things to remember (owner's own notes)
-->
""",
    "knowledge/features/README.md": """# Feature cards

One card per roadmap feature (template: `TEMPLATES/feature-card.md`); other subjects have topic
cards in `../topics/`. Read the card first: its generated part lists every linked source with a
one-liner. The front matter holds `status` (discovery, refinement, build, live), `priority` and
estimates; `tools/build_map.py` turns them into the roadmap.
""",
    "knowledge/topics/README.md": """# Topic cards

One card per subject that is not a roadmap feature (template: `TEMPLATES/topic-card.md`). Front
matter `match_topics` links digests to the card by their topic tags; everything below the
GENERATED marker is rewritten on every rebuild.
""",
    "03_archive/README.md": """# 03_archive

Things Mantis no longer uses day to day but keeps as a record. Nothing here is deleted
automatically. Name snapshot folders `<what>-<YYYY-MM-DD>/`.
""",
    "config/denylist.txt": "# Extra terms the engine repo must never contain (tools/leakcheck.py). One per line. Local only.\n",
}

JSON = {
    "knowledge/focus.json": {"_note": "The owner's choices from the site's Topics page. Written by tools/serve.py.",
                             "following": [], "on_roadmap": [], "off_roadmap": [], "archived_work": []},
    "knowledge/id_claims.json": {},
    "tasks/tasks.json": {"rev": 0, "rollover": "", "dismissed": [], "tasks": []},
    "tasks/archive.json": [],
    "tasks/followups.json": {"rev": 0, "items": []},
    "tasks/meetings.json": {"_note": "Recurring meetings for meeting briefs (MANTIS-IMP-037).", "meetings": []},
    "tasks/away.json": {"_note": "Away periods for the away planner (MANTIS-IMP-038).", "periods": []},
    "config/settings.json": {"_note": "Local settings for this instance. Never committed.",
                             "brand_prefixes": [], "classify_known_version_pairs": []},
}

LOCAL_CLAUDE = """# This Mantis instance (local only, never committed)

Describe here what this instance covers: the owner's role, company, products, preferred product
names, reference examples of each output, voice samples and company-specific evidence sources.
`CLAUDE.md` and `docs/` stay free of company detail.
"""


def main(check):
    missing = [f for f in FOLDERS if not (M / f).is_dir()]
    missing += [f for f in list(FILES) + list(JSON) if not (M / f).exists()]
    if not (ROOT / "CLAUDE.local.md").exists():
        missing.append("../CLAUDE.local.md")
    if check:
        print("Missing:" if missing else "Nothing missing.", *missing, sep="\n  ")
        return
    for f in FOLDERS:
        (M / f).mkdir(parents=True, exist_ok=True)
    for f, text in FILES.items():
        if not (M / f).exists():
            (M / f).write_text(text, encoding="utf-8")
    for f, data in JSON.items():
        if not (M / f).exists():
            (M / f).write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    if not (ROOT / "CLAUDE.local.md").exists():
        (ROOT / "CLAUDE.local.md").write_text(LOCAL_CLAUDE, encoding="utf-8")
    backlog = ROOT / "docs" / "project" / "IMPROVEMENT_BACKLOG.md"   # local: ideas for Mantis itself
    if not backlog.exists():
        backlog.parent.mkdir(parents=True, exist_ok=True)
        backlog.write_text("# IMPROVEMENT_BACKLOG\n\nIdeas for improving Mantis itself. Each entry: ID (MANTIS-IMP-001), title,\n"
                           "description, complexity, expected value, reasoning for deferral, trigger, status.\n", encoding="utf-8")
    print(f"Created {len(missing)} missing item(s)." if missing else "Nothing to create: the knowledge base exists.")
    print("Next: python tools/build_map.py, then python tools/serve.py --open")


if __name__ == "__main__":
    main("--check" in sys.argv)
