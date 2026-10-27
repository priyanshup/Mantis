# WORKFLOW RULES

What Mantis may and may not do, and what its terms mean: IDs, digests, confidence, evidence,
priority, assumptions, gaps, conflicts, decisions and edits. The step-by-step procedures live in
`docs/rules/workflow/` (ingest, answers, edits, the owner's day), indexed by
`docs/rules/WORKFLOW.md`; they point here with "rules: <section>". On what is allowed, this file
wins. On how to do it, the procedure files win. Where this file and convenience disagree, this
file wins (Non-Negotiable Principle in `docs/rules/PROJECT_VISION.md`).

**Paths:** unless written with a `mantis/` prefix, paths here are relative to `mantis/`
(`00_inbox/` means `mantis/00_inbox/`). Rules, system notes and plans live in `docs/`.
Registers are one file per entry under `knowledge/registers/` (`gaps/`, `assumptions/`,
`conflicts/`, `decisions/`, `assets/`; `documents/` is the generated index), read and written
only with `tools/entry.py`.

## ID Scheme

- Documents: `MANTIS-DOC-0001`, `MANTIS-DOC-0002`, ...
- Assumptions: `MANTIS-ASM-001`, `MANTIS-ASM-002`, ...
- Conflicts: `MANTIS-CFL-001`, `MANTIS-CFL-002`, ...
- Decisions: `MANTIS-DEC-001`, `MANTIS-DEC-002`, ...
- Knowledge Gaps: `MANTIS-GAP-001`, `MANTIS-GAP-002`, ...
- Knowledge assets (diagrams and other visuals): `MANTIS-AST-001`, ...

Rules:
- IDs are claimed with `python tools/entry.py next <kind>`, never picked by reading a register.
- IDs are assigned once, in order, and are permanent: never reused or reassigned, even if the
  item is later deleted, superseded, or found to be a duplicate.
- A Document's ID never changes even if its title changes later: the ID tracks the logical
  document, not its current name.

## Classification of a new file

Every new file is one of: **New document** / **New version of an existing document** /
**Duplicate** / **Related but distinct**. `tools/classify.py` scores it against the corpus with
the cut-offs in `tools/classify_config.json` (AD-011). Only its AMBIGUOUS verdict stops ingest to
ask the owner; a recurring meeting is never treated as a new version of the last one. Pasted
material (meeting notes, replies, screenshots) skips the verdict by owner instruction and is a new
document. A new version keeps the ID, raises `version`, and moves the prior digest to
`03_archive/` before the new one is written. A dated source snapshot in `01_sources/` is never
overwritten.

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

1. **Summary**: a short, plain-language description of what the document covers.
2. **Business Rules**: the concrete rules, policies, or logic stated in the source, each ending
   in a source citation.
3. **Actors**: the people, roles, systems, or entities involved.
4. **Dependencies**: other documents, systems, or decisions this content relies on or references.
5. **Regional Notes**: anything specific to a region/market, or "None" if the content is global.
6. **References**: the explicit list of source locations cited in the body (page numbers,
   section headers, slide numbers, etc., as applicable).
7. **Known Gaps**: anything the source document doesn't cover but that a reader would
   reasonably expect it to.
8. **Change Log**: an append-only log of edits made to this digest after creation. See "Change
   Log" below for the format and rules.

Every factual claim in the body ends with a source citation. See `TEMPLATES/digest.md` for the
fillable skeleton.

## Related Documents

`related_documents` in the front matter links a Digest to other Documents already in Mantis. Two
kinds of evidence justify a link:

- **Explicit citation**: the source names or links another ingested Document as its source, hub,
  or reference (e.g. a strategy page citing the mission page as its source).
- **Verbatim identical content**: a substantial block of text is duplicated word-for-word across
  two Documents (e.g. two pages sharing an identical Metrics section), even without an explicit
  citation between them.

Thematic or topical overlap alone (same team, same subject area, similar naming) is **not**
sufficient grounds for a link: only one of the two evidence types above.

Whichever applies, the digest must state which one it is (citation vs. text-match) rather than
presenting both the same way, so a future reader can judge the strength of the connection for
themselves.

## Confidence Rules

Confidence exists at two levels: **document-level** (`document_confidence` in the digest front
matter) and **item-level** (the status of each individual Assumption in the register). They are
judged separately.

### Item-level (per Assumption)

Each Assumption carries its own status in the Assumption register: `Open` / `Confirmed` /
`Corrected`. This is the finer-grained signal; see Assumption Lifecycle below.

### Document-level (`document_confidence`)

`document_confidence` reflects the overall reliability of the digest as a whole, judged
rule-based, never invented or vibes-based:

- **Very High**: multiple independent sources corroborate the same fact.
- **High**: explicitly and clearly stated in one authoritative source.
- **Medium**: stated in one source, but ambiguous or lacking detail.
- **Low**: a substantial portion of the digest, or a business-rule-level claim, rests on an
  assumption not explicitly stated in any source.
- **Very Low**: an open, unresolved conflict exists on this topic.

`document_confidence` is a holistic judgment, not a mechanical floor set by the presence of any
single Open assumption. A digest with one Open assumption on a minor, peripheral detail, while
the core business rules are explicitly sourced, should still be `High` or `Medium`, not
automatically dragged to `Low`. Judge based on what proportion of the content is
assumption-based versus explicitly sourced, and how important the assumption-based part is to
the digest's core claims. Reserve `Low` for when an assumption underpins a core business rule,
actor, or dependency, not a minor or cosmetic detail.

`confidence_reason` must state that judgment explicitly, e.g. "98% of content explicitly
sourced; one open assumption (MANTIS-ASM-001) on a minor detail — does not affect core business
rules," not just restate the confidence level or mechanically cite "contains an assumption."

Knowledge Gaps (see below) do not by themselves lower `document_confidence`: noting that the
source doesn't cover something is not the same as relying on an unverified inference. A gap
only affects confidence if and when it is promoted to an Assumption.

## Evidence Strength

`Evidence Strength` (`Strong` / `Moderate` / `Weak`) is a required field on every Assumption,
Conflict, and Knowledge Gap entry when first raised, and on every cross-check finding (see
"Potential Resolution"). It answers one question: how solid is the evidence behind this specific
item or finding?

- **Strong**: an explicit definition, a direct citation, or a direct contradiction was found.
  The evidence states the thing outright.
- **Moderate**: contextual or indirect evidence: plausible and consistent with the item, but not
  stated outright. Requires reading between two related statements.
- **Weak**: circumstantial: a single ambiguous mention, or requires connecting dots between
  things that aren't clearly related.

`Evidence Strength` drives the `Potential Resolution` threshold; see "Potential Resolution —
Shared Lifecycle Rule" below. It is assessed independently each time new evidence appears; the
same item can accumulate multiple pieces of evidence at different strengths over its lifetime
(e.g. a `Moderate` finding followed later by a `Strong` one).

**Four different kinds of sureness.** `document_confidence` says how reliable a digest is.
`Evidence Strength` says how solid the evidence is behind one item. `Priority` says what being
wrong would cost. Whether a proposed solution will work is a fourth thing: a hypothesis, tested by
measurement after launch (card "Measurement" and "Launch review"). Mantis never scores it, and
evidence that a problem exists is never presented as evidence that the solution will work.

## Priority

`Priority` (`Critical` / `High` / `Medium` / `Low`) says how much an open Assumption, Conflict
or Knowledge Gap matters, so the owner knows what to ask about first. Evidence Strength says how
sure we are; Priority says what it costs to be wrong. It is optional: an entry without it is "not
triaged yet", never Medium by default.

- **Critical**: blocks a decision, a release or a page the owner must publish now.
- **High**: affects scope, requirements or a date on a roadmap feature.
- **Medium**: changes detail on a page, not its direction.
- **Low**: nice to know.

Set it with `python tools/entry.py priority <ID> <Level> "<why>"` when the reason is clear from
the sources or the owner says so; otherwise leave it out. A guess at priority is an assumption
like any other. The Questions page and `map/registers.md` list Critical and High first, then
untriaged, then Medium and Low.

## Evidence Source Types

Beyond `Evidence Strength` (Strong/Moderate/Weak, above), which measures how solid a piece of
evidence is, evidence also comes from distinct **source types**, which carry different
reliability characteristics and must be tagged explicitly rather than presented uniformly:

- **MANTIS-ingested document citation**: a claim sourced from a document that has been ingested
  (`docs/rules/workflow/ingest.md`) and lives in `02_digests/`. This is the default, most reliable
  source type.
- **Direct SME consultation**: the user consulted a subject-matter expert (a colleague, a senior
  stakeholder) directly and relayed the answer back. Tag as: `Source: Direct SME consultation,
  [date].`
- **User's own outside knowledge**: the user's personal knowledge, stated directly, not yet
  backed by any ingested document. Tag as: `Source: User knowledge, [date], not yet present in any
  ingested document.` An answer given on the Questions page is tagged `Source: Owner answer via
  the Questions page, [date].`
- **External AI research**: a third-party AI research tool (named for this instance in
  `CLAUDE.local.md`) searched the company's own wiki/tracker directly and returned citations to
  specific pages with quoted content. This is **strong supporting evidence, but is not equivalent
  to a MANTIS-ingested digest citation** until/unless the cited page is itself later ingested;
  such a citation points to a source Mantis has not yet independently verified. Tag as:
  `Source: <tool> AI research, citing [page name/URL] — not yet MANTIS-ingested.`

When a resolution sourced from external AI research is later corroborated (or contradicted) by
the actual Mantis ingestion of the page it cited, treat that ingestion as new evidence in its own
right (see "Potential Resolution"): it does not silently "upgrade" the earlier AI-research-sourced
note in place; it is recorded alongside it, and any discrepancy between the two is flagged rather
than auto-resolved.

## Batch Processing

Documents in the inbox are processed continuously within a batch, **without stopping for review
after each individual digest**.

**Exception-based checkpoints: stop immediately, report, and wait when:**
1. Document classification is ambiguous (see "Classification of a new file"). Always stops.
2. A new Conflict is raised that you are sure of (see "Conflict Lifecycle"). Always stops, even
   mid-batch: a factual contradiction between sources is never batched past. A possible
   conflict found by the contradiction check does not stop the batch (see "Conflict Lifecycle").
3. A new Assumption is raised whose Evidence Strength doesn't clearly reach at least `Moderate`.
   A genuinely uncertain inference gets flagged live, not rolled into an end-of-batch report
   where it could sit unnoticed among routine items.
4. Anything that would require editing an **existing** digest still requires a preview and
   explicit approval before writing, per "Modifying Existing Digests".

Outside of these four triggers, keep processing straight through the batch. An unattended
background job never stops to ask: it leaves such an item, lists it under "NEEDS YOU", and ends
(`docs/rules/WORKFLOW.md`, "Buttons on the site").

**Batch size:** process up to 10 documents by default, then pause for the user's review of the
consolidated report (below) before continuing to the next batch. This is a checkpoint, not a full
stop: the user saying "continue" is enough to start the next batch of up to 10.

**End-of-batch report:** produced when the batch limit (10) is reached, the inbox empties, or one
of the four exception triggers forces a stop, whichever comes first. One consolidated report
covering everything processed in the batch so far:
- List of new document IDs and titles.
- Rollup of new Assumptions raised, with Evidence Strength.
- Rollup of new Conflicts raised, sure and possible.
- Rollup of new Knowledge Gaps raised.
- Anything that self-promoted to `Potential Resolution` during the batch (per the Evidence
  Strength threshold rule in "Potential Resolution — Shared Lifecycle Rule").

**Cross-check disclosure for new Knowledge Gaps:** when a newly-raised gap involves a term that
could plausibly relate to existing tracked terminology or frameworks (anything resembling a tier,
wave, deployment label, or classification scheme — e.g. a new "XYZ" label appearing alongside
already-known labels like a rollout wave, a market-type framework, or a maturity tier), the
rollup entry must state **what was checked and ruled out**, not just the bare conclusion. Name
each existing framework considered and why it was ruled in or out — e.g. "checked against the
Wave 1 rollout and the market-type framework; no connection found; source treats Tier A as an
explicit contrast to Wave 1, not a synonym" — rather than a bare "no connection found" or, worse,
silence on whether the check happened at all. This applies whether or not a connection is
actually found: a clean rule-out is exactly as reportable as a hit, since the point is letting the
user verify the check happened without needing to ask a follow-up question every time.

The per-document "stop and show me the digest" pattern remains available on request (e.g. for a
first look at a new document type, or a particularly dense or high-risk source).

## Assumptions vs. Knowledge Gaps

These are two distinct things and must not be conflated:

- **Assumption**: Claude infers something not explicitly stated, in order to produce a complete
  statement. Example: "region assumed Global based on vision language." An inference was made; it
  is tracked so it can later be confirmed or corrected. Tag it inline in the digest body as
  `[MANTIS-ASM-XXX]` and create the matching entry in `registers/assumptions/`, with an Evidence
  Strength assessment for the inference itself.
- **Knowledge Gap**: the source simply doesn't cover something, and no inference is made to fill
  it. The digest explicitly notes the gap and stops there. Example: "SAP is mentioned; which SAP
  module is never specified in this source." Note it inline as `[MANTIS-GAP-XXX]` (typically in
  Known Gaps) and create the matching entry in `registers/gaps/`. Do not guess to fill it.

The test: did completing the statement require inferring an unstated fact (Assumption), or did
the digest simply note an absence and go no further (Knowledge Gap)? If in doubt, prefer
Knowledge Gap: it makes no claim at all, whereas an Assumption asserts something that could later
turn out to be wrong.

**The source's own self-declared hedges are neither.** When a source explicitly flags its own
uncertainty — "the assumption is that...", "pending final confirmation of...", "(I think)" — that
is the source's stated uncertainty, not an inference Mantis is making. Quote it verbatim in the
digest body rather than converting it into a `MANTIS-ASM-XXX` entry. It only becomes a Mantis
Assumption if completing some *other* statement requires relying on it as if it were settled.

A Knowledge Gap can later be **promoted** to an Assumption (if a plausible inference becomes
needed) or escalated into a real question for an SME — for example, if an Output being built on
top of the knowledge base needs the missing detail. When that happens, create the new Assumption
entry (or raise the SME question), reference the originating `MANTIS-GAP-XXX` ID in it, and update
the Knowledge Gap entry's status to reflect the promotion rather than deleting it.

## Potential Resolution — Shared Lifecycle Rule

Assumptions, Conflicts, and Knowledge Gaps all share the same three-state resolution pattern:
`Open` → `Potential Resolution` → a final state (`Confirmed`/`Corrected` for Assumptions,
`Resolved` for Conflicts, `Promoted`/`Closed` for Knowledge Gaps). **Never jump straight from
`Open` to a final state automatically**: that final step is a human decision (one exception for
open questions, below). Two other
states are owner decisions too: `Deferred` (the owner said it is not decided yet; it waits on the
card under "Decided later" with its trigger) and `Unconfirmed` (a possible conflict, below).

Every new document is cross-checked against the open items it may bear on (`tools/classify.py`
lists them): Assumptions, Conflicts, Knowledge Gaps, and Decisions it might change. The
`Open` → `Potential Resolution` transition is threshold-based on `Evidence Strength`, not a human
decision:

- **`Strong` or `Moderate` evidence**: set its status to `Potential Resolution` directly. No
  pre-approval is needed for this specific transition: it is a system-generated provisional
  label, not a resolution. Report the finding explicitly: which item, what evidence, where
  (section/page) in the new document, and the Evidence Strength rating.
- **`Weak` evidence**: report the finding, but the item stays `Open`. Weak evidence never
  triggers `Potential Resolution` on its own.

Only the final step — moving an item from `Potential Resolution` to `Confirmed` / `Resolved` /
`Promoted` / `Closed` — always requires explicit user confirmation. Choosing "Answers it" on the
Questions page is that confirmation.

**One exception, decided by the owner on 2026-10-27 (MANTIS-IMP-094): open questions close
themselves.** A Knowledge Gap that a new source answers with `Strong` evidence is closed at once with
`tools/entry.py close`, which writes `Closed (auto, <date>: <evidence>; source <DOC>)` and lists
other open gaps the same answer may settle. Each of those closes only on its own Strong evidence.
The brief after a pull lists every automatic close, and `tools/entry.py reopen` undoes one. The
exception covers gaps only: Conflicts and Assumptions still wait for the owner, and Moderate
evidence still stops at `Potential Resolution`. Digests that cite the gap are not edited.

Before actually closing/confirming an item once approved, show what else is affected — which
digests reference it, via their `assumptions_referenced` / `conflicts_referenced` /
`gaps_referenced` front matter fields — before making any edits to those digests. This follows
the "Modifying Existing Digests" preview rule below: list the affected digests and what would
change in each, and wait for approval before editing any of them.

## Assumption Lifecycle

Register format in `registers/assumptions/<ID>.md`, one file per assumption: ID, topic,
statement, Evidence Strength, digest(s) referencing it, status (`Open` / `Potential Resolution` /
`Confirmed` / `Corrected`), date raised, resolution (blank until resolved). See
`TEMPLATES/assumption-entry.md`.

When clarifying information is provided, or a later document appears to bear on an Open
assumption (see "Potential Resolution" above):
1. Check it against **Open** assumptions first.
2. If a later *document* (rather than direct clarification) appears to confirm or contradict one,
   assess Evidence Strength: `Strong`/`Moderate` evidence sets it to `Potential Resolution`
   directly (no pre-approval needed for that step); `Weak` evidence is reported but leaves it
   `Open`.
3. If explicit clarification **confirms** one: mark it `Confirmed`, and update the digest's
   inline tag to `[CONFIRMED: MANTIS-ASM-XXX]`.
4. If explicit clarification **contradicts** one: mark it `Corrected`, note what changed, and
   list which digests need review. Do not auto-regenerate those digests: flag them as "pending
   review" and wait for approval before changing them.

### Open Assumptions Never Block Processing

An Open assumption never blocks processing. If the answer isn't known at the time an assumption
is raised (e.g. it requires asking a colleague who isn't immediately available), the assumption
stays `Open` indefinitely: there is no timeout or auto-expiry.

- The digest is still generated normally. `document_confidence` is assessed per the two-level
  confidence rule: an Open assumption affects `document_confidence` only in proportion to how
  central it is to the document's content, never as an automatic downgrade.
- The inline `[MANTIS-ASM-XXX]` flag is retained in the digest body exactly as raised.
- Processing of that document, and all subsequent documents, continues without waiting for the
  assumption to be resolved.

Open assumptions are only ever resolved when explicit clarification is provided later. A
periodic review of all Open assumptions is a human responsibility, not something the system
enforces or schedules automatically.

## Knowledge Gap Lifecycle

Register format in `registers/gaps/<ID>.md`, one file per gap: ID, topic, Evidence Strength,
digest(s) affected, what's missing, date raised, status (`Open` / `Potential Resolution` /
`Promoted` / `Closed`), and (once applicable) the ID it was promoted to. See
`TEMPLATES/gap-entry.md`.

Rules:
- No inference is made to fill a gap, and it carries no confidence penalty on the document
  beyond noting that the gap exists.
- A gap only needs to be revisited when something is being built on top of the knowledge base
  and turns out to need the missing detail (e.g. an Output requires it, or a later document seems
  related but doesn't fully resolve it), or when a new document's content appears to fill it.
- When a later document appears to fill a gap, assess Evidence Strength: `Strong`/`Moderate`
  sets it to `Potential Resolution` directly (no pre-approval needed for that step); `Weak` is
  reported but leaves it `Open`. Either way, only move it to `Promoted` or `Closed` once the user
  explicitly confirms, except a gap answered with Strong evidence, which closes itself (see
  "Potential Resolution", the exception).
- **Source-internal rendering ambiguity** (e.g. garbled, duplicated, or internally inconsistent
  content within a single source — mismatched statuses across repeated blocks, strikethrough
  formatting that contradicts a non-struck occurrence elsewhere, an inconsistent highlighting
  convention) is logged as a Knowledge Gap, distinct from "the source doesn't cover this." The
  source does cover it, just inconsistently, so no inference is made about which rendering or
  status is authoritative.
- **Named actors without stated roles** (e.g. a person mentioned once with no title or role
  given) are listed in the Actors section without an automatic Knowledge Gap entry. A Gap is only
  raised for substantive undefined terms or relationships — an acronym, a system, an ambiguous
  entity classification — not for every underspecified name.

## Conflict Lifecycle

Register format in `registers/conflicts/<ID>.md`, one file per conflict: ID, topic, Evidence
Strength, statement A + source, statement B + source, status (`Unconfirmed` / `Open` /
`Potential Resolution` / `Resolved`), digests affected, date raised, resolution. See
`TEMPLATES/conflict-entry.md`.

When a new digest contradicts an existing digest or card: do not resolve it. Record both
statements with their sources, tag both digests' front matter (`conflicts_referenced`) with the
conflict ID, and report it directly. The card keeps its claim until the owner decides; a
contradiction is never smoothed over in a card or a digest.

**Possible conflicts (2026-10-10, MANTIS-IMP-047).** When the contradiction check
(`tools/contradictions.py`) finds two statements that may disagree but you cannot tell whether
they truly conflict or the plan simply moved, record the conflict with status `Unconfirmed
(possible conflict found <date> by the contradiction check)` and carry on: it is posted to the
Questions page and does not stop the batch. The owner answers "Yes, they conflict" (it becomes
`Open`, or `Resolved` if they say which is right), "The plan changed" (`Resolved (plan changed)`,
the newer statement wins) or "Not a conflict" (`Closed (not a conflict)`).

Conflicts are never auto-resolved. Resolution is always a human call, recorded in the entry's
`resolution` field once made. When a later document appears to resolve a Conflict, assess
Evidence Strength: `Strong`/`Moderate` sets it to `Potential Resolution` directly (no
pre-approval needed for that step); `Weak` is reported but leaves it `Open`. Either way, only move
it to `Resolved` once the user explicitly confirms.

## Decision Log

Register format in `registers/decisions/<ID>.md` (one file per entry, written with
`tools/entry.py`): ID, date, the decision, the reasoning, sources/knowledge it was based on,
alternatives considered, consequences. See `TEMPLATES/decision-entry.md`. A decision is logged at
the moment the owner settles a choice, including one stated in an answer ("we will use the
existing roles").

This log is separate from factual digests: it records choices made on top of the knowledge base,
not documented facts. A Decision entry may cite Digests it was informed by, but a Digest
regeneration never alters a Decision entry.

## Modifying Existing Digests

Never silently edit an existing digest. Before any change:
1. Show a preview of exactly what would change and why.
2. Wait for explicit approval before writing the change.
3. After applying the edit, append a Change Log entry (see "Change Log" below): every approved
   edit gets logged, no exceptions.

This applies to any edit — correcting a fact, updating a confidence level, adding a citation, or
anything else — not just full regenerations.

**One exception, decided by the owner on 2026-10-27 (MANTIS-IMP-094): a card's monthly pull digest.**
A digest whose front matter has `pull_card` and `pull_month` collects that card's Jira and
Confluence changes for the month. A pull may add a dated `## <date>` section to it, cited to its new
source file, and rewrite its Summary to cover the month, without a preview. Nothing else in it
changes, and each addition still gets a Change Log line.

## Change Log

Every digest has a "Change Log" section at the bottom, below Known Gaps. It is a lightweight,
append-only record of edits made to that digest after creation, living in the digest itself, so
someone reading a single digest can see its edit history without cross-referencing conversation
logs or Git blame. It is not a Git replacement.

Format, one line per entry:

```
[date] — [what changed] — Triggered by: [document ID or user input] — Reason: [one line] — Related: [assumption/conflict/gap ID if applicable]
```

Rules:
- Append any time an approved edit is made to an existing digest: a field changed, an item
  confirmed/resolved, a cross-reference added, etc.
- **Never delete or rewrite existing lines.** Only append new ones.
- Every digest gets this section from creation, even if it starts empty (e.g. `(No changes yet.)`).
- This section is populated by edits, not by the initial digest generation itself: a digest's own
  creation is not a "change" to itself.

## Cards

A card (`knowledge/features/<slug>.md` for roadmap features, `knowledge/topics/<slug>.md` for
other subjects; templates in `TEMPLATES/`) is a knowledge record, not an output: every line of its
curated part cites a digest, so outputs may start from it and still trace to sources.
`tools/build_map.py` links each new digest to every card whose `match_topics` it carries and marks
it new; nothing is written to a card at ingest. At the end of a batch, each card with new sources
gets its curated summary refreshed, after the contradiction check: what agrees is folded in,
cited, and the IDs added to `source_documents`; what disagrees becomes a conflict and the card
keeps its claim (`docs/rules/workflow/ingest.md`, "End of batch"). A card's front matter (status,
priority, estimate) changes only when a source or the owner states it. `knowledge/personas.md`,
`knowledge/glossary.md` (with its Mishearings table) and `knowledge/entity_register.md` are shared
registers: add a persona, term, mishearing, alias or relation there, cited, when a source or the
owner introduces one.

**Decision sections (2026-10-10, MANTIS-IMP-074 to 076).** A feature card carries three sections
that make a decision possible: "Problem and outcome", "Measurement" and, after go-live,
"Launch review" with `review_on` in the front matter (format: `TEMPLATES/feature-card.md`; method:
the `pm-feature-framing` and `pm-success-metrics` skills). They follow the card's rules, with
labels instead of silence: every problem claim is *Observed* (cited), *Opinion* (who, cited) or
*Unknown*; a target no source gives is *Proposed* with its rationale and stays so until the owner
confirms it; a baseline is never invented. A request is never written as a validated problem.
Fill them as far as the sources go. `tools/readiness.py` reads them; Home judges readiness by the
evidence (observed or not, measured or not), never by how many fields are filled.

## Outputs

- Outputs (`outputs/confluence/`, `outputs/epics/`, `outputs/user-stories/`,
  `outputs/knowledge-docs/`) are generated only from Digests and cards, never from other Outputs.
  Exception: a Confluence export of a page Mantis wrote carries the owner's own edits; facts taken
  from it are cited as the owner's (`docs/rules/workflow/edits.md`, "Exports of our own pages").
- Team-facing outputs keep source citations visible, but omit internal confidence scores and
  IDs: those are working-knowledge-layer detail, not something a reader needs to see.
- How to write outputs (templates, brief, self-check, PM skills) is in
  `docs/rules/OUTPUTS_GUIDE.md`; a session that only writes an output reads that, not this file.

## Generated files

`tools/build_map.py` generates `mantis/knowledge/map/` (MAP.md, cards.md, topics.md, entities.md,
registers.md, and the JSON the site reads) from digest front matter, cards and registers, and
rebuilds the site. Run it at the end of every ingest or approved edit. Sessions read the map and
cards first and open only the digests they need (see `CLAUDE.md`). These files are derived and
are never edited by hand.
