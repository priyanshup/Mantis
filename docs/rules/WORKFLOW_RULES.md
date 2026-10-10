# WORKFLOW RULES

The full ingest rules, moved here unchanged from `docs/rules/WORKFLOW.md` on 2026-10-09. `docs/rules/WORKFLOW.md` is
now a one-page checklist that links to the sections below. References elsewhere to
"docs/rules/WORKFLOW.md, <section>" mean the section of that name in this file.

**Register paths (2026-10-09, AD-010).** The registers named below as flat files are now one
file per entry: `knowledge/index.md` is `knowledge/registers/documents/`, `knowledge_gaps.md`
is `registers/gaps/`, `assumptions.md` is `registers/assumptions/`, `conflicts.md` is
`registers/conflicts/` and `decisions.md` is `registers/decisions/`. The rules are unchanged;
read and write entries with `tools/entry.py`.

This document defines exactly how Mantis behaves: how documents are ingested, how
assumptions and conflicts are tracked, how confidence is assigned, and what is and
is not allowed to happen automatically. Where this document and convenience
disagree, this document wins — see the Core Principle in docs/project/PROJECT_PLAN.md and the
Non-Negotiable Principle in docs/rules/PROJECT_VISION.md.

**Path convention:** unless a path is explicitly written with a `mantis/` prefix,
paths in this document are relative to the `mantis/` knowledge-base directory (e.g.
`00_inbox/` means `mantis/00_inbox/`). Project meta files (rules, system design and plans)
live in `docs/` beside `mantis/`, written with their `docs/` prefix (for example
`docs/rules/WORKFLOW.md`); everything under `mantis/` is the working knowledge base itself.

## ID Scheme

- Documents: `MANTIS-DOC-0001`, `MANTIS-DOC-0002`, ...
- Assumptions: `MANTIS-ASM-001`, `MANTIS-ASM-002`, ...
- Conflicts: `MANTIS-CFL-001`, `MANTIS-CFL-002`, ...
- Decisions: `MANTIS-DEC-001`, `MANTIS-DEC-002`, ...
- Knowledge Gaps: `MANTIS-GAP-001`, `MANTIS-GAP-002`, ...

Rules:
- IDs are assigned once, in order, and are permanent.
- IDs are never reused and never reassigned, even if the underlying item is later
  deleted, superseded, or found to be a duplicate.
- A Document's ID never changes even if its title changes later — the ID tracks
  the logical document, not its current name.

## Digest Front Matter Template

Every digest in `02_digests/` starts with this YAML front matter:

```yaml
---
document_id: MANTIS-DOC-0001
source_file: 01_sources/MANTIS-DOC-0001/2026-07-02.pdf
original_title: "[exact original wiki page title]"
version: 1
region: [e.g. a market name, or "Global"]
topics: [tag1, tag2, tag3]
key_entities: [Distributor, SAP, Customer]
related_documents: []
document_confidence: High | Medium | Low | Very Low
confidence_reason: "[one line explaining the document-level judgment, e.g. '98% of content explicitly sourced; one open assumption (MANTIS-ASM-001) on a minor detail — does not affect core business rules.']"
assumptions_referenced: []
conflicts_referenced: []
gaps_referenced: []
generated_on: [date]
generated_by:
  tool: Claude Code
  model: [model name used]
repository_version: 0.1
workflow_version: 0.1
---
```

Followed by the digest body, in this fixed section order:

1. **Summary** — a short, plain-language description of what the document covers.
2. **Business Rules** — the concrete rules, policies, or logic stated in the
   source, each ending in a source citation.
3. **Actors** — the people, roles, systems, or entities involved.
4. **Dependencies** — other documents, systems, or decisions this content relies
   on or references.
5. **Regional Notes** — anything specific to a region/market, or "None" if the
   content is global.
6. **References** — the explicit list of source locations cited in the body
   (page numbers, section headers, slide numbers, etc., as applicable).
7. **Known Gaps** — anything the source document doesn't cover but that a reader
   would reasonably expect it to.
8. **Change Log** — an append-only log of edits made to this digest after
   creation. See "Change Log" below for the format and rules.

See `TEMPLATES/digest.md` for the fillable skeleton.

## Related Documents

`related_documents` in the front matter links a Digest to other Documents
already in Mantis. Two kinds of evidence justify a link:

- **Explicit citation** — the source names or links another ingested Document
  as its source, hub, or reference (e.g. a strategy page citing the mission page as
  its source).
- **Verbatim identical content** — a substantial block of text is duplicated
  word-for-word across two Documents (e.g. two pages sharing an identical Metrics
  section), even without an explicit citation
  between them.

Thematic or topical overlap alone (same team, same subject area, similar
naming) is **not** sufficient grounds for a link — only one of the two
evidence types above.

Whichever applies, the digest must state which one it is (citation vs.
text-match) rather than presenting both the same way, so a future reader can
judge the strength of the connection for themselves.

## Confidence Rules

Confidence exists at two levels: **document-level** (`document_confidence` in
the digest front matter) and **item-level** (the status of each individual
Assumption in `knowledge/assumptions.md`). They are judged separately.

### Item-level (per Assumption)

Each Assumption carries its own status in the Assumption register:
`Open` / `Confirmed` / `Corrected`. This is the finer-grained signal — see
Assumption Lifecycle below.

### Document-level (`document_confidence`)

`document_confidence` reflects the overall reliability of the digest as a
whole, judged rule-based, never invented or vibes-based:

- **Very High** — multiple independent sources corroborate the same fact.
- **High** — explicitly and clearly stated in one authoritative source.
- **Medium** — stated in one source, but ambiguous or lacking detail.
- **Low** — a substantial portion of the digest, or a business-rule-level
  claim, rests on an assumption not explicitly stated in any source.
- **Very Low** — an open, unresolved conflict exists on this topic.

`document_confidence` is a holistic judgment, not a mechanical floor set by
the presence of any single Open assumption. A digest with one Open assumption
on a minor, peripheral detail — while the core business rules are explicitly
sourced — should still be `High` or `Medium`, not automatically dragged to
`Low`. Judge based on what proportion of the content is assumption-based
versus explicitly sourced, and how important the assumption-based part is to
the digest's core claims. Reserve `Low` for when an assumption underpins a
core business rule, actor, or dependency — not a minor or cosmetic detail.

`confidence_reason` must state that judgment explicitly, e.g. "98% of content
explicitly sourced; one open assumption (MANTIS-ASM-001) on a minor detail — does
not affect core business rules," not just restate the confidence level or
mechanically cite "contains an assumption."

Knowledge Gaps (see below) do not by themselves lower `document_confidence`
— noting that the source doesn't cover something is not the same as relying on
an unverified inference. A gap only affects confidence if and when it is
promoted to an Assumption.

## Evidence Strength

`Evidence Strength` (`Strong` / `Moderate` / `Weak`) is a required field on
every Assumption, Conflict, and Knowledge Gap entry when first raised, and on
every Cross-Reference finding reported in a digest. It answers one question:
how solid is the evidence behind this specific item or finding?

- **Strong** — an explicit definition, a direct citation, or a direct
  contradiction was found. The evidence states the thing outright.
- **Moderate** — contextual or indirect evidence: plausible and consistent
  with the item, but not stated outright. Requires reading between two
  related statements.
- **Weak** — circumstantial: a single ambiguous mention, or requires
  connecting dots between things that aren't clearly related.

`Evidence Strength` drives the `Potential Resolution` threshold — see
"Potential Resolution — Shared Lifecycle Rule" below. It is assessed
independently each time new evidence appears; the same item can accumulate
multiple pieces of evidence at different strengths over its lifetime (e.g. a
`Moderate` finding followed later by a `Strong` one).

## Priority

`Priority` (`Critical` / `High` / `Medium` / `Low`) says how much an open
Assumption, Conflict or Knowledge Gap matters, so the owner knows what to ask
about first. Evidence Strength says how sure we are; Priority says what it
costs to be wrong. It is optional: an entry without it is "not triaged yet",
never Medium by default.

- **Critical**: blocks a decision, a release or a page the owner must publish now.
- **High**: affects scope, requirements or a date on a roadmap feature.
- **Medium**: changes detail on a page, not its direction.
- **Low**: nice to know.

Set it with `python tools/entry.py priority <ID> <Level> "<why>"` when the
reason is clear from the sources or the owner says so; otherwise leave it out.
A guess at priority is an assumption like any other. The Open items page and
`map/registers.md` list Critical and High first, then untriaged, then Medium
and Low.

## Evidence Source Types

Beyond `Evidence Strength` (Strong/Moderate/Weak, above), which measures how
solid a piece of evidence is, evidence also comes from distinct **source
types**, which carry different reliability characteristics and must be
tagged explicitly rather than presented uniformly:

- **MANTIS-ingested document citation** — a claim sourced from a document that
  has gone through the full Ingestion Workflow below and lives in
  `02_digests/`. This is the default, most reliable source type — it is
  what most digest-to-digest citations in this repository are.
- **Direct SME consultation** — the user consulted a subject-matter expert
  (a colleague, a senior stakeholder) directly and relayed the answer back.
  Tag as: `Source: Direct SME consultation, [date].`
- **User's own outside knowledge** — the user's personal knowledge, stated
  directly, not yet backed by any ingested document. Tag as: `Source: User
  knowledge, [date], not yet present in any ingested document.`
- **External AI research** — a third-party AI research tool (named for this
  instance in `CLAUDE.local.md`) searched the company's own wiki/tracker directly and
  returned citations to specific pages with quoted content. This is
  **strong supporting evidence, but is not equivalent to a MANTIS-ingested
  digest citation** until/unless the cited page is itself later ingested
  through the normal pipeline above — such a citation points to a source
  Mantis has not yet independently verified via ingestion. Tag as: `Source:
  <tool> AI research, citing [page name/URL] — not yet MANTIS-ingested.`

When a resolution sourced from external AI research is later corroborated (or
contradicted) by the actual Mantis ingestion of the page it cited, treat that
ingestion as new evidence in its own right (per Cross-Reference & Impact
Analysis, below) — it does not silently "upgrade" the earlier AI-research-sourced
note in place; it is recorded alongside it, and any discrepancy between the
two is flagged rather than auto-resolved.

## Ingestion Workflow

1. A new file appears in `00_inbox/`. Read it once. Generate a topic
   fingerprint: tags, key entities, and a one-line summary.
2. Compare that fingerprint against the topics/entities already listed in
   `knowledge/index.md`. *(Since 2026-10-09 `tools/classify.py` does this comparison; see
   AD-011 and the checklist in `docs/rules/WORKFLOW.md`.)*
3. If the match to an existing document is unclear in any way — could be a new
   version, could be a different-but-related document, could be a duplicate —
   **STOP**. Do not guess. Show the candidate matches and ask for a
   classification: **New document** / **New version of an existing document** /
   **Duplicate** / **Related but distinct**. Only proceed automatically if there
   is no plausible overlap at all. *(Since 2026-10-09 the cut-offs in
   `tools/classify_config.json` define "unclear": only the AMBIGUOUS verdict stops. Pasted
   notes and other pasted material skip the verdict by owner instruction.)*
4. Assign the document identity:
   - New document: assign the next `MANTIS-DOC-####` ID.
   - New version: reuse the existing `document_id`, increment `version`.
5. Move/copy the source file into `01_sources/{document_id}/{date}.{ext}` —
   never overwrite an existing dated snapshot.
6. If this was a new version replacing a prior one, move the prior digest to
   `03_archive/` before generating the new one.
7. Generate the digest following the front matter template above. Every
   factual claim in the body ends with a source citation.
8. For anything the digest states that isn't explicitly backed by the source,
   first decide which of the two applies (see "Assumptions vs. Knowledge
   Gaps" below):
   - If completing the statement required inferring something not stated in
     the source: tag it inline as `[MANTIS-ASM-XXX]` in the digest body, and
     create a matching entry in `knowledge/assumptions.md`, with an Evidence
     Strength assessment for the inference itself. **If that Evidence
     Strength does not clearly reach at least `Moderate`** (i.e. it would sit
     at `Open` with weak-to-no corroboration), this is a batch-processing
     checkpoint — see "Batch Processing" below: stop, report the assumption
     live, and wait, rather than continuing the batch past a shaky inference.
   - If the source simply doesn't cover the point and no inference is made:
     note the gap inline as `[MANTIS-GAP-XXX]` in the digest body (typically in
     Known Gaps), and create a matching entry in
     `knowledge/knowledge_gaps.md`. Do not guess to fill it.
9. If this digest contradicts an existing digest: do not resolve it. Create an
   entry in `knowledge/conflicts.md` with both statements and their sources,
   tag both digests' front matter (`conflicts_referenced`) with the conflict
   ID, and report it directly. **A new Conflict is always a batch-processing
   checkpoint** — see "Batch Processing" below: stop and report it live, even
   mid-batch.
10. **Cross-Reference & Impact Analysis.** Before finalizing, check the new
    document's content against all currently Open items in
    `knowledge/assumptions.md`, `knowledge/conflicts.md`, and
    `knowledge/knowledge_gaps.md`. (Decisions and Knowledge Assets are not
    part of this check yet — those registers are currently empty/not built;
    extend this step to include them once they have real entries.)
    - If the new document appears to confirm, contradict, or partially
      corroborate an Open item, assess its `Evidence Strength` (see "Evidence
      Strength" above): `Strong` / `Moderate` / `Weak`.
    - Report it explicitly: which item, what evidence, where (section/page)
      in the new document, and the Evidence Strength assessment.
    - **`Strong` or `Moderate`** — set the item's status to `Potential
      Resolution` directly, no need to ask first. This is a system-generated
      provisional label, not a resolution: no repository meaning changes yet,
      it just surfaces the finding clearly in the next report. See
      "Potential Resolution — Shared Lifecycle Rule" below.
    - **`Weak`** — report the finding, but leave the item at `Open`. Weak
      evidence is never enough on its own to propose `Potential Resolution`.
    - Regardless of Evidence Strength, only move an item to `Closed` /
      `Confirmed` / `Resolved` once the user explicitly confirms — that step
      always requires approval.
11. Update `knowledge/index.md` with this digest's topics, entities, and a link
    to the digest file. *(Superseded 2026-10-09, MANTIS-IMP-013: `build_map.py` generates
    the index entry. Nothing to write by hand.)*
12. Move the original file out of `00_inbox/`.

## Batch Processing

This is the default mode from Phase 7 onward (scaling past the pilot).
Documents in the inbox are processed continuously within a batch, **without
stopping for review after each individual digest** — a change from the
Phase 6 pilot pattern of reporting after every document.

**Exception-based checkpoints — stop immediately, report, and wait when:**
1. Document classification is ambiguous (Ingestion Workflow step 3 — new /
   version / duplicate / related-but-distinct). Unchanged from before —
   always stops.
2. A new Conflict is raised (Ingestion Workflow step 9). Always stops now,
   even mid-batch — a factual contradiction between sources is never batched
   past.
3. A new Assumption is raised whose Evidence Strength doesn't clearly reach
   at least `Moderate` (Ingestion Workflow step 8). A genuinely uncertain
   inference gets flagged live, not rolled into an end-of-batch report where
   it could sit unnoticed among routine items.
4. Anything that would require editing an **existing** digest still requires
   a preview and explicit approval before writing, per "Modifying Existing
   Digests" — this pauses batch continuation the same way it always has.

Outside of these four triggers, keep processing straight through the batch.

**Batch size:** process up to 10 documents by default, then pause for the
user's review of the consolidated report (below) before continuing to the
next batch. This is a checkpoint, not a full stop — the user reviewing the
report and saying "continue" is enough to start the next batch of up to 10.

**End-of-batch report:** produced when the batch limit (10) is reached, the
inbox empties, or one of the four exception triggers forces a stop —
whichever comes first. One consolidated report covering everything
processed in the batch so far:
- List of new document IDs and titles.
- Rollup of new Assumptions raised, with Evidence Strength.
- Rollup of new Conflicts raised.
- Rollup of new Knowledge Gaps raised.
- Anything that self-promoted to `Potential Resolution` during the batch
  (per the Evidence Strength threshold rule in "Potential Resolution —
  Shared Lifecycle Rule").

**Cross-check disclosure for new Knowledge Gaps:** when a newly-raised gap involves a
term that could plausibly relate to existing tracked terminology or frameworks (anything
resembling a tier, wave, deployment label, or classification scheme — e.g. a new "XYZ" label
appearing alongside already-known labels like a rollout wave, a market-type framework, or a
maturity tier), the rollup entry must state **what was checked and ruled out**, not just the bare
conclusion. Name each existing framework considered and why it was ruled in or out — e.g.
"checked against the Wave 1 rollout and the market-type framework; no connection found;
source treats Tier A as an explicit contrast to Wave 1, not a synonym" — rather than a bare "no
connection found" or, worse, silence on whether the check happened at all. This applies
whether or not a connection is actually found: a clean rule-out is exactly as reportable as a
hit, since the point is letting the user verify the check happened without needing to ask a
follow-up question every time.

The per-document "stop and show me the digest" pattern used during the Phase
6 pilot remains available on request (e.g. for a first look at a new
document type, or a particularly dense/high-risk source) but is no longer
the default once processing at scale.

## Assumptions vs. Knowledge Gaps

These are two distinct things and must not be conflated:

- **Assumption** — Claude infers something not explicitly stated, in order to
  produce a complete statement. Example: "region assumed Global based on
  vision language." An inference was made; it is tracked so it can later be
  confirmed or corrected. Logged in `knowledge/assumptions.md`.
- **Knowledge Gap** — the source simply doesn't cover something, and no
  inference is made to fill it. The digest explicitly notes the gap and stops
  there. Example: "SAP is mentioned; which SAP module is never specified in
  this source." Logged in `knowledge/knowledge_gaps.md`. (This register was
  named "Information Gap" until 2026-07-02; it was renamed to "Knowledge Gap"
  to reflect that it tracks what the Mantis corpus doesn't yet know, not that any
  one source document is incomplete.)

The test: did completing the statement require inferring an unstated fact
(Assumption), or did the digest simply note an absence and go no further
(Knowledge Gap)? If in doubt, prefer Knowledge Gap — it makes no claim at
all, whereas an Assumption asserts something that could later turn out to be
wrong.

**The source's own self-declared hedges are neither.** When a source
explicitly flags its own uncertainty — "the assumption is that...", "pending
final confirmation of...", "(I think)" — that is the source's stated
uncertainty, not an inference Mantis is making. Quote it verbatim in the digest
body rather than converting it into a `MANTIS-ASM-XXX` entry. It only becomes a
Mantis Assumption if completing some *other* statement requires relying on it as
if it were settled.

A Knowledge Gap can later be **promoted** to an Assumption (if a plausible
inference becomes needed) or escalated into a real question for an SME — for
example, if an Output being built on top of the knowledge base needs the
missing detail. When that happens, create the new Assumption entry (or raise
the SME question), reference the originating `MANTIS-GAP-XXX` ID in it, and
update the Knowledge Gap entry's status to reflect the promotion rather than
deleting it.

## Potential Resolution — Shared Lifecycle Rule

Assumptions, Conflicts, and Knowledge Gaps all share the same three-state
resolution pattern: `Open` → `Potential Resolution` → a final state
(`Confirmed`/`Corrected` for Assumptions, `Resolved` for Conflicts,
`Promoted`/`Closed` for Knowledge Gaps). **Never jump straight from `Open` to
a final state automatically** — that final step is always a human decision.

The `Open` → `Potential Resolution` transition, however, is threshold-based
on `Evidence Strength` (see "Evidence Strength" above), not a human decision:

- **`Strong` or `Moderate` evidence** — when a new document (via
  Cross-Reference & Impact Analysis, step 10) or any other new information
  appears to bear on an existing `Open` item at this strength, set its status
  to `Potential Resolution` directly. No pre-approval is needed for this
  specific transition — it is a system-generated provisional label, not a
  resolution. Report the finding clearly (which item, what evidence, where
  it came from, and the Evidence Strength rating) in the next report.
- **`Weak` evidence** — report the finding, but the item stays `Open`. Weak
  evidence never triggers `Potential Resolution` on its own.

Only the final step — moving an item from `Potential Resolution` to
`Confirmed` / `Resolved` / `Promoted` / `Closed` — always requires explicit
user confirmation. That has not changed.

Before actually closing/confirming an item once approved, show what else is
affected — which digests reference it, via their `assumptions_referenced` /
`conflicts_referenced` / `gaps_referenced` front matter fields — before making
any edits to those digests. This follows the existing "Modifying Existing
Digests" preview rule below: list the affected digests and what would change
in each, and wait for approval before editing any of them.

## Assumption Lifecycle

Register format in `knowledge/assumptions.md`, one entry per assumption: ID,
topic, statement, Evidence Strength, digest(s) referencing it, status (`Open`
/ `Potential Resolution` / `Confirmed` / `Corrected`), date raised, resolution
(blank until resolved). See `TEMPLATES/assumption-entry.md`.

When clarifying information is provided, or a later document appears to bear
on an Open assumption (see Cross-Reference & Impact Analysis and "Potential
Resolution — Shared Lifecycle Rule" above):
1. Check it against **Open** assumptions first.
2. If a later *document* (rather than direct clarification) appears to
   confirm or contradict one, assess Evidence Strength: `Strong`/`Moderate`
   evidence sets it to `Potential Resolution` directly (no pre-approval
   needed for that step); `Weak` evidence is reported but leaves it `Open`.
3. If explicit clarification **confirms** one: mark it `Confirmed`, and update
   the digest's inline tag to `[CONFIRMED: MANTIS-ASM-XXX]`.
4. If explicit clarification **contradicts** one: mark it `Corrected`, note
   what changed, and list which digests need review. Do not auto-regenerate
   those digests — flag them as "pending review" and wait for approval before
   changing them.

### Open Assumptions Never Block Processing

An Open assumption never blocks processing. If the answer isn't known at the
time an assumption is raised (e.g. it requires asking a colleague who isn't
immediately available), the assumption stays `Open` indefinitely — there is no
timeout or auto-expiry.

- The digest is still generated normally. `document_confidence` is assessed
  per the two-level confidence rule: an Open assumption affects
  `document_confidence` only in proportion to how central it is to the
  document's content, never as an automatic downgrade.
- The inline `[MANTIS-ASM-XXX]` flag is retained in the digest body exactly as
  raised.
- Processing of that document, and all subsequent documents, continues
  without waiting for the assumption to be resolved.

Open assumptions are only ever resolved when explicit clarification is
provided later. A periodic review of all Open assumptions is a human
responsibility — not something the system enforces or schedules
automatically.

## Knowledge Gap Lifecycle

Register format in `knowledge/knowledge_gaps.md`, one entry per gap: ID,
topic, Evidence Strength, digest(s) affected, what's missing, date raised,
status (`Open` / `Potential Resolution` / `Promoted` / `Closed`), and (once
applicable) the ID it was promoted to. See `TEMPLATES/gap-entry.md`.

Rules:
- No inference is made to fill a gap, and it carries no confidence penalty on
  the document beyond noting that the gap exists.
- A gap only needs to be revisited when something is being built on top of the
  knowledge base and turns out to need the missing detail (e.g. an Output
  requires it, or a later document seems related but doesn't fully resolve
  it), or when a new document's content appears to fill it (see
  Cross-Reference & Impact Analysis above).
- When a later document appears to fill a gap, assess Evidence Strength:
  `Strong`/`Moderate` sets it to `Potential Resolution` directly (no
  pre-approval needed for that step); `Weak` is reported but leaves it
  `Open`. Either way, only move it to `Promoted` or `Closed` once the user
  explicitly confirms.
- **Source-internal rendering ambiguity** (e.g. garbled, duplicated, or
  internally inconsistent content within a single source — mismatched
  statuses across repeated blocks, strikethrough formatting that contradicts
  a non-struck occurrence elsewhere, an inconsistent highlighting
  convention) is logged as a Knowledge Gap, distinct from "the source doesn't
  cover this." The source does cover it — just inconsistently — so no
  inference is made about which rendering or status is authoritative.
- **Named actors without stated roles** (e.g. a person mentioned once with no
  title or role given) are listed in the Actors section without an automatic
  Knowledge Gap entry. A Gap is only raised for substantive undefined terms
  or relationships — an acronym, a system, an ambiguous entity
  classification — not for every underspecified name.

## Conflict Lifecycle

Register format in `knowledge/conflicts.md`, one entry per conflict: ID, topic,
Evidence Strength, statement A + source, statement B + source, status
(`Open` / `Potential Resolution` / `Resolved`), digests affected, date
raised, resolution. See `TEMPLATES/conflict-entry.md`.

Conflicts are never auto-resolved. Resolution is always a human call, recorded
in the entry's `resolution` field once made. When a later document appears to
resolve a Conflict, assess Evidence Strength: `Strong`/`Moderate` sets it to
`Potential Resolution` directly (no pre-approval needed for that step);
`Weak` is reported but leaves it `Open`. Either way, only move it to
`Resolved` once the user explicitly confirms.

## Decision Log

Register format in `knowledge/registers/decisions/<ID>.md` (one file per entry, written with `tools/entry.py`): ID, date, the decision, the
reasoning, sources/knowledge it was based on, alternatives considered. See
`TEMPLATES/decision-entry.md`.

This log is separate from factual digests — it records choices made on top of
the knowledge base, not documented facts. A Decision entry may cite Digests it
was informed by, but a Digest regeneration never alters a Decision entry.

## Modifying Existing Digests

Never silently edit an existing digest. Before any change:
1. Show a preview of exactly what would change and why.
2. Wait for explicit approval before writing the change.
3. After applying the edit, append a Change Log entry (see "Change Log"
   below) — every approved edit gets logged, no exceptions.

This applies to any edit — correcting a fact, updating a confidence level,
adding a citation, or anything else — not just full regenerations.

## Change Log

Every digest has a "Change Log" section at the bottom, below Known Gaps. It is
a lightweight, append-only record of edits made to that digest after
creation — not a new registry, not a separate file, just a log living in the
digest itself. It exists so that months from now, someone reading a single
digest can see its edit history without cross-referencing conversation logs
or Git blame. It is not a Git replacement.

Format — one line per entry:

```
[date] — [what changed] — Triggered by: [document ID or user input] — Reason: [one line] — Related: [assumption/conflict/gap ID if applicable]
```

Rules:
- Append any time an approved edit is made to an existing digest — a field
  changed, an item confirmed/resolved, a cross-reference added, etc.
- **Never delete or rewrite existing lines.** Only append new ones.
- Every digest gets this section from creation, even if it starts empty
  (e.g. `(No changes yet.)`).
- This section is populated by edits, not by the initial digest generation
  itself — a digest's own creation is not a "change" to itself.

## Outputs

- Outputs (`outputs/confluence/`, `outputs/epics/`, `outputs/user-stories/`,
  `outputs/knowledge-docs/`) are generated only from Digests and cards, never from other
  Outputs. Exception: a Confluence export of a page Mantis wrote carries the owner's own
  edits; facts taken from it are cited as the owner's, per `docs/rules/WORKFLOW.md`,
  "Exports of our own pages".
- Team-facing outputs keep source citations visible, but omit internal
  confidence scores and IDs — those are working-knowledge-layer detail, not
  something a reader of the onboarding guide or a user story needs to see.
- How to write outputs (templates, brief, self-check, PM skills) is in
  `docs/rules/OUTPUTS_GUIDE.md` (added 2026-10-09). This file covers ingestion; a session
  that only writes an output reads `docs/rules/OUTPUTS_GUIDE.md`, not this file.

## Feature cards and shared registers (added 2026-10-09)

- `knowledge/features/<feature>.md` holds one card per feature (template:
  `TEMPLATES/feature-card.md`). A card is a knowledge record, not an output:
  every line cites a digest, so outputs may start from it and still trace to sources.
- At ingest, if the new document touches a feature that has a card, update the
  card in the same change: add the document to its sources and any new rule, metric
  or gap, each cited. A contradiction is still raised as a Conflict, never smoothed
  over in the card.
- `knowledge/personas.md` and `knowledge/glossary.md` are shared registers. Add a
  persona or term there, cited, when a source introduces one.

---

## Navigation map (added 2026-10-07)

`tools/build_map.py` generates `mantis/knowledge/map/` (MAP.md, topics.md, entities.md,
registers.md, graph.json) from digest front matter and the registers. Run it at the end of
every ingest or approved edit. Sessions read the map first and open only the digests they
need. See `CLAUDE.md`. These files are derived and are never edited by hand.
