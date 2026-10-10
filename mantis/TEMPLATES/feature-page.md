---
feature: <feature slug, same as the card>
type: page
status: draft   # draft / review / published
updated: YYYY-MM-DD
---

<!-- Feature page (Confluence). A starting point, not a form: drop or merge sections that
don't help this feature. Rules: docs/rules/OUTPUTS_GUIDE.md. Reference: see CLAUDE.local.md.
Each fact lives in one section. Status only in the header and At a glance. -->

# <Feature name>

Status | Product owner | Jira <KEY> | Updated <date>

## At a glance

| | |
|---|---|
| Persona | <who, one line; link to personas register> |
| Problem | <one sentence> |
| Primary job | When <situation>, I want to <action>, so I can <outcome> |
| Hypothesis | If <change>, then <result>, measured by <primary metric> |
| Scope | MVP: <jobs>. Later: <jobs> |
| Status | <discovery / ready for build / in build> |
| Decision needed | <what, from whom, by when> |

## Persona
*Source: <doc IDs>*
Role, where they work, goal, main pain, today's workaround, digital comfort.
Mark the card **assumed** or **interviewed**.

## Problem
*Source:*
What goes wrong today and what it costs. Two or three sentences.

## Proposal and scope
*Source:*
What we will build, in plain numbered steps.

| In (MVP) | Later | Out (no-gos) |
|---|---|---|

Rabbit holes: <known traps to avoid, one line each>

## Business context
*Source:*
A. Value and competitiveness. B. Legal and compliance. C. Risk of doing nothing.
One line per point; skip a letter if nothing applies.

## Current state
*Source:*

| Tool or channel | What it does | Key limitation |
|---|---|---|

## Jobs to be done
*Source:*
Numbered list, MVP or Later on each. Acceptance criteria live in the epic, not here.

## Success metrics
*Source:*

| Metric | Primary or guardrail | Baseline | Target | By when | Data source |
|---|---|---|---|---|---|

Mark a target that no source gives as Proposed, with its reason. Decision rule: what result
makes us scale, iterate, hold, investigate or roll back. For mandatory work, replace the table
with the obligation, how it is accepted and the evidence of completion.

## Assumptions and risks
*Source:*

| Item | Assumption or risk | How we check or mitigate |
|---|---|---|

## Open questions

| Question | Blocks build? | Owner | Due |
|---|---|---|---|

## Appendix
- RICE: Reach, Impact, Confidence, Effort, with the scale, the unit and the total.
- Contacts (named people).
- Glossary: link to `mantis/knowledge/glossary.md`; add only terms new to this page.
- Sources and change log.
