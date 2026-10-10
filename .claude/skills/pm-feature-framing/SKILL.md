---
name: pm-feature-framing
description: Frame a feature before writing about it, starting from the problem, not the request. Use when identifying a new feature, drafting a feature page or brief, filling a card's "Problem and outcome", deciding MVP scope, or prioritising features against each other.
---

# Feature framing

The output feeds `mantis/TEMPLATES/brief.md` and the card's "Problem and outcome" section.

## How deep to go

Match the depth to the decision, not to the template.

- **Routine edit or a page update:** skip this skill.
- **Already-approved commitment:** record who approved it (cited), the constraint, the outcome
  it is meant to bring and how it will be validated. Do not reopen discovery unless new evidence
  undercuts it; then say so once.
- **Mandatory, compliance or security work:** record the obligation and its source, the risk it
  addresses, and how completion is proven. No problem validation and no growth metric.
- **New initiative or a stakeholder request:** all the steps below.

## Steps

1. **Separate the request from the problem.** A request is evidence that someone wants
   something, not that the problem exists or that this solution fixes it. Record who asked for
   what, cited.
2. **Problem evidence, labelled.** Each claim is *Observed* (a source shows it happening: data,
   a ticket, a field visit, a user's own account), *Opinion* (someone believes it: name who) or
   *Unknown*. Cover who is affected, the job they are trying to do, what goes wrong, how often,
   how badly, and the cost of doing nothing. Never write pain, research findings or consensus
   that no source states. A problem with only opinions is not validated, however well written.
3. **Outcome.** The one change for users or the business this should bring, cited or marked
   *Proposed*. If you can't name one, say so: that is the finding.
4. **Options.** One or two other ways to reach the outcome, including doing nothing, a process
   change, an existing capability or a spreadsheet. Say why this one, or that another is better.
5. **Recommendation:** discover first, validate (a cheap test), build, defer or reject, with the
   uncertainty that could change it. When the problem is unclear, recommend focused discovery
   instead of an implementation-ready spec. Disagree with the request when the evidence says so;
   say it once, plainly, and leave the decision to the owner.
6. **Scope.** Set the appetite (how much it is worth), split jobs into MVP, Later and Out
   (no-gos), name the rabbit holes.
7. **Dependencies.** Check the map and feature cards: what must exist first?
8. **Next decision.** What has to be decided next, by whom, and what it needs first.

## Comparing features

Only when the owner is choosing between features: RICE (Reach × Impact × Confidence / Effort)
can help. Use it only with values from sources, or values marked *Proposed* with a reason for the
owner to confirm. Never invent scores to look rigorous; when the inputs are guesses, explain the
trade-off in words and name the assumption that would change the ranking.

Methods: opportunity solution tree, Teresa Torres (https://www.producttalk.org/opportunity-solution-trees/). Shape Up pitch: problem, appetite, solution, rabbit holes, no-gos (https://basecamp.com/shapeup/1.5-chapter-06). RICE, Intercom (https://www.intercom.com/blog/rice-simple-prioritization-for-product-managers/).
