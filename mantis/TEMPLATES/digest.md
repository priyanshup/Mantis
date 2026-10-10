---
document_id: MANTIS-DOC-XXXX
source_file: 01_sources/MANTIS-DOC-XXXX/YYYY-MM-DD.ext
original_title: "[exact original wiki page title]"
version: 1
region: [e.g. a market name, or "Global"]
topics: [tag1, tag2, tag3]
key_entities: [Entity1, Entity2, Entity3]
related_documents: []
document_confidence: High | Medium | Low | Very Low
confidence_reason: "[one line explaining the document-level judgment, per docs/rules/WORKFLOW.md confidence rules — not just restating the level]"
assumptions_referenced: []
conflicts_referenced: []
gaps_referenced: []
generated_on: YYYY-MM-DD
generated_by:
  tool: Claude Code
  model: [model name used]
repository_version: 0.1
workflow_version: 0.1
---

## Summary

[120 words or fewer, standing alone: what the document is, what it decides or states, and
what is still open. The first sentence is the document's one-liner on every card, so it must
say what the document is. `tools/peek.py` shows only this section.]

## Business Rules

- [Rule or policy statement, ending in a source citation.]

## Actors

- [Person, role, system, or entity involved.]

## Dependencies

- [Other documents, systems, or decisions this content relies on or references.]

## Regional Notes

[Only if something is specific to a region or market. Leave the section out otherwise.]

## References

[Only for locations not already given in the inline citations, such as page or slide numbers.
Leave the section out otherwise.]

## Known Gaps

- [MANTIS-GAP-XXX] [Anything the source doesn't cover but a reader would
  reasonably expect it to — no inference made. See
  `knowledge/registers/gaps/` with `python tools/entry.py add gap`.]

## Change Log

(No changes yet.)

<!-- Append one line per approved edit, oldest first. Never delete or rewrite
existing lines. Format:
[date] — [what changed] — Triggered by: [document ID or user input] — Reason: [one line] — Related: [assumption/conflict/gap ID if applicable]
-->
