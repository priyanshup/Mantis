---
feature: <feature slug, same as the card>
type: page
status: draft   # draft / review / published
updated: YYYY-MM-DD
---

<!-- Feature page (Confluence). A starting point, not a form: drop or merge sections that
don't help this feature. Rules: docs/rules/OUTPUTS_GUIDE.md. Reference: mantis/config/voice.md.
Each fact lives in one section. Status lives in the header line only. Plain words everywhere;
what only engineers need goes under Technical detail, never into the plain sections.
Each *Source:* line names sources in words the reader knows (a meeting, a page, a person),
never a Mantis ID or a file path. -->

# <Feature name>

**Status:** <stage> | **Product owner:** <name> | **Jira:** <KEY> | **Updated:** <date>

## At a glance

| | |
|---|---|
| Persona | <who, one line, as named in the personas register> |
| Problem | <one sentence> |
| Primary job | When <situation>, I want to <action>, so I can <outcome> |
| Hypothesis | If <change>, then <result>, measured by <primary metric> |
| Scope | MVP: <jobs>. Later: <jobs> |
| Decision needed | <what, from whom, by when> |

## Persona
*Source: <named in words>*
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

## Technical detail
*Source:*
For engineers: systems and integrations touched, data and its owner, non-functional needs
(volume, speed, security). Only what the plain sections leave out; drop the section if nothing.

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
The primary job first, then the numbered jobs, each marked MVP or Later. Acceptance criteria live
in the epic, not here.

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
- Glossary: only the terms new to this page, one line each.
- Sources and change log.
