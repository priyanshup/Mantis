---
name: pm-success-metrics
description: Plan how a feature's success is measured and reviewed after launch. Use when writing a card's "Measurement" or "Launch review" section, the metrics part of a feature page or brief, or when asked how to measure a feature.
---

# Success metrics

Shipping is not success. A feature succeeds when the outcome it was built for happens, and that
can only be known if it is measured. A metric earns its place by informing a decision; one that
changes nothing is noise.

## The plan (card section "Measurement")

1. Start from the outcome (pm-feature-framing). Write the **hypothesis**: if we change X, then Y
   happens, because Z.
2. Pick the HEART category that fits (Happiness, Engagement, Adoption, Retention, Task success),
   then go Goal → Signal (the behaviour that shows progress) → Metric (how we count it). Prefer
   behaviour over opinion. Never count outputs such as features shipped.
3. **One primary metric**, plus one or two **guardrails** (what must not get worse: support
   tickets, error rate, order value). Each gets, where it applies:
   - definition (what is counted, out of what), population, measurement window;
   - data source, and whether it is instrumented today (yes / no / unknown);
   - owner (who reads it);
   - baseline: a sourced value, or *Unknown* plus where to get it. **Never invent a baseline.**
     An unknown baseline does not block a valuable feature; plan the step that gets it.
   - target: a sourced value, or *Proposed* with its rationale, awaiting the owner. No false
     precision: a range or a direction is fine when that is all the evidence supports.
4. **Decision rule:** what result means scale, iterate, hold, investigate or roll back.
5. Check the metric can be measured with the tools in the knowledge base (the product analytics
   tool, the app database, reports). If it can't, say what instrumentation is missing.
6. **Proportionate:** a discovery-stage feature needs only the outcome and a candidate metric;
   a full plan is due before build. A small fix needs no plan.

**Mandatory, compliance, security or reliability work** has no growth metric. Record the
obligation (cited), the acceptance criteria and the evidence of completion (audit, test report,
sign-off), plus any risk-reduction measure that matters.

## After launch (card section "Launch review")

- Set `review_on` when the feature goes live: the date by which the effect should be visible in
  the data (enough users through the flow, a full ordering cycle, a season), not a fixed 30 days.
- On that date record the result with its source and date, what it means against the hypothesis
  and target, the decision taken (a decision entry), and follow-ups.
- No data is a finding, not a pass: write *Measurement gap* with why and how to close it.
- Never claim an outcome because the feature shipped.

Method: HEART and Goals-Signals-Metrics, Kerry Rodden, Google (https://www.productplan.com/glossary/heart-framework/).
