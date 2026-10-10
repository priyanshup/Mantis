---
feature: <kebab-case-name>
title: "<Feature name>"
jira: <KEY or none>
status: <discovery / refinement / build / live>
priority: <P1 / P2 / P3>
estimate_2027: "<complexity, effort or Not estimated>"
match_topics: [<digest topic tags that belong to this feature>]
source_documents: [<digests the curated text below already covers>]
gaps: [MANTIS-GAP-XXX]
conflicts: []
updated: YYYY-MM-DD
---

<!-- Feature card: the one file to read first about a feature. A knowledge record, not an
output: every line cites a document. Write only the curated part; tools/cards.py appends the
generated part (sources with one-liners, open questions, people and systems) on every
rebuild and marks sources the curated part does not cover yet. Keep it to facts; opinions and
proposals go in outputs. -->

## In one paragraph
<What it is, for whom, where it stands. Cited.>

## Persona
<Link to the personas register entry. Labels used in sources, if they differ.>

## Jobs and scope
| # | Job | MVP or later | Source |
|---|---|---|---|

## Business rules agreed so far
- <rule> (MANTIS-DOC-XXXX)

## Metrics
| Metric | Baseline | Target | Source |
|---|---|---|---|

## Next steps (optional, while work is in flight)
| Step | Who | Status | Source |
|---|---|---|---|
