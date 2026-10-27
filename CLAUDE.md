# Mantis

The owner's personal assistant and knowledge repository. The repo is the source of truth, not any
chat. Rules: `docs/rules/PROJECT_VISION.md`. Workflow: `docs/rules/WORKFLOW.md`, an index naming
the one file in `docs/rules/workflow/` for each task. Writing: `docs/rules/OUTPUTS_GUIDE.md`.
Tools: `docs/system/SKILLS.md`. Where things live: `README.md` and each folder's README; cleanup:
`docs/system/MAINTENANCE.md`.

## Read cheaply, in this order

1. **The subject's card** (`mantis/knowledge/map/cards.md` lists them): `knowledge/features/<slug>.md`
   or `knowledge/topics/<slug>.md`. Its generated part lists every source with a one-liner, the
   open questions with live status, and the people and systems involved.
2. **A person, system or place:** `python tools/graph.py <name>` (or `path <A> <B>`); someone the
   owner works with: `python tools/people.py show <name>`.
3. **A document:** `python tools/peek.py <ids>`; the whole digest only when the summary is not enough.
4. **Open questions:** `knowledge/map/registers.md`; one with `python tools/entry.py show <ID>`.
5. **What the owner owns:** `knowledge/focus.json` (followed, archived, on the roadmap; set on the
   Features page). Put those first in reports and checks.
6. Never read the register folders, `MAP.md` or many digests whole. No card for a subject: look in
   `MAP.md` or `topics.md`, then consider a topic card.

## Write

- Registers only through `tools/entry.py`: `next`, `add`, `status`, `note`; `close` for an open
  question a source clearly answers, `reopen` to undo it.
- Cards: only the curated part above the GENERATED marker; add newly covered sources to
  `source_documents`.
- Never edit by hand: `knowledge/map/*`, card text below the marker, index entries (except Notes), the site.
- After any change: `python tools/build_map.py` (map, cards, index, lint, health, site).

## The owner's day

- "Pull": `docs/rules/workflow/pull.md`; only the owner starts one. Filters: `python tools/pull.py filters`.
  One-off Jira and Confluence reads: `python tools/atl.py` (read-only). The mirror (`mantis/mirror/`)
  is not a source; a pull packet becomes one when copied to `01_sources/`.
- "I'm meeting X": a meeting brief; "follow up with X on Y": `python tools/followups.py add`; time
  away: a handover. All in `docs/rules/workflow/day.md`, as are tasks (`python tools/tasks.py`).
- A question about the product or the work: a sourced answer (`docs/rules/workflow/questions.md`).
- Site buttons run the same work as background jobs (`tools/jobs.py`); results: Sources, Health and jobs.

## Session start

The hook starts the site and runs weekly housekeeping. In the first session of a day only, it asks
for the daily brief and today's meeting briefs; after that the owner asks. It reports what waits in
`mantis/00_inbox/` (answers, page edits, files): tell the owner in one line; the next pull processes
them, and only the owner starts a pull.

## The site

http://localhost:8000: Today, Meetings, Features, Questions, Sources; people and the library in a
side panel. It changes no knowledge directly: answers, page edits and dropped files go to the inbox;
filters, tasks, follow-ups, meetings and Undo are the owner's settings. It strips Mantis IDs and repo
paths, but outputs should not contain them anyway.

## Token habits

- One task per session; read the smallest thing that answers. Convert inbox files with
  `python tools/extract.py` and read the Markdown. Point to site pages instead of pasting them.

## Rules that do not change

- Every statement is cited to a source or flagged as an assumption.
- Conflicts are recorded, never silently resolved.
- Say each thing once; plain words first, technical detail apart (`OUTPUTS_GUIDE.md`).
- When unsure, stop and ask; doubts the owner can settle go on the Questions page.
- Deferred ideas about Mantis itself go in `docs/project/IMPROVEMENT_BACKLOG.md`.
