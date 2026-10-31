---
feature: <kebab-case-name>
title: "<Feature name>"
jira: <KEY or none>
work: <business (the default), technical, or both: whether the requirements come from users, from engineering, or from both (e.g. a bug backlog)>
status: <discovery / refinement / build / live>
priority: <P1 / P2 / P3>
estimate_2027: "<complexity, effort or Not estimated>"
match_topics: [<digest topic tags that belong to this feature>]
source_documents: [<digests the curated text below already covers>]
gaps: [MANTIS-GAP-XXX]
conflicts: []
review_on:   # YYYY-MM-DD, set when the feature goes live: when its effect should be measurable
updated: YYYY-MM-DD
---

<!-- Feature card: the one file to read first about a feature. A knowledge record, not an
output: every line cites a document. Write only the curated part; tools/cards.py appends the
generated part (sources with one-liners, open questions, people and systems) on every
rebuild and marks sources the curated part does not cover yet. Keep it to facts; opinions and
proposals go in outputs, except where a line below is labelled Opinion or Proposed.
Method for the three decision sections: .claude/skills/pm-feature-framing and pm-success-metrics.
Fill them as far as the sources go; an honest Unknown is better than a filled-in guess. -->

## In one paragraph
<What it is, for whom, where it stands. Cited.>

## Problem and outcome
<!-- Mark every claim *Observed* (a source shows it happening), *Opinion* (someone says so:
name who) or *Unknown* (nobody knows yet). A request is not evidence of a problem. -->
- **Request:** <who asked for what, and when> (source)
- **Work type:** <discretionary / mandatory: the obligation / approved commitment: who approved> (source)
- **Problem:**
    - *Observed:* <what goes wrong today, for whom, how often, how badly> (source)
    - *Opinion:* <Name says ...> (source)
    - *Unknown:* <what we don't know that could change the decision>
- **Outcome wanted:** <what changes for users or the business> (source, or *Proposed*)
- **Cost of doing nothing:** <...> (source, or *Unknown*)
- **Decision status:** <idea / in discovery / approved to build (who, source) / live>
- **Next decision:** <what, who decides, what it needs first>

## Persona
<Link to the personas register entry. Labels used in sources, if they differ.>

## Jobs and scope
| # | Job | MVP or later | Source |
|---|---|---|---|

## Business rules agreed so far
- <rule> (MANTIS-DOC-XXXX)

## Measurement
**Hypothesis:** If <change>, then <result>, because <reason> (source, or *Proposed*).

- **Primary: <metric name>**: <definition: what is counted, out of what>
    - Population: <who> · Window: <period> · Data source: <tool or report> (instrumented: yes / no / unknown) · Owner: <who reads it>
    - Baseline: <value (source)> or *Unknown*: get it from <where>
    - Target: <value (source)> or *Proposed:* <value>, because <rationale>; awaiting the owner
- **Guardrail: <metric name>**: <definition>; must not <get worse by how much>
- **Decision rule:** scale if <...>; iterate if <...>; hold or investigate if <...>; roll back if <...>

<!-- Mandatory, compliance or security work: replace the metrics with
- **Obligation:** <what must be true, and by when> (source)
- **Acceptance:** <how we check it is met>
- **Evidence of completion:** <what proves it: audit, test report, sign-off> -->

## Launch review
<!-- After go-live, on review_on. A filled field is not a success: record what the data says. -->
- **Reviewed on:** <date>
- **Result:** <measured value (source, date)> or *Measurement gap:* <why there is no data, and how to get it>
- **Interpretation:** <what it means against the hypothesis and target>
- **Decision:** <scale / iterate / hold / investigate / roll back> (decision entry)
- **Follow-ups:** <actions, who>

## Next steps (optional, while work is in flight)
| Step | Who | Status | Source |
|---|---|---|---|
