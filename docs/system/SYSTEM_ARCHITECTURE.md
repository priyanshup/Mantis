# SYSTEM_ARCHITECTURE

This document defines the data model for Mantis: the core objects tracked by the
system and how they relate to one another. It exists so that any future digest,
workflow, or tooling decision has a stable, shared vocabulary to build on.

## Core Objects

### Document
A logical source document — e.g. one wiki page, one PDF, one PPT deck.

- Has a permanent ID, format `MANTIS-DOC-0001`.
- The ID never changes, even if the document's title changes later.
- A Document is a container for history: it can have multiple Versions over time,
  but it is not itself a file — the file lives in a Version.

### Version
A dated snapshot of a Document's source file.

- Stored immutably. An old export is never overwritten — a new Version is added
  alongside it, and the old one remains in place.
- Each Version belongs to exactly one Document.
- At any point in time, a Document has one current Version (the most recent), but
  prior Versions remain retrievable.

### Digest
A markdown summary generated from the current Version of a Document.

- This is the "working knowledge" layer: cited and tagged, and what future reading
  and question-answering actually uses instead of re-reading raw source files.
- A Digest is generated from exactly one Version of exactly one Document.
- When a Document gets a new Version, its Digest is regenerated (see docs/rules/WORKFLOW.md,
  Phase 4, for the rules governing that transition — this document only defines
  the objects, not the process).

### Assumption
Something stated in a Digest that was not explicitly present in the source.

- ID format: `MANTIS-ASM-001`.
- Status: `Open` / `Confirmed` / `Corrected`.
- Tracks a list of which Digests reference it — an Assumption can be shared across
  multiple Digests if the same unverified claim shows up in more than one place.

### Conflict
Two or more sources disagreeing on a fact.

- ID format: `MANTIS-CFL-001`.
- Records the competing statements together with their sources.
- Status: `Open` / `Resolved`.
- Tracks which Digests are affected by the conflict.
- Conflicts are never auto-resolved — resolution is a human decision, recorded
  against the Conflict's status.

### Decision
A product/business decision made on top of the knowledge — distinct from a
documented fact. Example: "we chose to build Feature X using SAP."

- Kept separate from factual Digests so that a knowledge update (a new Version, a
  regenerated Digest) never silently overwrites a Decision's rationale.
- A Decision can reference the Digests that informed it, but it is not itself
  derived from a single Version the way a Digest is.

### Knowledge Gap
Something the Mantis corpus doesn't yet know — the source simply doesn't cover a
point, and no inference is made to fill it, unlike an Assumption. Example:
"SAP is mentioned; which SAP module is never specified in this source."

- ID format: `MANTIS-GAP-001`.
- Status: `Open` / `Potential Resolution` / `Promoted` / `Closed`.
- Tracks which Digests are affected by the gap.
- A Knowledge Gap can later be promoted to an Assumption, or escalated into a
  real question for an SME, if something built on top of the knowledge base
  (e.g. an Output) needs the missing detail. (See docs/rules/WORKFLOW.md, Assumptions vs.
  Knowledge Gaps.)

### Output
Anything generated for external use — onboarding guide sections, user stories,
epics.

- Outputs always cite Digests directly.
- Outputs are never used as a source for other Outputs. This is a hard rule: it
  prevents errors from compounding across generations (an Output built on an
  Output built on an Output, with no path back to an original source).

## Relationships Diagram

```
Document (MANTIS-DOC-0001)
   |
   |  1..N (immutable, dated, never overwritten)
   v
Version (2026-07-02, 2026-05-14, ...)
   |
   |  1 current Version -> regenerated on new Version
   v
Digest (cited, tagged working knowledge)
   |
   |  cited by (never used as a source for another Output)
   v
Output (onboarding guide section, user story, epic)

Attached to Digest(s) via ID reference, not by containment:

  Assumption   (MANTIS-ASM-001)  --- referenced by ---> [Digest, Digest, ...]
  Conflict     (MANTIS-CFL-001)  --- affects        ---> [Digest, Digest, ...]
  Decision     (MANTIS-DEC-001)  --- informed by     ---> [Digest, Digest, ...]
  Knowledge Gap (MANTIS-GAP-001) --- affects         ---> [Digest, Digest, ...]
```

Reading the diagram: Documents accumulate Versions; each current Version produces
a Digest; Digests are what Outputs cite. Assumptions, Conflicts, Decisions, and
Knowledge Gaps are not part of that spine — they are separate registers (see
`mantis/knowledge/registers/assumptions/`, `conflicts/`, `decisions/` and `gaps/`, one file per
entry since 2026-10-09) that attach to
one or more Digests by ID reference, so a single Assumption, Conflict, or
Knowledge Gap can be traced across every Digest it touches without duplicating
its record.

## Why Decisions and Digests Are Separate
A Digest is a derived artifact — it can be regenerated wholesale if the source
Version changes, without loss, because the source is still there to regenerate
from. A Decision is not derived from a source in that way; it is a record of a
choice made by a person, using the knowledge available at the time. Merging the
two would mean a routine Digest regeneration could silently erase the rationale
behind a real business decision. Keeping them as separate objects, linked only by
ID reference, protects against that.

## Why Outputs Cannot Source Other Outputs
Allowing an Output to cite another Output would let a paraphrase of a paraphrase
become an implicit source of truth, with the citation trail growing further from
the original document at each step. Requiring every Output to cite Digests
directly keeps every generated artifact exactly one hop from cited, working
knowledge — and Digests, in turn, are one hop from an immutable Version of an
original source.

## Generated layers (added 2026-10-09, AD-009)

Two layers are derived from the Markdown and never edited by hand. Both are rebuilt by
`python tools/build_map.py`.

- **Map** (`mantis/knowledge/map/`): one-line indexes of documents, topics, entities, open
  register entries and features, plus `graph.json`. Sessions read these instead of the
  full registers.
- **Index** (`mantis/knowledge/registers/documents/`): one entry per document, generated from
  the digest's front matter and the current register statuses, so it cannot drift. Each entry
  keeps a hand-written `#### Notes` section (MANTIS-IMP-013).
- **Site** (`%LOCALAPPDATA%/Mantis/site`, outside OneDrive so rebuilds do not sync): the read-only reading view, served at http://localhost:8000. It shows
  the roadmap from feature card front matter and, per feature, the card, the Confluence
  page, the epic and the stories from `mantis/outputs/`. It strips Mantis IDs so pages paste
  cleanly into Confluence and Jira. Since it holds no knowledge of its own, it is outside
  the citation chain: a page copied from it is the Output it was generated from.

## Cards: the reading layer (added 2026-10-09, AD-014)

Every subject has one card: roadmap features in `mantis/knowledge/features/`, everything else in
`mantis/knowledge/topics/`. A card has a curated summary (cited, written by Claude or the owner)
and a generated part that `tools/cards.py` rewrites on every rebuild: every digest linked to the
card by its topic tags, each with its one-line summary, the open questions with live status, and
the people and systems named. Sources the summary does not cover yet are marked new, and the
card says so, so freshness is visible instead of silently lost. Reading a card replaces opening
the digests behind it: a subject with 30 documents costs about 1,500 tokens instead of 60,000.

The owner chooses which cards matter on the site's Features page: **Follow** puts a card in
Following (ranked by the owner), and **Roadmap** adds a topic card to the Roadmap board or takes a
roadmap feature off it. The choices live in `mantis/knowledge/focus.json`, written by `tools/serve.py`; they are
preferences, not knowledge, so they skip the inbox and apply at once.

## Engine and knowledge (added 2026-10-10, MANTIS-IMP-036)

The engine (tools, site code, rules, templates, skills) is version-controlled on its own and
holds no knowledge. The knowledge (`mantis/` except `TEMPLATES/` and `README.md`), instance notes
(`CLAUDE.local.md`, `mantis/config/`) and project history (`docs/project/`, the architecture
decisions) stay local. `.gitignore` is an allow-list and `tools/leakcheck.py` blocks any commit
that names local knowledge. `tools/init.py` creates an empty knowledge base, so a fresh clone
works from the first run. Setup: `docs/system/SETUP.md`.

## The owner's day (added 2026-10-10)

People (`knowledge/people.md`), follow-ups, recurring meetings, away periods and suggested
deadlines live beside the tasks in `mantis/tasks/`. They are preferences and working state, not
source knowledge, so the site writes them directly (`/api/followups`, `/api/schedule`,
`/api/deadlines`) and reads them live (`/api/extra`). Cards may carry a "Next steps" table;
`tools/steps.py` reads it into `map/steps.json`, which feeds follow-ups, deadlines, the away
planner and briefs. Meeting briefs, handovers and status updates are gathered by code for free
and written by Claude; they are saved in `mantis/tasks/briefs/` and never cited as sources.

## Background jobs (added 2026-10-10, MANTIS-IMP-034)

The site's buttons start fixed jobs through `tools/serve.py` and `tools/jobs.py`: free jobs run
Python, Claude jobs run Claude Code headless in the project with the same rules (so CLAUDE.md
applies), one at a time, on the owner's subscription. An unattended job never asks: items that
need the owner end the job as "needs you". `build_map.py` takes a lock so builds started by the
server, a job and a session never overlap.

