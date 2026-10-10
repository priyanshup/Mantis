# WORKFLOW: ingest checklist

Read this before ingesting. The full rules, definitions and examples are in
`docs/rules/WORKFLOW_RULES.md`; open a named section there only when a step needs it. On what is
allowed, the rules win. On how to do it, this checklist wins: registers are written with
`tools/entry.py`, never by opening and editing the large files. Paths are relative to
`mantis/` unless they start with `tools/` or `docs/`, or name a root file.

## Before you start

- Ingest in batches. The owner drops files or pastes into `00_inbox/`; one session ingests
  them all. Avoid parallel ingest sessions. If one cannot be avoided, `entry.py` still
  keeps IDs unique.
- Pasted meeting notes (owner instruction, 2026-10-08): do not stop to ask about
  classification or a missing date. Treat each paste as a new document, cross-check it
  against existing digests, log garbled names and missing dates as gaps, and report.
  Updating an existing digest still needs a preview and approval.
- The same applies to anything else the owner pastes or screenshots in chat: vendor or
  support replies, emails, chat threads, settings screens, certificate details. When a
  session works through such material, capture it once at the end as one document: the
  pasted text verbatim and screenshots transcribed, each as a numbered Part, plus the owner's
  own statements as a last Part. Write files with the Write tool,
  not shell heredocs, which break on apostrophes.
- Never pick an ID by reading a register. Claim it: `python tools/entry.py next doc`
  (or `gap 3`, `asm`, `cfl`, `dec`).

## For each document

1. **Extract.** `python tools/extract.py` turns inbox files (Confluence Word exports, HTML,
   DOCX, PDF) into Markdown in `00_inbox/.extracted/`. Read that, not the original.
2. **Fingerprint and classify.** Note tags, key entities and a one-line summary, then run
   `python tools/classify.py --title "..." --topics a,b --entities "X, Y"`. It gives the verdict
   (NEW DOCUMENT: go on; NEW VERSION of a digest: go on as a version and say so; AMBIGUOUS:
   `peek.py` the top matches, then stop and ask), the cards the document joins through its
   tags, and the open items it may bear on. Pasted meeting notes skip the verdict (see Before
   you start). Cut-offs: `tools/classify_config.json`.
3. **Identity.** New document: claim the next DOC ID. New version: keep the ID, raise
   `version`, move the old digest to `03_archive/`.
4. **Source.** Save the original to `01_sources/{id}/{date}.{ext}`. Never overwrite a dated snapshot.
5. **Digest.** Write it from `TEMPLATES/digest.md` into `02_digests/{id}.md`. Every claim is
   cited. The Summary comes first and stands alone in 120 words or fewer; its first sentence
   becomes the document's one-liner on every card, so make it say what the document is. Give
   it at least one topic tag a card matches (step 2 lists them), or a card cannot find it.
   Leave out sections with nothing to say. Confidence: rules, Confidence Rules.
6. **Assumptions, gaps, conflicts.** Decide which applies (rules: Assumptions vs. Knowledge
   Gaps). Claim IDs, write the entries to a scratch file in the register's format, then
   `python tools/entry.py add gap <file>` (or `asm`, `cfl`). Stop and report live for a new
   conflict or an assumption below Moderate evidence (rules: Batch Processing). Add a
   Priority line only when the sources make the stakes clear (rules: Priority).
7. **Cross-check.** Read only the open items step 2 listed: `python tools/entry.py show <ID>`.
   Strong or Moderate evidence: `python tools/entry.py status <ID> "Potential Resolution (<date>: <evidence>)"`.
   Weak: report only. Only the owner closes, confirms or resolves (rules: Potential Resolution).
8. **Index and cards.** Nothing to write: `build_map.py` generates the index entry and adds the
   document to every card whose tags it carries, marked new. If the document changes a
   roadmap feature's status or priority, update that card's front matter. Add new personas and
   terms to `knowledge/personas.md` and `glossary.md`. In `knowledge/entity_register.md`, add a
   relation the document states between two entities (cited), a type for a new important
   entity, and an alias the source confirms. Never merge names on a guess.
9. **Inbox.** Move the original out of `00_inbox/`.
10. **Diagrams.** After `build_map.py`, run `python tools/assets.py review --doc <ID>` and open
   each candidate image. Register a clear diagram, screenshot or reference table:
   `assets.py new <hash>` prints a pre-filled entry; claim an ID (`entry.py next ast`), fill
   in the title, type and a cited description, then `entry.py add ast`. Ignore the rest with
   `assets.py ignore <hash> "why"`. Ask the owner only when it is unclear whether an image is
   worth keeping.

## End of batch

- Run `python tools/build_map.py`. It rebuilds the map, cards, index, lint, health report and site.
- Refresh the summaries of cards that now show new sources (`map/cards.md`, column "new"): read
  only the new sources' one-liners on the card (or `peek.py`), update the curated part, cited,
  and add their IDs to `source_documents`. A subject with 3+ documents and no card
  (`map/cards.md`, "Suggested new cards") gets a topic card in `knowledge/topics/` from
  `TEMPLATES/topic-card.md`.
- Give the end-of-batch report (rules: Batch Processing).

## Owner answers from the site

`00_inbox/answers-*.md` files come from the Open items page (the session-start hook says when
one is waiting). The owner's answer is user knowledge: cite it as "Source: Owner answer via
the Open items page, <date>". For each item in the file:

1. Read the entry: `python tools/entry.py show <ID>`.
2. **Answers it.** Record the answer:
   `python tools/entry.py note <ID> "Resolution" "Source: Owner answer via the Open items page, <date>. <answer>"`,
   then set the final status with `entry.py status`: a gap Closed, an assumption Confirmed or
   Corrected, a conflict Resolved. The owner choosing "Answers it" is the explicit
   confirmation the rules require. If the answer contradicts a digest, raise a conflict and
   report it instead of closing.
3. **Partly answers it.** Add it with `entry.py note <ID> "Owner answer" "..."` and leave
   the status as it is.
4. **Name and term questions** (`NAME-…`, `TERM-…`). Same thing: add the second name as an
   alias of the first in `knowledge/entity_register.md` (Entities table), cited "Owner answer,
   <date>". Different things: add the pair to its "Not the same" table so it is not asked
   again. A term the owner explains: give it a type in the Entities table and a row in
   `knowledge/glossary.md`, both cited the same way.
5. **Someone else must answer.** Add `entry.py note <ID> "Ask" "<who>"` (plus any answer
   text) and leave the status as it is.
6. Update any feature card the answer changes, cited the same way. An edit to an existing
   digest still needs a preview and the owner's approval.
7. Move the file to `03_archive/answers/`, run `python tools/build_map.py`, and report each
   item: what you recorded and its new status.

## Owner edits from the site

`00_inbox/edit-*.md` files are pages, epics or stories the owner edited on the site. They are
the owner's own words: apply them as written, do not rewrite them or run the humanizer.

1. Run `python tools/apply_edits.py`. For each edit it checks the file has not changed since
   the owner opened it, swaps in the new body, keeps the front matter and leading notes, sets
   `updated:` and archives the edit. It prints a line diff.
2. If it reports "changed after the owner opened it", nothing was written: merge the two by
   hand, show the owner the result, then delete the edit file.
3. Read the diff. If the edit changes facts (a new decision, owner, date or scope), tell the
   owner and offer to update the feature card, cited as "Source: Owner edit of <page>, <date>".
4. Run `python tools/build_map.py` and report each document and what changed.

## Exports of our own pages

A Confluence export of a page Mantis wrote (it matches a file in `outputs/`) is not a new
source document. The owner edits pages in Confluence, so the export is the owner's latest
version and may carry facts Mantis lacks.

1. Extract it, then compare it with the matching file in `outputs/` section by section.
2. Sections only the export has: restore them into the output, unchanged.
3. Facts only the export has (a name, role, link, date, owner): record them where they
   belong (card, `user_knowledge.md`, `entity_register.md`), cited "Owner's Confluence page,
   <date>". If one contradicts Mantis, follow the owner's page, correct Mantis and say so;
   if it contradicts a source document, raise a conflict instead.
4. Archive the previous output in `03_archive/outputs-confluence-<date>/` and the export in
   `03_archive/confluence-exports-<date>/`.
5. After updating the page, report the changed sections mapped to the Confluence page's own
   headings (OUTPUTS_GUIDE, "Updating a page already in Confluence").

## Decisions

When the owner settles a choice between options (a route, a vendor approach, a scope cut),
log it: `python tools/entry.py next dec`, write the entry from `TEMPLATES/decision-entry.md`,
`entry.py add dec <file>`, and cite the DEC ID on the feature card. A decision is the owner's
choice, not a fact, so it never closes a gap by itself; it records why work went one way.

## People, follow-ups and next steps

- **People** live in `knowledge/people.md` (`tools/people.py`): role, team, aliases, channel,
  briefing style, the owner's notes. When a source names someone new with a role, add their
  section, the role cited, as well as the entity register row. Briefing styles and notes are the
  owner's; write a proposed one only when asked, marked `*proposed:*`.
- **Follow-ups** (`tools/followups.py`): when the owner says "follow up with X on Y", or a task
  can't close because someone hasn't replied, add one (`--kind wait` for things owed to the
  owner, with `--chase` when a date is known). When meeting notes are ingested, every action for
  someone else becomes a follow-up for that person (`--source` naming the meeting); the owner's
  own actions become tasks (`tools/tasks.py add`). A follow-up stays open until marked done.
- **Next steps on cards:** while work is in flight, keep the card's "Next steps" table current
  (Step | Who | Status | Due | Source). Steps owned by someone else appear on that person's
  follow-up list by themselves; the Due column feeds suggested deadlines and the away planner.
- **Suggested deadlines** (`tools/deadlines.py`): never set a due date the owner didn't give.
  When preparing the daily brief, if a source states a date for an undated task ("by end of
  month", "before go-live"), save it as a suggestion: `python tools/deadlines.py add TASK_ID DATE "why"`.
  The owner accepts or declines it on Today.

## Meeting briefs

When the owner says they are meeting someone ("I'm meeting Sam now, what should I discuss?"),
or the Brief me button runs the job:

1. `python tools/brief.py gather "<person or meeting>"`. It prints everything known, free: role,
   briefing style, notes, open follow-ups (with IDs), steps waiting on them, the owner's own steps,
   shared cards, open questions, decisions since the last brief, away dates.
2. Write the brief as JSON (format in `tools/brief.py`): sections "Update <first name> on", "Ask
   <first name>", "Decide together", "Chase", "Personal". One short line per bullet; the
   background in `detail`; the source in words (never a Mantis ID or path); the follow-up ID in
   `followup` when the bullet is one, so the owner can tick it off; the card slug in `card`.
   Order by the person's briefing style. Use only what the gather output or the cards say;
   "Personal" bullets come only from the owner's notes. Topics worth tracking go in `new_followups`.
3. `python tools/brief.py save <file>`. It shows on Today and on the person's card; each bullet
   expands. In chat, also give the bullets in a few lines.

**Weekly status update:** the same format with `"for": "Weekly status"` and `"kind": "status"`,
from `python tools/brief.py status` (what changed on followed cards in the last 7 days). Sections:
Done this week, In progress, Blocked or at risk, Decisions needed, Next week.

## Away planner and handover

The owner records time away on Today (or `tools/schedule.py add-away START END --cover NAME`).
From 5 working days before, the daily brief and Today list what needs the owner first and what
falls inside the window (`python tools/away.py scan`): dated tasks and steps, chase dates and
the recurring meetings they will miss. A handover is written per recipient:

1. `python tools/away.py gather "<recipient>"`.
2. Write it in the brief JSON format with `"kind": "handover"`, framed by the recipient's briefing
   style: for a BA the steps, contacts and what to do if something happens; for a senior PO the
   decisions pending and priorities; for a manager status, risks and what may escalate. Same
   rules as briefs: plain words, sources in words, nothing invented.
3. `python tools/away.py save <file>`. It opens from the away panel on Today and can be copied.

## Buttons on the site (background jobs)

The site's buttons run fixed jobs (`tools/jobs.py`): free ones run Python; ones marked ✦ run
Claude Code headless in this folder, on the owner's normal subscription quota. An unattended job
follows these same rules but never asks: wherever a rule says stop and ask, it leaves that item,
lists it under "NEEDS YOU:" in its final message, and the job ends as "needs you". Process
those items in chat. Recent jobs and their results are on the Health page.

## Daily brief and the owner's tasks

The owner's tasks live in `mantis/tasks/` and are edited on the site's Today page. Never edit
`tasks.json` by hand; use `tools/tasks.py`.

- **Once a day** (the session-start hook says when): run `python tools/tasks.py context`, then
  write up to 5 suggestions as a JSON list and save them with `python tools/tasks.py suggest <file>`.
  Each suggestion: `title` (an action, verb first), `why` (one sentence, from the context),
  `who` (a name from the sources), `say` (what to tell them, in two sentences or fewer),
  `questions` (up to 4, ready to ask), `estimate` (minutes), `priority`, `source` (the card or
  open item it comes from, in words). Base them only on the context output: blocked tasks,
  due items, reminders, carried-over tasks, and open items on cards the owner follows, with
  items waiting for a decision first. No suggestion without a named person or a clear next step.
  The context also lists follow-ups, steps waiting on people, an upcoming away period (nudge on
  what must happen before it) and undated tasks (save any date a source states as a suggested deadline).
- **When the owner asks** for a task or reminder in chat: `python tools/tasks.py add "Title"`
  with `--remind YYYY-MM-DD`, `--due`, `--contact`, `--priority`, `--estimate`, `--note` as given.
- Done items move to `archive.json` the next day and are deleted 7 days later, automatically.

## Never

- Edit an existing digest without a preview and the owner's approval, then a Change Log
  line (rules: Modifying Existing Digests).
- Resolve a conflict or close an item without the owner.
- Edit generated files: `knowledge/map/*` or the site (`%LOCALAPPDATA%/Mantis/site`).
