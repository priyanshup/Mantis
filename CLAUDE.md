# Mantis

The owner's personal assistant and knowledge repository. The repo is the source of truth, not
any chat. Rules: `docs/rules/PROJECT_VISION.md`. Workflow: `docs/rules/WORKFLOW.md`, a short
index that names the one file in `docs/rules/workflow/` to read for each task. Writing for a reader: `docs/rules/OUTPUTS_GUIDE.md`. Tools and setup:
`docs/system/SKILLS.md`. Where things live: `README.md`, then the README in each folder.
Cleanup and what goes where: `docs/system/MAINTENANCE.md`.

## Read cheaply, in this order

1. **The card for the subject.** `mantis/knowledge/map/cards.md` lists every card. Roadmap
   features: `mantis/knowledge/features/<slug>.md`; any other subject:
   `mantis/knowledge/topics/<slug>.md`. A card's generated part lists every linked source with a
   one-line summary, the open questions with live status, and the people and systems involved.
2. **A person, system or place:** `python tools/graph.py <name>` (or `path <A> <B>`). Someone the owner
   works with (role, briefing style, what is open with them): `python tools/people.py show <name>`.
3. **A document:** `python tools/peek.py <ids>` (header and Summary). Open the whole digest only
   when the summary is not enough.
4. **Open questions:** `mantis/knowledge/map/registers.md`; one entry with
   `python tools/entry.py show <ID>`.
5. **What the owner owns:** `mantis/knowledge/focus.json` lists the cards they follow, the cards they archived (hidden everywhere, kept in Mantis), and what
   is on their roadmap (set on the site's Topics page). Put those first in reports and checks.
6. Do not read the register folders, `MAP.md` or many digests whole. If a subject has no card,
   look it up in `MAP.md` or `topics.md`, then consider a topic card.

## Write

- Registers only through `tools/entry.py` (`next`, `add`, `status`, `note`).
- Cards: edit only the curated part above the GENERATED marker. When the summary takes in new
  sources, add their IDs to `source_documents`; the card then stops flagging them as new.
- Generated, never edited by hand: `mantis/knowledge/map/*`, card text below the marker, index
  entries (except their Notes), and the site.
- After any change run `python tools/build_map.py`: map, cards, index, lint, health report, site.

## The owner's day

- "I'm meeting X, what should I discuss?": a meeting brief (`docs/rules/workflow/day.md`, "Meeting briefs").
- "Follow up with X on Y": `python tools/followups.py add`. Time away and handovers: "Away planner and handover".
- A question about the product or the work ("what is the target for…?"): a sourced answer (`docs/rules/workflow/questions.md`).
- Buttons on the site run the same work in the background (`tools/jobs.py`); results are on the Health page.

## Session start

The hook starts the site, runs weekly housekeeping, asks for the daily brief once a day, and
reports what waits in `mantis/00_inbox/`: answers (`answers-*.md`), page edits (`edit-*.md`) and
files to ingest. Tell the owner, then handle them as `docs/rules/workflow/answers.md`, `edits.md` or `ingest.md` says before other work. The
owner's tasks and reminders go through `python tools/tasks.py` (docs/rules/workflow/day.md, "Daily brief").

## The site

http://localhost:8000, read by the owner and copied into Confluence and Jira Cloud. It is
read-only except answers to open questions and page edits, which go to the inbox. It strips
Mantis IDs, source columns and repo paths, but outputs should not contain them anyway.

## Token habits

- One task per session; read the smallest thing that answers (card, graph, peek, digest).
- Convert inbox files with `python tools/extract.py` and read the Markdown, not the original.
- Do not paste file contents the owner can read on the site; point to the page.

## Rules that do not change

- Every statement is cited to a source or flagged as an assumption.
- Conflicts are recorded, never silently resolved.
- When unsure, stop and ask; doubts the owner can settle go on the Open items page.
- Deferred ideas about Mantis itself go in `docs/project/IMPROVEMENT_BACKLOG.md`.
