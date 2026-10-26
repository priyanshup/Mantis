# Ingesting sources

Part of the workflow (index and the rules for every task: `../WORKFLOW.md`). Use this file for: Adding any document, file or paste to Mantis.

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
   Transcripts and dictated notes: `python tools/mishear.py <source file>` lists words the
   glossary knows are misheard ("MTs" for empties). Write the meaning in the digest and add
   "(transcript: MTs)" the first time, so the correction is visible. A new mishearing the owner
   confirms goes into the glossary's Mishearings table.
6. **Assumptions, gaps, conflicts.** Decide which applies (rules: Assumptions vs. Knowledge
   Gaps). Claim IDs, write the entries to a scratch file in the register's format, then
   `python tools/entry.py add gap <file>` (or `asm`, `cfl`). `add` refuses an entry that looks
   like a question already closed, resolved or answered, and names those entries: read them,
   and if one settles it, cite it in the digest instead of asking again; re-run with
   `--still-new` only when the question is genuinely new (MANTIS-IMP-088). In `key_entities`,
   use the register's canonical names (`python tools/graph.py <name>`), so a known thing under
   a new spelling does not become a new name question. Stop and report live for a new
   conflict or an assumption below Moderate evidence (rules: Batch Processing). Add a
   Priority line only when the sources make the stakes clear (rules: Priority).
7. **Cross-check.** Read only the open items step 2 listed: `python tools/entry.py show <ID>`.
   Strong or Moderate evidence: `python tools/entry.py status <ID> "Potential Resolution (<date>: <evidence>)"`.
   Weak: report only. Only the owner closes, confirms or resolves (rules: Potential Resolution).
   Then the contradiction check: `python tools/contradictions.py context <ID>` prints the new
   source beside its cards and closest sources. For each statement that disagrees on a date,
   number, scope, owner or meaning, add a conflict with Statement A and B and
   `Status: Unconfirmed (possible conflict found <date> by the contradiction check)`. Do not
   change the card's claim; the owner settles it on Open items. A batch or job does not stop
   for these; a conflict you are sure of still stops it (rules: Batch Processing).
8. **Index and cards.** Nothing to write: `build_map.py` generates the index entry and adds the
   document to every card whose tags it carries, marked new. If the document changes a
   roadmap feature's status or priority, update that card's front matter. Add new personas and
   terms to `knowledge/personas.md` and `glossary.md`. In `knowledge/entity_register.md`, add a
   relation the document states between two entities (cited), a type for a new important
   entity, and an alias the source confirms. Never merge names on a guess.
9. **Inbox.** Move the original out of `00_inbox/`.
10. **Diagrams: not at ingest.** `build_map.py` already pulls the new source's images out and
   sets decorative ones aside. Candidates are reviewed when a page needs a visual (OUTPUTS_GUIDE
   step 3) or the owner asks, never as a routine ingest step: that is where the cost pays off
   (MANTIS-IMP-057).

## End of batch

- Run `python tools/build_map.py`. It rebuilds the map, cards, index, lint, health report and site.
- Refresh the summaries of cards that now show new sources (`map/cards.md`, column "new"): run
  `python tools/contradictions.py context --card <slug>` first. Where a new source disagrees
  with the summary, record an unconfirmed conflict and keep the summary's claim; fold in only
  what does not clash. Then update the curated part, cited, and add the IDs to
  `source_documents`. A subject with 3+ documents and no card
  (`map/cards.md`, "Suggested new cards") gets a topic card in `knowledge/topics/` from
  `TEMPLATES/topic-card.md`.
- For each card whose summary you refreshed, run `python tools/support.py check --card <slug>`
  (MANTIS-IMP-079). A verifier checks every business rule and *Observed* problem line not yet
  checked against its current sources: supported, partially supported, unsupported, contradicted
  or indeterminate, plus counterevidence from the card's other sources. It costs tokens only for new
  or changed claims. A claim found contradicted, or disputed by another source, becomes a possible
  conflict (status Unconfirmed, rules: Conflict Lifecycle) and the card keeps its claim. Report
  unsupported and partly supported claims in the end-of-batch report. Never rewrite a claim, a
  source or a decision on the verifier's word; `python tools/support.py report` lists what is open.
- After the summaries are refreshed, run `python tools/changes.py behind`: it lists every page, epic and
  story whose card changed after it was written, and which card sections changed. Update each one in
  the same session: only the parts those sections touch, cited, following `docs/rules/OUTPUTS_GUIDE.md`
  ("Updating a page already in Confluence or Jira"), then set its `updated` date. The site's Confluence
  and Jira panels then show the owner exactly which sections or fields to paste. An output marked
  `track_card: false` copies someone else's text verbatim and is never rewritten.
- Give the end-of-batch report (rules: Batch Processing), including the outputs you updated.

## Estimation sheet

When the owner sends the team's estimation sheet: ingest it as a document first (so the
estimates are cited), then `python tools/estimates.py preview <file>`. It matches each row to a
card by shared words and lists weak or missing matches. Fix those with
`--map "row text=card-slug"` or leave them out with `--skip "row text"`, show the owner the
preview, then `python tools/estimates.py apply <file> --doc <ID> [--map ...] [--skip ...]` and run
`build_map.py`. A row with no card (for example a new initiative) is reported, never forced onto
one; it may need a topic card.
