# WORKFLOW: index

Read this before any Mantis task. The full rules, definitions and examples are in
`docs/rules/WORKFLOW_RULES.md`; open a named section there only when a step needs it. On what is
allowed, the rules win. On how to do it, this checklist wins: registers are written with
`tools/entry.py`, never by opening and editing the large files. Paths are relative to
`mantis/` unless they start with `tools/` or `docs/`, or name a root file.

The workflow is split by task so a session or job reads only what it needs (MANTIS-IMP-058).
Read this index, then the one file for the task:

| Task (section names other files refer to) | File |
|---|---|
| Pull: what changed in Jira, Confluence and the inbox since the last pull (the owner says "pull") | `workflow/pull.md` |
| Before you start, For each document, End of batch, Estimation sheet | `workflow/ingest.md` |
| Owner answers from the site, Decisions | `workflow/answers.md` |
| Owner edits from the site, Exports of our own pages | `workflow/edits.md` |
| Daily brief and the owner's tasks, People, follow-ups and next steps, Meeting briefs, Away planner and handover | `workflow/day.md` |
| Answering a question (the Ask box, or a question in chat that needs the knowledge base) | `workflow/questions.md` |

## Buttons on the site (background jobs)

The site's buttons run fixed jobs (`tools/jobs.py`): free ones run Python; ones marked ✦ run
Claude Code headless in this folder, on the owner's normal subscription quota. An unattended job
follows these same rules but never asks: wherever a rule says stop and ask, it leaves that item,
lists it under "NEEDS YOU:" in its final message, and the job ends as "needs you". Process
those items in chat. Recent jobs and their results are under Health and jobs on the Sources page.

## Never

- Edit an existing digest without a preview and the owner's approval, then a Change Log
  line (rules: Modifying Existing Digests). One exception: a pull adds a dated section to the
  card's monthly pull digest (`pull.md`, 3.2).
- Resolve a conflict or close an item without the owner. One exception: an open question (gap) a
  source answers with Strong evidence closes itself, cited, and the owner can undo it (rules:
  Potential Resolution).
- Edit generated files: `knowledge/map/*` or the site (`%LOCALAPPDATA%/Mantis/site`).
